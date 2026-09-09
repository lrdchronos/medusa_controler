import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple, Union, Set
from ..domain.models.entity import Entity, EntityType, DynamicToken
from ..domain.models.tile_map import TileMap
from ..domain.models.spell_template import SpellTemplate, SpellShape, AoEShape
from ..domain.rules.initiative_tracker import InitiativeTracker
from ..domain.rules.combat_serializer import CombatStateSerializer
from ..domain.rules.combatant_rules import CombatantRules
from ..domain.rules.spell_projection_controller import SpellProjectionController
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
                logger.error("Erro no listener %s: %s", listener, e)

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
                "TileMap configurado no CombatManager: '%s' (%dx%d tiles). Grade tática: %dx%d células.",
                tile_map.tileset_name,
                tile_map.width,
                tile_map.height,
                cols,
                self.__grid_manager.rows,
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
                logger.warning("Não foi possível carregar TileMap a partir de '%s': %s", self.__map_source, e)
                self.__grid_manager = GridManager(
                    map_width=1920.0,
                    map_height=1080.0,
                    columns=cols,
                    feet_per_square=feet,
                )
        else:
            self.__map_type = "image"
            self.__grid_manager = GridManager(
                map_width=1920.0,
                map_height=1080.0,
                columns=cols,
                feet_per_square=feet,
            )

        self.__combatants = list(data["combatants"])
        self.__hidden_combatants = {c.uid: c for c in self.__combatants if c.is_hidden}
        self.__turn_order = [c for c in self.__combatants if not c.is_hidden]
        self.__current_turn_index = -1
        self.__round_number = 1

        self.__fog_manager.load_state(data.get("fog_of_war", []))

        logger.info(
            "Encontro carregado: '%s' (%s) [tipo=%s] com %d combatentes (%d ocultos) e %d células de névoa.",
            self.__title,
            self.__encounter_uid,
            self.__map_type,
            len(self.__combatants),
            len(self.__hidden_combatants),
            self.__fog_manager.count,
        )
        self.notify_listeners()

    def start_combat(self, combatants: Optional[List[Entity]] = None) -> None:
        """Inicializa formalmente o combate ativo."""
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
            "Combate iniciado com %d combatentes ativos (%d ocultos). Turno ativo: '%s' (Rodada %d).",
            len(self.__turn_order),
            len(self.__hidden_combatants),
            active_name,
            self.__round_number,
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
        logger.debug(
            "GridManager atualizado: %fx%f com %d colunas (cell_size=%.2fpx).",
            width,
            height,
            cols,
            self.__grid_manager.cell_size,
        )

    # --- Staging de Iniciativas e Ordenação D&D 5E ---

    def generate_draft_initiatives(self) -> Dict[str, int]:
        """Rola 1d20 + DEX mod para cada participante revelado."""
        return InitiativeTracker.generate_draft_initiatives(self.__combatants)

    def apply_initiatives(self, final_scores: Dict[str, int]) -> None:
        """Aplica iniciativas, ordena com desempates 5E e isola ocultos."""
        self.__turn_order, self.__hidden_combatants = InitiativeTracker.calculate_turn_order(
            self.__combatants, final_scores
        )

        if self.__turn_order:
            self.__current_turn_index = 0
            self.__round_number = 1
        else:
            self.__current_turn_index = -1

        active_name = self.active_character.name if self.active_character else "Nenhum"
        logger.info(
            "Iniciativas consolidadas e aplicadas para %d combatentes ativos (%d ocultos). Turno ativo: '%s' (Rodada %d).",
            len(self.__turn_order),
            len(self.__hidden_combatants),
            active_name,
            self.__round_number,
        )
        self.notify_listeners()

    def roll_initiatives(self, manual_rolls: Optional[Dict[str, int]] = None) -> List[Entity]:
        """Rola e aplica iniciativas diretamente."""
        scores = self.generate_draft_initiatives()
        if manual_rolls:
            for combatant in self.__combatants:
                if combatant.is_hidden:
                    continue
                if combatant.uid in manual_rolls:
                    scores[combatant.uid] = manual_rolls[combatant.uid]
                elif combatant.name in manual_rolls:
                    scores[combatant.uid] = manual_rolls[combatant.name]
            for k, v in manual_rolls.items():
                if k not in scores:
                    scores[k] = v

        self.apply_initiatives(scores)
        return list(self.__turn_order)

    # --- Gerenciamento de Turnos ---

    def next_turn(self) -> Optional[Entity]:
        """Avança para o próximo participante válido na fila de iniciativa."""
        prev_idx = self.__current_turn_index
        self.__current_turn_index, self.__round_number, active_char = InitiativeTracker.advance_turn(
            self.__turn_order, self.__current_turn_index, self.__round_number
        )
        if self.__current_turn_index != prev_idx:
            active_name = active_char.name if active_char else "Nenhum"
            logger.info("Passar Turno: combatente ativo '%s' (Rodada %d).", active_name, self.__round_number)
        self.notify_listeners()
        return active_char

    def previous_turn(self) -> Optional[Entity]:
        """Retrocede para o participante anterior válido na fila de iniciativas."""
        prev_idx = self.__current_turn_index
        self.__current_turn_index, self.__round_number, active_char = InitiativeTracker.rewind_turn(
            self.__turn_order, self.__current_turn_index, self.__round_number
        )
        if self.__current_turn_index != prev_idx:
            active_name = active_char.name if active_char else "Nenhum"
            logger.info("Retroceder Turno: combatente ativo '%s' (Rodada %d).", active_name, self.__round_number)
        self.notify_listeners()
        return active_char

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
        """Registra um novo combatente em tempo de execução."""
        self.__current_turn_index = CombatantRules.spawn_combatant(
            self.__combatants,
            self.__turn_order,
            self.__hidden_combatants,
            self.__current_turn_index,
            self.has_combat_started,
            entity,
            position,
            initiative_slot,
        )
        self.notify_listeners()

    def get_combatant(self, uid_or_name: str) -> Optional[Entity]:
        """Busca um combatente por UID ou Nome."""
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
            logger.info("Dano aplicado: %d em %s (HP: %d/%d)", amount, combatant.name, combatant.current_hp, combatant.max_hp)
            self.notify_listeners()
            return True
        logger.warning("Combatente '%s' não encontrado para aplicar %d de dano.", uid_or_name, amount)
        return False

    def apply_heal(self, uid_or_name: str, amount: int) -> bool:
        """Aplica cura ao combatente identificado e notifica ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.heal(amount)
            logger.info("Cura aplicada: %d em %s (HP: %d/%d)", amount, combatant.name, combatant.current_hp, combatant.max_hp)
            self.notify_listeners()
            return True
        logger.warning("Combatente '%s' não encontrado para aplicar %d de cura.", uid_or_name, amount)
        return False

    # --- Visibilidade Tática e Movimentação no Grid ---

    def reveal_combatant(self, uid_or_name: str) -> Optional[Entity]:
        """Revela um combatente oculto e o insere na fila de turnos."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is None:
            logger.warning("Combatente '%s' não encontrado para revelação.", uid_or_name)
            return None

        self.__current_turn_index = CombatantRules.reveal_combatant(
            combatant,
            self.__turn_order,
            self.__hidden_combatants,
            self.__current_turn_index,
            self.has_combat_started,
        )
        self.notify_listeners()
        return combatant

    def toggle_combatant_visibility(self, uid_or_name: str) -> bool:
        """Alterna a visibilidade tática (is_hidden) de um combatente."""
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
        """Define explicitamente a visibilidade tática de um combatente."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            self.__current_turn_index = CombatantRules.set_combatant_visibility(
                combatant,
                self.__turn_order,
                self.__hidden_combatants,
                self.__current_turn_index,
                self.has_combat_started,
                is_hidden,
            )
            self.notify_listeners()
            return True
        return False

    def set_combatant_position(self, uid_or_name: str, x: int, y: int) -> bool:
        """Atualiza a posição do combatente no grid."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            prev_pos = combatant.position
            combatant.set_position(x, y)
            logger.info("Movimento no Grid: '%s' movido de (%s, %s) para (%d, %d).", combatant.name, prev_pos.get('x'), prev_pos.get('y'), x, y)
            self.notify_listeners()
            return True
        return False

    def toggle_condition(self, uid_or_name: str, condition: str) -> bool:
        """Alterna uma condição no combatente."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            is_active = combatant.toggle_condition(condition)
            status_desc = "adicionada" if is_active else "removida"
            logger.info("Condição '%s' %s para combatente '%s' (Condições ativas: %s).", condition, status_desc, combatant.name, list(combatant.conditions))
            self.notify_listeners()
            return is_active
        return False

    def add_condition(self, uid_or_name: str, condition: str) -> bool:
        """Adiciona uma condição ao combatente."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.add_condition(condition)
            logger.info("Condição '%s' adicionada a '%s'.", condition, combatant.name)
            self.notify_listeners()
            return True
        return False

    def remove_condition(self, uid_or_name: str, condition: str) -> bool:
        """Remove uma condição do combatente."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.remove_condition(condition)
            logger.info("Condição '%s' removida de '%s'.", condition, combatant.name)
            self.notify_listeners()
            return True
        return False

    # --- Projeção Tática de Magias (Spell AoE Overlay) ---

    def set_spell_template(self, template: Optional[SpellTemplate]) -> None:
        """Define ou limpa o template de magia ativo."""
        self.__active_spell_template = template
        if template is not None:
            logger.info(
                "Template de magia configurado: shape=%s size=%fft width=%fft active=%s rot=%.1f°.",
                template.shape.value,
                template.size_feet,
                template.width_feet,
                template.is_active,
                template.rotation_degrees,
            )
        else:
            logger.info("Template de magia desativado.")
        self.notify_listeners()

    def update_spell_origin(self, world_x: float, world_y: float) -> None:
        """Atualiza a posição de origem da magia no espaço de mundo contínuo."""
        updated = SpellProjectionController.update_origin(self.__active_spell_template, world_x, world_y)
        if updated is not None:
            self.__active_spell_template = updated
            self.notify_listeners()

    def rotate_spell(self, delta_degrees: float) -> None:
        """Incrementa/decrementa o ângulo de rotação horizontal (yaw) da magia."""
        updated = SpellProjectionController.rotate_spell(self.__active_spell_template, delta_degrees)
        if updated is not None:
            self.__active_spell_template = updated
            self.notify_listeners()

    def set_spell_pitch(self, pitch_degrees: float) -> None:
        """Define a inclinação vertical (pitch) da magia."""
        updated = SpellProjectionController.set_pitch(self.__active_spell_template, pitch_degrees)
        if updated is not None:
            self.__active_spell_template = updated
            self.notify_listeners()

    def adjust_spell_pitch(self, delta_degrees: float) -> None:
        """Incrementa/decrementa a inclinação vertical (pitch) da magia."""
        updated = SpellProjectionController.adjust_pitch(self.__active_spell_template, delta_degrees)
        if updated is not None:
            self.__active_spell_template = updated
            self.notify_listeners()

    def set_spell_origin_z(self, z_feet: float) -> None:
        """Define a altitude de origem Z da magia em pés."""
        updated = SpellProjectionController.set_origin_z(self.__active_spell_template, z_feet)
        if updated is not None:
            self.__active_spell_template = updated
            self.notify_listeners()

    def adjust_spell_origin_z(self, delta_feet: float) -> None:
        """Incrementa/decrementa a altitude de origem Z da magia em pés."""
        updated = SpellProjectionController.adjust_origin_z(self.__active_spell_template, delta_feet)
        if updated is not None:
            self.__active_spell_template = updated
            self.notify_listeners()

    def get_spell_aoe_cells(self) -> Set[Tuple[int, int]]:
        """Retorna o conjunto de células matriciais atingidas pela magia ativa."""
        return SpellProjectionController.get_aoe_cells(
            self.__active_spell_template, self.__grid_manager, self.__tile_map
        )

    def toggle_spell_active(self, is_active: Optional[bool] = None) -> bool:
        """Alterna ou define o estado de ativação da projeção de magia."""
        feet = float(self.__grid_data.get("feet_per_square", 5.0))
        self.__active_spell_template, new_active = SpellProjectionController.toggle_active(
            self.__active_spell_template, is_active, feet
        )
        self.notify_listeners()
        return new_active

    def set_spell_visibility(self, is_visible: bool) -> None:
        """Define a visibilidade temporária da projeção de magia."""
        if self.__active_spell_template is not None and self.__active_spell_template.is_visible != is_visible:
            self.__active_spell_template = self.__active_spell_template.with_visibility(is_visible)
            self.notify_listeners()

    # --- Encerramento e Reset de Combate ---

    def reset_combat(self) -> None:
        """Reseta o estado de combate."""
        logger.info("Resetando estado de combate do encontro: '%s' (%s).", self.__title, self.__encounter_uid)

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

    def clear_combat(self) -> None:
        """Alias para reset_combat()."""
        self.reset_combat()

    def save_fog_to_encounter_file(self) -> bool:
        """Persiste o estado atual da névoa de guerra diretamente no arquivo JSON do encontro ativo."""
        if not self.__encounter_uid:
            logger.warning("Não há encontro ativo carregado para salvar a névoa de guerra.")
            return False

        try:
            resolved_path = self._encounter_loader.resolve_encounter_path(self.__encounter_uid)
            if resolved_path is None or not resolved_path.is_file():
                logger.error("Arquivo do encontro '%s' não foi encontrado para salvar a névoa.", self.__encounter_uid)
                return False

            with open(resolved_path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)

            raw_json["fog_of_war"] = self.__fog_manager.export_state()

            with open(resolved_path, "w", encoding="utf-8") as f:
                json.dump(raw_json, f, indent=4, ensure_ascii=False)

            logger.info(
                "Névoa de guerra (%d células) salva com sucesso em '%s'.",
                self.__fog_manager.count,
                resolved_path.name,
            )
            return True
        except Exception as e:
            logger.error("Erro ao persistir névoa de guerra no arquivo do encontro '%s': %s", self.__encounter_uid, e)
            return False

    # --- Persistência e Save State de Combate ---

    def get_save_path(self, encounter_uid: Optional[str] = None) -> Path:
        """Retorna o caminho canônico do snapshot de combate."""
        target_uid = encounter_uid or self.__encounter_uid
        return CombatStateSerializer.get_save_path(target_uid)

    def has_save_state(self, encounter_uid: Optional[str] = None) -> bool:
        """Verifica a existência física do arquivo de snapshot de combate correspondente."""
        target_uid = encounter_uid or self.__encounter_uid
        return CombatStateSerializer.has_save_state(target_uid)

    def save_combat_state(self, encounter_uid: Optional[str] = None) -> bool:
        """Captura e salva o snapshot do estado de combate."""
        target_uid = encounter_uid or self.__encounter_uid
        return CombatStateSerializer.save_state(
            encounter_uid=target_uid,
            round_number=self.__round_number,
            current_turn_index=self.__current_turn_index,
            turn_order=self.__turn_order,
            hidden_combatants=self.__hidden_combatants,
            combatants=self.__combatants,
            fog_manager=self.__fog_manager,
        )

    def load_combat_state(self, encounter_uid: Optional[str] = None) -> bool:
        """Restaura uma sessão de combate salva."""
        target_uid = encounter_uid or self.__encounter_uid
        if not target_uid:
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
            logger.error("Arquivo de save de combate '%s' não foi encontrado.", save_path)
            return False

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                save_data = json.load(f)

            base_uid = save_data.get("encounter_uid", encounter_uid)
            self.load_encounter(base_uid)

            self.__round_number = int(save_data.get("round", 1))
            self.__current_turn_index = int(save_data.get("current_turn_index", -1))

            self.__combatants, combatants_by_uid, self.__hidden_combatants = (
                CombatStateSerializer.restore_combatants_state(
                    self.__combatants, save_data.get("combatants_state", [])
                )
            )

            saved_turn_order_uids = save_data.get("turn_order", [])
            reordered: List[Entity] = []
            if saved_turn_order_uids:
                for uid in saved_turn_order_uids:
                    if uid in combatants_by_uid:
                        ent = combatants_by_uid[uid]
                        if not ent.is_hidden:
                            reordered.append(ent)

            for c in self.__combatants:
                if not c.is_hidden and c not in reordered:
                    reordered.append(c)

            self.__turn_order = reordered
            self.__fog_manager.load_state(save_data.get("fog_of_war", []))

            active_name = self.active_character.name if self.active_character else "Nenhum"
            logger.info(
                "Estado de combate restaurado com sucesso de '%s': Rodada %d, Turno Ativo: '%s' (índice %d), %d combatentes, %d células de névoa.",
                save_path.name,
                self.__round_number,
                active_name,
                self.__current_turn_index,
                len(self.__combatants),
                self.__fog_manager.count,
            )
            self.notify_listeners()
            return True
        except Exception as e:
            logger.error("Erro ao carregar estado de combate a partir de '%s': %s", save_path, e)
            return False

    def delete_save_state(self, encounter_uid: Optional[str] = None) -> None:
        """Remove com segurança o snapshot de combate do disco."""
        target_uid = encounter_uid or self.__encounter_uid
        CombatStateSerializer.delete_save_state(target_uid)
