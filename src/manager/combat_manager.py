import os
import logging
import json
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple, Union, Set
from ..domain.models.entity import Entity, EntityType, DynamicToken
from ..domain.models.tile_map import TileMap
from ..domain.models.spell_template import SpellTemplate, SpellShape, AoEShape
from ..domain.rules.aoe_calculator import calculate_aoe_cells
from ..domain.models.fog_manager import FogManager
from ..domain.loaders.encounter_loader import EncounterLoader
from .grid_manager import GridManager

logger = logging.getLogger(__name__)


class CombatManager:
    """
    Motor central de gerenciamento de encontros de combate e turnos do Medusa VTT.
    Responsável por carregar o encontro, rolar e ordenar iniciativas com desempates (D&D 5E),
    gerenciar o ponteiro de turno ativo, rodadas, despachar dano/cura, visibilidade, posicionamento
    e projeção tática de áreas de efeito de feitiços (SpellTemplate).
    """

    def __init__(self, encounter_loader: Optional[EncounterLoader] = None) -> None:
        self._encounter_loader = encounter_loader or EncounterLoader()
        self.__encounter_uid: str = ""
        self.__title: str = "Encontro"
        self.__description: str = ""
        self.__map_type: str = "image"
        self.__map_source: Optional[str] = None
        self.__map_file: Optional[str] = None
        self.__tile_map: Optional[TileMap] = None
        self.__environment: Dict[str, Any] = {"is_sunlight": False, "is_raining": False}
        self.__grid_data: Dict[str, Any] = {"columns": 25, "feet_per_square": 5}
        self.__grid_manager: Optional[GridManager] = None

        self.__combatants: List[Entity] = []
        self.__turn_order: List[Entity] = []
        self.__hidden_combatants: Dict[str, Entity] = {}
        self.__current_turn_index: int = -1
        self.__round_number: int = 1

        # Projeção Tática de Áreas de Efeito de Feitiços (Spell AoE)
        self.__active_spell_template: Optional[SpellTemplate] = None

        # Gerenciador de Névoa de Guerra (Fog of War)
        self.__fog_manager: FogManager = FogManager()
        self.__fog_manager.add_listener(self.notify_listeners)

        self.__listeners: List[Callable[[], None]] = []

    # --- Properties ---

    @property
    def encounter_uid(self) -> str:
        return self.__encounter_uid

    @property
    def title(self) -> str:
        return self.__title

    @property
    def description(self) -> str:
        return self.__description

    @property
    def map_type(self) -> str:
        return self.__map_type

    @property
    def map_source(self) -> Optional[str]:
        return self.__map_source

    @property
    def map_file(self) -> Optional[str]:
        return self.__map_file

    @property
    def map_image_path(self) -> Optional[str]:
        """Alias para map_file."""
        return self.__map_file

    @property
    def tile_map(self) -> Optional[TileMap]:
        """Referência ao mapa modular ativo (TileMap), se houver."""
        return self.__tile_map

    @property
    def environment(self) -> Dict[str, Any]:
        return self.__environment.copy()

    @property
    def grid_data(self) -> Dict[str, Any]:
        return self.__grid_data.copy()

    @property
    def grid_manager(self) -> Optional[GridManager]:
        return self.__grid_manager

    @property
    def fog_manager(self) -> FogManager:
        """Gerenciador central de Névoa de Guerra (Fog of War)."""
        return self.__fog_manager

    @property
    def combatants(self) -> List[Entity]:
        """Retorna cópia defensiva da lista de todos os combatentes."""
        return list(self.__combatants)

    @property
    def hidden_combatants(self) -> Dict[str, Entity]:
        """Retorna cópia defensiva do mapa de combatentes latentes/ocultos fora da ordem de turnos."""
        return self.__hidden_combatants.copy()

    @property
    def turn_order(self) -> List[Entity]:
        """Retorna cópia defensiva da lista de turnos ativos ordenados por iniciativa (exclui ocultos)."""
        return list(self.__turn_order)

    @property
    def turn_order_uids(self) -> List[str]:
        """Retorna lista indexada de UIDs que compõem a ordem corrente de turnos ativos."""
        return [c.uid for c in self.__turn_order]

    @property
    def current_turn_index(self) -> int:
        return self.__current_turn_index

    @property
    def round_number(self) -> int:
        return self.__round_number

    @property
    def current_round(self) -> int:
        """Alias para round_number."""
        return self.__round_number

    @property
    def active_character(self) -> Optional[Entity]:
        """Retorna o combatente do turno ativo, ou None caso o combate não tenha iniciado."""
        if 0 <= self.__current_turn_index < len(self.__turn_order):
            return self.__turn_order[self.__current_turn_index]
        return None

    @property
    def has_combat_started(self) -> bool:
        return self.__current_turn_index >= 0 and len(self.__turn_order) > 0

    @property
    def active_spell_template(self) -> Optional[SpellTemplate]:
        """Template de área de efeito de feitiço ativo para projeção tática."""
        return self.__active_spell_template

    @active_spell_template.setter
    def active_spell_template(self, template: Optional[SpellTemplate]) -> None:
        self.__active_spell_template = template
        self.notify_listeners()

    # --- Observer / Notificação de Mudanças ---

    def add_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self.__listeners:
            self.__listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        if listener in self.__listeners:
            self.__listeners.remove(listener)

    def notify_listeners(self) -> None:
        for listener in list(self.__listeners):
            try:
                listener()
            except Exception as e:
                logger.error(f"Erro no listener {listener}: {e}")

    # --- Carregamento de Encontro e Mapa ---

    def set_tile_map(self, tile_map: Optional[TileMap]) -> None:
        """Define o mapa modular ativo e sincroniza a resolução do GridManager mantendo a grade tática independente."""
        self.__tile_map = tile_map
        if tile_map is not None:
            cols = self.__grid_data.get("columns") if bool(self.__encounter_uid) else tile_map.width
            if cols is None:
                cols = tile_map.width
            feet = self.__grid_data.get("feet_per_square", 5)
            self.__grid_manager = GridManager(
                map_width=float(tile_map.width * 32),
                map_height=float(tile_map.height * 32),
                columns=cols,
                feet_per_square=feet,
            )
            logger.info(
                f"TileMap configurado no CombatManager: '{tile_map.tileset_name}' "
                f"({tile_map.width}x{tile_map.height} tiles). Grade tática: {cols}x{self.__grid_manager.rows} células."
            )
        self.notify_listeners()

    def is_walkable(self, x: int, y: int) -> bool:
        """Verifica se a célula do grid tático (x, y) permite trânsito de entidades."""
        if self.__grid_manager is not None:
            if not self.__grid_manager.is_valid_cell(x, y):
                return False
            if self.__tile_map is not None:
                return self.__tile_map.is_walkable_at_grid(
                    x, y, self.__grid_manager.columns, self.__grid_manager.rows
                )
            return True
        if self.__tile_map is not None:
            return self.__tile_map.is_walkable(x, y)
        return True

    def is_walkable_for_size(self, col: int, row: int, size: Union[str, int, float] = 1) -> bool:
        """
        Verifica se todas as células sob o perímetro/footprint de uma criatura
        de tamanho especificado (1x1, 2x2, 3x3, 4x4) permitem passagem livre (is_walkable == True).
        """
        if self.__grid_manager is not None:
            cells = self.__grid_manager.get_creature_grid_cells(col, row, size)
            for c, r in cells:
                if not self.is_walkable(c, r):
                    return False
            return True
        return self.is_walkable(col, row)

    def is_walkable_for_entity(self, entity: Entity, col: int, row: int) -> bool:
        """Verifica se o espaço (col, row) é transitável para a entidade com base no seu tamanho."""
        size = getattr(entity, "size", "Medium")
        return self.is_walkable_for_size(col, row, size)

    def load_encounter(self, encounter_id_or_path: str) -> None:
        """Carrega dados do encontro, popula os combatentes e inicializa o GridManager."""
        data = self._encounter_loader.load_encounter(encounter_id_or_path)
        self.__encounter_uid = data["uid"]
        self.__title = data["title"]
        self.__description = data["description"]
        self.__map_type = data.get("map_type", "image")
        self.__map_source = data.get("map_source") or data.get("map_file")
        self.__map_file = self.__map_source
        self.__environment = data.get("environment", {"is_sunlight": False, "is_raining": False})
        self.__grid_data = data.get("grid", {"columns": 25, "feet_per_square": 5})

        cols = self.__grid_data.get("columns", 25)
        feet = self.__grid_data.get("feet_per_square", 5)

        # Carrega TileMap se map_type for tilemap ou se map_source for arquivo JSON
        self.__tile_map = None
        is_tilemap_type = (self.__map_type == "tilemap") or (
            self.__map_source and str(self.__map_source).lower().endswith(".json")
        )

        if is_tilemap_type and self.__map_source:
            try:
                self.__tile_map = TileMap.from_file(self.__map_source)
                self.__map_type = "tilemap"
                self.__grid_manager = GridManager(
                    map_width=float(self.__tile_map.width * 32),
                    map_height=float(self.__tile_map.height * 32),
                    columns=cols,
                    feet_per_square=feet,
                )
            except Exception as e:
                logger.warning(f"Não foi possível carregar TileMap a partir de '{self.__map_source}': {e}")
                self.__grid_manager = GridManager(
                    map_width=1920.0,
                    map_height=1080.0,
                    columns=cols,
                    feet_per_square=feet,
                )
        else:
            self.__map_type = "image"
            # Inicializa GridManager com dimensões padrão de tela (ajustadas dinamicamente quando a textura carrega)
            self.__grid_manager = GridManager(
                map_width=1920.0,
                map_height=1080.0,
                columns=cols,
                feet_per_square=feet,
            )

        self.__combatants = list(data["combatants"])
        self.__hidden_combatants = {c.uid: c for c in self.__combatants if c.is_hidden}
        # Inicialmente, a fila é a lista de combatentes ativos não ocultos
        self.__turn_order = [c for c in self.__combatants if not c.is_hidden]
        self.__current_turn_index = -1
        self.__round_number = 1

        # Carrega estado da Névoa de Guerra
        self.__fog_manager.load_state(data.get("fog_of_war", []))

        logger.info(
            f"Encontro carregado: '{self.__title}' ({self.__encounter_uid}) [tipo={self.__map_type}] com {len(self.__combatants)} combatentes "
            f"({len(self.__hidden_combatants)} ocultos) e {self.__fog_manager.count} células de névoa."
        )
        self.notify_listeners()

    def start_combat(self, combatants: Optional[List[Entity]] = None) -> None:
        """
        Inicializa formalmente o combate ativo:
        - Itera sobre os combatentes: se combatant.is_hidden (ou hidden), adiciona a self.__hidden_combatants
          e NÃO insere seu UID em self.__turn_order.
        - Define round_number = 1 e current_turn_index = 0 estritamente sobre os elementos válidos de self.__turn_order.
        - Notifica Observers conectados.
        """
        if combatants is not None:
            self.__combatants = list(combatants)

        self.__hidden_combatants.clear()
        active_combatants: List[Entity] = []

        for c in self.__combatants:
            if c.is_hidden:
                self.__hidden_combatants[c.uid] = c
            else:
                active_combatants.append(c)

        self.__turn_order = active_combatants
        if self.__turn_order:
            self.__current_turn_index = 0
            self.__round_number = 1
        else:
            self.__current_turn_index = -1
            self.__round_number = 1

        active_name = self.active_character.name if self.active_character else "Nenhum"
        logger.info(
            f"Combate iniciado com {len(self.__turn_order)} combatentes ativos "
            f"({len(self.__hidden_combatants)} ocultos). Turno ativo: '{active_name}' (Rodada {self.__round_number})."
        )
        self.notify_listeners()

    def update_grid_manager_dimensions(self, width: float, height: float) -> None:
        """Atualiza a resolução do mapa no GridManager preservando colunas e escala de pés."""
        cols = self.__grid_data.get("columns", 25)
        feet = self.__grid_data.get("feet_per_square", 5)
        self.__grid_manager = GridManager(
            map_width=width,
            map_height=height,
            columns=cols,
            feet_per_square=feet,
        )
        logger.debug(f"GridManager atualizado: {width}x{height} com {cols} colunas (cell_size={self.__grid_manager.cell_size:.2f}px).")


    # --- Staging de Iniciativas e Ordenação D&D 5E ---

    def generate_draft_initiatives(self) -> Dict[str, int]:
        """
        Rola 1d20 + DEX mod para cada participante revelado (não oculto) e devolve um dicionário temporário
        {combatant_uid: score} sem alterar o estado oficial de combate.
        Nenhum dado de iniciativa é rolado para combatentes ocultos (hidden == True).
        """
        draft: Dict[str, int] = {}
        for combatant in self.__combatants:
            if combatant.is_hidden:
                continue
            d20 = random.randint(1, 20)
            score = d20 + combatant.initiative_mod
            draft[combatant.uid] = score
        logger.debug(f"Draft de iniciativas gerado para {len(draft)} participantes revelados.")
        return draft

    def apply_initiatives(self, final_scores: Dict[str, int]) -> None:
        """
        Recebe o dicionário consolidado de iniciativas (UID ou Nome -> Score),
        atribui os valores às entidades ativas, aplica a ordenação com desempate do D&D 5E
        (Iniciativa -> Modificador DEX -> Nome), isola combatentes ocultos em hidden_combatants
        e notifica os Observers.
        """
        self.__hidden_combatants.clear()
        revealed_combatants: List[Entity] = []

        for combatant in self.__combatants:
            if combatant.is_hidden:
                self.__hidden_combatants[combatant.uid] = combatant
                continue

            if combatant.uid in final_scores:
                score = final_scores[combatant.uid]
            elif combatant.name in final_scores:
                score = final_scores[combatant.name]
            else:
                d20 = random.randint(1, 20)
                score = d20 + combatant.initiative_mod

            combatant.set_initiative(score)
            revealed_combatants.append(combatant)

        # Ordenação com critérios de desempate D&D 5E
        self.__turn_order = sorted(
            revealed_combatants,
            key=lambda c: (c.initiative_score, c.initiative_mod, c.name),
            reverse=True,
        )

        if self.__turn_order:
            self.__current_turn_index = 0
            self.__round_number = 1
        else:
            self.__current_turn_index = -1

        active_name = self.active_character.name if self.active_character else "Nenhum"
        logger.info(
            f"Iniciativas consolidadas e aplicadas para {len(self.__turn_order)} combatentes ativos "
            f"({len(self.__hidden_combatants)} ocultos). Turno ativo: '{active_name}' (Rodada {self.__round_number})."
        )
        self.notify_listeners()

    def roll_initiatives(self, manual_rolls: Optional[Dict[str, int]] = None) -> List[Entity]:
        """
        Rola e aplica iniciativas diretamente, permitindo overrides manuais via dicionário (UID ou Nome).
        Combatentes ocultos permanecem fora da rolagem e da fila de turnos.
        Mantém total compatibilidade e utiliza o pipeline oficial.
        """
        scores = self.generate_draft_initiatives()
        if manual_rolls:
            for combatant in self.__combatants:
                if combatant.is_hidden:
                    continue
                if combatant.uid in manual_rolls:
                    scores[combatant.uid] = manual_rolls[combatant.uid]
                elif combatant.name in manual_rolls:
                    scores[combatant.uid] = manual_rolls[combatant.name]
            # Também preserva quaisquer outras chaves passadas em manual_rolls
            for k, v in manual_rolls.items():
                if k not in scores:
                    scores[k] = v

        self.apply_initiatives(scores)
        return list(self.__turn_order)

    # --- Gerenciamento de Turnos ---

    def next_turn(self) -> Optional[Entity]:
        """
        Avança para o próximo participante válido (vivo com HP > 0) na fila de iniciativa de forma circular.
        Ao completar uma volta completa (índice 0), incrementa o número da rodada.
        Pula automaticamente combatentes mortos/incapacitados sem travamentos.
        """
        if not self.__turn_order:
            return None

        has_alive = any(c.is_alive and c.current_hp > 0 for c in self.__turn_order)
        if not has_alive:
            logger.info("Todos os combatentes estão mortos/incapacitados. Não há participantes válidos para avançar o turno.")
            self.notify_listeners()
            return None

        num_combatants = len(self.__turn_order)

        if self.__current_turn_index < 0:
            found_idx = -1
            for i, c in enumerate(self.__turn_order):
                if c.is_alive and c.current_hp > 0:
                    found_idx = i
                    break
            self.__current_turn_index = found_idx if found_idx >= 0 else 0
            self.__round_number = 1
        else:
            count = 0
            while count < num_combatants:
                self.__current_turn_index = (self.__current_turn_index + 1) % num_combatants
                if self.__current_turn_index == 0:
                    self.__round_number += 1
                candidate = self.__turn_order[self.__current_turn_index]
                if candidate.is_alive and candidate.current_hp > 0:
                    break
                count += 1

            if count >= num_combatants:
                logger.info("Todos os combatentes estão mortos/incapacitados. Turno não avançado.")
                self.notify_listeners()
                return None

        active_name = self.active_character.name if self.active_character else "Nenhum"
        logger.info(f"Passar Turno: combatente ativo '{active_name}' (Rodada {self.__round_number}).")
        self.notify_listeners()
        return self.active_character

    def previous_turn(self) -> Optional[Entity]:
        """Retrocede para o participante anterior válido (vivo com HP > 0) na fila de iniciativas."""
        if not self.__turn_order:
            return None

        has_alive = any(c.is_alive and c.current_hp > 0 for c in self.__turn_order)
        if not has_alive:
            logger.info("Todos os combatentes estão mortos/incapacitados. Turno não retrocedido.")
            self.notify_listeners()
            return None

        num_combatants = len(self.__turn_order)
        count = 0
        while count < num_combatants:
            if self.__current_turn_index <= 0:
                self.__current_turn_index = num_combatants - 1
                if self.__round_number > 1:
                    self.__round_number -= 1
            else:
                self.__current_turn_index -= 1
            candidate = self.__turn_order[self.__current_turn_index]
            if candidate.is_alive and candidate.current_hp > 0:
                break
            count += 1

        active_name = self.active_character.name if self.active_character else "Nenhum"
        logger.info(f"Retroceder Turno: combatente ativo '{active_name}' (Rodada {self.__round_number}).")
        self.notify_listeners()
        return self.active_character

    def set_turn_index(self, index: int) -> None:
        """Define o turno ativo diretamente por índice."""
        if 0 <= index < len(self.__turn_order):
            self.__current_turn_index = index
            self.notify_listeners()

    # --- Gerenciamento de Combatentes e Despachante de Dano/Cura ---

    def add_combatant(self, combatant: Entity) -> None:
        """Adiciona um combatente ao encontro e notifica ouvintes."""
        if combatant not in self.__combatants:
            self.__combatants.append(combatant)
            if combatant.is_hidden:
                self.__hidden_combatants[combatant.uid] = combatant
            elif combatant not in self.__turn_order:
                self.__turn_order.append(combatant)
            self.notify_listeners()

    def spawn_combatant(
        self,
        entity: Entity,
        position: Tuple[int, int],
        initiative_slot: str = "next",
    ) -> None:
        """
        Registra um novo combatente em tempo de execução, define sua posição
        no grid e insere seu UID na ordem de iniciativa corrente se visível.
        Suporta inserção dinâmica no slot 'next' (logo após o turno ativo) ou 'end' (final da rodada).
        """
        entity.set_position(position[0], position[1])
        if entity not in self.__combatants:
            self.__combatants.append(entity)

        if entity.is_hidden:
            self.__hidden_combatants[entity.uid] = entity
            if entity in self.__turn_order:
                old_idx = self.__turn_order.index(entity)
                self.__turn_order.pop(old_idx)
                if old_idx < self.__current_turn_index:
                    self.__current_turn_index -= 1
        else:
            self.__hidden_combatants.pop(entity.uid, None)
            if self.has_combat_started and self.__turn_order:
                if entity in self.__turn_order:
                    old_idx = self.__turn_order.index(entity)
                    self.__turn_order.pop(old_idx)
                    if old_idx < self.__current_turn_index:
                        self.__current_turn_index -= 1

                if initiative_slot == "next":
                    target_idx = self.__current_turn_index + 1
                    if target_idx > len(self.__turn_order):
                        target_idx = len(self.__turn_order)
                    self.__turn_order.insert(target_idx, entity)
                else:  # "end"
                    self.__turn_order.append(entity)
            else:
                if entity not in self.__turn_order:
                    if initiative_slot == "next" and self.__turn_order:
                        self.__turn_order.insert(0, entity)
                    else:
                        self.__turn_order.append(entity)

        etype_val = entity.entity_type.value if hasattr(entity, "entity_type") else "unknown"
        logger.info(
            f"Novo combatente spawnado no combate: '{entity.name}' (Tipo: {etype_val}) "
            f"na posição ({position[0]}, {position[1]}), slot de iniciativa: '{initiative_slot}' (hidden={entity.is_hidden})."
        )
        self.notify_listeners()

    def get_combatant(self, uid_or_name: str) -> Optional[Entity]:
        """Busca um combatente por UID ou Nome (em combatentes gerais ou repositório de ocultos)."""
        for c in self.__combatants:
            if c.uid == uid_or_name or c.name.lower() == uid_or_name.lower():
                return c
        if uid_or_name in self.__hidden_combatants:
            return self.__hidden_combatants[uid_or_name]
        return None

    def apply_damage(self, uid_or_name: str, amount: int) -> bool:
        """Aplica dano ao combatente identificado e notifica ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.take_damage(amount)
            logger.info(
                f"Dano aplicado: {amount} em {combatant.name} (HP: {combatant.current_hp}/{combatant.max_hp})"
            )
            self.notify_listeners()
            return True
        logger.warning(f"Combatente '{uid_or_name}' não encontrado para aplicar {amount} de dano.")
        return False

    def apply_heal(self, uid_or_name: str, amount: int) -> bool:
        """Aplica cura ao combatente identificado e notifica ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.heal(amount)
            logger.info(
                f"Cura aplicada: {amount} em {combatant.name} (HP: {combatant.current_hp}/{combatant.max_hp})"
            )
            self.notify_listeners()
            return True
        logger.warning(f"Combatente '{uid_or_name}' não encontrado para aplicar {amount} de cura.")
        return False

    # --- Visibilidade Tática e Movimentação no Grid ---

    def reveal_combatant(self, uid_or_name: str) -> Optional[Entity]:
        """
        Revela um combatente oculto (is_hidden = False), resgata de hidden_combatants
        e o insere na posição subsequente da fila de turnos em relação ao turno ativo:
          target_index = self.current_turn_index + 1
        Notifica os ouvintes (Observer Pattern) para sincronização imediata da DMWindow,
        PlayerWindow e InitiativeHUD.
        """
        combatant = self.get_combatant(uid_or_name)
        if combatant is None:
            logger.warning(f"Combatente '{uid_or_name}' não encontrado para revelação.")
            return None

        combatant.set_hidden(False)
        self.__hidden_combatants.pop(combatant.uid, None)

        if self.has_combat_started and self.__turn_order:
            if combatant in self.__turn_order:
                old_idx = self.__turn_order.index(combatant)
                if old_idx != self.__current_turn_index:
                    self.__turn_order.pop(old_idx)
                    if old_idx < self.__current_turn_index:
                        self.__current_turn_index -= 1
                    target_idx = self.__current_turn_index + 1
                    self.__turn_order.insert(target_idx, combatant)
            else:
                target_idx = self.__current_turn_index + 1
                if target_idx > len(self.__turn_order):
                    target_idx = len(self.__turn_order)
                self.__turn_order.insert(target_idx, combatant)
        elif combatant not in self.__turn_order:
            self.__turn_order.append(combatant)

        logger.info(
            f"Combatente '{combatant.name}' revelado com sucesso e posicionado como próximo a agir na fila de turnos."
        )
        self.notify_listeners()
        return combatant

    def toggle_combatant_visibility(self, uid_or_name: str) -> bool:
        """Alterna a visibilidade tática (is_hidden) de um combatente e sincroniza a ordem de turnos."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            if combatant.is_hidden:
                self.reveal_combatant(uid_or_name)
                return False
            else:
                self.set_combatant_visibility(uid_or_name, is_hidden=True)
                return True
        return False

    def set_combatant_visibility(self, uid_or_name: str, is_hidden: bool) -> bool:
        """Define explicitamente a visibilidade tática de um combatente e sincroniza a fila de turnos."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            if not is_hidden and combatant.is_hidden:
                self.reveal_combatant(uid_or_name)
            else:
                combatant.set_hidden(is_hidden)
                if is_hidden:
                    self.__hidden_combatants[combatant.uid] = combatant
                    if combatant in self.__turn_order:
                        old_idx = self.__turn_order.index(combatant)
                        self.__turn_order.pop(old_idx)
                        if self.has_combat_started:
                            if old_idx < self.__current_turn_index:
                                self.__current_turn_index -= 1
                            elif self.__current_turn_index >= len(self.__turn_order):
                                self.__current_turn_index = max(0, len(self.__turn_order) - 1) if self.__turn_order else -1
                else:
                    self.__hidden_combatants.pop(combatant.uid, None)
                status_desc = "Oculto" if is_hidden else "Visível"
                logger.info(f"Visibilidade definida: '{combatant.name}' is_hidden={is_hidden} ({status_desc}).")
                self.notify_listeners()
            return True
        return False

    def set_combatant_position(self, uid_or_name: str, x: int, y: int) -> bool:
        """Atualiza a posição do combatente no grid ou coordenadas de mundo com log."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            prev_pos = combatant.position
            combatant.set_position(x, y)
            logger.info(
                f"Movimento no Grid: '{combatant.name}' movido de ({prev_pos.get('x')}, {prev_pos.get('y')}) "
                f"para ({x}, {y})."
            )
            self.notify_listeners()
            return True
        return False

    def toggle_condition(self, uid_or_name: str, condition: str) -> bool:
        """
        Alterna uma condição no combatente (adiciona se ausente, remove se presente).
        Notifica os ouvintes (Observer Pattern) para sincronização instantânea.
        """
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            is_active = combatant.toggle_condition(condition)
            status_desc = "adicionada" if is_active else "removida"
            logger.info(
                f"Condição '{condition}' {status_desc} para combatente '{combatant.name}' "
                f"(Condições ativas: {list(combatant.conditions)})."
            )
            self.notify_listeners()
            return is_active
        return False

    def add_condition(self, uid_or_name: str, condition: str) -> bool:
        """Adiciona uma condição ao combatente e notifica os ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.add_condition(condition)
            logger.info(f"Condição '{condition}' adicionada a '{combatant.name}'.")
            self.notify_listeners()
            return True
        return False

    def remove_condition(self, uid_or_name: str, condition: str) -> bool:
        """Remove uma condição do combatente e notifica os ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.remove_condition(condition)
            logger.info(f"Condição '{condition}' removida de '{combatant.name}'.")
            self.notify_listeners()
            return True
        return False

    # --- Projeção Tática de Magias (Spell AoE Overlay) ---

    def set_spell_template(self, template: Optional[SpellTemplate]) -> None:
        """Define ou limpa o template de magia ativo e notifica os ouvintes."""
        self.__active_spell_template = template
        if template is not None:
            logger.info(
                f"Template de magia configurado: shape={template.shape.value} "
                f"size={template.size_feet}ft width={template.width_feet}ft "
                f"active={template.is_active} rot={template.rotation_degrees:.1f}°."
            )
        else:
            logger.info("Template de magia desativado.")
        self.notify_listeners()

    def update_spell_origin(self, world_x: float, world_y: float) -> None:
        """Atualiza a posição de origem da magia no espaço de mundo contínuo e notifica ouvintes."""
        if self.__active_spell_template is not None:
            self.__active_spell_template = self.__active_spell_template.with_origin((world_x, world_y))
            self.__active_spell_template = self.__active_spell_template.with_visibility(True)
            self.notify_listeners()

    def rotate_spell(self, delta_degrees: float) -> None:
        """Incrementa/decrementa o ângulo de rotação horizontal (yaw) da magia em passos angulares com wrap-around."""
        if self.__active_spell_template is not None:
            new_rot = (self.__active_spell_template.rotation_degrees + delta_degrees) % 360.0
            self.__active_spell_template = self.__active_spell_template.with_rotation(new_rot)
            logger.debug(f"Rotação da magia ajustada: {self.__active_spell_template.rotation_degrees:.1f}°")
            self.notify_listeners()

    def set_spell_pitch(self, pitch_degrees: float) -> None:
        """Define a inclinação vertical (pitch) da magia e notifica ouvintes."""
        if self.__active_spell_template is not None:
            self.__active_spell_template = self.__active_spell_template.with_pitch(pitch_degrees)
            logger.debug(f"Pitch da magia ajustado: {self.__active_spell_template.pitch_degrees:.1f}°")
            self.notify_listeners()

    def adjust_spell_pitch(self, delta_degrees: float) -> None:
        """Incrementa/decrementa a inclinação vertical (pitch) da magia."""
        if self.__active_spell_template is not None:
            new_pitch = (self.__active_spell_template.pitch_degrees + delta_degrees) % 360.0
            self.__active_spell_template = self.__active_spell_template.with_pitch(new_pitch)
            logger.debug(f"Pitch da magia ajustado: {self.__active_spell_template.pitch_degrees:.1f}°")
            self.notify_listeners()

    def set_spell_origin_z(self, z_feet: float) -> None:
        """Define a altitude de origem Z da magia em pés e notifica ouvintes."""
        if self.__active_spell_template is not None:
            self.__active_spell_template = self.__active_spell_template.with_origin_z(z_feet)
            logger.debug(f"Altitude Z da magia ajustada: {self.__active_spell_template.origin_z_feet:.1f}ft")
            self.notify_listeners()

    def adjust_spell_origin_z(self, delta_feet: float) -> None:
        """Incrementa/decrementa a altitude de origem Z da magia em pés."""
        if self.__active_spell_template is not None:
            new_z = max(0.0, self.__active_spell_template.origin_z_feet + delta_feet)
            self.__active_spell_template = self.__active_spell_template.with_origin_z(new_z)
            logger.debug(f"Altitude Z da magia ajustada: {self.__active_spell_template.origin_z_feet:.1f}ft")
            self.notify_listeners()

    def get_spell_aoe_cells(self) -> Set[Tuple[int, int]]:
        """Retorna o conjunto de células matriciais (col, row) atingidas pela magia ativa."""
        if self.__active_spell_template is None or not self.__active_spell_template.is_active:
            return set()
        return calculate_aoe_cells(self.__active_spell_template, self.__grid_manager, self.__tile_map)

    def toggle_spell_active(self, is_active: Optional[bool] = None) -> bool:
        """Alterna ou define o estado de ativação da projeção de magia."""
        if self.__active_spell_template is not None:
            new_active = not self.__active_spell_template.is_active if is_active is None else bool(is_active)
            self.__active_spell_template = self.__active_spell_template.with_active(new_active)
            logger.info(f"Projeção de magia: is_active={new_active}")
            self.notify_listeners()
            return new_active
        else:
            # Inicializa um template padrão baseado no grid ativo
            feet = float(self.__grid_data.get("feet_per_square", 5.0))
            self.__active_spell_template = SpellTemplate(
                shape=AoEShape.CIRCLE,
                size_feet=feet * 4.0,
                width_feet=feet,
                rotation_degrees=0.0,
                origin_world=(0.0, 0.0),
                origin_z_feet=0.0,
                pitch_degrees=0.0,
                is_active=True,
                is_visible=True,
            )
            logger.info("Template padrão de magia inicializado e ativado.")
            self.notify_listeners()
            return True

    def set_spell_visibility(self, is_visible: bool) -> None:
        """Define a visibilidade temporária da projeção de magia (ex: mouse saiu do minimapa)."""
        if self.__active_spell_template is not None and self.__active_spell_template.is_visible != is_visible:
            self.__active_spell_template = self.__active_spell_template.with_visibility(is_visible)
            self.notify_listeners()

    # --- Encerramento e Reset de Combate ---

    def reset_combat(self) -> None:
        """
        Reseta o estado do combate: limpa combatentes ativos, fila de iniciativas,
        ponteiro de turnos, rodadas, referências de mapa, GridManager e SpellTemplate.
        Notifica todos os Observers conectados.
        """
        enc_title = self.__title
        enc_uid = self.__encounter_uid
        logger.info(f"Resetando estado de combate do encontro: '{enc_title}' ({enc_uid}).")

        self.__encounter_uid = ""
        self.__title = "Encontro"
        self.__description = ""
        self.__map_type = "image"
        self.__map_source = None
        self.__map_file = None
        self.__tile_map = None
        self.__environment = {"is_sunlight": False, "is_raining": False}
        self.__grid_data = {"columns": 25, "feet_per_square": 5}
        self.__grid_manager = None
        self.__active_spell_template = None

        self.__combatants.clear()
        self.__turn_order.clear()
        self.__hidden_combatants.clear()
        self.__current_turn_index = -1
        self.__round_number = 1
        self.__fog_manager.clear_all()

        logger.info("Estado do CombatManager resetado com sucesso.")
        self.notify_listeners()

    def save_fog_to_encounter_file(self) -> bool:
        """
        Persiste o estado atual da névoa de guerra diretamente no arquivo JSON do encontro ativo em disco.
        Retorna True em caso de sucesso.
        """
        if not self.__encounter_uid:
            logger.warning("Não há encontro ativo carregado para salvar a névoa de guerra.")
            return False

        try:
            resolved_path = self._encounter_loader.resolve_encounter_path(self.__encounter_uid)
            if resolved_path is None or not resolved_path.is_file():
                logger.error(f"Arquivo do encontro '{self.__encounter_uid}' não foi encontrado para salvar a névoa.")
                return False

            import json
            with open(resolved_path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)

            raw_json["fog_of_war"] = self.__fog_manager.export_state()

            with open(resolved_path, "w", encoding="utf-8") as f:
                json.dump(raw_json, f, indent=4, ensure_ascii=False)

            logger.info(
                f"Névoa de guerra ({self.__fog_manager.count} células) salva com sucesso em '{resolved_path.name}'."
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao persistir névoa de guerra no arquivo do encontro '{self.__encounter_uid}': {e}")
            return False

    def clear_combat(self) -> None:
        """Alias para reset_combat()."""
        self.reset_combat()

    # --- Persistência e Save State de Combate ---

    def get_save_path(self, encounter_uid: Optional[str] = None) -> Path:
        """
        Retorna o caminho canônico do snapshot de combate em creations/encounters/saves/{uid}_save.json,
        garantindo a existência do diretório de destino.
        """
        target_uid = encounter_uid or self.__encounter_uid
        if not target_uid:
            target_uid = "unknown_encounter"
        uid_stem = Path(target_uid).stem
        if uid_stem.endswith("_save"):
            uid_stem = uid_stem[:-5]

        saves_dir = Path("creations/encounters/saves")
        saves_dir.mkdir(parents=True, exist_ok=True)
        return saves_dir / f"{uid_stem}_save.json"

    def has_save_state(self, encounter_uid: Optional[str] = None) -> bool:
        """
        Verifica a existência física do arquivo de snapshot de combate correspondente.
        """
        target_uid = encounter_uid or self.__encounter_uid
        if not target_uid:
            return False
        save_path = self.get_save_path(target_uid)
        return save_path.is_file()

    def save_combat_state(self, encounter_uid: Optional[str] = None) -> bool:
        """
        Captura o turno ativo (current_turn_index), rodada atual (round_number), ordem de iniciativa
        calculada (turn_order), estado atual da névoa de guerra via FogManager.export_state() e snapshot
        individual de cada entidade instanciada (HP atual, condições ativas, posição no grid e status hidden).
        Grava o JSON em creations/encounters/saves/{encounter_uid}_save.json com encoding UTF-8.
        """
        target_uid = encounter_uid or self.__encounter_uid
        if not target_uid:
            logger.warning("Nenhum encontro ativo carregado para salvar o estado de combate.")
            return False

        try:
            save_path = self.get_save_path(target_uid)

            turn_order_uids = [c.uid for c in self.__turn_order if not c.is_hidden]
            hidden_combatants_uids = list(self.__hidden_combatants.keys())
            combatants_state = []
            for c in self.__combatants:
                etype_str = c.entity_type.value if hasattr(c, "entity_type") else ("player" if getattr(c, "is_player", False) else "monster")
                combatants_state.append({
                    "uid": c.uid,
                    "name": c.name,
                    "is_alive": c.is_alive,
                    "current_hp": c.current_hp,
                    "max_hp": c.max_hp,
                    "armor_class": c.armor_class,
                    "entity_type": etype_str,
                    "token_sprite": getattr(c, "token_sprite", None),
                    "size": getattr(c, "size", "Medium"),
                    "conditions": list(c.conditions),
                    "position": c.position,
                    "hidden": c.is_hidden,
                })

            snapshot = {
                "encounter_uid": target_uid,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "round": self.__round_number,
                "current_turn_index": self.__current_turn_index,
                "turn_order": turn_order_uids,
                "hidden_combatants": hidden_combatants_uids,
                "fog_of_war": self.__fog_manager.export_state(),
                "combatants_state": combatants_state,
            }

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=4, ensure_ascii=False)

            logger.info(
                f"Estado de combate salvo com sucesso em '{save_path}' (Rodada {self.__round_number}, "
                f"Turno {self.__current_turn_index}, {len(combatants_state)} combatentes, "
                f"{len(hidden_combatants_uids)} ocultos, {self.__fog_manager.count} células de névoa)."
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar estado de combate do encontro '{target_uid}': {e}")
            return False

    def load_combat_state(self, encounter_uid: Optional[str] = None) -> bool:
        """
        Restaura uma sessão de combate salva a partir de creations/encounters/saves/{encounter_uid}_save.json:
        - Reconstrói a rodada, o combatente ativo e a fita de turnos na ordem exata salva.
        - Atualiza as instâncias de entidades com o current_hp, condições, posições (x, y) e visibilidade gravadas.
        - Recria dinamicamente tokens inseridos no meio do combate (Mid-Combat Token Spawning).
        - Segrega combatentes ocultos em hidden_combatants e restaura turn_order exclusivamente com combatentes revelados.
        - Sincroniza o FogManager com o array 'fog_of_war' do save.
        - Notifica a PlayerWindow e a DMWindow via Padrão Observer para renderização imediata.
        """
        target_uid = encounter_uid or self.__encounter_uid
        if not target_uid:
            # Se não houver UID definido, tenta encontrar o save mais recente na pasta de saves
            saves_dir = Path("creations/encounters/saves")
            if saves_dir.is_dir():
                save_files = sorted(saves_dir.glob("*_save.json"), key=os.path.getmtime, reverse=True)
                if save_files:
                    target_uid = save_files[0].stem.replace("_save", "")
            if not target_uid:
                logger.warning("UID do encontro não fornecido e nenhum save encontrado para carregar estado de combate.")
                return False

        save_path = self.get_save_path(target_uid)
        if not save_path.is_file():
            logger.error(f"Arquivo de save de combate '{save_path}' não foi encontrado.")
            return False

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                save_data = json.load(f)

            # 1. Carrega o encontro base para garantir instanciação dos templates e configuração de mapa/grid
            base_uid = save_data.get("encounter_uid", encounter_uid)
            self.load_encounter(base_uid)

            # 2. Restaura Rodada e Índice de Turno
            self.__round_number = int(save_data.get("round", 1))
            self.__current_turn_index = int(save_data.get("current_turn_index", -1))

            # 3. Restaura Estado e Atributos de Cada Combatente
            existing_by_uid = {c.uid: c for c in self.__combatants}
            existing_by_name = {c.name.lower(): c for c in self.__combatants}

            combatants_by_uid: Dict[str, Entity] = {}
            for c_state in save_data.get("combatants_state", []):
                uid = c_state.get("uid")
                name = c_state.get("name")
                c: Optional[Entity] = None

                if uid and uid in existing_by_uid:
                    c = existing_by_uid[uid]
                elif name and name.lower() in existing_by_name:
                    c = existing_by_name[name.lower()]
                    if uid:
                        c.set_uid(uid)
                else:
                    # Entidade dinâmica spawnada no meio do combate (Mid-Combat Token Spawn)
                    etype_val = c_state.get("entity_type", "neutral")
                    max_hp_val = int(c_state.get("max_hp", 1))
                    ac_val = int(c_state.get("armor_class", 10))
                    token_sprite_val = c_state.get("token_sprite")
                    c = DynamicToken(
                        name=name or "Token",
                        max_hp=max_hp_val,
                        armor_class=ac_val,
                        uid=uid,
                        entity_type=etype_val,
                        token_sprite=token_sprite_val,
                    )
                    self.__combatants.append(c)
                    if uid:
                        existing_by_uid[uid] = c

                if c is not None:
                    combatants_by_uid[c.uid] = c

                    # HP e Vitalidade
                    if "max_hp" in c_state:
                        c.set_max_hp(int(c_state["max_hp"]))
                    if "current_hp" in c_state:
                        hp = int(c_state["current_hp"])
                        c.set_current_hp(hp)
                        if hp <= 0 or not c_state.get("is_alive", True):
                            c.die()

                    # Condições
                    if "conditions" in c_state:
                        for cond in c.conditions:
                            c.remove_condition(cond)
                        for cond in c_state["conditions"]:
                            c.add_condition(cond)

                    # Posição no Grid
                    if "position" in c_state:
                        pos = c_state["position"]
                        if isinstance(pos, dict):
                            px = int(pos.get("x", pos.get("col", 0)))
                            py = int(pos.get("y", pos.get("row", 0)))
                            c.set_position(px, py)

                    # Visibilidade Tática
                    if "hidden" in c_state:
                        c.set_hidden(bool(c_state["hidden"]))
                    elif "is_hidden" in c_state:
                        c.set_hidden(bool(c_state["is_hidden"]))

            # Reconstrói repositório de combatentes ocultos
            self.__hidden_combatants = {c.uid: c for c in self.__combatants if c.is_hidden}

            # 4. Reconstrói a Ordem Exata de Turnos (Fita de Iniciativas) contendo exclusivamente entidades não ocultas
            saved_turn_order_uids = save_data.get("turn_order", [])
            reordered: List[Entity] = []
            if saved_turn_order_uids:
                for uid in saved_turn_order_uids:
                    if uid in combatants_by_uid:
                        ent = combatants_by_uid[uid]
                        if not ent.is_hidden:
                            reordered.append(ent)

            # Combatentes ativos/visíveis que não constam na lista salva são mantidos ao final
            for c in self.__combatants:
                if not c.is_hidden and c not in reordered:
                    reordered.append(c)

            self.__turn_order = reordered

            # 5. Sincroniza a Névoa de Guerra (FogManager)
            self.__fog_manager.load_state(save_data.get("fog_of_war", []))

            active_name = self.active_character.name if self.active_character else "Nenhum"
            logger.info(
                f"Estado de combate restaurado com sucesso de '{save_path.name}': "
                f"Rodada {self.__round_number}, Turno Ativo: '{active_name}' (índice {self.__current_turn_index}), "
                f"{len(self.__combatants)} combatentes, {self.__fog_manager.count} células de névoa."
            )

            # 6. Notifica Observers para renderização imediata
            self.notify_listeners()
            return True

        except Exception as e:
            logger.error(f"Erro ao carregar estado de combate a partir de '{save_path}': {e}")
            return False

    def delete_save_state(self, encounter_uid: Optional[str] = None) -> None:
        """
        Remove com segurança o arquivo de snapshot de combate correspondente do disco.
        """
        target_uid = encounter_uid or self.__encounter_uid
        if not target_uid:
            logger.warning("UID do encontro não fornecido para exclusão do save.")
            return

        try:
            save_path = self.get_save_path(target_uid)
            if save_path.is_file():
                save_path.unlink(missing_ok=True)
                logger.info(f"Arquivo de save de combate excluído com sucesso: '{save_path}'.")
            else:
                logger.debug(f"Nenhum arquivo de save encontrado para exclusão em '{save_path}'.")
        except Exception as e:
            logger.error(f"Erro ao excluir arquivo de save de combate para '{target_uid}': {e}")



