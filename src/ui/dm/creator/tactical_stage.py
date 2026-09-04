import logging
import os
import math
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import arcade
from ....manager.grid_manager import GridManager
from ....domain.builders.encounter_builder import EncounterBuilder
from ....domain.models.tile_map import TileMap
from ...utils.tilemap_renderer import TileMapRenderer
from ...utils.sprite_utils import SpriteFactory
from ...components.discrete_scroll_list import DiscreteScrollList


logger = logging.getLogger(__name__)


class CreatorTacticalStage:
    """
    Componente especializado para a Etapa 2 do Criador de Encontros (Palco Tático e Posicionamento).
    Gerencia:
      - Instanciação de tokens a partir das seleções da Etapa 1.
      - GridManager sobreposto ao mapa escolhido.
      - Borda/Doca de Reserva de Spawn.
      - Interatividade Drag & Drop com Snap-to-Grid (grid_to_world_center).
      - Controle de visibilidade inicial (is_hidden) via clique duplo ou botão direito.
      - Paginação e listagem de todos os combatentes via DiscreteScrollList.
      - Geração e persistência do arquivo JSON via EncounterBuilder.
    """

    def __init__(self) -> None:
        self.config_data: Dict[str, Any] = {}
        self.staging_combatants: List[Dict[str, Any]] = []
        self.grid_manager: Optional[GridManager] = None
        self.tile_map: Optional[TileMap] = None
        self.tilemap_renderer: Optional[TileMapRenderer] = None

        self.scroll_list: DiscreteScrollList = DiscreteScrollList(item_height=28, spacing=4)

        self.dragged_combatant_idx: Optional[int] = None
        self.drag_pos: Tuple[float, float] = (0.0, 0.0)

        self._last_map_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
        self._last_reserve_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

        self._last_click_time: float = 0.0
        self._last_clicked_idx: Optional[int] = None

        self.error_message: Optional[str] = None
        self.success_message: Optional[str] = None
        self.saved_encounter_path: Optional[str] = None

    def initialize(
        self,
        config_data: Dict[str, Any],
        available_characters: List[Dict[str, Any]],
        available_monsters: List[Dict[str, Any]],
    ) -> None:
        """Configura o palco tático a partir dos dados consolidados do formulário."""
        self.config_data = config_data.copy()
        self.error_message = None
        self.success_message = None
        self.saved_encounter_path = None
        self.dragged_combatant_idx = None

        map_type = self.config_data.get("map_type", "image")
        map_source = self.config_data.get("map_source") or self.config_data.get("map_path")
        columns = config_data.get("columns", 25)
        feet_per_square = config_data.get("feet_per_square", 5)

        if map_type == "tilemap" and map_source:
            try:
                self.tile_map = TileMap.from_file(map_source)
                self.tilemap_renderer = TileMapRenderer(tile_map=self.tile_map)
                self.grid_manager = GridManager(
                    map_width=self.tile_map.width * 32.0,
                    map_height=self.tile_map.height * 32.0,
                    columns=columns,
                    feet_per_square=feet_per_square,
                )
            except Exception as e:
                logger.error(f"Erro ao instanciar TileMap no CreatorTacticalStage: {e}")
                self.tile_map = None
                self.tilemap_renderer = None
                self.grid_manager = GridManager(
                    map_width=1920.0,
                    map_height=1080.0,
                    columns=columns,
                    feet_per_square=feet_per_square,
                )
        else:
            self.tile_map = None
            self.tilemap_renderer = None
            self.grid_manager = GridManager(
                map_width=1920.0,
                map_height=1080.0,
                columns=columns,
                feet_per_square=feet_per_square,
            )

        self.staging_combatants = []

        # 1. Personagens Jogadores
        selected_uids = config_data.get("selected_character_uids", set())
        for char in available_characters:
            if char["uid"] in selected_uids:
                self.staging_combatants.append({
                    "entity_type": "playable_character",
                    "character_id": char["uid"],
                    "monster_id": None,
                    "name": char["name"],
                    "is_player": True,
                    "is_hidden": False,
                    "placed": False,
                    "col": 0,
                    "row": 0,
                })

        # 2. Monstros
        counts = config_data.get("monster_counts", {})
        for mon in available_monsters:
            mid = mon["uid"]
            qty = counts.get(mid, 0)
            base_name = mon["name"]
            for i in range(1, qty + 1):
                instance_name = f"{base_name} {i}" if qty > 1 else base_name
                self.staging_combatants.append({
                    "entity_type": "monster",
                    "character_id": None,
                    "monster_id": mid,
                    "name": instance_name,
                    "is_player": False,
                    "is_hidden": False,
                    "placed": False,
                    "col": 0,
                    "row": 0,
                })

        self.scroll_list.items = self.staging_combatants
        self.scroll_list.reset_scroll()

        logger.info(
            f"CreatorTacticalStage inicializado com {len(self.staging_combatants)} combatentes para o mapa '{config_data.get('map_name')}' (Tipo: {map_type})."
        )

    def save_encounter(self, directory: str = "creations/encounters") -> Optional[Path]:
        """Serializa e grava o encontro no disco."""
        self.error_message = None
        self.success_message = None

        if not self.staging_combatants:
            self.error_message = "Nenhum combatente presente para salvar o encontro!"
            return None

        # Posiciona automaticamente no grid tokens que ficaram na reserva
        columns = self.config_data.get("columns", 25)
        rows = self.grid_manager.rows if self.grid_manager else 14

        for idx, item in enumerate(self.staging_combatants):
            if not item["placed"]:
                item["col"] = idx % columns
                item["row"] = (idx // columns) if item["is_player"] else (rows - 1 - (idx // columns))
                item["placed"] = True

        builder = EncounterBuilder()
        builder.with_metadata(
            title=self.config_data.get("title", "Novo Encontro"),
            description=self.config_data.get("description", ""),
        )
        map_type = self.config_data.get("map_type", "image")
        map_source = self.config_data.get("map_source") or self.config_data.get("map_path", "assets/images/maps/open_field_grass_trees.jpg")
        builder.with_map(map_source=map_source, map_type=map_type)
        builder.with_grid(
            columns=columns,
            feet_per_square=self.config_data.get("feet_per_square", 5),
        )
        builder.with_environment(is_sunlight=self.config_data.get("is_sunlight", False))

        for item in self.staging_combatants:
            if item["is_player"]:
                builder.add_character(
                    character_id=item["character_id"],
                    col=item["col"],
                    row=item["row"],
                    is_hidden=item["is_hidden"],
                )
            else:
                builder.add_monster(
                    monster_id=item["monster_id"],
                    instance_name=item["name"],
                    col=item["col"],
                    row=item["row"],
                    is_hidden=item["is_hidden"],
                )

        try:
            saved_path = builder.save_to_file(directory=directory)
            self.saved_encounter_path = str(saved_path)
            self.success_message = f"Encontro salvo com sucesso: {saved_path.name}"
            logger.info(f"Encontro gravado com sucesso em '{saved_path}'.")
            return saved_path
        except Exception as e:
            self.error_message = f"Erro ao salvar: {e}"
            logger.error(f"Falha ao persistir encontro via EncounterBuilder: {e}")
            return None

    # --- Renderização ---

    def draw_sidebar(self, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        """Desenha o painel lateral esquerdo com a lista de staging e botões de ação."""
        sec_y = top_y - 18
        self._render_text("stg_sec_t", "🛠️ ETAPA 2: POSICIONAMENTO TÁTICO", 16, sec_y, (241, 196, 15, 255), 10, True, text_cache)

        # Dica de Usabilidade
        tip_y = sec_y - 20
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, tip_y, panel_w - 24, 22), (20, 30, 42, 255))
        self._render_text("stg_tip", "💡 Arraste da Reserva para o Grid | Clique Dir / Duplo: Ocultar", panel_w / 2, tip_y, (160, 210, 255, 255), 7, False, text_cache, anchor_x="center")

        # Roster de Combatentes com DiscreteScrollList
        list_top = tip_y - 18
        feedback_area_h = 30 if (self.success_message or self.error_message) else 10
        btn_area_h = 60
        list_h = max(60.0, list_top - feedback_area_h - btn_area_h - 20.0)

        self.scroll_list.set_bounds(x=12.0, y=list_top, width=panel_w - 24.0, height=list_h)
        self.scroll_list.items = self.staging_combatants

        # Renderização dos slots visíveis
        visible_items = self.scroll_list.visible_items
        for slot_idx, (idx, item) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = self.scroll_list.get_slot_rect(slot_idx)
            is_placed = item["placed"]
            is_hidden = item["is_hidden"]
            is_player = item["is_player"]
            is_selected = (idx == self.dragged_combatant_idx)

            if is_selected:
                row_bg = (45, 62, 85, 255)
                row_bd = (241, 196, 15, 255)
            elif is_placed:
                row_bg = (30, 42, 58, 255)
                row_bd = (46, 204, 113, 200)
            else:
                row_bg = (22, 28, 38, 255)
                row_bd = (70, 90, 120, 180)

            arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), row_bg)
            arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), row_bd, 1.5 if is_selected else 1.0)

            # Miniatura do token / ícone
            token_cx = slot_cx - slot_w / 2.0 + 14.0
            SpriteFactory.draw_tactical_token(
                name=item["name"],
                is_player=is_player,
                x=token_cx,
                y=slot_cy,
                radius=10.0,
                is_alive=True,
                is_hidden=is_hidden,
                is_selected=is_selected,
                is_active=False,
                text_cache=text_cache,
                token_key=f"stg_slot_tok_{idx}",
            )

            # Nome do combatente
            text_x = token_cx + 14.0
            name_c = (100, 200, 255, 255) if is_player else (255, 138, 128, 255)
            self._render_text(f"stg_n_{idx}", item["name"][:14], text_x, slot_cy, name_c, 8, True, text_cache)

            # Status de posicionamento (marcador verde se posicionado; cinza/dourado se pendente)
            pos_str = f"[{item['col']},{item['row']}]" if is_placed else "Pendente"
            pos_c = (46, 204, 113, 255) if is_placed else (140, 155, 175, 255)
            pos_x = slot_cx + slot_w / 2.0 - 52.0
            self._render_text(f"stg_p_{idx}", pos_str, pos_x, slot_cy, pos_c, 7, True, text_cache, anchor_x="center")

            # Alternador de visibilidade (is_hidden)
            eye_s = "👁️❌" if is_hidden else "👁️"
            eye_x = slot_cx + slot_w / 2.0 - 14.0
            self._render_text(f"stg_eye_{idx}", eye_s, eye_x, slot_cy, (255, 255, 255, 255), 9, False, text_cache, anchor_x="center")

        # Indicador visual discreto da scroll list
        if len(self.staging_combatants) > self.scroll_list.visible_item_count:
            self.scroll_list._draw_scroll_indicator(text_cache)

        # Feedback
        feedback_y = list_top - list_h - 14
        if self.success_message:
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, feedback_y, panel_w - 24, 24), (27, 77, 62, 255))
            self._render_text("stg_succ", f"✅ {self.success_message[:38]}", panel_w / 2, feedback_y, (163, 228, 215, 255), 8, True, text_cache, anchor_x="center")
        elif self.error_message:
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, feedback_y, panel_w - 24, 24), (120, 40, 31, 255))
            self._render_text("stg_err_2", f"⚠️ {self.error_message[:38]}", panel_w / 2, feedback_y, (255, 215, 0, 255), 8, True, text_cache, anchor_x="center")

        # Botões de Ação
        btn_y = 36
        btn_w = (panel_w - 36) / 2

        # ⬅️ Voltar
        b_back_x = 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_back_x, btn_y, btn_w - 4, 36), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_back_x, btn_y, btn_w - 4, 36), (70, 90, 120, 200), 1)
        self._render_text("b_stg_back", "⬅️ Voltar", b_back_x, btn_y, (236, 240, 241, 255), 9, True, text_cache, anchor_x="center")

        # 💾 Salvar Encontro
        b_save_x = 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_save_x, btn_y, btn_w - 4, 36), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_save_x, btn_y, btn_w - 4, 36), (231, 76, 60, 255), 2)
        self._render_text("b_stg_save", "💾 Salvar Encontro", b_save_x, btn_y, (255, 255, 255, 255), 9, True, text_cache, anchor_x="center")

    def draw_canvas(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        text_cache: Dict[str, arcade.Text],
        texture_cache: Dict[str, arcade.Texture],
    ) -> None:
        """Desenha o mapa tático, grade sobreposta, dock de reserva e tokens."""
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), (12, 16, 22, 255))

        banner_h = 36
        reserve_h = 70
        margin = 10

        avail_w = vw - margin * 2
        avail_h = vh - banner_h - reserve_h - margin * 2

        world_w = self.grid_manager.map_width if self.grid_manager else 1920.0
        world_h = self.grid_manager.map_height if self.grid_manager else 1080.0

        scale = min(avail_w / world_w, avail_h / world_h)
        draw_w = world_w * scale
        draw_h = world_h * scale

        draw_x = vx + (vw - draw_w) / 2
        draw_y = vy + reserve_h + (vh - banner_h - reserve_h - draw_h) / 2

        self._last_map_rect = (draw_x, draw_y, draw_w, draw_h)

        # 1. Mapa de Batalha
        columns = self.config_data.get("columns", 25)
        rows = self.grid_manager.rows if self.grid_manager else 14
        cell_w = draw_w / columns
        cell_h = draw_h / rows

        if self.tile_map is not None and self.tilemap_renderer is not None:
            tile_w = draw_w / float(self.tile_map.width)
            tile_h = draw_h / float(self.tile_map.height)
            self.tilemap_renderer.update_layout(draw_x, draw_y, tile_w, tile_h)
            self.tilemap_renderer.draw(pixelated=True)
            arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (60, 80, 110, 220), 1.5)
        else:
            map_path = self.config_data.get("map_path")
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
                arcade.draw_texture_rect(tex, arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h))
                arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (60, 80, 110, 220), 1.5)
            else:
                arcade.draw_rect_filled(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (24, 32, 28, 255))

        # 2. Grade Matricial (Luminous Steel Cyan)
        grid_color = (130, 205, 255, 175)

        for c in range(columns + 1):
            lx = draw_x + c * cell_w
            arcade.draw_line(lx, draw_y, lx, draw_y + draw_h, grid_color, 1.2)

        for r in range(rows + 1):
            ly = draw_y + r * cell_h
            arcade.draw_line(draw_x, ly, draw_x + draw_w, ly, grid_color, 1.2)

        # 3. Doca de Reserva
        res_x = vx + margin
        res_y = vy + 6
        res_w = vw - margin * 2
        self._last_reserve_rect = (res_x, res_y, res_w, reserve_h - 10)

        arcade.draw_rect_filled(arcade.XYWH(res_x + res_w / 2, res_y + (reserve_h - 10) / 2, res_w, reserve_h - 10), (18, 24, 34, 255))
        arcade.draw_rect_outline(arcade.XYWH(res_x + res_w / 2, res_y + (reserve_h - 10) / 2, res_w, reserve_h - 10), (70, 95, 130, 200), 1.5)
        self._render_text("stg_res_lbl", "📦 BORDA DE SPAWN / TOKENS EM RESERVA (Arraste para o mapa)", res_x + 12, res_y + (reserve_h - 10) - 10, (241, 196, 15, 255), 7, True, text_cache)

        # 4. Renderização dos Tokens
        token_radius = (min(cell_w, cell_h) * 0.88) / 2.0
        reserve_slot_w = 46.0

        for idx, item in enumerate(self.staging_combatants):
            is_being_dragged = (idx == self.dragged_combatant_idx)

            if is_being_dragged:
                cx, cy = self.drag_pos
            elif item["placed"]:
                cx = draw_x + (item["col"] + 0.5) * cell_w
                cy = draw_y + (item["row"] + 0.5) * cell_h
            else:
                cx = res_x + 28 + idx * reserve_slot_w
                cy = res_y + (reserve_h - 10) / 2 - 4

            SpriteFactory.draw_tactical_token(
                name=item["name"],
                is_player=item["is_player"],
                x=cx,
                y=cy,
                radius=token_radius,
                is_alive=True,
                is_hidden=item["is_hidden"],
                is_selected=is_being_dragged,
                is_active=False,
                text_cache=text_cache,
                token_key=f"stg_{idx}",
            )

        # Banner Superior
        title_str = self.config_data.get("title", "Encontro")
        feet_per_sq = self.config_data.get("feet_per_square", 5)
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, banner_h), (12, 16, 22, 230))
        arcade.draw_line(vx, vy + vh - banner_h, vx + vw, vy + vh - banner_h, (50, 65, 90, 200), 1)
        self._render_text("dm_stg_hdr", f"🗺️ PALCO TÁTICO: {title_str[:30]} ({columns} cols • {feet_per_sq}ft)", vx + 16, vy + vh - 18, (241, 196, 15, 255), 10, True, text_cache)

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
        cached.draw()

    # --- Eventos do Palco Tático ---

    def handle_mouse_press(self, x: float, y: float, split_x: float, h: float, button: int) -> Optional[str]:
        """
        Processa cliques na sidebar ou no canvas tático.
        Retorna ações como "RETURN_TO_STAGE_1", "SAVE_ENCOUNTER" ou None.
        """
        if x < split_x:
            header_h = 56
            tab_bar_h = 42
            top_y = h - header_h - tab_bar_h
            return self._handle_sidebar_press(x, y, split_x, top_y)

        return self._handle_canvas_press(x, y, button)

    def _handle_sidebar_press(self, x: float, y: float, panel_w: float, top_y: float) -> Optional[str]:
        # Interação com itens visíveis da DiscreteScrollList
        visible_items = self.scroll_list.visible_items
        for slot_idx, (idx, item) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = self.scroll_list.get_slot_rect(slot_idx)
            left = slot_cx - slot_w / 2.0
            right = slot_cx + slot_w / 2.0
            top = slot_cy + slot_h / 2.0
            bottom = slot_cy - slot_h / 2.0

            if left <= x <= right and bottom <= y <= top:
                eye_x = slot_cx + slot_w / 2.0 - 14.0
                if abs(x - eye_x) <= 15:
                    item["is_hidden"] = not item["is_hidden"]
                    logger.info(f"Combatente '{item['name']}' visibilidade alternada para is_hidden={item['is_hidden']}")
                    return None
                else:
                    # Seleciona para posicionamento tático (Drag & Drop)
                    self.dragged_combatant_idx = idx
                    self.drag_pos = (float(x), float(y))
                    logger.info(f"Combatente '{item['name']}' selecionado na sidebar para posicionamento.")
                    return None

        # Botões Inferiores
        btn_y = 36
        btn_w = (panel_w - 36) / 2

        # ⬅️ Voltar
        b_back_x = 12 + btn_w / 2
        if abs(y - btn_y) <= 18 and abs(x - b_back_x) <= (btn_w - 4) / 2:
            return "RETURN_TO_STAGE_1"

        # 💾 Salvar Encontro
        b_save_x = 12 + btn_w + btn_w / 2
        if abs(y - btn_y) <= 18 and abs(x - b_save_x) <= (btn_w - 4) / 2:
            return "SAVE_ENCOUNTER"

        return None

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """Processa a rolagem discreta na lista lateral de combatentes."""
        return self.scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)

    def _handle_canvas_press(self, x: float, y: float, button: int) -> Optional[str]:
        now = time.time()
        is_double_click = False

        draw_x, draw_y, draw_w, draw_h = self._last_map_rect
        res_x, res_y, res_w, res_h = self._last_reserve_rect

        columns = self.config_data.get("columns", 25)
        rows = self.grid_manager.rows if self.grid_manager else 14
        cell_w = draw_w / columns
        cell_h = draw_h / rows
        radius = (min(cell_w, cell_h) * 0.88) / 2.0
        reserve_slot_w = 46.0

        for idx, item in enumerate(reversed(self.staging_combatants)):
            real_idx = len(self.staging_combatants) - 1 - idx

            if item["placed"]:
                cx = draw_x + (item["col"] + 0.5) * cell_w
                cy = draw_y + (item["row"] + 0.5) * cell_h
            else:
                cx = res_x + 28 + real_idx * reserve_slot_w
                cy = res_y + res_h / 2 - 4

            dist_sq = (x - cx) ** 2 + (y - cy) ** 2
            if dist_sq <= (radius + 6) ** 2:
                if self._last_clicked_idx == real_idx and (now - self._last_click_time) <= 0.35:
                    is_double_click = True

                self._last_click_time = now
                self._last_clicked_idx = real_idx

                # Alternar Visibilidade (Botão Direito ou Duplo Clique)
                if button == arcade.MOUSE_BUTTON_RIGHT or is_double_click:
                    item["is_hidden"] = not item["is_hidden"]
                    logger.info(f"Combatente '{item['name']}' visibilidade alternada para is_hidden={item['is_hidden']}")
                    return None

                # Inicia Drag & Drop (Botão Esquerdo)
                if button == arcade.MOUSE_BUTTON_LEFT:
                    self.dragged_combatant_idx = real_idx
                    self.drag_pos = (float(x), float(y))
                    return None

        return None

    def handle_mouse_drag(self, x: float, y: float) -> None:
        if self.dragged_combatant_idx is not None:
            self.drag_pos = (float(x), float(y))

    def handle_mouse_release(self, x: float, y: float, split_x: float) -> None:
        """Aplica Snap-to-Grid no token arrastado ou retorna para a reserva."""
        if self.dragged_combatant_idx is not None:
            item = self.staging_combatants[self.dragged_combatant_idx]
            draw_x, draw_y, draw_w, draw_h = self._last_map_rect

            # Se soltar sobre o mapa de batalha: Snap-to-Grid
            if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                columns = self.config_data.get("columns", 25)
                rows = self.grid_manager.rows if self.grid_manager else 14
                cell_w = draw_w / columns
                cell_h = draw_h / rows

                col = int(math.floor((x - draw_x) / cell_w))
                row = int(math.floor((y - draw_y) / cell_h))

                clamped_col = max(0, min(columns - 1, col))
                clamped_row = max(0, min(rows - 1, row))

                item["placed"] = True
                item["col"] = clamped_col
                item["row"] = clamped_row
                logger.info(f"Token '{item['name']}' posicionado no grid: [{clamped_col}, {clamped_row}].")
            else:
                item["placed"] = False
                logger.info(f"Token '{item['name']}' retornado para a reserva.")

            self.dragged_combatant_idx = None
