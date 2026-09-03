import logging
import os
from typing import Optional, List, Dict, Any, Set, Tuple
import arcade
from ...utils.sprite_utils import SpriteFactory
from .text_input import TextInputWidget, SmartTextInput
from ....domain.models.tile_map import TileMap
from ...utils.tilemap_renderer import TileMapRenderer
from ....manager.grid_manager import GridManager

logger = logging.getLogger(__name__)

# --- Paleta de Cores Dark Fantasy (PREMISES.md) ---
COLOR_BG_PRIMARY = (14, 18, 24, 255)        # #0E1218 (Azul escuro grafite)
COLOR_ACCENT_GOLD = (241, 196, 15, 255)     # #F1C40F (Dourado místico)
COLOR_PC_BLUE = (41, 128, 185, 255)         # #2980B9 (Azul Jogador)
COLOR_MONSTER_RED = (192, 57, 43, 255)      # #C0392B (Carmim / Vermelho Sangue)
COLOR_PANEL_BG = (20, 26, 36, 255)
COLOR_PANEL_BORDER = (45, 60, 85, 200)
COLOR_CARD_BG = (20, 26, 36, 255)
COLOR_CARD_BG_SELECTED = (30, 42, 58, 255)
COLOR_TEXT_TITLE = (241, 196, 15, 255)
COLOR_TEXT_MAIN = (200, 210, 225, 255)
COLOR_TEXT_MUTED = (140, 155, 175, 255)
COLOR_TEXT_WHITE = (255, 255, 255, 255)
COLOR_TEXT_CYAN = (100, 200, 255, 255)
COLOR_BTN_BG = (35, 45, 60, 255)
COLOR_BTN_BORDER = (70, 90, 120, 200)
COLOR_SUCCESS_BG = (39, 174, 96, 255)
COLOR_SUCCESS_BORDER = (46, 204, 113, 255)
COLOR_ERROR_BG = (120, 40, 31, 255)


def filter_monster_presets(monsters: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Filtra presets de monstros aplicando correspondência de substring parcial (estilo SQL LIKE '%query%').
    Verifica se a query sanitizada está contida no 'name', 'uid', 'type', 'sub_type' ou na lista de 'tags'.
    Se a query for vazia, restaura e retorna a listagem completa.
    """
    sanitized = query.strip().lower()
    if not sanitized:
        logger.debug(f"Filtro de busca vazio: restaurando listagem completa ({len(monsters)} monstros).")
        return [m.copy() for m in monsters]

    filtered: List[Dict[str, Any]] = []
    for mon in monsters:
        name = str(mon.get("name", "")).lower()
        uid = str(mon.get("uid", "")).lower()
        m_type = str(mon.get("type", "")).lower()
        sub_type = str(mon.get("sub_type", "")).lower()

        # Checa correspondência em tags
        tags = mon.get("tags", [])
        tag_match = False
        if isinstance(tags, (list, tuple, set)):
            tag_match = any(sanitized in str(t).lower() for t in tags)
        elif isinstance(tags, str):
            tag_match = sanitized in tags.lower()

        # Fallback defensivo em raw_data caso exista
        raw_match = False
        raw = mon.get("raw_data")
        if isinstance(raw, dict):
            raw_type = str(raw.get("type", "")).lower()
            raw_sub = str(raw.get("sub_type", "")).lower()
            raw_tags = raw.get("tags", [])
            if isinstance(raw_tags, (list, tuple, set)):
                raw_match = any(sanitized in str(t).lower() for t in raw_tags) or sanitized in raw_type or sanitized in raw_sub
            elif isinstance(raw_tags, str):
                raw_match = sanitized in raw_tags.lower() or sanitized in raw_type or sanitized in raw_sub

        if (
            sanitized in name
            or sanitized in uid
            or sanitized in m_type
            or sanitized in sub_type
            or tag_match
            or raw_match
        ):
            filtered.append(mon.copy())

    logger.info(
        f"Filtragem de monstros executada | Query: '{sanitized}' | Resultados: {len(filtered)}/{len(monsters)}"
    )
    return filtered


class CreatorConfigForm:
    """
    Componente especializado para a Etapa 1 do Criador de Encontros (Formulário e Configuração).
    
    Premissas Arquiteturais Aplicadas (PREMISES.md):
      - OOD & Modularização Estrita com decomposição de responsabilidades.
      - Encapsulamento Poka-Yoke com atributos privados (__) e propriedades com validação.
      - Retorno de cópias defensivas para coleções mutáveis.
      - Renderização Dark Fantasy via SpriteFactory (sem instanciação de texturas no loop).
      - Suporte a texto rico com SmartTextInput.
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
        self.__selected_map_index: int = 0  # Alias

        self.__tilemap_cache: Dict[str, TileMap] = {}
        self.__tilemap_renderers: Dict[str, TileMapRenderer] = {}

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

        # Estado da Listagem Rolável e Busca
        self.__search_query: str = ""
        self.__filtered_monsters: List[Dict[str, Any]] = []
        self.__scroll_offset: float = 0.0
        self.__visible_height: float = 160.0
        self.__item_height: float = 38.0
        self.__item_gap: float = 4.0

        # Estado de Arraste da Barra de Rolagem
        self.__is_dragging_scrollbar: bool = False
        self.__scrollbar_drag_start_y: float = 0.0
        self.__scrollbar_drag_start_offset: float = 0.0
        self.__last_list_bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

        self._init_defaults()

    def _init_defaults(self) -> None:
        """Inicializa seleções padrão para personagens e contagens de monstros."""
        if self.__available_characters and not self.__selected_character_uids:
            for char in self.__available_characters:
                self.__selected_character_uids.add(char["uid"])

        for mon in self.__available_monsters:
            mid = mon["uid"]
            if mid not in self.__monster_counts:
                self.__monster_counts[mid] = 2 if "kobold" in mid.lower() else 0

        self.apply_monster_filter(self.__search_query)

    # --- Propriedades e Encapsulamento Defensivo (Poka-Yoke) ---

    @property
    def map_type(self) -> str:
        """Modo ativo de mapa ('image' ou 'tilemap')."""
        return self.__map_type

    @map_type.setter
    def map_type(self, value: str) -> None:
        norm = str(value).strip().lower()
        if norm in ("image", "tilemap") and norm != self.__map_type:
            self.__map_type = norm
            logger.info(f"Modo de mapa alterado para '{self.__map_type}'.")

    @property
    def current_map_info(self) -> Dict[str, Any]:
        """Retorna o dicionário de dados do mapa atualmente selecionado."""
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
        """Retorna cópia defensiva da lista de mapas por imagem estática."""
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
        """Alias para available_image_maps."""
        return self.available_image_maps

    @available_maps.setter
    def available_maps(self, maps: List[Dict[str, str]]) -> None:
        self.available_image_maps = maps

    @property
    def available_tilemaps(self) -> List[Dict[str, Any]]:
        """Retorna cópia defensiva da lista de mapas por tileset."""
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
        """Retorna uma cópia defensiva da lista de personagens disponíveis."""
        return [c.copy() for c in self.__available_characters]

    @available_characters.setter
    def available_characters(self, characters: List[Dict[str, Any]]) -> None:
        if not isinstance(characters, list):
            raise TypeError("available_characters deve ser uma lista.")
        self.__available_characters = [c.copy() for c in characters]

    @property
    def available_monsters(self) -> List[Dict[str, Any]]:
        """Retorna uma cópia defensiva da lista de presets de monstros."""
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
        """Retorna cópia defensiva da lista filtrada de monstros."""
        return [m.copy() for m in self.__filtered_monsters]

    @property
    def scroll_offset(self) -> float:
        return self.__scroll_offset

    @scroll_offset.setter
    def scroll_offset(self, value: float) -> None:
        try:
            val = float(value)
        except (ValueError, TypeError):
            val = 0.0
        self.__scroll_offset = max(0.0, min(self.max_scroll, val))

    @property
    def visible_height(self) -> float:
        return self.__visible_height

    @visible_height.setter
    def visible_height(self, value: float) -> None:
        self.__visible_height = max(50.0, float(value))

    @property
    def item_height(self) -> float:
        return self.__item_height

    @item_height.setter
    def item_height(self, value: float) -> None:
        self.__item_height = max(20.0, float(value))

    @property
    def item_gap(self) -> float:
        return self.__item_gap

    @item_gap.setter
    def item_gap(self, value: float) -> None:
        self.__item_gap = max(0.0, float(value))

    @property
    def is_dragging_scrollbar(self) -> bool:
        return self.__is_dragging_scrollbar

    @is_dragging_scrollbar.setter
    def is_dragging_scrollbar(self, value: bool) -> None:
        self.__is_dragging_scrollbar = bool(value)

    @property
    def last_list_bounds(self) -> Tuple[float, float, float, float]:
        return self.__last_list_bounds

    @last_list_bounds.setter
    def last_list_bounds(self, bounds: Tuple[float, float, float, float]) -> None:
        self.__last_list_bounds = (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))

    # --- Métodos de Conveniência e Manipulação de Estado ---

    def toggle_character(self, character_uid: str) -> bool:
        """Alterna a seleção de um personagem jogador pelo UID."""
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
        """Recarrega arquivos de mapas, personagens e presets de monstros preservando contagens."""
        self.__available_image_maps = [m.copy() for m in available_maps]
        self.__available_maps = self.__available_image_maps
        if available_tilemaps is not None:
            self.__available_tilemaps = [t.copy() for t in available_tilemaps]
        self.__available_characters = [c.copy() for c in available_characters]
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
        """Aplica o filtro de busca por substring e reseta o scroll para o topo."""
        self.__search_query = query.strip()
        self.__filtered_monsters = filter_monster_presets(self.__available_monsters, self.__search_query)
        self.__scroll_offset = 0.0

    @property
    def max_scroll(self) -> float:
        """Calcula o limite máximo de deslocamento de rolagem."""
        total_item_h = self.__item_height + self.__item_gap
        total_content_height = len(self.__filtered_monsters) * total_item_h
        return max(0.0, total_content_height - self.__visible_height + 8.0)

    def update(self, delta_time: float) -> None:
        self.__title_input.update(delta_time)
        self.__description_input.update(delta_time)
        self.__search_input.update(delta_time)

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida o formulário antes de prosseguir para o palco tático."""
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
        """Retorna os dados consolidados do formulário com cópias defensivas para o palco de staging."""
        cur_map = self.current_map_info
        map_path = cur_map.get("path", "assets/images/maps/open_field_grass_trees.jpg")

        return {
            "title": self.__title_input.text.strip(),
            "description": self.__description_input.text.strip(),
            "map_type": self.__map_type,
            "map_source": map_path,
            "map_path": map_path,  # Retrocompatibilidade
            "map_name": cur_map.get("name", "Mapa"),
            "columns": self.__columns,
            "feet_per_square": self.__feet_per_square,
            "is_sunlight": self.__is_sunlight,
            "selected_character_uids": set(self.__selected_character_uids),
            "monster_counts": dict(self.__monster_counts),
        }

    # --- Renderização OOD Modular ---

    def draw_form(self, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        """Desenha todo o painel esquerdo da Etapa 1 delegando para submétodos especializados."""
        try:
            if arcade.get_window() is None:
                return
        except Exception:
            return

        sec_y = top_y - 18
        self._draw_header(panel_w, sec_y, text_cache)
        box_d_y = self._draw_text_fields(panel_w, sec_y, text_cache)
        map_row_y = self._draw_map_selector(panel_w, box_d_y - 24, text_cache)
        grid_y = self._draw_grid_steppers(panel_w, map_row_y - 28, text_cache)
        pc_bottom_y = self._draw_character_checkboxes(panel_w, grid_y - 28, text_cache)
        search_bar_y = self._draw_monster_search_bar(panel_w, pc_bottom_y - 10, text_cache)
        list_bottom_y = self._draw_monster_list(panel_w, search_bar_y - 18, text_cache)
        self._draw_error_and_submit(panel_w, list_bottom_y, text_cache)

    def _draw_header(self, panel_w: float, sec_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        self._render_text(
            "wiz_sec_t",
            "🛠️ CRIADOR DE ENCONTROS (ETAPA 1: CONFIGURAÇÃO)",
            16,
            sec_y,
            COLOR_TEXT_TITLE,
            10,
            True,
            text_cache,
        )

    def _draw_text_fields(self, panel_w: float, sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        # Título
        lbl_t_y = sec_y - 24
        self._render_text("lbl_title", "• Título do Encontro:", 16, lbl_t_y, COLOR_TEXT_MAIN, 9, True, text_cache)
        box_t_y = lbl_t_y - 18
        self.__title_input.draw(panel_w / 2, box_t_y, panel_w - 32, 26, text_cache)

        # Descrição
        lbl_d_y = box_t_y - 22
        self._render_text("lbl_desc", "• Descrição do Encontro:", 16, lbl_d_y, COLOR_TEXT_MAIN, 9, True, text_cache)
        box_d_y = lbl_d_y - 18
        self.__description_input.draw(panel_w / 2, box_d_y, panel_w - 32, 26, text_cache)
        return box_d_y

    def _draw_map_selector(self, panel_w: float, map_sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        self._render_text("lbl_map_sec", "• Mapa & Grade Tática:", 16, map_sec_y, COLOR_TEXT_MAIN, 9, True, text_cache)

        # Abas / Alternador de Modo: [ 🖼️ Mapa por Imagem ] | [ 🧩 Mapa por Tileset ]
        tab_y = map_sec_y - 20
        tab_w = (panel_w - 38) / 2.0
        tab_img_x = 16.0 + tab_w / 2.0
        tab_tile_x = 16.0 + tab_w + 6.0 + tab_w / 2.0

        is_img = (self.__map_type == "image")
        is_tile = (self.__map_type == "tilemap")

        # Aba Imagem
        img_bg = (35, 52, 75, 255) if is_img else (20, 26, 36, 255)
        img_bd = COLOR_ACCENT_GOLD if is_img else COLOR_PANEL_BORDER
        img_fg = COLOR_ACCENT_GOLD if is_img else COLOR_TEXT_MUTED
        arcade.draw_rect_filled(arcade.XYWH(tab_img_x, tab_y, tab_w, 22), img_bg)
        arcade.draw_rect_outline(arcade.XYWH(tab_img_x, tab_y, tab_w, 22), img_bd, 1.5 if is_img else 1)
        self._render_text("tab_img_lbl", "🖼️ Mapa por Imagem", tab_img_x, tab_y, img_fg, 8, is_img, text_cache, anchor_x="center")

        # Aba Tileset
        tile_bg = (35, 52, 75, 255) if is_tile else (20, 26, 36, 255)
        tile_bd = COLOR_ACCENT_GOLD if is_tile else COLOR_PANEL_BORDER
        tile_fg = COLOR_ACCENT_GOLD if is_tile else COLOR_TEXT_MUTED
        arcade.draw_rect_filled(arcade.XYWH(tab_tile_x, tab_y, tab_w, 22), tile_bg)
        arcade.draw_rect_outline(arcade.XYWH(tab_tile_x, tab_y, tab_w, 22), tile_bd, 1.5 if is_tile else 1)
        self._render_text("tab_tile_lbl", "🧩 Mapa por Tileset", tab_tile_x, tab_y, tile_fg, 8, is_tile, text_cache, anchor_x="center")

        # Linha do Seletor [◀] [Nome do Mapa] [▶]
        map_row_y = tab_y - 24
        cur_map = self.current_map_info

        # [◀]
        b_prev_m_x = 30
        arcade.draw_rect_filled(arcade.XYWH(b_prev_m_x, map_row_y, 26, 24), COLOR_BTN_BG)
        arcade.draw_rect_outline(arcade.XYWH(b_prev_m_x, map_row_y, 26, 24), COLOR_BTN_BORDER, 1)
        self._render_text("b_map_prev", "◀", b_prev_m_x, map_row_y, COLOR_ACCENT_GOLD, 10, True, text_cache, anchor_x="center")

        # Caixa do Nome do Mapa
        map_box_w = panel_w - 180
        map_box_x = 30 + 13 + map_box_w / 2 + 4
        arcade.draw_rect_filled(arcade.XYWH(map_box_x, map_row_y, map_box_w, 24), COLOR_PANEL_BG)
        arcade.draw_rect_outline(arcade.XYWH(map_box_x, map_row_y, map_box_w, 24), COLOR_PANEL_BORDER, 1)
        prefix = "🧩 " if is_tile else "🖼️ "
        self._render_text("map_name_t", f"{prefix}{cur_map['name'][:22]}", map_box_x, map_row_y, COLOR_TEXT_CYAN, 8, True, text_cache, anchor_x="center")

        # [▶]
        b_next_m_x = map_box_x + map_box_w / 2 + 17
        arcade.draw_rect_filled(arcade.XYWH(b_next_m_x, map_row_y, 26, 24), COLOR_BTN_BG)
        arcade.draw_rect_outline(arcade.XYWH(b_next_m_x, map_row_y, 26, 24), COLOR_BTN_BORDER, 1)
        self._render_text("b_map_next", "▶", b_next_m_x, map_row_y, COLOR_ACCENT_GOLD, 10, True, text_cache, anchor_x="center")
        return map_row_y

    def _draw_grid_steppers(self, panel_w: float, grid_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        self._render_text("lbl_cols", "Cols:", 16, grid_y, COLOR_TEXT_MUTED, 8, True, text_cache)

        b_c_min_x = 65
        arcade.draw_rect_filled(arcade.XYWH(b_c_min_x, grid_y, 22, 22), COLOR_BTN_BG)
        self._render_text("b_c_min", "-", b_c_min_x, grid_y, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")

        arcade.draw_rect_filled(arcade.XYWH(b_c_min_x + 24, grid_y, 30, 22), (18, 24, 34, 255))
        self._render_text("val_cols", str(self.__columns), b_c_min_x + 24, grid_y, COLOR_TEXT_WHITE, 9, True, text_cache, anchor_x="center")

        b_c_plus_x = b_c_min_x + 48
        arcade.draw_rect_filled(arcade.XYWH(b_c_plus_x, grid_y, 22, 22), COLOR_BTN_BG)
        self._render_text("b_c_plus", "+", b_c_plus_x, grid_y, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")

        feet_lbl_x = b_c_plus_x + 30
        self._render_text("lbl_feet", "Ft/sq:", feet_lbl_x, grid_y, COLOR_TEXT_MUTED, 8, True, text_cache)

        b_f_min_x = feet_lbl_x + 45
        arcade.draw_rect_filled(arcade.XYWH(b_f_min_x, grid_y, 22, 22), COLOR_BTN_BG)
        self._render_text("b_f_min", "-", b_f_min_x, grid_y, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")

        arcade.draw_rect_filled(arcade.XYWH(b_f_min_x + 24, grid_y, 26, 22), (18, 24, 34, 255))
        self._render_text("val_feet", str(self.__feet_per_square), b_f_min_x + 24, grid_y, COLOR_TEXT_WHITE, 9, True, text_cache, anchor_x="center")

        b_f_plus_x = b_f_min_x + 48
        arcade.draw_rect_filled(arcade.XYWH(b_f_plus_x, grid_y, 22, 22), COLOR_BTN_BG)
        self._render_text("b_f_plus", "+", b_f_plus_x, grid_y, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")
        return grid_y

    def _draw_character_checkboxes(self, panel_w: float, pc_sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        self._render_text("lbl_pcs", "• Personagens dos Jogadores (PJs):", 16, pc_sec_y, COLOR_TEXT_MAIN, 9, True, text_cache)

        pc_list_top = pc_sec_y - 16
        for idx, char in enumerate(self.__available_characters[:3]):
            cy = pc_list_top - idx * 24
            is_checked = char["uid"] in self.__selected_character_uids

            cb_x = 26
            cb_bg = (30, 42, 58, 255) if is_checked else (18, 24, 34, 255)
            cb_border = COLOR_ACCENT_GOLD if is_checked else (60, 75, 100, 200)
            arcade.draw_rect_filled(arcade.XYWH(cb_x, cy, 16, 16), cb_bg)
            arcade.draw_rect_outline(arcade.XYWH(cb_x, cy, 16, 16), cb_border, 1.5)
            if is_checked:
                self._render_text(f"cb_check_{idx}", "✓", cb_x, cy, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")

            char_desc = f"{char['name']} (Nv {char['level']} {char['class_summary']})"
            lbl_color = COLOR_TEXT_CYAN if is_checked else COLOR_TEXT_MUTED
            self._render_text(f"char_lbl_{idx}", char_desc[:38], 44, cy, lbl_color, 8, is_checked, text_cache)

        count_shown = min(len(self.__available_characters), 3)
        return pc_list_top - count_shown * 24

    def _draw_monster_search_bar(self, panel_w: float, mon_sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        self._render_text("lbl_mons", "• Presets de Monstros (Inimigos):", 16, mon_sec_y, COLOR_TEXT_MAIN, 9, True, text_cache)

        search_bar_y = mon_sec_y - 20
        search_input_w = panel_w - 32 - 38
        search_cx = 16 + search_input_w / 2
        self.__search_input.draw(search_cx, search_bar_y, search_input_w, 24, text_cache)

        # Botão de Lupa [🔍]
        btn_search_x = panel_w - 16 - 16
        arcade.draw_rect_filled(arcade.XYWH(btn_search_x, search_bar_y, 32, 24), (35, 48, 68, 255))
        arcade.draw_rect_outline(arcade.XYWH(btn_search_x, search_bar_y, 32, 24), COLOR_ACCENT_GOLD, 1)
        self._render_text("btn_search_ico", "🔍", btn_search_x, search_bar_y, COLOR_ACCENT_GOLD, 10, True, text_cache, anchor_x="center")
        return search_bar_y

    def _draw_monster_list(self, panel_w: float, list_top_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        list_w = panel_w - 32
        list_left = 16.0
        list_bottom_y = list_top_y - self.__visible_height
        self.__last_list_bounds = (list_left, list_top_y, list_w, self.__visible_height)

        # Fundo do Container Rolável
        arcade.draw_rect_filled(
            arcade.XYWH(list_left + list_w / 2, list_top_y - self.__visible_height / 2, list_w, self.__visible_height),
            (15, 20, 28, 255),
        )
        arcade.draw_rect_outline(
            arcade.XYWH(list_left + list_w / 2, list_top_y - self.__visible_height / 2, list_w, self.__visible_height),
            COLOR_PANEL_BORDER,
            1,
        )

        total_item_h = self.__item_height + self.__item_gap
        has_scrollbar = (len(self.__filtered_monsters) * total_item_h > self.__visible_height)
        card_w = list_w - (14 if has_scrollbar else 8)
        card_cx = list_left + 4 + card_w / 2

        if not self.__filtered_monsters:
            msg = (
                f"Nenhum monstro encontrado para '{self.__search_query}'"
                if self.__search_query
                else "Nenhum preset de monstro carregado."
            )
            self._render_text(
                "mon_list_empty",
                msg[:45],
                list_left + list_w / 2,
                list_top_y - self.__visible_height / 2,
                COLOR_TEXT_MUTED,
                9,
                False,
                text_cache,
                anchor_x="center",
            )
        else:
            for idx, mon in enumerate(self.__filtered_monsters):
                self._draw_monster_card(
                    mon=mon,
                    idx=idx,
                    card_cx=card_cx,
                    card_w=card_w,
                    total_item_h=total_item_h,
                    list_top_y=list_top_y,
                    list_bottom_y=list_bottom_y,
                    text_cache=text_cache,
                )

        if has_scrollbar:
            self._draw_scrollbar(list_left, list_top_y, list_w, total_item_h)

        return list_bottom_y

    def _draw_monster_card(
        self,
        mon: Dict[str, Any],
        idx: int,
        card_cx: float,
        card_w: float,
        total_item_h: float,
        list_top_y: float,
        list_bottom_y: float,
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        item_top = list_top_y + self.__scroll_offset - idx * total_item_h - 4
        item_cy = item_top - self.__item_height / 2
        item_bottom = item_top - self.__item_height

        # Clipping / Descarte de itens fora do viewport visível
        if item_bottom > list_top_y or item_top < list_bottom_y:
            return

        mid = mon["uid"]
        qty = self.__monster_counts.get(mid, 0)

        # Cartão do Monstro
        card_bg = COLOR_CARD_BG_SELECTED if qty > 0 else COLOR_CARD_BG
        card_bd = COLOR_ACCENT_GOLD if qty > 0 else (45, 60, 85, 180)
        arcade.draw_rect_filled(arcade.XYWH(card_cx, item_cy, card_w, self.__item_height), card_bg)
        arcade.draw_rect_outline(arcade.XYWH(card_cx, item_cy, card_w, self.__item_height), card_bd, 1.5 if qty > 0 else 1)

        # 1. Miniatura / Token Dark Fantasy via SpriteFactory
        token_cx = card_cx - card_w / 2 + 18
        SpriteFactory.draw_tactical_token(
            name=mon.get("name", mid),
            is_player=False,
            x=token_cx,
            y=item_cy,
            radius=12.0,
            is_alive=True,
            is_hidden=False,
            is_selected=(qty > 0),
            text_cache=text_cache,
            token_key=f"cfg_tok_{mid}",
        )

        # 2. Informações Textuais (Nome e Estatísticas CR / HP / CA)
        text_x = token_cx + 18
        mon_name = mon.get("name", mid.title())
        name_color = (255, 138, 128, 255) if qty > 0 else (230, 235, 245, 255)
        self._render_text(
            f"m_name_{mid}",
            mon_name[:22],
            text_x,
            item_cy + 7,
            name_color,
            8,
            True,
            text_cache,
        )

        cr_val = mon.get("cr", 0)
        hp_val = mon.get("max_hp", 10)
        ac_val = mon.get("armor_class", 10)
        mon_stats = f"CR {cr_val} • HP {hp_val} • CA {ac_val}"
        self._render_text(
            f"m_stat_{mid}",
            mon_stats,
            text_x,
            item_cy - 7,
            COLOR_TEXT_MUTED,
            7,
            False,
            text_cache,
        )

        # 3. Controles de Quantidade [-] [qtd] [+]
        card_right = card_cx + card_w / 2
        bm_x = card_right - 62
        qty_x = card_right - 40
        bp_x = card_right - 18

        # [-]
        arcade.draw_rect_filled(arcade.XYWH(bm_x, item_cy, 18, 18), COLOR_BTN_BG)
        self._render_text(f"b_m_min_{mid}", "-", bm_x, item_cy, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")

        # [qtd]
        arcade.draw_rect_filled(arcade.XYWH(qty_x, item_cy, 22, 18), (18, 24, 34, 255))
        qty_color = COLOR_ACCENT_GOLD if qty > 0 else COLOR_TEXT_WHITE
        self._render_text(
            f"val_mqty_{mid}",
            str(qty),
            qty_x,
            item_cy,
            qty_color,
            8,
            True,
            text_cache,
            anchor_x="center",
        )

        # [+]
        arcade.draw_rect_filled(arcade.XYWH(bp_x, item_cy, 18, 18), COLOR_BTN_BG)
        self._render_text(f"b_m_plus_{mid}", "+", bp_x, item_cy, COLOR_ACCENT_GOLD, 9, True, text_cache, anchor_x="center")

    def _draw_scrollbar(self, list_left: float, list_top_y: float, list_w: float, total_item_h: float) -> None:
        track_x = list_left + list_w - 6
        track_w = 6.0
        track_h = self.__visible_height - 8.0
        track_cy = list_top_y - self.__visible_height / 2
        arcade.draw_rect_filled(arcade.XYWH(track_x, track_cy, track_w, track_h), (25, 32, 45, 200))

        total_content_height = len(self.__filtered_monsters) * total_item_h
        thumb_h = max(20.0, track_h * (self.__visible_height / total_content_height))
        scroll_ratio = self.__scroll_offset / self.max_scroll if self.max_scroll > 0 else 0.0
        track_travel = track_h - thumb_h
        thumb_top_y = (list_top_y - 4) - scroll_ratio * track_travel
        thumb_cy = thumb_top_y - thumb_h / 2

        thumb_col = COLOR_ACCENT_GOLD if self.__is_dragging_scrollbar else (70, 95, 130, 220)
        arcade.draw_rect_filled(arcade.XYWH(track_x, thumb_cy, track_w, thumb_h), thumb_col)

    def _draw_error_and_submit(self, panel_w: float, list_bottom_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        # Mensagem de Erro
        if self.__error_message:
            err_y = list_bottom_y - 16
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, err_y, panel_w - 32, 22), COLOR_ERROR_BG)
            self._render_text(
                "wiz_err",
                f"⚠️ {self.__error_message}",
                panel_w / 2,
                err_y,
                (255, 215, 0, 255),
                8,
                True,
                text_cache,
                anchor_x="center",
            )

        # Botão "➡️ Posicionar no Mapa"
        btn_next_y = 32
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_next_y, panel_w - 40, 34), COLOR_SUCCESS_BG)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_next_y, panel_w - 40, 34), COLOR_SUCCESS_BORDER, 2)
        self._render_text(
            "b_go_stage2",
            "➡️ POSICIONAR NO MAPA (ETAPA 2)",
            panel_w / 2,
            btn_next_y,
            COLOR_TEXT_WHITE,
            10,
            True,
            text_cache,
            anchor_x="center",
        )

    def draw_preview(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        text_cache: Dict[str, arcade.Text],
        texture_cache: Dict[str, arcade.Texture],
    ) -> None:
        """Desenha a área de pré-visualização do lado direito na Etapa 1."""
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), (12, 16, 22, 255))

        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, 36), (18, 24, 34, 255))
        arcade.draw_line(vx, vy + vh - 36, vx + vw, vy + vh - 36, (50, 65, 90, 200), 1)
        self._render_text("wiz_prev_hdr", "🗺️ PRÉ-VISUALIZAÇÃO DO MAPA & COMBATENTES", vx + 16, vy + vh - 18, COLOR_TEXT_TITLE, 10, True, text_cache)

        cur_map = self.current_map_info
        map_path = cur_map.get("path")
        is_tilemap = (self.__map_type == "tilemap")

        preview_h = vh * 0.46
        preview_w = vw - 40
        preview_cx = vx + vw / 2
        preview_cy = vy + vh - 36 - preview_h / 2 - 16

        # Fundo do Preview
        arcade.draw_rect_filled(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (18, 24, 34, 255))

        if is_tilemap and map_path:
            # Renderização de TileMap Dinâmico com Aspect-Fit Proporcional
            tile_map = None
            if map_path in self.__tilemap_cache:
                tile_map = self.__tilemap_cache[map_path]
            else:
                try:
                    tile_map = TileMap.from_file(map_path)
                    self.__tilemap_cache[map_path] = tile_map
                except Exception as e:
                    logger.warning(f"Erro ao carregar preview do TileMap '{map_path}': {e}")

            if tile_map is not None:
                if map_path not in self.__tilemap_renderers:
                    try:
                        self.__tilemap_renderers[map_path] = TileMapRenderer(tile_map=tile_map)
                    except Exception as e:
                        logger.warning(f"Erro ao instanciar TileMapRenderer para preview: {e}")

                renderer = self.__tilemap_renderers.get(map_path)
                if renderer is not None:
                    native_w = tile_map.width * 32.0
                    native_h = tile_map.height * 32.0
                    scale_factor, rend_w, rend_h, off_x, off_y = GridManager.calculate_aspect_fit(
                        viewport_width=preview_w,
                        viewport_height=preview_h,
                        native_width=native_w,
                        native_height=native_h,
                    )
                    draw_x = preview_cx - preview_w / 2 + off_x
                    draw_y = preview_cy - preview_h / 2 + off_y
                    cell_w = rend_w / tile_map.width
                    cell_h = rend_h / tile_map.height

                    renderer.update_layout(draw_x, draw_y, cell_w, cell_h)
                    renderer.draw(pixelated=True)
                    arcade.draw_rect_outline(arcade.XYWH(draw_x + rend_w / 2, draw_y + rend_h / 2, rend_w, rend_h), (70, 95, 130, 220), 1.5)

                    # Desenha a grade tática configurada independente sobreposta ao preview
                    grid_cols = max(1, self.__columns)
                    grid_rows = max(1, round(grid_cols * (rend_h / rend_w)))
                    grid_cell_w = rend_w / float(grid_cols)
                    grid_cell_h = rend_h / float(grid_rows)
                    grid_color = (130, 205, 255, 75)
                    for c in range(grid_cols + 1):
                        lx = draw_x + float(c) * grid_cell_w
                        arcade.draw_line(lx, draw_y, lx, draw_y + rend_h, grid_color, 1.0)
                    for r in range(grid_rows + 1):
                        ly = draw_y + float(r) * grid_cell_h
                        arcade.draw_line(draw_x, ly, draw_x + rend_w, ly, grid_color, 1.0)
                else:
                    self._render_text("wiz_no_tm", f"🧩 Tileset {tile_map.width}x{tile_map.height}", preview_cx, preview_cy, COLOR_TEXT_CYAN, 10, True, text_cache, anchor_x="center")
            else:
                self._render_text("wiz_no_tex", "Layout JSON do Tilemap", preview_cx, preview_cy, COLOR_TEXT_MUTED, 10, False, text_cache, anchor_x="center")
        else:
            # Renderização de Imagem Estática com Aspect-Fit
            tex = None
            if map_path and not str(map_path).lower().endswith((".json", ".xml", ".txt", ".csv")):
                resolved = str(os.path.abspath(map_path)) if os.path.isfile(map_path) else map_path
                if resolved not in texture_cache:
                    try:
                        if os.path.isfile(resolved):
                            texture_cache[resolved] = arcade.load_texture(resolved)
                        else:
                            texture_cache[resolved] = None
                    except Exception:
                        texture_cache[resolved] = None
                tex = texture_cache.get(resolved)

            if tex is not None:
                arcade.draw_texture_rect(tex, arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h))
                arcade.draw_rect_outline(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (70, 95, 130, 220), 2)
            else:
                arcade.draw_rect_filled(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (25, 35, 45, 255))
                self._render_text("wiz_no_tex", "Miniatura do Mapa", preview_cx, preview_cy, COLOR_TEXT_MUTED, 11, False, text_cache, anchor_x="center")

        # Cartão de Resumo
        card_y = preview_cy - preview_h / 2 - 16
        card_h = card_y - 20
        card_cy = card_y - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(preview_cx, card_cy, preview_w, card_h), (16, 22, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(preview_cx, card_cy, preview_w, card_h), (50, 65, 90, 200), 1)

        self._render_text("wiz_res_t", "RESUMO DO ENCONTRO EM CRIAÇÃO", vx + 32, card_y - 18, COLOR_TEXT_TITLE, 9, True, text_cache)

        num_pcs = len(self.__selected_character_uids)
        num_mons = sum(self.__monster_counts.values())
        tot = num_pcs + num_mons

        map_type_label = "🧩 Tileset Modular Dinâmico" if is_tilemap else "🖼️ Imagem Fixa Estática"
        self._render_text("wiz_res_mtype", f"• Tipo de Mapa: {map_type_label}", vx + 32, card_y - 38, COLOR_ACCENT_GOLD if is_tilemap else COLOR_TEXT_CYAN, 8, True, text_cache)
        self._render_text("wiz_res_p", f"• Jogadores Selecionados: {num_pcs}", vx + 32, card_y - 56, COLOR_TEXT_CYAN, 8, False, text_cache)
        self._render_text("wiz_res_m", f"• Monstros Instanciados: {num_mons}", vx + 32, card_y - 74, (255, 138, 128, 255), 8, False, text_cache)
        self._render_text("wiz_res_g", f"• Grade Tática: {self.__columns} colunas • {self.__feet_per_square} ft/quadrado", vx + 32, card_y - 92, COLOR_TEXT_MAIN, 8, False, text_cache)
        self._render_text("wiz_res_tot", f"• Total de Combatentes: {tot}", vx + 32, card_y - 110, (46, 204, 113, 255), 9, True, text_cache)

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
        cached = cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y="center",
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        try:
            cached.draw()
        except Exception:
            pass

    # --- Tratamento de Eventos de Mouse e Rolagem ---

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """
        Processa a rolagem do mouse sobre o container de monstros.
        scroll_y > 0 significa rolar para cima (reduz scroll_offset), scroll_y < 0 rola para baixo.
        """
        list_l, list_t, list_w, list_h = self.__last_list_bounds
        if list_l <= x <= list_l + list_w and list_t - list_h <= y <= list_t:
            step = 30.0
            new_offset = self.__scroll_offset - (scroll_y * step)
            self.scroll_offset = new_offset
            return True
        return False

    def handle_mouse_press(self, x: float, y: float, panel_w: float, top_y: float) -> Optional[str]:
        """Processa cliques no formulário e na listagem rolável de monstros."""
        # 1. Inputs de Texto
        input_clicked = self._handle_input_clicks(x, y)
        if input_clicked:
            return None

        sec_y = top_y - 18
        lbl_t_y = sec_y - 24
        box_t_y = lbl_t_y - 18
        lbl_d_y = box_t_y - 22
        box_d_y = lbl_d_y - 18
        map_sec_y = box_d_y - 24
        tab_y = map_sec_y - 20
        map_row_y = tab_y - 24
        grid_y = map_row_y - 28
        pc_sec_y = grid_y - 28
        pc_list_top = pc_sec_y - 16
        mon_sec_y = pc_list_top - min(len(self.__available_characters), 3) * 24 - 10
        search_bar_y = mon_sec_y - 20

        # 2. Abas de Tipo de Mapa [ 🖼️ Mapa por Imagem ] | [ 🧩 Mapa por Tileset ]
        if self._handle_map_tab_click(x, y, panel_w, tab_y):
            return None

        # 3. Seletor de Mapa [◀] [Nome] [▶]
        if self._handle_map_selector_click(x, y, panel_w, map_row_y):
            return None

        # 4. Steppers de Grade
        if self._handle_grid_steppers_click(x, y, grid_y):
            return None

        # 5. Checkboxes de Personagens
        if self._handle_pc_checkboxes_click(x, y, panel_w, pc_list_top):
            return None

        # 6. Botão de Lupa [🔍]
        if self._handle_monster_search_click(x, y, panel_w, search_bar_y):
            return None

        # 7. Lista Rolável e Scrollbar
        if self._handle_monster_list_clicks(x, y):
            return None

        # 8. Botão Avançar "➡️ Posicionar no Mapa"
        btn_next_y = 32
        if abs(y - btn_next_y) <= 18 and abs(x - panel_w / 2) <= (panel_w - 40) / 2:
            is_valid, err = self.validate()
            if is_valid:
                self.__error_message = None
                return "PROCEED_TO_STAGE_2"
            else:
                self.__error_message = err
                return None

        return None

    def _handle_input_clicks(self, x: float, y: float) -> bool:
        if self.__search_input.handle_mouse_press(x, y):
            self.__title_input.blur()
            self.__description_input.blur()
            if not self.__search_input.text and self.__search_query:
                self.apply_monster_filter("")
            return True

        if self.__title_input.handle_mouse_press(x, y):
            self.__description_input.blur()
            self.__search_input.blur()
            return True

        if self.__description_input.handle_mouse_press(x, y):
            self.__title_input.blur()
            self.__search_input.blur()
            return True

        self.__title_input.blur()
        self.__description_input.blur()
        self.__search_input.blur()
        return False

    def _handle_map_tab_click(self, x: float, y: float, panel_w: float, tab_y: float) -> bool:
        if abs(y - tab_y) <= 12:
            tab_w = (panel_w - 38) / 2.0
            tab_img_x = 16.0 + tab_w / 2.0
            tab_tile_x = 16.0 + tab_w + 6.0 + tab_w / 2.0
            if abs(x - tab_img_x) <= tab_w / 2.0:
                self.map_type = "image"
                return True
            elif abs(x - tab_tile_x) <= tab_w / 2.0:
                self.map_type = "tilemap"
                return True
        return False

    def _cycle_map(self, delta: int) -> None:
        """Avança ou retrocede na lista de mapas ativos de acordo com o modo."""
        if self.__map_type == "tilemap":
            if self.__available_tilemaps:
                self.selected_tilemap_index = self.__selected_tilemap_index + delta
        else:
            if self.__available_image_maps:
                self.selected_image_index = self.__selected_image_index + delta

    def _handle_map_selector_click(self, x: float, y: float, panel_w: float, map_row_y: float) -> bool:
        b_prev_m_x = 30
        if abs(y - map_row_y) <= 12 and abs(x - b_prev_m_x) <= 13:
            self._cycle_map(-1)
            return True

        map_box_w = panel_w - 180
        map_box_x = 30 + 13 + map_box_w / 2 + 4
        b_next_m_x = map_box_x + map_box_w / 2 + 17
        if abs(y - map_row_y) <= 12 and abs(x - b_next_m_x) <= 13:
            self._cycle_map(1)
            return True

        return False

    def _handle_grid_steppers_click(self, x: float, y: float, grid_y: float) -> bool:
        b_c_min_x = 65
        if abs(y - grid_y) <= 11 and abs(x - b_c_min_x) <= 11:
            self.columns = max(5, self.__columns - 1)
            return True

        b_c_plus_x = b_c_min_x + 48
        if abs(y - grid_y) <= 11 and abs(x - b_c_plus_x) <= 11:
            self.columns = min(60, self.__columns + 1)
            return True

        feet_lbl_x = b_c_plus_x + 30
        b_f_min_x = feet_lbl_x + 45
        if abs(y - grid_y) <= 11 and abs(x - b_f_min_x) <= 11:
            self.feet_per_square = max(1, self.__feet_per_square - 5) if self.__feet_per_square > 5 else max(1, self.__feet_per_square - 1)
            return True

        b_f_plus_x = b_f_min_x + 48
        if abs(y - grid_y) <= 11 and abs(x - b_f_plus_x) <= 11:
            self.feet_per_square = self.__feet_per_square + 5 if self.__feet_per_square >= 5 else 5
            return True

        return False

    def _handle_pc_checkboxes_click(self, x: float, y: float, panel_w: float, pc_list_top: float) -> bool:
        for idx, char in enumerate(self.__available_characters[:3]):
            cy = pc_list_top - idx * 24
            if abs(y - cy) <= 12 and abs(x - panel_w / 2) <= (panel_w - 32) / 2:
                cid = char["uid"]
                self.toggle_character(cid)
                return True
        return False

    def _handle_monster_search_click(self, x: float, y: float, panel_w: float, search_bar_y: float) -> bool:
        btn_search_x = panel_w - 16 - 16
        if abs(y - search_bar_y) <= 12 and abs(x - btn_search_x) <= 16:
            self.apply_monster_filter(self.__search_input.text)
            return True
        return False

    def _handle_monster_list_clicks(self, x: float, y: float) -> bool:
        list_l, list_t, list_w, list_h = self.__last_list_bounds
        list_bottom_y = list_t - list_h

        total_item_h = self.__item_height + self.__item_gap
        has_scrollbar = (len(self.__filtered_monsters) * total_item_h > self.__visible_height)
        card_w = list_w - (14 if has_scrollbar else 8)
        card_cx = list_l + 4 + card_w / 2

        # Clique na Scrollbar
        if has_scrollbar:
            track_x = list_l + list_w - 6
            track_h = self.__visible_height - 8.0
            total_content_height = len(self.__filtered_monsters) * total_item_h
            thumb_h = max(20.0, track_h * (self.__visible_height / total_content_height))
            track_travel = track_h - thumb_h

            if abs(x - track_x) <= 8 and (list_bottom_y <= y <= list_t):
                self.__is_dragging_scrollbar = True
                self.__scrollbar_drag_start_y = y
                self.__scrollbar_drag_start_offset = self.__scroll_offset
                click_ratio = max(0.0, min(1.0, ((list_t - 4 - thumb_h / 2) - y) / max(1.0, track_travel)))
                self.scroll_offset = click_ratio * self.max_scroll
                return True

        # Clique nos itens / steppers dentro do viewport
        if list_l <= x <= list_l + list_w and list_bottom_y <= y <= list_t:
            for idx, mon in enumerate(self.__filtered_monsters):
                item_top = list_t + self.__scroll_offset - idx * total_item_h - 4
                item_cy = item_top - self.__item_height / 2
                item_bottom = item_top - self.__item_height

                if item_bottom > list_t or item_top < list_bottom_y:
                    continue

                if abs(y - item_cy) <= self.__item_height / 2:
                    mid = mon["uid"]
                    card_right = card_cx + card_w / 2
                    bm_x = card_right - 62
                    bp_x = card_right - 18

                    # [-]
                    if abs(x - bm_x) <= 10:
                        self.decrement_monster(mid)
                        return True

                    # [+]
                    if abs(x - bp_x) <= 10:
                        self.increment_monster(mid)
                        return True

        return False

    def handle_mouse_drag(self, x: float, y: float) -> bool:
        """Processa arraste da barra de rolagem e seleção de texto nos inputs."""
        if self.__is_dragging_scrollbar and self.max_scroll > 0:
            list_l, list_t, list_w, list_h = self.__last_list_bounds
            total_item_h = self.__item_height + self.__item_gap
            total_content_height = len(self.__filtered_monsters) * total_item_h
            track_h = self.__visible_height - 8.0
            thumb_h = max(20.0, track_h * (self.__visible_height / total_content_height))
            track_travel = track_h - thumb_h

            delta_y = self.__scrollbar_drag_start_y - y
            delta_ratio = delta_y / max(1.0, track_travel)
            new_offset = self.__scrollbar_drag_start_offset + delta_ratio * self.max_scroll
            self.scroll_offset = new_offset
            return True

        if self.__title_input.is_focused:
            return self.__title_input.handle_mouse_drag(x, y)
        if self.__description_input.is_focused:
            return self.__description_input.handle_mouse_drag(x, y)
        if self.__search_input.is_focused:
            return self.__search_input.handle_mouse_drag(x, y)
        return False

    def handle_mouse_release(self, x: float, y: float) -> None:
        """Finaliza arraste de scrollbar ou de seleção."""
        self.__is_dragging_scrollbar = False
        self.__title_input.handle_mouse_release(x, y)
        self.__description_input.handle_mouse_release(x, y)
        self.__search_input.handle_mouse_release(x, y)

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        """Processa atalhos de teclado e acionamento da busca por ENTER."""
        if self.__search_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.RETURN):
                self.apply_monster_filter(self.__search_input.text)
                return True
            if symbol == arcade.key.ESCAPE:
                self.__search_input.blur()
                return True
            res = self.__search_input.handle_key_press(symbol, modifiers)
            if not self.__search_input.text and self.__search_query:
                self.apply_monster_filter("")
            return res

        if self.__title_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.TAB):
                self.__title_input.blur()
                self.__description_input.focus()
                return True
            return self.__title_input.handle_key_press(symbol, modifiers)

        if self.__description_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.TAB):
                self.__description_input.blur()
                self.__search_input.focus()
                return True
            return self.__description_input.handle_key_press(symbol, modifiers)

        return False

    def handle_key_release(self, symbol: int, modifiers: int) -> None:
        self.__title_input.handle_key_release(symbol, modifiers)
        self.__description_input.handle_key_release(symbol, modifiers)
        self.__search_input.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        if self.__search_input.is_focused:
            return self.__search_input.handle_text_input(text)
        if self.__title_input.is_focused:
            return self.__title_input.handle_text_input(text)
        if self.__description_input.is_focused:
            return self.__description_input.handle_text_input(text)
        return False
