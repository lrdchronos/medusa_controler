import logging
from typing import Any
import arcade
from ...utils.ui_constants import Colors, Typography, Dimensions, Spacing, with_alpha

logger = logging.getLogger(__name__)


class EncountersTabRenderer:
    """
    Renderizador da Aba de Encontros (Aba 0 da DMWindow).
    """

    @staticmethod
    def draw(tab: Any, panel_w: float, top_y: float) -> None:
        """Desenha a lista de encontros via DiscreteScrollList, cartão de detalhes e modais de ação."""
        sec_y = top_y - 20
        tab._get_text("enc_sec_t", "ARQUIVOS DE ENCONTRO DISPONÍVEIS", Spacing.MD, sec_y, Colors.ACCENT_GOLD, Typography.SIZE_LABEL, bold=True).draw()

        # Botão Atualizar
        btn_ref_x = panel_w - 70
        arcade.draw_rect_filled(arcade.XYWH(btn_ref_x, sec_y, 80, 24), Colors.BG_CARD)
        arcade.draw_rect_outline(arcade.XYWH(btn_ref_x, sec_y, 80, 24), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        tab._get_text("enc_btn_ref", "🔄 Atualizar", btn_ref_x, sec_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 2. Configuração do Espaço da Lista Rolável
        list_top = sec_y - 22
        card_h = 210
        list_h = max(80.0, list_top - card_h - 16.0)

        tab.scroll_list.set_bounds(x=12.0, y=list_top, width=panel_w - 24.0, height=list_h)
        tab.scroll_list.items = tab.encounters_list

        if not tab.encounters_list:
            tab._get_text("enc_empty", "Nenhum arquivo JSON de encontro encontrado em creations/encounters/", Spacing.MD, list_top - 20, Colors.TEXT_MUTED, Typography.SIZE_BADGE, bold=False).draw()
        else:
            visible_items = tab.scroll_list.visible_items
            has_scrollbar = len(tab.encounters_list) > tab.scroll_list.visible_item_count

            for slot_idx, (idx, enc) in enumerate(visible_items):
                slot_cx, slot_cy, slot_w, slot_h = tab.scroll_list.get_slot_rect(slot_idx)
                is_selected = (idx == tab.selected_index)

                bg_c = Colors.BG_CARD_HOVER if is_selected else (22, 28, 38, 255)
                bd_c = Colors.ACCENT_GOLD if is_selected else Colors.BORDER_SUBTLE

                arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), bg_c)
                arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), bd_c, Dimensions.BORDER_WIDTH_THICK if is_selected else Dimensions.BORDER_WIDTH_DEFAULT)

                enc_uid = enc.get("uid") or enc.get("filename", "")
                has_save = tab.session_manager.has_encounter_save(enc_uid)

                title_str = enc.get("title") or enc.get("filename") or enc.get("file_name") or enc.get("uid", "Encontro")
                save_indicator = " 💾 [SAVE]" if has_save else ""
                full_title = f"⚔️ {title_str[:22]}{save_indicator}"
                title_color = Colors.ACCENT_GOLD if is_selected else (Colors.ACCENT_GOLD if has_save else Colors.TEXT_PRIMARY)
                tab._get_text(f"enc_item_t_{idx}", full_title, slot_cx - slot_w / 2 + 12, slot_cy + 9, title_color, Typography.SIZE_MICRO, bold=True).draw()

                filename_str = enc.get("filename") or enc.get("file_name") or enc.get("path", "")
                count = enc.get("combatants_count", 0)
                sub_str = f"Arquivo: {filename_str[:22]} • {count} combatentes"
                tab._get_text(f"enc_item_s_{idx}", sub_str, slot_cx - slot_w / 2 + 12, slot_cy - 10, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False).draw()

                btn_offset_right = 10 if not has_scrollbar else 16

                # [ 🗑️ Excluir ]
                b_del_w = 48
                b_del_x = slot_cx + slot_w / 2 - btn_offset_right - b_del_w / 2
                arcade.draw_rect_filled(arcade.XYWH(b_del_x, slot_cy, b_del_w, 24), (120, 35, 35, 255))
                arcade.draw_rect_outline(arcade.XYWH(b_del_x, slot_cy, b_del_w, 24), (180, 50, 50, 200), Dimensions.BORDER_WIDTH_DEFAULT)
                tab._get_text(f"b_del_{idx}", "🗑️ Excluir", b_del_x, slot_cy, (255, 200, 200, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

                # [ ✏️ Editar ]
                b_edit_w = 48
                b_edit_x = b_del_x - b_del_w / 2 - 4 - b_edit_w / 2
                arcade.draw_rect_filled(arcade.XYWH(b_edit_x, slot_cy, b_edit_w, 24), (35, 55, 80, 255))
                arcade.draw_rect_outline(arcade.XYWH(b_edit_x, slot_cy, b_edit_w, 24), (70, 110, 160, 200), Dimensions.BORDER_WIDTH_DEFAULT)
                tab._get_text(f"b_edit_{idx}", "✏️ Editar", b_edit_x, slot_cy, (180, 220, 255, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

            if has_scrollbar:
                tab.scroll_list._draw_scroll_indicator(tab.text_cache)

        # 3. Cartão de Detalhes e Ações do Encontro Selecionado
        card_top = list_top - list_h - 10
        card_cy = card_top - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), Colors.BG_MODAL)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        sel_enc = tab.encounters_list[tab.selected_index] if (tab.encounters_list and 0 <= tab.selected_index < len(tab.encounters_list)) else None
        if sel_enc:
            title_str = sel_enc.get("title") or sel_enc.get("filename") or sel_enc.get("file_name", "")
            filename_str = sel_enc.get("filename") or sel_enc.get("file_name") or sel_enc.get("path", "")
            map_str = sel_enc.get("map_path") or sel_enc.get("map_source") or sel_enc.get("map_file") or "assets/images/battlemaps/forest_01.png"
            sel_uid = sel_enc.get("uid") or sel_enc.get("filename", "")
            sel_has_save = tab.session_manager.has_encounter_save(sel_uid)

            save_suffix = " (Sessão Salva Disponível 💾)" if sel_has_save else ""
            tab._get_text("enc_d_t", f"DETALHES: {title_str[:26]}{save_suffix}", 24, card_top - 18, Colors.ACCENT_GOLD, Typography.SIZE_BADGE, bold=True).draw()
            tab._get_text("enc_d_f", f"• Arquivo: {filename_str}", 24, card_top - 38, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False).draw()
            tab._get_text("enc_d_m", f"• Mapa: {map_str[:42]}", 24, card_top - 56, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False).draw()

            grid_info = sel_enc.get("grid", {})
            cols = grid_info.get("columns", 25) if isinstance(grid_info, dict) else 25
            feet = grid_info.get("feet_per_square", 5) if isinstance(grid_info, dict) else 5
            tab._get_text("enc_d_g", f"• Grid Tático: {cols} colunas • {feet} ft/quadrado", 24, card_top - 74, Colors.TEXT_CYAN, Typography.SIZE_MICRO, bold=True).draw()

            comb_names = ", ".join(sel_enc.get("combatant_names", [])) if "combatant_names" in sel_enc else f"{sel_enc.get('combatants_count', 0)} combatentes"
            tab._get_text("enc_d_c", f"• Combatentes: {comb_names[:58]}...", 24, card_top - 92, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False).draw()

            btn_sub_y = card_top - 122
            btn_sub_w = (panel_w - 36) / 2

            # [ ✏️ Editar Encontro ]
            b_d_edit_x = 12 + btn_sub_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_d_edit_x, btn_sub_y, btn_sub_w - 4, 26), (35, 55, 80, 255))
            arcade.draw_rect_outline(arcade.XYWH(b_d_edit_x, btn_sub_y, btn_sub_w - 4, 26), (70, 110, 160, 200), Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("enc_b_d_edit", "✏️ Editar Encontro", b_d_edit_x, btn_sub_y, (180, 220, 255, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

            # [ 🗑️ Excluir Encontro ]
            b_d_del_x = 12 + btn_sub_w + btn_sub_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_d_del_x, btn_sub_y, btn_sub_w - 4, 26), (120, 35, 35, 255))
            arcade.draw_rect_outline(arcade.XYWH(b_d_del_x, btn_sub_y, btn_sub_w - 4, 26), (180, 50, 50, 200), Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("enc_b_d_del", "🗑️ Excluir Encontro", b_d_del_x, btn_sub_y, (255, 200, 200, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

            # Botão Principal [ ▶ INICIAR ENCONTRO TÁTICO ]
            btn_start_y = card_top - 165
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_start_y, panel_w - 40, Dimensions.BTN_HEIGHT_DEFAULT), Colors.NPC_RED)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_start_y, panel_w - 40, Dimensions.BTN_HEIGHT_DEFAULT), Colors.DANGER, Dimensions.BORDER_WIDTH_THICK)
            btn_label = "💾 RETOMAR OU INICIAR ENCONTRO" if sel_has_save else "▶ INICIAR ENCONTRO TÁTICO"
            tab._get_text("enc_b_start", btn_label, panel_w / 2, btn_start_y, Colors.TEXT_WHITE, Typography.SIZE_BADGE, bold=True, anchor_x="center").draw()

        # 4. Modais
        if tab.pending_delete_encounter is not None:
            EncountersTabRenderer.draw_delete_confirmation_modal(tab, panel_w, top_y)

        if tab.pending_resume_encounter is not None:
            EncountersTabRenderer.draw_resume_confirmation_modal(tab, panel_w, top_y)

    @staticmethod
    def draw_delete_confirmation_modal(tab: Any, panel_w: float, top_y: float) -> None:
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, top_y / 2, panel_w, top_y), (10, 14, 20, 220))

        enc = tab.pending_delete_encounter or {}
        title = enc.get("title") or enc.get("filename") or enc.get("uid", "Encontro")

        modal_w = min(panel_w - 28, 420.0)
        modal_h = 175.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2

        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (22, 28, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), Colors.NPC_RED, Dimensions.BORDER_WIDTH_THICK)

        tab._get_text("del_mod_hdr", "⚠️ CONFIRMAR EXCLUSÃO DE ENCONTRO", modal_cx, modal_cy + modal_h / 2 - 20, Colors.ACCENT_GOLD, Typography.SIZE_BADGE, bold=True, anchor_x="center").draw()

        msg_line1 = f"Deseja realmente excluir o encontro '{title[:30]}'?"
        msg_line2 = "Esta ação não pode ser desfeita."
        tab._get_text("del_mod_m1", msg_line1, modal_cx, modal_cy + 12, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_x="center").draw()
        tab._get_text("del_mod_m2", msg_line2, modal_cx, modal_cy - 8, (255, 140, 140, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        btn_y = modal_cy - modal_h / 2 + 30
        btn_w = (modal_w - 36) / 2

        # [ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_can_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_can_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        tab._get_text("del_mod_b_can", "Cancelar", b_can_x, btn_y, (236, 240, 241, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # [ Confirmar Exclusão ]
        b_conf_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_conf_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), Colors.NPC_RED)
        arcade.draw_rect_outline(arcade.XYWH(b_conf_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), Colors.DANGER, Dimensions.BORDER_WIDTH_THICK)
        tab._get_text("del_mod_b_conf", "Confirmar Exclusão", b_conf_x, btn_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

    @staticmethod
    def draw_resume_confirmation_modal(tab: Any, panel_w: float, top_y: float) -> None:
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, top_y / 2, panel_w, top_y), (10, 14, 20, 220))

        enc = tab.pending_resume_encounter or {}
        title = enc.get("title") or enc.get("filename") or enc.get("uid", "Encontro")

        modal_w = min(panel_w - 24, 460.0)
        modal_h = 190.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2

        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (22, 28, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), Colors.ACCENT_GOLD, Dimensions.BORDER_WIDTH_THICK)

        tab._get_text("res_mod_hdr", "💾 SESSÃO DE COMBATE SALVA DETECTADA", modal_cx, modal_cy + modal_h / 2 - 20, Colors.ACCENT_GOLD, Typography.SIZE_BADGE, bold=True, anchor_x="center").draw()

        msg_line1 = f"Existe uma sessão de combate salva para '{title[:28]}'."
        msg_line2 = "Deseja retomar de onde parou ou iniciar do zero?"
        tab._get_text("res_mod_m1", msg_line1, modal_cx, modal_cy + 22, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_x="center").draw()
        tab._get_text("res_mod_m2", msg_line2, modal_cx, modal_cy + 5, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        btn_y = modal_cy - modal_h / 2 + 55
        btn_w = (modal_w - 32) / 2

        # 1. [ 💾 Retomar Último Save ]
        b_res_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_res_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_res_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), Colors.SUCCESS, Dimensions.BORDER_WIDTH_THICK)
        tab._get_text("res_mod_b_resume", "💾 Retomar Último Save", b_res_x, btn_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 2. [ 🔄 Começar do Zero ]
        b_zero_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_zero_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), Colors.NPC_RED)
        arcade.draw_rect_outline(arcade.XYWH(b_zero_x, btn_y, btn_w - 4, Dimensions.BTN_SIZE_COMPACT_MD), Colors.DANGER, Dimensions.BORDER_WIDTH_THICK)
        tab._get_text("res_mod_b_zero", "🔄 Começar do Zero", b_zero_x, btn_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 3. [ ❌ Cancelar ]
        btn_can_y = modal_cy - modal_h / 2 + 20
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        tab._get_text("res_mod_b_can", "❌ Cancelar", modal_cx, btn_can_y, (200, 210, 225, 255), Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
