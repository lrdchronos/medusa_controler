import logging
from typing import Dict, Any
import arcade
from ....utils.sprite_utils import SpriteFactory
from ....utils.ui_constants import Colors, Typography, Dimensions, Spacing
from .preview_renderer import PreviewRenderer

logger = logging.getLogger(__name__)

# Compatibilidade retroativa com tokens do Design System
COLOR_BG_PRIMARY = Colors.BG_DARK
COLOR_ACCENT_GOLD = Colors.ACCENT_GOLD
COLOR_PC_BLUE = Colors.BTN_PRIMARY_BG
COLOR_MONSTER_RED = Colors.DANGER
COLOR_PANEL_BG = Colors.BG_PANEL
COLOR_PANEL_BORDER = Colors.BORDER_DEFAULT
COLOR_CARD_BG = Colors.BG_CARD
COLOR_CARD_BG_SELECTED = Colors.BG_CARD_ALT
COLOR_TEXT_TITLE = Colors.TEXT_GOLD
COLOR_TEXT_MAIN = Colors.TEXT_PRIMARY
COLOR_TEXT_MUTED = Colors.TEXT_MUTED
COLOR_TEXT_WHITE = Colors.TEXT_PRIMARY
COLOR_TEXT_CYAN = Colors.TEXT_CYAN
COLOR_BTN_BG = Colors.BTN_DEFAULT_BG
COLOR_BTN_BORDER = Colors.BTN_DEFAULT_BORDER
COLOR_SUCCESS_BG = Colors.SUCCESS
COLOR_SUCCESS_BORDER = Colors.SUCCESS_BORDER
COLOR_ERROR_BG = Colors.DANGER_BORDER


class ConfigFormRenderer:
    """
    Renderizador do painel esquerdo do formulário de configuração da Etapa 1
    (título, descrição, tipo de mapa, grid steppers, PJs e monstros).
    """

    @staticmethod
    def draw_form(form: Any, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        """Desenha todo o painel esquerdo da Etapa 1."""
        try:
            if arcade.get_window() is None:
                return
        except Exception:
            return

        sec_y = top_y - 18
        ConfigFormRenderer.draw_header(panel_w, sec_y, text_cache)
        box_d_y = ConfigFormRenderer.draw_text_fields(form, panel_w, sec_y, text_cache)
        map_row_y = ConfigFormRenderer.draw_map_selector(form, panel_w, box_d_y - 24, text_cache)
        grid_y = ConfigFormRenderer.draw_grid_steppers(form, panel_w, map_row_y - 28, text_cache)
        pc_bottom_y = ConfigFormRenderer.draw_character_checkboxes(form, panel_w, grid_y - 28, text_cache)
        search_bar_y = ConfigFormRenderer.draw_monster_search_bar(form, panel_w, pc_bottom_y - 10, text_cache)
        list_bottom_y = ConfigFormRenderer.draw_monster_list(form, panel_w, search_bar_y - 18, text_cache)
        ConfigFormRenderer.draw_error_and_submit(form, panel_w, list_bottom_y, text_cache)

    @staticmethod
    def draw_header(panel_w: float, sec_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        PreviewRenderer.render_text(
            "wiz_sec_t",
            "🛠️ CRIADOR DE ENCONTROS (ETAPA 1: CONFIGURAÇÃO)",
            16,
            sec_y,
            Colors.TEXT_GOLD,
            Typography.SIZE_BADGE,
            True,
            text_cache,
        )

    @staticmethod
    def draw_text_fields(form: Any, panel_w: float, sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        # Título
        lbl_t_y = sec_y - 24
        PreviewRenderer.render_text("lbl_title", "• Título do Encontro:", 16, lbl_t_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache)
        box_t_y = lbl_t_y - 18
        form.title_input.draw(panel_w / 2, box_t_y, panel_w - 32, 26, text_cache)

        # Descrição
        lbl_d_y = box_t_y - 22
        PreviewRenderer.render_text("lbl_desc", "• Descrição do Encontro:", 16, lbl_d_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache)
        box_d_y = lbl_d_y - 18
        form.description_input.draw(panel_w / 2, box_d_y, panel_w - 32, 26, text_cache)
        return box_d_y

    @staticmethod
    def draw_map_selector(form: Any, panel_w: float, map_sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        PreviewRenderer.render_text("lbl_map_sec", "• Mapa & Grade Tática:", 16, map_sec_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache)

        tab_y = map_sec_y - 20
        tab_w = (panel_w - 38) / 2.0
        tab_img_x = 16.0 + tab_w / 2.0
        tab_tile_x = 16.0 + tab_w + 6.0 + tab_w / 2.0

        is_img = (form.map_type == "image")
        is_tile = (form.map_type == "tilemap")

        # Aba Imagem
        img_bg = Colors.BG_CARD_ALT if is_img else Colors.BG_PANEL
        img_bd = Colors.ACCENT_GOLD if is_img else Colors.BORDER_DEFAULT
        img_fg = Colors.TEXT_GOLD if is_img else Colors.TEXT_MUTED
        arcade.draw_rect_filled(arcade.XYWH(tab_img_x, tab_y, tab_w, 22), img_bg)
        arcade.draw_rect_outline(arcade.XYWH(tab_img_x, tab_y, tab_w, 22), img_bd, 1.5 if is_img else 1)
        PreviewRenderer.render_text("tab_img_lbl", "🖼️ Mapa por Imagem", tab_img_x, tab_y, img_fg, Typography.SIZE_MICRO - 1, is_img, text_cache, anchor_x="center")

        # Aba Tileset
        tile_bg = Colors.BG_CARD_ALT if is_tile else Colors.BG_PANEL
        tile_bd = Colors.ACCENT_GOLD if is_tile else Colors.BORDER_DEFAULT
        tile_fg = Colors.TEXT_GOLD if is_tile else Colors.TEXT_MUTED
        arcade.draw_rect_filled(arcade.XYWH(tab_tile_x, tab_y, tab_w, 22), tile_bg)
        arcade.draw_rect_outline(arcade.XYWH(tab_tile_x, tab_y, tab_w, 22), tile_bd, 1.5 if is_tile else 1)
        PreviewRenderer.render_text("tab_tile_lbl", "🧩 Mapa por Tileset", tab_tile_x, tab_y, tile_fg, Typography.SIZE_MICRO - 1, is_tile, text_cache, anchor_x="center")

        # Linha do Seletor [◀] [Nome do Mapa] [▶]
        map_row_y = tab_y - 24
        cur_map = form.current_map_info

        # [◀]
        b_prev_m_x = 30
        arcade.draw_rect_filled(arcade.XYWH(b_prev_m_x, map_row_y, 26, 24), Colors.BTN_DEFAULT_BG)
        arcade.draw_rect_outline(arcade.XYWH(b_prev_m_x, map_row_y, 26, 24), Colors.BTN_DEFAULT_BORDER, 1)
        PreviewRenderer.render_text("b_map_prev", "◀", b_prev_m_x, map_row_y, Colors.ACCENT_GOLD, Typography.SIZE_LABEL - 1, True, text_cache, anchor_x="center")

        # Caixa do Nome do Mapa
        map_box_w = panel_w - 180
        map_box_x = 30 + 13 + map_box_w / 2 + 4
        arcade.draw_rect_filled(arcade.XYWH(map_box_x, map_row_y, map_box_w, 24), Colors.BG_PANEL)
        arcade.draw_rect_outline(arcade.XYWH(map_box_x, map_row_y, map_box_w, 24), Colors.BORDER_DEFAULT, 1)
        prefix = "🧩 " if is_tile else "🖼️ "
        PreviewRenderer.render_text("map_name_t", f"{prefix}{cur_map['name'][:22]}", map_box_x, map_row_y, Colors.TEXT_CYAN, Typography.SIZE_MICRO - 1, True, text_cache, anchor_x="center")

        # [▶]
        b_next_m_x = map_box_x + map_box_w / 2 + 17
        arcade.draw_rect_filled(arcade.XYWH(b_next_m_x, map_row_y, 26, 24), Colors.BTN_DEFAULT_BG)
        arcade.draw_rect_outline(arcade.XYWH(b_next_m_x, map_row_y, 26, 24), Colors.BTN_DEFAULT_BORDER, 1)
        PreviewRenderer.render_text("b_map_next", "▶", b_next_m_x, map_row_y, Colors.ACCENT_GOLD, Typography.SIZE_LABEL - 1, True, text_cache, anchor_x="center")
        return map_row_y

    @staticmethod
    def draw_grid_steppers(form: Any, panel_w: float, grid_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        PreviewRenderer.render_text("lbl_cols", "Cols:", 16, grid_y, Colors.TEXT_MUTED, Typography.SIZE_MICRO - 1, True, text_cache)

        b_c_min_x = 65
        arcade.draw_rect_filled(arcade.XYWH(b_c_min_x, grid_y, 22, 22), Colors.BTN_DEFAULT_BG)
        PreviewRenderer.render_text("b_c_min", "-", b_c_min_x, grid_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

        arcade.draw_rect_filled(arcade.XYWH(b_c_min_x + 24, grid_y, 30, 22), Colors.BG_DARK)
        PreviewRenderer.render_text("val_cols", str(form.columns), b_c_min_x + 24, grid_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

        b_c_plus_x = b_c_min_x + 48
        arcade.draw_rect_filled(arcade.XYWH(b_c_plus_x, grid_y, 22, 22), Colors.BTN_DEFAULT_BG)
        PreviewRenderer.render_text("b_c_plus", "+", b_c_plus_x, grid_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

        feet_lbl_x = b_c_plus_x + 30
        PreviewRenderer.render_text("lbl_feet", "Ft/sq:", feet_lbl_x, grid_y, Colors.TEXT_MUTED, Typography.SIZE_MICRO - 1, True, text_cache)

        b_f_min_x = feet_lbl_x + 45
        arcade.draw_rect_filled(arcade.XYWH(b_f_min_x, grid_y, 22, 22), Colors.BTN_DEFAULT_BG)
        PreviewRenderer.render_text("b_f_min", "-", b_f_min_x, grid_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

        arcade.draw_rect_filled(arcade.XYWH(b_f_min_x + 24, grid_y, 26, 22), Colors.BG_DARK)
        PreviewRenderer.render_text("val_feet", str(form.feet_per_square), b_f_min_x + 24, grid_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

        b_f_plus_x = b_f_min_x + 48
        arcade.draw_rect_filled(arcade.XYWH(b_f_plus_x, grid_y, 22, 22), Colors.BTN_DEFAULT_BG)
        PreviewRenderer.render_text("b_f_plus", "+", b_f_plus_x, grid_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")
        return grid_y

    @staticmethod
    def draw_character_checkboxes(form: Any, panel_w: float, pc_sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        PreviewRenderer.render_text("lbl_pcs", "• Personagens dos Jogadores (PJs):", 16, pc_sec_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache)

        pc_list_top = pc_sec_y - 16
        chars = form.available_characters
        count_shown = min(len(chars), 5)
        pc_list_h = count_shown * (form.pc_item_height + form.pc_item_spacing)
        pc_list_w = panel_w - 32
        pc_list_left = 16.0

        if not chars:
            return pc_list_top

        form.pc_scroll_list.set_bounds(pc_list_left, pc_list_top, pc_list_w, pc_list_h)
        form.pc_scroll_list.items = chars

        visible_items = form.pc_scroll_list.visible_items
        for slot_idx, (idx, char) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = form.pc_scroll_list.get_slot_rect(slot_idx)
            is_checked = char["uid"] in form.selected_character_uids

            slot_bg = Colors.BG_CARD_ALT if is_checked else Colors.BG_PANEL
            arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), slot_bg)
            slot_bd = Colors.ACCENT_GOLD if is_checked else Colors.BORDER_DEFAULT
            arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), slot_bd, 1)

            cb_x = slot_cx - slot_w / 2 + 12
            cb_bg = Colors.BG_CARD_ALT if is_checked else Colors.BG_DARK
            cb_border = Colors.ACCENT_GOLD if is_checked else Colors.BORDER_DEFAULT
            arcade.draw_rect_filled(arcade.XYWH(cb_x, slot_cy, 16, 16), cb_bg)
            arcade.draw_rect_outline(arcade.XYWH(cb_x, slot_cy, 16, 16), cb_border, 1.5)
            if is_checked:
                PreviewRenderer.render_text(f"cb_check_{char['uid']}", "✓", cb_x, slot_cy, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

            char_desc = f"{char['name']} (Nv {char.get('level', 1)} {char.get('class_summary', '')})"
            lbl_color = Colors.TEXT_CYAN if is_checked else Colors.TEXT_MUTED
            PreviewRenderer.render_text(f"char_lbl_{char['uid']}", char_desc[:38], cb_x + 16, slot_cy, lbl_color, Typography.SIZE_MICRO - 1, is_checked, text_cache)

        if len(chars) > form.pc_scroll_list.visible_item_count:
            form.pc_scroll_list._draw_scroll_indicator(text_cache)

        return pc_list_top - pc_list_h

    @staticmethod
    def draw_monster_search_bar(form: Any, panel_w: float, mon_sec_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        PreviewRenderer.render_text("lbl_mons", "• Presets de Monstros (Inimigos):", 16, mon_sec_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, True, text_cache)

        search_bar_y = mon_sec_y - 20
        search_input_w = panel_w - 32 - 38
        search_cx = 16 + search_input_w / 2
        form.search_input.draw(search_cx, search_bar_y, search_input_w, 24, text_cache)

        # Botão de Lupa [🔍]
        btn_search_x = panel_w - 16 - 16
        arcade.draw_rect_filled(arcade.XYWH(btn_search_x, search_bar_y, 32, 24), Colors.BTN_DEFAULT_BG)
        arcade.draw_rect_outline(arcade.XYWH(btn_search_x, search_bar_y, 32, 24), Colors.ACCENT_GOLD, 1)
        PreviewRenderer.render_text("btn_search_ico", "🔍", btn_search_x, search_bar_y, Colors.ACCENT_GOLD, Typography.SIZE_LABEL - 1, True, text_cache, anchor_x="center")
        return search_bar_y

    @staticmethod
    def draw_monster_list(form: Any, panel_w: float, list_top_y: float, text_cache: Dict[str, arcade.Text]) -> float:
        list_w = panel_w - 32
        list_left = 16.0
        list_bottom_y = list_top_y - form.visible_height
        form.last_list_bounds = (list_left, list_top_y, list_w, form.visible_height)
        form.scroll_list.set_bounds(list_left, list_top_y, list_w, form.visible_height)
        form.scroll_list.items = form.filtered_monsters

        arcade.draw_rect_filled(
            arcade.XYWH(list_left + list_w / 2, list_top_y - form.visible_height / 2, list_w, form.visible_height),
            Colors.BG_DARK,
        )
        arcade.draw_rect_outline(
            arcade.XYWH(list_left + list_w / 2, list_top_y - form.visible_height / 2, list_w, form.visible_height),
            Colors.BORDER_DEFAULT,
            1,
        )

        filtered = form.filtered_monsters
        if not filtered:
            msg = (
                f"Nenhum monstro encontrado para '{form.search_query}'"
                if form.search_query
                else "Nenhum preset de monstro carregado."
            )
            PreviewRenderer.render_text(
                "mon_list_empty",
                msg[:45],
                list_left + list_w / 2,
                list_top_y - form.visible_height / 2,
                Colors.TEXT_MUTED,
                Typography.SIZE_MICRO,
                False,
                text_cache,
                anchor_x="center",
            )
        else:
            visible_items = form.scroll_list.visible_items
            for slot_idx, (idx, mon) in enumerate(visible_items):
                slot_cx, slot_cy, slot_w, slot_h = form.scroll_list.get_slot_rect(slot_idx)
                ConfigFormRenderer.draw_monster_card(
                    form=form,
                    mon=mon,
                    idx=idx,
                    card_cx=slot_cx,
                    card_cy=slot_cy,
                    card_w=slot_w,
                    card_h=slot_h,
                    text_cache=text_cache,
                )

        if len(filtered) > form.scroll_list.visible_item_count:
            form.scroll_list._draw_scroll_indicator(text_cache)

        return list_bottom_y

    @staticmethod
    def draw_monster_card(
        form: Any,
        mon: Dict[str, Any],
        idx: int,
        card_cx: float,
        card_cy: float,
        card_w: float,
        card_h: float,
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        mid = mon["uid"]
        qty = form.get_monster_count(mid)

        card_bg = Colors.BG_CARD_ALT if qty > 0 else Colors.BG_CARD
        card_bd = Colors.ACCENT_GOLD if qty > 0 else Colors.BORDER_DEFAULT
        arcade.draw_rect_filled(arcade.XYWH(card_cx, card_cy, card_w, card_h), card_bg)
        arcade.draw_rect_outline(arcade.XYWH(card_cx, card_cy, card_w, card_h), card_bd, 1.5 if qty > 0 else 1)

        token_cx = card_cx - card_w / 2 + 18
        SpriteFactory.draw_tactical_token(
            name=mon.get("name", mid),
            is_player=False,
            x=token_cx,
            y=card_cy,
            radius=12.0,
            is_alive=True,
            is_hidden=False,
            is_selected=(qty > 0),
            text_cache=text_cache,
            token_key=f"cfg_tok_{mid}",
        )

        text_x = token_cx + 18
        mon_name = mon.get("name", mid.title())
        name_color = Colors.TEXT_CRIMSON if qty > 0 else Colors.TEXT_PRIMARY
        PreviewRenderer.render_text(
            f"m_name_{mid}",
            mon_name[:22],
            text_x,
            card_cy + 7,
            name_color,
            Typography.SIZE_MICRO - 1,
            True,
            text_cache,
        )

        cr_val = mon.get("cr", 0)
        hp_val = mon.get("max_hp", 10)
        ac_val = mon.get("armor_class", 10)
        mon_stats = f"CR {cr_val} • HP {hp_val} • CA {ac_val}"
        PreviewRenderer.render_text(
            f"m_stat_{mid}",
            mon_stats,
            text_x,
            card_cy - 7,
            Colors.TEXT_MUTED,
            Typography.SIZE_MICRO - 2,
            False,
            text_cache,
        )

        card_right = card_cx + card_w / 2
        bm_x = card_right - 62
        qty_x = card_right - 40
        bp_x = card_right - 18

        # [-]
        arcade.draw_rect_filled(arcade.XYWH(bm_x, card_cy, 18, 18), Colors.BTN_DEFAULT_BG)
        PreviewRenderer.render_text(f"b_m_min_{mid}", "-", bm_x, card_cy, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

        # [qtd]
        arcade.draw_rect_filled(arcade.XYWH(qty_x, card_cy, 22, 18), Colors.BG_DARK)
        qty_color = Colors.ACCENT_GOLD if qty > 0 else Colors.TEXT_PRIMARY
        PreviewRenderer.render_text(
            f"val_mqty_{mid}",
            str(qty),
            qty_x,
            card_cy,
            qty_color,
            Typography.SIZE_MICRO - 1,
            True,
            text_cache,
            anchor_x="center",
        )

        # [+]
        arcade.draw_rect_filled(arcade.XYWH(bp_x, card_cy, 18, 18), Colors.BTN_DEFAULT_BG)
        PreviewRenderer.render_text(f"b_m_plus_{mid}", "+", bp_x, card_cy, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, True, text_cache, anchor_x="center")

    @staticmethod
    def draw_error_and_submit(form: Any, panel_w: float, list_bottom_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        if form.error_message:
            err_y = list_bottom_y - 16
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, err_y, panel_w - 32, 22), Colors.DANGER_BORDER)
            PreviewRenderer.render_text(
                "wiz_err",
                f"⚠️ {form.error_message}",
                panel_w / 2,
                err_y,
                Colors.TEXT_GOLD,
                Typography.SIZE_MICRO - 1,
                True,
                text_cache,
                anchor_x="center",
            )

        btn_next_y = 32
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_next_y, panel_w - 40, 34), Colors.SUCCESS)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_next_y, panel_w - 40, 34), Colors.SUCCESS_BORDER, 2)
        PreviewRenderer.render_text(
            "b_go_stage2",
            "➡️ POSICIONAR NO MAPA (ETAPA 2)",
            panel_w / 2,
            btn_next_y,
            Colors.TEXT_PRIMARY,
            Typography.SIZE_LABEL - 1,
            True,
            text_cache,
            anchor_x="center",
        )
