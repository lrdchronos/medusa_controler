import logging
from typing import Optional, Any
import arcade

logger = logging.getLogger(__name__)


class ConfigFormInputHandler:
    """
    Controlador especializado de eventos de entrada (mouse, scroll, teclado)
    para a Etapa 1 do Criador de Encontros.
    """

    @staticmethod
    def handle_mouse_scroll(form: Any, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """Processa a rolagem discreta do mouse sobre o container de PJs ou de monstros."""
        if form.pc_scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y):
            return True
        return form.scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)

    @staticmethod
    def handle_mouse_press(form: Any, x: float, y: float, panel_w: float, top_y: float) -> Optional[str]:
        """Processa cliques no formulário e na listagem rolável de monstros."""
        # 1. Inputs de Texto
        if ConfigFormInputHandler._handle_input_clicks(form, x, y):
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
        chars = form.available_characters
        count_shown = min(len(chars), 5)
        pc_list_h = count_shown * (form.pc_item_height + form.pc_item_spacing)
        pc_bottom_y = pc_list_top - pc_list_h
        mon_sec_y = pc_bottom_y - 10
        search_bar_y = mon_sec_y - 20

        # 2. Abas de Tipo de Mapa [ 🖼️ Mapa por Imagem ] | [ 🧩 Mapa por Tileset ]
        if ConfigFormInputHandler._handle_map_tab_click(form, x, y, panel_w, tab_y):
            return None

        # 3. Seletor de Mapa [◀] [Nome] [▶]
        if ConfigFormInputHandler._handle_map_selector_click(form, x, y, panel_w, map_row_y):
            return None

        # 4. Steppers de Grade
        if ConfigFormInputHandler._handle_grid_steppers_click(form, x, y, grid_y):
            return None

        # 5. Checkboxes de Personagens
        if ConfigFormInputHandler._handle_pc_checkboxes_click(form, x, y, panel_w, pc_list_top):
            return None

        # 6. Botão de Lupa [🔍]
        if ConfigFormInputHandler._handle_monster_search_click(form, x, y, panel_w, search_bar_y):
            return None

        # 7. Lista Rolável e Scrollbar
        if ConfigFormInputHandler._handle_monster_list_clicks(form, x, y):
            return None

        # 8. Botão Avançar "➡️ Posicionar no Mapa"
        btn_next_y = 32
        if abs(y - btn_next_y) <= 18 and abs(x - panel_w / 2) <= (panel_w - 40) / 2:
            is_valid, err = form.validate()
            if is_valid:
                form.error_message = None
                return "PROCEED_TO_STAGE_2"
            else:
                form.error_message = err
                return None

        return None

    @staticmethod
    def _handle_input_clicks(form: Any, x: float, y: float) -> bool:
        if form.search_input.handle_mouse_press(x, y):
            form.title_input.blur()
            form.description_input.blur()
            if not form.search_input.text and form.search_query:
                form.apply_monster_filter("")
            return True

        if form.title_input.handle_mouse_press(x, y):
            form.description_input.blur()
            form.search_input.blur()
            return True

        if form.description_input.handle_mouse_press(x, y):
            form.title_input.blur()
            form.search_input.blur()
            return True

        form.title_input.blur()
        form.description_input.blur()
        form.search_input.blur()
        return False

    @staticmethod
    def _handle_map_tab_click(form: Any, x: float, y: float, panel_w: float, tab_y: float) -> bool:
        if abs(y - tab_y) <= 12:
            tab_w = (panel_w - 38) / 2.0
            tab_img_x = 16.0 + tab_w / 2.0
            tab_tile_x = 16.0 + tab_w + 6.0 + tab_w / 2.0
            if abs(x - tab_img_x) <= tab_w / 2.0:
                form.map_type = "image"
                return True
            elif abs(x - tab_tile_x) <= tab_w / 2.0:
                form.map_type = "tilemap"
                return True
        return False

    @staticmethod
    def cycle_map(form: Any, delta: int) -> None:
        """Avança ou retrocede na lista de mapas ativos de acordo com o modo."""
        if form.map_type == "tilemap":
            if form.available_tilemaps:
                form.selected_tilemap_index = form.selected_tilemap_index + delta
        else:
            if form.available_image_maps:
                form.selected_image_index = form.selected_image_index + delta

    @staticmethod
    def _handle_map_selector_click(form: Any, x: float, y: float, panel_w: float, map_row_y: float) -> bool:
        b_prev_m_x = 30
        if abs(y - map_row_y) <= 12 and abs(x - b_prev_m_x) <= 13:
            ConfigFormInputHandler.cycle_map(form, -1)
            return True

        map_box_w = panel_w - 180
        map_box_x = 30 + 13 + map_box_w / 2 + 4
        b_next_m_x = map_box_x + map_box_w / 2 + 17
        if abs(y - map_row_y) <= 12 and abs(x - b_next_m_x) <= 13:
            ConfigFormInputHandler.cycle_map(form, 1)
            return True

        return False

    @staticmethod
    def _handle_grid_steppers_click(form: Any, x: float, y: float, grid_y: float) -> bool:
        b_c_min_x = 65
        if abs(y - grid_y) <= 11 and abs(x - b_c_min_x) <= 11:
            form.columns = max(5, form.columns - 1)
            return True

        b_c_plus_x = b_c_min_x + 48
        if abs(y - grid_y) <= 11 and abs(x - b_c_plus_x) <= 11:
            form.columns = min(60, form.columns + 1)
            return True

        feet_lbl_x = b_c_plus_x + 30
        b_f_min_x = feet_lbl_x + 45
        if abs(y - grid_y) <= 11 and abs(x - b_f_min_x) <= 11:
            form.feet_per_square = max(1, form.feet_per_square - 5) if form.feet_per_square > 5 else max(1, form.feet_per_square - 1)
            return True

        b_f_plus_x = b_f_min_x + 48
        if abs(y - grid_y) <= 11 and abs(x - b_f_plus_x) <= 11:
            form.feet_per_square = form.feet_per_square + 5 if form.feet_per_square >= 5 else 5
            return True

        return False

    @staticmethod
    def _handle_pc_checkboxes_click(form: Any, x: float, y: float, panel_w: float, pc_list_top: float) -> bool:
        if not form.pc_scroll_list.is_point_inside(x, y):
            return False

        item_match = form.pc_scroll_list.get_item_at_position(x, y)
        if item_match is not None:
            actual_idx, char = item_match
            cid = char["uid"]
            form.toggle_character(cid)
            return True

        visible_items = form.pc_scroll_list.visible_items
        for slot_idx, (idx, char) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = form.pc_scroll_list.get_slot_rect(slot_idx)
            left = slot_cx - slot_w / 2.0
            right = slot_cx + slot_w / 2.0
            top = slot_cy + slot_h / 2.0
            bottom = slot_cy - slot_h / 2.0
            if left <= x <= right and bottom <= y <= top:
                cid = char["uid"]
                form.toggle_character(cid)
                return True
        return False

    @staticmethod
    def _handle_monster_search_click(form: Any, x: float, y: float, panel_w: float, search_bar_y: float) -> bool:
        btn_search_x = panel_w - 16 - 16
        if abs(y - search_bar_y) <= 12 and abs(x - btn_search_x) <= 16:
            form.apply_monster_filter(form.search_input.text)
            return True
        return False

    @staticmethod
    def _handle_monster_list_clicks(form: Any, x: float, y: float) -> bool:
        if not form.scroll_list.is_point_inside(x, y):
            return False

        filtered = form.filtered_monsters
        # Clique na Scrollbar
        if len(filtered) > form.scroll_list.visible_item_count:
            list_l, list_t, list_w, list_h = form.scroll_list.bounds
            track_x = list_l + list_w - 4.0 - 3.0
            if abs(x - track_x) <= 10:
                form.is_dragging_scrollbar = True
                form._scrollbar_drag_start_y = y
                form._scrollbar_drag_start_offset = form.scroll_list.start_index
                track_h = max(10.0, list_h - 8.0)
                visible_count = form.scroll_list.visible_item_count
                thumb_h = max(16.0, track_h * (visible_count / max(1, len(filtered))))
                track_travel = max(1.0, track_h - thumb_h)
                click_ratio = max(0.0, min(1.0, ((list_t - 4.0 - thumb_h / 2.0) - y) / track_travel))
                form.scroll_list.start_index = int(round(click_ratio * form.scroll_list.max_start_index))
                return True

        # Clique nos itens / steppers dentro do viewport
        visible_items = form.scroll_list.visible_items
        for slot_idx, (idx, mon) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = form.scroll_list.get_slot_rect(slot_idx)
            left = slot_cx - slot_w / 2.0
            right = slot_cx + slot_w / 2.0
            top = slot_cy + slot_h / 2.0
            bottom = slot_cy - slot_h / 2.0

            if left <= x <= right and bottom <= y <= top:
                mid = mon["uid"]
                card_right = slot_cx + slot_w / 2.0
                bm_x = card_right - 62
                bp_x = card_right - 18

                # [-]
                if abs(x - bm_x) <= 12:
                    form.decrement_monster(mid)
                    return True

                # [+]
                if abs(x - bp_x) <= 12:
                    form.increment_monster(mid)
                    return True

                return True

        return False

    @staticmethod
    def handle_mouse_drag(form: Any, x: float, y: float) -> bool:
        """Processa arraste da barra de rolagem e seleção de texto nos inputs."""
        filtered = form.filtered_monsters
        if form.is_dragging_scrollbar and form.scroll_list.max_start_index > 0:
            list_l, list_t, list_w, list_h = form.scroll_list.bounds
            total_items = max(1, len(filtered))
            visible_count = form.scroll_list.visible_item_count
            track_h = max(10.0, list_h - 8.0)
            thumb_h = max(16.0, track_h * (visible_count / total_items))
            track_travel = max(1.0, track_h - thumb_h)

            delta_y = form._scrollbar_drag_start_y - y
            delta_ratio = delta_y / track_travel
            new_idx = int(round(form._scrollbar_drag_start_offset + delta_ratio * form.scroll_list.max_start_index))
            form.scroll_list.start_index = new_idx
            return True

        if form.title_input.is_focused:
            return form.title_input.handle_mouse_drag(x, y)
        if form.description_input.is_focused:
            return form.description_input.handle_mouse_drag(x, y)
        if form.search_input.is_focused:
            return form.search_input.handle_mouse_drag(x, y)
        return False

    @staticmethod
    def handle_mouse_release(form: Any, x: float, y: float) -> None:
        """Finaliza arraste de scrollbar ou de seleção."""
        form.is_dragging_scrollbar = False
        form.title_input.handle_mouse_release(x, y)
        form.description_input.handle_mouse_release(x, y)
        form.search_input.handle_mouse_release(x, y)

    @staticmethod
    def handle_key_press(form: Any, symbol: int, modifiers: int) -> bool:
        """Processa atalhos de teclado e acionamento da busca por ENTER."""
        if form.search_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.RETURN):
                form.apply_monster_filter(form.search_input.text)
                return True
            if symbol == arcade.key.ESCAPE:
                form.search_input.blur()
                return True
            res = form.search_input.handle_key_press(symbol, modifiers)
            if not form.search_input.text and form.search_query:
                form.apply_monster_filter("")
            return res

        if form.title_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.TAB):
                form.title_input.blur()
                form.description_input.focus()
                return True
            return form.title_input.handle_key_press(symbol, modifiers)

        if form.description_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.TAB):
                form.description_input.blur()
                form.search_input.focus()
                return True
            return form.description_input.handle_key_press(symbol, modifiers)

        return False

    @staticmethod
    def handle_key_release(form: Any, symbol: int, modifiers: int) -> None:
        form.title_input.handle_key_release(symbol, modifiers)
        form.description_input.handle_key_release(symbol, modifiers)
        form.search_input.handle_key_release(symbol, modifiers)

    @staticmethod
    def handle_text_input(form: Any, text: str) -> bool:
        if form.search_input.is_focused:
            return form.search_input.handle_text_input(text)
        if form.title_input.is_focused:
            return form.title_input.handle_text_input(text)
        if form.description_input.is_focused:
            return form.description_input.handle_text_input(text)
        return False
