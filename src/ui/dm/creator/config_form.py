import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
import arcade
from .text_input import TextInputWidget, SmartTextInput
from ....domain.models.tile_map import TileMap
from ...utils.tilemap_renderer import TileMapRenderer
from ...components.discrete_scroll_list import DiscreteScrollList
from ....domain.rules.preset_filters import filter_monster_presets
from .renderers.preview_renderer import PreviewRenderer
from .renderers.config_form_renderer import (
    ConfigFormRenderer,
    COLOR_BG_PRIMARY,
    COLOR_ACCENT_GOLD,
    COLOR_PC_BLUE,
    COLOR_MONSTER_RED,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_CARD_BG,
    COLOR_CARD_BG_SELECTED,
    COLOR_TEXT_TITLE,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_WHITE,
    COLOR_TEXT_CYAN,
    COLOR_BTN_BG,
    COLOR_BTN_BORDER,
    COLOR_SUCCESS_BG,
    COLOR_SUCCESS_BORDER,
    COLOR_ERROR_BG,
)
from .handlers.config_form_input_handler import ConfigFormInputHandler

logger = logging.getLogger(__name__)


class CreatorConfigForm:
    """
    Componente especializado para a Etapa 1 do Criador de Encontros (Formulário e Configuração).
    Gerencia estado, validação, filtros de monstros e delega renderização e eventos
    para submódulos coesos e desacoplados.
    """

    def __init__(
        self,
        available_maps: List[Dict[str, str]],
        available_characters: List[Dict[str, Any]],
        available_monsters: List[Dict[str, Any]],
        available_tilemaps: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.__available_image_maps: List[Dict[str, str]] = [m.copy() for m in available_maps]
        self.__available_maps: List[Dict[str, str]] = self.__available_image_maps  # Alias
        self.__available_tilemaps: List[Dict[str, Any]] = [t.copy() for t in (available_tilemaps or [])]
        self.__available_characters: List[Dict[str, Any]] = [c.copy() for c in available_characters]
        self.__available_monsters: List[Dict[str, Any]] = [m.copy() for m in available_monsters]

        # Modo de Mapa: 'image' (Mapa por Imagem) ou 'tilemap' (Mapa por Tileset)
        self.__map_type: str = "image"
        self.__selected_image_index: int = 0
        self.__selected_tilemap_index: int = 0
        self.__selected_map_index: int = 0

        self.tilemap_cache: Dict[str, TileMap] = {}
        self.tilemap_renderers: Dict[str, TileMapRenderer] = {}

        # Widgets de Texto Inteligentes (SmartTextInput)
        self.__title_input = TextInputWidget(
            widget_id="wiz_title",
            placeholder="Digite o título do encontro...",
            initial_text="Emboscada na Floresta",
            max_length=60,
            font_size=9,
        )
        self.__description_input = TextInputWidget(
            widget_id="wiz_desc",
            placeholder="Digite a descrição da batalha...",
            initial_text="Grupo de monstros surpreende os heróis em uma clareira.",
            max_length=140,
            font_size=8,
        )
        self.__search_input = SmartTextInput(
            widget_id="wiz_mon_search",
            placeholder="Buscar monstro...",
            initial_text="",
            max_length=40,
            font_size=8,
        )

        self.__columns: int = 25
        self.__feet_per_square: int = 5
        self.__is_sunlight: bool = False

        self.__selected_character_uids: Set[str] = set()
        self.__monster_counts: Dict[str, int] = {}
        self.__error_message: Optional[str] = None

        # Estado da Listagem de PJs (DiscreteScrollList - 5 slots visíveis)
        self.pc_item_height: float = 24.0
        self.pc_item_spacing: float = 2.0
        self.pc_visible_count: int = 5
        self.__pc_scroll_list = DiscreteScrollList(
            item_height=int(self.pc_item_height),
            spacing=int(self.pc_item_spacing),
            visible_item_count=self.pc_visible_count,
            items=self.__available_characters,
        )

        # Estado da Listagem Rolável Discreta e Busca de Monstros
        self.__search_query: str = ""
        self.__filtered_monsters: List[Dict[str, Any]] = []
        self.__visible_height: float = 160.0
        self.__item_height: float = 38.0
        self.__item_gap: float = 4.0
        self.__scroll_list = DiscreteScrollList(
            item_height=int(self.__item_height),
            spacing=int(self.__item_gap),
            height=self.__visible_height,
        )

        # Estado de Arraste da Barra de Rolagem
        self.is_dragging_scrollbar: bool = False
        self._scrollbar_drag_start_y: float = 0.0
        self._scrollbar_drag_start_offset: int = 0
        self._CreatorConfigForm__last_list_bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

        self._init_defaults()

    def _init_defaults(self) -> None:
        """Inicializa seleções padrão para personagens e contagens de monstros (iniciando estritamente com 0)."""
        if self.__available_characters and not self.__selected_character_uids:
            for char in self.__available_characters:
                self.__selected_character_uids.add(char["uid"])

        self.__pc_scroll_list.items = self.__available_characters

        for mon in self.__available_monsters:
            mid = mon["uid"]
            if mid not in self.__monster_counts:
                self.__monster_counts[mid] = 0

        self.apply_monster_filter(self.__search_query)

    # --- Propriedades e Encapsulamento Defensivo (Poka-Yoke) ---

    @property
    def map_type(self) -> str:
        return self.__map_type

    @map_type.setter
    def map_type(self, value: str) -> None:
        norm = str(value).strip().lower()
        if norm in ("image", "tilemap") and norm != self.__map_type:
            self.__map_type = norm
            logger.info(f"Modo de mapa alterado para '{self.__map_type}'.")

    @property
    def current_map_info(self) -> Dict[str, Any]:
        if self.__map_type == "tilemap":
            if self.__available_tilemaps and 0 <= self.__selected_tilemap_index < len(self.__available_tilemaps):
                return self.__available_tilemaps[self.__selected_tilemap_index].copy()
            return {"name": "Nenhum Tileset", "filename": "", "path": "", "width": 25, "height": 14}
        else:
            if self.__available_image_maps and 0 <= self.__selected_image_index < len(self.__available_image_maps):
                return self.__available_image_maps[self.__selected_image_index].copy()
            return {"name": "Nenhum Mapa", "filename": "", "path": ""}

    @property
    def available_image_maps(self) -> List[Dict[str, str]]:
        return [m.copy() for m in self.__available_image_maps]

    @available_image_maps.setter
    def available_image_maps(self, maps: List[Dict[str, str]]) -> None:
        if not isinstance(maps, list):
            raise TypeError("available_image_maps deve ser uma lista.")
        self.__available_image_maps = [m.copy() for m in maps]
        self.__available_maps = self.__available_image_maps
        if self.__selected_image_index >= len(self.__available_image_maps):
            self.__selected_image_index = max(0, len(self.__available_image_maps) - 1)

    @property
    def available_maps(self) -> List[Dict[str, str]]:
        return self.available_image_maps

    @available_maps.setter
    def available_maps(self, maps: List[Dict[str, str]]) -> None:
        self.available_image_maps = maps

    @property
    def available_tilemaps(self) -> List[Dict[str, Any]]:
        return [t.copy() for t in self.__available_tilemaps]

    @available_tilemaps.setter
    def available_tilemaps(self, tilemaps: List[Dict[str, Any]]) -> None:
        if not isinstance(tilemaps, list):
            raise TypeError("available_tilemaps deve ser uma lista.")
        self.__available_tilemaps = [t.copy() for t in tilemaps]
        if self.__selected_tilemap_index >= len(self.__available_tilemaps):
            self.__selected_tilemap_index = max(0, len(self.__available_tilemaps) - 1)

    @property
    def available_characters(self) -> List[Dict[str, Any]]:
        return [c.copy() for c in self.__available_characters]

    @available_characters.setter
    def available_characters(self, characters: List[Dict[str, Any]]) -> None:
        if not isinstance(characters, list):
            raise TypeError("available_characters deve ser uma lista.")
        self.__available_characters = [c.copy() for c in characters]
        self.__pc_scroll_list.items = self.__available_characters

    @property
    def available_monsters(self) -> List[Dict[str, Any]]:
        return [m.copy() for m in self.__available_monsters]

    @available_monsters.setter
    def available_monsters(self, monsters: List[Dict[str, Any]]) -> None:
        if not isinstance(monsters, list):
            raise TypeError("available_monsters deve ser uma lista.")
        self.__available_monsters = [m.copy() for m in monsters]
        self.apply_monster_filter(self.__search_query)

    @property
    def title_input(self) -> TextInputWidget:
        return self.__title_input

    @property
    def description_input(self) -> TextInputWidget:
        return self.__description_input

    @property
    def search_input(self) -> SmartTextInput:
        return self.__search_input

    @property
    def columns(self) -> int:
        return self.__columns

    @columns.setter
    def columns(self, value: int) -> None:
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 25
        self.__columns = max(1, min(100, value))

    @property
    def feet_per_square(self) -> int:
        return self.__feet_per_square

    @feet_per_square.setter
    def feet_per_square(self, value: int) -> None:
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = 5
        self.__feet_per_square = max(1, value)

    @property
    def selected_image_index(self) -> int:
        return self.__selected_image_index

    @selected_image_index.setter
    def selected_image_index(self, index: int) -> None:
        if not self.__available_image_maps:
            self.__selected_image_index = 0
            return
        self.__selected_image_index = int(index) % len(self.__available_image_maps)

    @property
    def selected_tilemap_index(self) -> int:
        return self.__selected_tilemap_index

    @selected_tilemap_index.setter
    def selected_tilemap_index(self, index: int) -> None:
        if not self.__available_tilemaps:
            self.__selected_tilemap_index = 0
            return
        self.__selected_tilemap_index = int(index) % len(self.__available_tilemaps)

    @property
    def selected_map_index(self) -> int:
        if self.__map_type == "tilemap":
            return self.__selected_tilemap_index
        return self.__selected_image_index

    @selected_map_index.setter
    def selected_map_index(self, index: int) -> None:
        if self.__map_type == "tilemap":
            self.selected_tilemap_index = index
        else:
            self.selected_image_index = index

    @property
    def is_sunlight(self) -> bool:
        return self.__is_sunlight

    @is_sunlight.setter
    def is_sunlight(self, value: bool) -> None:
        self.__is_sunlight = bool(value)

    @property
    def selected_character_uids(self) -> Set[str]:
        return self.__selected_character_uids

    @selected_character_uids.setter
    def selected_character_uids(self, uids: Any) -> None:
        if isinstance(uids, (set, list, tuple)):
            self.__selected_character_uids = set(str(u) for u in uids)
        else:
            raise TypeError("selected_character_uids deve ser um conjunto ou lista de strings.")

    @property
    def monster_counts(self) -> Dict[str, int]:
        return self.__monster_counts

    @monster_counts.setter
    def monster_counts(self, counts: Dict[str, int]) -> None:
        if not isinstance(counts, dict):
            raise TypeError("monster_counts deve ser um dicionário.")
        self.__monster_counts = {str(k): max(0, int(v)) for k, v in counts.items()}

    @property
    def error_message(self) -> Optional[str]:
        return self.__error_message

    @error_message.setter
    def error_message(self, message: Optional[str]) -> None:
        self.__error_message = str(message) if message is not None else None

    @property
    def search_query(self) -> str:
        return self.__search_query

    @search_query.setter
    def search_query(self, query: str) -> None:
        self.apply_monster_filter(str(query))

    @property
    def filtered_monsters(self) -> List[Dict[str, Any]]:
        return [m.copy() for m in self.__filtered_monsters]

    @property
    def pc_scroll_list(self) -> DiscreteScrollList:
        return self.__pc_scroll_list

    @property
    def character_scroll_list(self) -> DiscreteScrollList:
        return self.__pc_scroll_list

    @property
    def scroll_list(self) -> DiscreteScrollList:
        return self.__scroll_list

    @property
    def start_index(self) -> int:
        return self.__scroll_list.start_index

    @start_index.setter
    def start_index(self, val: int) -> None:
        self.__scroll_list.start_index = val

    @property
    def scroll_offset(self) -> float:
        total_item_h = self.__item_height + self.__item_gap
        return float(self.__scroll_list.start_index * total_item_h)

    @scroll_offset.setter
    def scroll_offset(self, value: float) -> None:
        total_item_h = self.__item_height + self.__item_gap
        try:
            val = float(value)
        except (ValueError, TypeError):
            val = 0.0
        if total_item_h > 0:
            target_idx = int(round(val / total_item_h))
            self.__scroll_list.start_index = target_idx

    @property
    def visible_height(self) -> float:
        return self.__visible_height

    @visible_height.setter
    def visible_height(self, value: float) -> None:
        self.__visible_height = max(50.0, float(value))
        self.__scroll_list.height = self.__visible_height

    @property
    def item_height(self) -> float:
        return self.__item_height

    @item_height.setter
    def item_height(self, value: float) -> None:
        self.__item_height = max(20.0, float(value))
        self.__scroll_list.item_height = int(self.__item_height)

    @property
    def item_gap(self) -> float:
        return self.__item_gap

    @item_gap.setter
    def item_gap(self, value: float) -> None:
        self.__item_gap = max(0.0, float(value))
        self.__scroll_list.spacing = int(self.__item_gap)

    @property
    def last_list_bounds(self) -> Tuple[float, float, float, float]:
        return self.__scroll_list.bounds

    @last_list_bounds.setter
    def last_list_bounds(self, bounds: Tuple[float, float, float, float]) -> None:
        self._CreatorConfigForm__last_list_bounds = bounds
        self.__scroll_list.set_bounds(float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))

    # --- Métodos de Conveniência e Manipulação de Estado ---

    def toggle_character(self, character_uid: str) -> bool:
        if character_uid in self.__selected_character_uids:
            self.__selected_character_uids.remove(character_uid)
            return False
        else:
            self.__selected_character_uids.add(character_uid)
            return True

    def is_character_selected(self, character_uid: str) -> bool:
        return character_uid in self.__selected_character_uids

    def get_monster_count(self, monster_uid: str) -> int:
        return self.__monster_counts.get(monster_uid, 0)

    def set_monster_count(self, monster_uid: str, count: int) -> None:
        self.__monster_counts[monster_uid] = max(0, min(99, int(count)))

    def increment_monster(self, monster_uid: str, delta: int = 1) -> int:
        current = self.get_monster_count(monster_uid)
        new_val = max(0, min(99, current + delta))
        self.__monster_counts[monster_uid] = new_val
        return new_val

    def decrement_monster(self, monster_uid: str, delta: int = 1) -> int:
        return self.increment_monster(monster_uid, -delta)

    def update_sources(
        self,
        available_maps: List[Dict[str, str]],
        available_characters: List[Dict[str, Any]],
        available_monsters: List[Dict[str, Any]],
        available_tilemaps: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.__available_image_maps = [m.copy() for m in available_maps]
        self.__available_maps = self.__available_image_maps
        if available_tilemaps is not None:
            self.__available_tilemaps = [t.copy() for t in available_tilemaps]
        self.__available_characters = [c.copy() for c in available_characters]
        self.__pc_scroll_list.items = self.__available_characters
        self.__available_monsters = [m.copy() for m in available_monsters]

        if self.__selected_image_index >= len(self.__available_image_maps):
            self.__selected_image_index = 0
        if self.__selected_tilemap_index >= len(self.__available_tilemaps):
            self.__selected_tilemap_index = 0
        self._init_defaults()
        logger.info(
            f"Fontes do Criador atualizadas: {len(self.__available_image_maps)} imagens de mapa, {len(self.__available_tilemaps)} tilemaps, {len(self.__available_characters)} PJs, {len(self.__available_monsters)} monstros."
        )

    def apply_monster_filter(self, query: str) -> None:
        self.__search_query = query.strip()
        self.__filtered_monsters = filter_monster_presets(self.__available_monsters, self.__search_query)
        self.__scroll_list.items = self.__filtered_monsters
        self.__scroll_list.reset_scroll()

    @property
    def max_scroll(self) -> float:
        total_item_h = self.__item_height + self.__item_gap
        return float(self.__scroll_list.max_start_index * total_item_h)

    def update(self, delta_time: float) -> None:
        self.__title_input.update(delta_time)
        self.__description_input.update(delta_time)
        self.__search_input.update(delta_time)

    def validate(self) -> Tuple[bool, Optional[str]]:
        if not self.__title_input.text.strip():
            return False, "O título do encontro é obrigatório!"

        if self.__map_type == "tilemap" and not self.__available_tilemaps:
            return False, "Nenhum layout de tilemap disponível encontrado em creations/maps/!"
        elif self.__map_type == "image" and not self.__available_image_maps:
            return False, "Nenhum mapa de imagem disponível encontrado em assets/images/maps/!"

        has_combatants = bool(self.__selected_character_uids) or any(q > 0 for q in self.__monster_counts.values())
        if not has_combatants:
            return False, "Selecione ao menos um personagem ou monstro!"

        if self.__columns <= 0:
            return False, "A grade deve ter pelo menos 1 coluna!"

        if self.__feet_per_square <= 0:
            return False, "Pés por quadrado deve ser maior que 0!"

        return True, None

    def get_config_data(self) -> Dict[str, Any]:
        cur_map = self.current_map_info
        map_path = cur_map.get("path", "assets/images/maps/open_field_grass_trees.jpg")

        return {
            "title": self.__title_input.text.strip(),
            "description": self.__description_input.text.strip(),
            "map_type": self.__map_type,
            "map_source": map_path,
            "map_path": map_path,
            "map_name": cur_map.get("name", "Mapa"),
            "columns": self.__columns,
            "feet_per_square": self.__feet_per_square,
            "is_sunlight": self.__is_sunlight,
            "selected_character_uids": set(self.__selected_character_uids),
            "monster_counts": dict(self.__monster_counts),
        }

    def load_configuration(self, data: Dict[str, Any]) -> None:
        title = data.get("title", "")
        self.__title_input.set_text(title)

        description = data.get("description", "")
        self.__description_input.set_text(description)

        raw_map_type = data.get("map_type")
        raw_map_source = data.get("map_source") or data.get("map_file") or data.get("map_path") or ""

        if not raw_map_type:
            raw_map_type = "tilemap" if str(raw_map_source).lower().endswith(".json") else "image"
        self.map_type = str(raw_map_type).strip().lower()

        if self.__map_type == "tilemap":
            found_idx = 0
            if raw_map_source:
                for idx, item in enumerate(self.__available_tilemaps):
                    if (
                        item.get("path") == raw_map_source
                        or item.get("filename") == raw_map_source
                        or Path(item.get("path", "")).name == Path(raw_map_source).name
                    ):
                        found_idx = idx
                        break
            self.selected_tilemap_index = found_idx
        else:
            found_idx = 0
            if raw_map_source:
                for idx, item in enumerate(self.__available_image_maps):
                    if (
                        item.get("path") == raw_map_source
                        or item.get("filename") == raw_map_source
                        or Path(item.get("path", "")).name == Path(raw_map_source).name
                    ):
                        found_idx = idx
                        break
            self.selected_image_index = found_idx

        grid_data = data.get("grid", {})
        if isinstance(grid_data, dict):
            self.columns = grid_data.get("columns", 25)
            self.feet_per_square = grid_data.get("feet_per_square", 5)

        env_data = data.get("environment", {})
        if isinstance(env_data, dict):
            self.is_sunlight = bool(env_data.get("is_sunlight", False))

        raw_combatants = data.get("combatants", [])
        selected_pcs: Set[str] = set()
        monster_counts: Dict[str, int] = {m["uid"]: 0 for m in self.__available_monsters}

        for c in raw_combatants:
            if isinstance(c, dict):
                etype = c.get("entity_type", "monster")
                if etype in ("playable_character", "character", "pc"):
                    cid = c.get("character_id") or c.get("uid")
                    if cid:
                        selected_pcs.add(str(cid))
                else:
                    mid = c.get("monster_id")
                    if mid:
                        monster_counts[str(mid)] = monster_counts.get(str(mid), 0) + 1
            else:
                if getattr(c, "is_player", False):
                    cid = getattr(c, "character_id", getattr(c, "uid", None))
                    if cid:
                        selected_pcs.add(str(cid))
                else:
                    mid = getattr(c, "monster_id", getattr(c, "uid", None))
                    if mid:
                        monster_counts[str(mid)] = monster_counts.get(str(mid), 0) + 1

        self.selected_character_uids = selected_pcs
        self.monster_counts = monster_counts
        self.error_message = None
        logger.info(f"CreatorConfigForm carregado para edição com {len(selected_pcs)} PJs e {sum(monster_counts.values())} monstros.")

    # --- Delegações de Renderização ---

    def draw_form(self, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        ConfigFormRenderer.draw_form(self, panel_w, top_y, text_cache)

    def draw_preview(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        text_cache: Dict[str, arcade.Text],
        texture_cache: Dict[str, arcade.Texture],
    ) -> None:
        PreviewRenderer.draw_preview(self, vx, vy, vw, vh, text_cache, texture_cache)

    def _render_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool,
        cache: Dict[str, arcade.Text],
        anchor_x: str = "left",
    ) -> None:
        PreviewRenderer.render_text(key, text, x, y, color, font_size, bold, cache, anchor_x=anchor_x)

    # --- Delegações de Eventos de Mouse e Teclado ---

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        return ConfigFormInputHandler.handle_mouse_scroll(self, x, y, scroll_x, scroll_y)

    def handle_mouse_press(self, x: float, y: float, panel_w: float, top_y: float) -> Optional[str]:
        return ConfigFormInputHandler.handle_mouse_press(self, x, y, panel_w, top_y)

    def handle_mouse_drag(self, x: float, y: float) -> bool:
        return ConfigFormInputHandler.handle_mouse_drag(self, x, y)

    def handle_mouse_release(self, x: float, y: float) -> None:
        ConfigFormInputHandler.handle_mouse_release(self, x, y)

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        return ConfigFormInputHandler.handle_key_press(self, symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int) -> None:
        ConfigFormInputHandler.handle_key_release(self, symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        return ConfigFormInputHandler.handle_text_input(self, text)
