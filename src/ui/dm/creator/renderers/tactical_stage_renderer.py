import logging
import os
from typing import Dict, Any
import arcade
from ....utils.sprite_utils import SpriteFactory
from ....utils.ui_constants import Colors, Typography, Dimensions, Spacing

logger = logging.getLogger(__name__)


class TacticalStageRenderer:
    """
    Renderizador do Palco Tático (Etapa 2 do Criador de Encontros).
    Gerencia o desenho da barra lateral, mapa de batalha com aspect-fit,
    camada de névoa de guerra, doca de reserva e tokens táticos.
    """

    @staticmethod
    def render_text(
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
                font_name=Typography.FONT_FAMILY_UI,
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

    @staticmethod
    def draw_sidebar(stage: Any, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        """Desenha o painel lateral esquerdo com a lista de staging e botões de ação."""
        sec_y = top_y - 18
        TacticalStageRenderer.render_text("stg_sec_t", "🛠️ ETAPA 2: POSICIONAMENTO TÁTICO", 16, sec_y, Colors.TEXT_GOLD, Typography.SIZE_LABEL - 1, True, text_cache)

        # Dica de Usabilidade
        tip_y = sec_y - 20
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, tip_y, panel_w - 24, 22), Colors.BG_PANEL)
        TacticalStageRenderer.render_text("stg_tip", "💡 Arraste da Reserva para o Grid | Clique Dir / Duplo: Ocultar", panel_w / 2, tip_y, Colors.TEXT_CYAN, Typography.SIZE_MICRO - 2, False, text_cache, anchor_x="center")

        # Painel de Controle de Névoa de Guerra (FogControlPanel)
        fog_next_y = stage.fog_panel.draw(panel_w, tip_y - 14)

        # Roster de Combatentes com DiscreteScrollList
        list_top = fog_next_y - 4
        feedback_area_h = 30 if (stage.success_message or stage.error_message) else 10
        btn_area_h = 60
        list_h = max(50.0, list_top - feedback_area_h - btn_area_h - 10.0)

        stage.scroll_list.set_bounds(x=12.0, y=list_top, width=panel_w - 24.0, height=list_h)
        stage.scroll_list.items = stage.staging_combatants

        # Renderização dos slots visíveis
        visible_items = stage.scroll_list.visible_items
        for slot_idx, (idx, item) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = stage.scroll_list.get_slot_rect(slot_idx)
            is_placed = item["placed"]
            is_hidden = item["is_hidden"]
            is_player = item["is_player"]
            is_selected = (idx == stage.dragged_combatant_idx)

            if is_selected:
                row_bg = Colors.BG_CARD_ALT
                row_bd = Colors.ACCENT_GOLD
            elif is_placed:
                row_bg = Colors.BG_PANEL
                row_bd = Colors.SUCCESS_BORDER
            else:
                row_bg = Colors.BG_CARD
                row_bd = Colors.BORDER_DEFAULT

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
            name_c = Colors.TEXT_CYAN if is_player else Colors.TEXT_CRIMSON
            TacticalStageRenderer.render_text(f"stg_n_{idx}", item["name"][:14], text_x, slot_cy, name_c, Typography.SIZE_MICRO - 1, True, text_cache)

            # Status de posicionamento
            pos_str = f"[{item['col']},{item['row']}]" if is_placed else "Pendente"
            pos_c = Colors.SUCCESS if is_placed else Colors.TEXT_MUTED
            pos_x = slot_cx + slot_w / 2.0 - 52.0
            TacticalStageRenderer.render_text(f"stg_p_{idx}", pos_str, pos_x, slot_cy, pos_c, Typography.SIZE_MICRO - 2, True, text_cache, anchor_x="center")

            # Alternador de visibilidade
            eye_s = "👁️❌" if is_hidden else "👁️"
            eye_x = slot_cx + slot_w / 2.0 - 14.0
            TacticalStageRenderer.render_text(f"stg_eye_{idx}", eye_s, eye_x, slot_cy, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, False, text_cache, anchor_x="center")

        if len(stage.staging_combatants) > stage.scroll_list.visible_item_count:
            stage.scroll_list._draw_scroll_indicator(text_cache)

        # Feedback
        feedback_y = list_top - list_h - 14
        if stage.success_message:
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, feedback_y, panel_w - 24, 24), Colors.SUCCESS)
            TacticalStageRenderer.render_text("stg_succ", f"✅ {stage.success_message[:38]}", panel_w / 2, feedback_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, True, text_cache, anchor_x="center")
        elif stage.error_message:
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, feedback_y, panel_w - 24, 24), Colors.DANGER_BORDER)
            TacticalStageRenderer.render_text("stg_err_2", f"⚠️ {stage.error_message[:38]}", panel_w / 2, feedback_y, Colors.TEXT_GOLD, Typography.SIZE_MICRO - 1, True, text_cache, anchor_x="center")

        # Botões de Ação
        if stage.is_editing:
            btn_row1_y = 54
            btn_row2_y = 20
            btn_w = (panel_w - 36) / 2

            # ⬅️ Voltar
            b_back_x = 12 + btn_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_back_x, btn_row1_y, btn_w - 4, 28), Colors.BTN_DEFAULT_BG)
            arcade.draw_rect_outline(arcade.XYWH(b_back_x, btn_row1_y, btn_w - 4, 28), Colors.BTN_DEFAULT_BORDER, 1)
            TacticalStageRenderer.render_text("b_stg_back", "⬅️ Voltar", b_back_x, btn_row1_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, True, text_cache, anchor_x="center")

            # ❌ Cancelar Edição
            b_cancel_x = 12 + btn_w + btn_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_cancel_x, btn_row1_y, btn_w - 4, 28), Colors.DANGER)
            arcade.draw_rect_outline(arcade.XYWH(b_cancel_x, btn_row1_y, btn_w - 4, 28), Colors.DANGER_BORDER, 1)
            TacticalStageRenderer.render_text("b_stg_cancel", "❌ Cancelar Edição", b_cancel_x, btn_row1_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, True, text_cache, anchor_x="center")

            # 💾 Salvar Alterações
            b_save_w = panel_w - 24
            b_save_x = panel_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_save_x, btn_row2_y, b_save_w, 32), Colors.SUCCESS)
            arcade.draw_rect_outline(arcade.XYWH(b_save_x, btn_row2_y, b_save_w, 32), Colors.SUCCESS_BORDER, 2)
            TacticalStageRenderer.render_text("b_stg_save", "💾 Salvar Alterações", b_save_x, btn_row2_y, Colors.TEXT_PRIMARY, Typography.SIZE_LABEL - 1, True, text_cache, anchor_x="center")

        else:
            btn_y = 36
            btn_w = (panel_w - 36) / 2

            # ⬅️ Voltar
            b_back_x = 12 + btn_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_back_x, btn_y, btn_w - 4, 36), Colors.BTN_DEFAULT_BG)
            arcade.draw_rect_outline(arcade.XYWH(b_back_x, btn_y, btn_w - 4, 36), Colors.BTN_DEFAULT_BORDER, 1)
            TacticalStageRenderer.render_text("b_stg_back", "⬅️ Voltar", b_back_x, btn_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

            # 💾 Salvar Encontro
            b_save_x = 12 + btn_w + btn_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_save_x, btn_y, btn_w - 4, 36), Colors.SUCCESS)
            arcade.draw_rect_outline(arcade.XYWH(b_save_x, btn_y, btn_w - 4, 36), Colors.SUCCESS_BORDER, 2)
            TacticalStageRenderer.render_text("b_stg_save", "💾 Salvar Encontro", b_save_x, btn_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

    @staticmethod
    def draw_canvas(
        stage: Any,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        text_cache: Dict[str, arcade.Text],
        texture_cache: Dict[str, arcade.Texture],
    ) -> None:
        """Desenha o mapa tático, grade sobreposta, dock de reserva e tokens."""
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), Colors.BG_DARK)

        banner_h = 36
        reserve_h = 70
        margin = 10

        avail_w = vw - margin * 2
        avail_h = vh - banner_h - reserve_h - margin * 2

        world_w = stage.grid_manager.map_width if stage.grid_manager else 1920.0
        world_h = stage.grid_manager.map_height if stage.grid_manager else 1080.0

        scale = min(avail_w / world_w, avail_h / world_h)
        draw_w = world_w * scale
        draw_h = world_h * scale

        draw_x = vx + (vw - draw_w) / 2
        draw_y = vy + reserve_h + (vh - banner_h - reserve_h - draw_h) / 2

        stage._last_map_rect = (draw_x, draw_y, draw_w, draw_h)

        # 1. Mapa de Batalha
        columns = stage.config_data.get("columns", 25)
        rows = stage.grid_manager.rows if stage.grid_manager else 14
        cell_w = draw_w / columns
        cell_h = draw_h / rows

        if stage.tile_map is not None and stage.tilemap_renderer is not None:
            tile_w = draw_w / float(stage.tile_map.width)
            tile_h = draw_h / float(stage.tile_map.height)
            stage.tilemap_renderer.update_layout(draw_x, draw_y, tile_w, tile_h)
            stage.tilemap_renderer.draw(pixelated=True)
            arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), Colors.BORDER_DEFAULT, 1.5)
        else:
            map_path = stage.config_data.get("map_path")
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
                arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), Colors.BORDER_DEFAULT, 1.5)
            else:
                arcade.draw_rect_filled(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), Colors.BG_PANEL)

        # 2. Grade Matricial
        grid_color = Colors.GRID_LINE

        for c in range(columns + 1):
            lx = draw_x + c * cell_w
            arcade.draw_line(lx, draw_y, lx, draw_y + draw_h, grid_color, 1.2)

        for r in range(rows + 1):
            ly = draw_y + r * cell_h
            arcade.draw_line(draw_x, ly, draw_x + draw_w, ly, grid_color, 1.2)

        # 2.5. Camada de Névoa de Guerra
        fogged_cells = stage.fog_manager.get_fogged_cells()
        if fogged_cells:
            for (f_col, f_row) in fogged_cells:
                if 0 <= f_col < columns and 0 <= f_row < rows:
                    fcx = draw_x + (f_col + 0.5) * cell_w
                    fcy = draw_y + (f_row + 0.5) * cell_h
                    arcade.draw_rect_filled(
                        arcade.XYWH(fcx, fcy, cell_w, cell_h),
                        Colors.FOG_OVERLAY,
                    )
                    arcade.draw_rect_outline(
                        arcade.XYWH(fcx, fcy, cell_w, cell_h),
                        Colors.FOG_BORDER,
                        1.0,
                    )

        # 3. Doca de Reserva
        res_x = vx + margin
        res_y = vy + 6
        res_w = vw - margin * 2
        stage._last_reserve_rect = (res_x, res_y, res_w, reserve_h - 10)

        arcade.draw_rect_filled(arcade.XYWH(res_x + res_w / 2, res_y + (reserve_h - 10) / 2, res_w, reserve_h - 10), Colors.BG_PANEL)
        arcade.draw_rect_outline(arcade.XYWH(res_x + res_w / 2, res_y + (reserve_h - 10) / 2, res_w, reserve_h - 10), Colors.BORDER_DEFAULT, 1.5)
        TacticalStageRenderer.render_text("stg_res_lbl", "📦 BORDA DE SPAWN / TOKENS EM RESERVA (Arraste para o mapa)", res_x + 12, res_y + (reserve_h - 10) - 10, Colors.TEXT_GOLD, Typography.SIZE_MICRO - 2, True, text_cache)

        # 4. Renderização dos Tokens
        token_radius = (min(cell_w, cell_h) * 0.88) / 2.0
        reserve_slot_w = 46.0

        for idx, item in enumerate(stage.staging_combatants):
            is_being_dragged = (idx == stage.dragged_combatant_idx)

            if is_being_dragged:
                cx, cy = stage.drag_pos
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
        title_str = stage.config_data.get("title", "Encontro")
        feet_per_sq = stage.config_data.get("feet_per_square", 5)
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, banner_h), (12, 16, 22, 230))
        arcade.draw_line(vx, vy + vh - banner_h, vx + vw, vy + vh - banner_h, Colors.BORDER_DEFAULT, 1)
        TacticalStageRenderer.render_text("dm_stg_hdr", f"🗺️ PALCO TÁTICO: {title_str[:30]} ({columns} cols • {feet_per_sq}ft)", vx + 16, vy + vh - 18, Colors.TEXT_GOLD, Typography.SIZE_LABEL - 1, True, text_cache)
