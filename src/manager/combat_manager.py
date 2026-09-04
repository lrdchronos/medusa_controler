import logging
import random
from typing import List, Dict, Any, Optional, Callable, Tuple
from ..domain.models.entity import Entity
from ..domain.models.tile_map import TileMap
from ..domain.models.spell_template import SpellTemplate, SpellShape
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
        self.__current_turn_index: int = -1
        self.__round_number: int = 1

        # Projeção Tática de Áreas de Efeito de Feitiços (Spell AoE)
        self.__active_spell_template: Optional[SpellTemplate] = None

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
    def combatants(self) -> List[Entity]:
        """Retorna cópia defensiva da lista de todos os combatentes."""
        return list(self.__combatants)

    @property
    def turn_order(self) -> List[Entity]:
        """Retorna cópia defensiva da lista de turnos ordenados por iniciativa."""
        return list(self.__turn_order)

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
        # Inicialmente, a fila é a lista na ordem de inserção
        self.__turn_order = list(self.__combatants)
        self.__current_turn_index = -1
        self.__round_number = 1

        logger.info(
            f"Encontro carregado: '{self.__title}' ({self.__encounter_uid}) [tipo={self.__map_type}] com {len(self.__combatants)} combatentes."
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
        Rola 1d20 + DEX mod para cada participante e devolve um dicionário temporário
        {combatant_uid: score} sem alterar o estado oficial de combate.
        """
        draft: Dict[str, int] = {}
        for combatant in self.__combatants:
            d20 = random.randint(1, 20)
            score = d20 + combatant.initiative_mod
            draft[combatant.uid] = score
        logger.debug(f"Draft de iniciativas gerado para {len(draft)} participantes.")
        return draft

    def apply_initiatives(self, final_scores: Dict[str, int]) -> None:
        """
        Recebe o dicionário consolidado de iniciativas (UID ou Nome -> Score),
        atribui os valores às entidades, aplica a ordenação com desempate do D&D 5E
        (Iniciativa -> Modificador DEX -> Nome) e notifica os Observers.
        """
        for combatant in self.__combatants:
            if combatant.uid in final_scores:
                score = final_scores[combatant.uid]
            elif combatant.name in final_scores:
                score = final_scores[combatant.name]
            else:
                d20 = random.randint(1, 20)
                score = d20 + combatant.initiative_mod

            combatant.set_initiative(score)

        # Ordenação com critérios de desempate D&D 5E
        self.__turn_order = sorted(
            self.__combatants,
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
            f"Iniciativas consolidadas e aplicadas para {len(self.__combatants)} combatentes. "
            f"Turno ativo: '{active_name}' (Rodada {self.__round_number})."
        )
        self.notify_listeners()

    def roll_initiatives(self, manual_rolls: Optional[Dict[str, int]] = None) -> List[Entity]:
        """
        Rola e aplica iniciativas diretamente, permitindo overrides manuais via dicionário (UID ou Nome).
        Mantém total compatibilidade e utiliza o pipeline oficial.
        """
        scores = self.generate_draft_initiatives()
        if manual_rolls:
            for combatant in self.__combatants:
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
        Avança para o próximo participante na fila de iniciativa de forma circular.
        Ao completar uma volta completa, incrementa o número da rodada.
        """
        if not self.__turn_order:
            return None

        if self.__current_turn_index < 0:
            self.__current_turn_index = 0
            self.__round_number = 1
        else:
            self.__current_turn_index = (self.__current_turn_index + 1) % len(self.__turn_order)
            if self.__current_turn_index == 0:
                self.__round_number += 1

        active_name = self.active_character.name if self.active_character else "Nenhum"
        logger.info(f"Passar Turno: combatente ativo '{active_name}' (Rodada {self.__round_number}).")
        self.notify_listeners()
        return self.active_character

    def previous_turn(self) -> Optional[Entity]:
        """Retrocede para o participante anterior na fila de iniciativas."""
        if not self.__turn_order:
            return None

        if self.__current_turn_index <= 0:
            self.__current_turn_index = len(self.__turn_order) - 1
            if self.__round_number > 1:
                self.__round_number -= 1
        else:
            self.__current_turn_index -= 1

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
            if combatant not in self.__turn_order:
                self.__turn_order.append(combatant)
            self.notify_listeners()

    def get_combatant(self, uid_or_name: str) -> Optional[Entity]:
        """Busca um combatente por UID ou Nome."""
        for c in self.__combatants:
            if c.uid == uid_or_name or c.name.lower() == uid_or_name.lower():
                return c
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

    def toggle_combatant_visibility(self, uid_or_name: str) -> bool:
        """Alterna a visibilidade tática (is_hidden) de um combatente."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            new_hidden = not combatant.is_hidden
            combatant.set_hidden(new_hidden)
            status_desc = "Oculto (Invisível aos Jogadores)" if new_hidden else "Visível (Exibido aos Jogadores)"
            logger.info(f"Visibilidade alterada: '{combatant.name}' agora está {status_desc}.")
            self.notify_listeners()
            return new_hidden
        return False

    def set_combatant_visibility(self, uid_or_name: str, is_hidden: bool) -> bool:
        """Define explicitamente a visibilidade tática de um combatente."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.set_hidden(is_hidden)
            logger.info(f"Visibilidade definida: '{combatant.name}' is_hidden={is_hidden}.")
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
        """Incrementa/decrementa o ângulo de rotação da magia em passos angulares com wrap-around."""
        if self.__active_spell_template is not None:
            new_rot = (self.__active_spell_template.rotation_degrees + delta_degrees) % 360.0
            self.__active_spell_template = self.__active_spell_template.with_rotation(new_rot)
            logger.debug(f"Rotação da magia ajustada: {self.__active_spell_template.rotation_degrees:.1f}°")
            self.notify_listeners()

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
                shape=SpellShape.CIRCLE,
                size_feet=feet * 4.0,
                width_feet=feet,
                rotation_degrees=0.0,
                origin_world=(0.0, 0.0),
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
        self.__current_turn_index = -1
        self.__round_number = 1

        logger.info("Estado do CombatManager resetado com sucesso.")
        self.notify_listeners()

    def clear_combat(self) -> None:
        """Alias para reset_combat()."""
        self.reset_combat()

