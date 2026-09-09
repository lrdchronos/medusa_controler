import logging
from typing import Any, Callable, Optional, Dict

logger = logging.getLogger(__name__)


class EncountersTabInputHandler:
    """
    Tratador de eventos de entrada para a aba de Encontros (Aba 0 da DMWindow).
    """

    @staticmethod
    def handle_click(
        tab: Any,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        on_start_combat_callback: Callable[[str], None],
        on_edit_encounter_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """Processa cliques na aba de encontros com suporte a exclusão modal, save state e edição."""
        # 1. Interceptação Modal de Decisão de Save State
        if tab.pending_resume_encounter is not None:
            return EncountersTabInputHandler._handle_resume_modal_click(
                tab, x, y, panel_w, top_y, on_start_combat_callback
            )

        # 2. Interceptação Modal de Exclusão Poka-Yoke
        if tab.pending_delete_encounter is not None:
            return EncountersTabInputHandler._handle_delete_modal_click(
                tab, x, y, panel_w, top_y
            )

        sec_y = top_y - 20

        # 3. Botão Atualizar
        btn_ref_x = panel_w - 70
        if abs(y - sec_y) <= 12 and abs(x - btn_ref_x) <= 40:
            tab.refresh()
            return True

        # 4. Interação com a Lista Rolável Discreta
        visible_items = tab.scroll_list.visible_items
        has_scrollbar = len(tab.encounters_list) > tab.scroll_list.visible_item_count

        for slot_idx, (idx, enc) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = tab.scroll_list.get_slot_rect(slot_idx)
            left = slot_cx - slot_w / 2.0
            right = slot_cx + slot_w / 2.0
            top = slot_cy + slot_h / 2.0
            bottom = slot_cy - slot_h / 2.0

            if left <= x <= right and bottom <= y <= top:
                btn_offset_right = 10 if not has_scrollbar else 16

                # Botão Excluir no Card
                b_del_w = 48
                b_del_x = slot_cx + slot_w / 2 - btn_offset_right - b_del_w / 2
                if abs(y - slot_cy) <= 12 and abs(x - b_del_x) <= b_del_w / 2:
                    tab.selected_index = idx
                    tab.pending_delete_encounter = enc
                    logger.info("Aberto modal de confirmação para exclusão de '%s'", enc.get('title'))
                    return True

                # Botão Editar no Card
                b_edit_w = 48
                b_edit_x = b_del_x - b_del_w / 2 - 4 - b_edit_w / 2
                if abs(y - slot_cy) <= 12 and abs(x - b_edit_x) <= b_edit_w / 2:
                    tab.selected_index = idx
                    if on_edit_encounter_callback is not None:
                        on_edit_encounter_callback(enc)
                    return True

                # Selecionar Card
                tab.selected_index = idx
                return True

        # 5. Interação no Cartão de Detalhes
        return EncountersTabInputHandler._handle_details_card_click(
            tab, x, y, panel_w, sec_y, on_start_combat_callback, on_edit_encounter_callback
        )

    @staticmethod
    def _handle_resume_modal_click(
        tab: Any,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        on_start_combat_callback: Callable[[str], None],
    ) -> bool:
        modal_w = min(panel_w - 24, 460.0)
        modal_h = 190.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2
        btn_y = modal_cy - modal_h / 2 + 55
        btn_w = (modal_w - 32) / 2

        b_res_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        b_zero_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        btn_can_y = modal_cy - modal_h / 2 + 20

        enc = tab.pending_resume_encounter
        enc_id = enc.get("uid") or enc.get("id") or enc.get("filename") or enc.get("path", "")

        # Clique em [ 💾 Retomar Último Save ]
        if abs(y - btn_y) <= 16 and abs(x - b_res_x) <= (btn_w - 4) / 2:
            logger.info("Retomando save state do encontro '%s'.", enc_id)
            tab.session_manager.resume_encounter_save(enc_id)
            tab.pending_resume_encounter = None
            if tab.dm_window is not None:
                setattr(tab.dm_window, "active_tab", 2)
            return True

        # Clique em [ 🔄 Começar do Zero ]
        if abs(y - btn_y) <= 16 and abs(x - b_zero_x) <= (btn_w - 4) / 2:
            logger.info("Descartando save e iniciando do zero encontro '%s'.", enc_id)
            tab.session_manager.delete_encounter_save(enc_id)
            tab.pending_resume_encounter = None
            on_start_combat_callback(enc_id)
            return True

        # Clique em [ ❌ Cancelar ]
        if abs(y - btn_can_y) <= 12 and abs(x - modal_cx) <= (modal_w - 28) / 2:
            logger.info("Abertura de encontro cancelada no modal de save state.")
            tab.pending_resume_encounter = None
            return True

        # Clique fora fecha modal
        if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
            tab.pending_resume_encounter = None
            return True

        return True

    @staticmethod
    def _handle_delete_modal_click(
        tab: Any,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
    ) -> bool:
        modal_w = min(panel_w - 28, 420.0)
        modal_h = 175.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2
        btn_y = modal_cy - modal_h / 2 + 30
        btn_w = (modal_w - 36) / 2

        b_can_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        b_conf_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2

        # Clique em [ Cancelar ]
        if abs(y - btn_y) <= 16 and abs(x - b_can_x) <= (btn_w - 4) / 2:
            logger.info("Exclusão de encontro cancelada pelo usuário.")
            tab.pending_delete_encounter = None
            return True

        # Clique em [ Confirmar Exclusão ]
        if abs(y - btn_y) <= 16 and abs(x - b_conf_x) <= (btn_w - 4) / 2:
            enc = tab.pending_delete_encounter
            uid = enc.get("uid") or enc.get("filename") or enc.get("path", "")
            success = tab.session_manager.delete_encounter(uid)
            if success:
                logger.info("Encontro '%s' excluído após confirmação do usuário.", uid)
            tab.pending_delete_encounter = None
            tab.refresh()
            return True

        # Clique fora do diálogo fecha modal
        if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
            tab.pending_delete_encounter = None
            return True

        return True

    @staticmethod
    def _handle_details_card_click(
        tab: Any,
        x: float,
        y: float,
        panel_w: float,
        sec_y: float,
        on_start_combat_callback: Callable[[str], None],
        on_edit_encounter_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        list_top = sec_y - 22
        card_h = 210
        list_h = max(80.0, list_top - card_h - 16.0)
        card_top = list_top - list_h - 10

        sel_enc = (
            tab.encounters_list[tab.selected_index]
            if (tab.encounters_list and 0 <= tab.selected_index < len(tab.encounters_list))
            else None
        )
        if sel_enc:
            btn_sub_y = card_top - 122
            btn_sub_w = (panel_w - 36) / 2

            # [ ✏️ Editar Encontro ] no Cartão de Detalhes
            b_d_edit_x = 12 + btn_sub_w / 2
            if abs(y - btn_sub_y) <= 13 and abs(x - b_d_edit_x) <= (btn_sub_w - 4) / 2:
                if on_edit_encounter_callback is not None:
                    on_edit_encounter_callback(sel_enc)
                return True

            # [ 🗑️ Excluir Encontro ] no Cartão de Detalhes
            b_d_del_x = 12 + btn_sub_w + btn_sub_w / 2
            if abs(y - btn_sub_y) <= 13 and abs(x - b_d_del_x) <= (btn_sub_w - 4) / 2:
                tab.pending_delete_encounter = sel_enc
                logger.info("Aberto modal de confirmação para exclusão de '%s'", sel_enc.get('title'))
                return True

            # [ ▶ INICIAR ENCONTRO TÁTICO ]
            btn_start_y = card_top - 165
            if abs(y - btn_start_y) <= 18 and abs(x - panel_w / 2) <= (panel_w - 40) / 2:
                enc_id = sel_enc.get("uid") or sel_enc.get("id") or sel_enc.get("filename") or sel_enc.get("path", "")
                if tab.session_manager.has_encounter_save(enc_id):
                    tab.pending_resume_encounter = sel_enc
                    logger.info("Save detectado para '%s'. Abrindo modal de decisão.", enc_id)
                else:
                    on_start_combat_callback(enc_id)
                return True

        return False
