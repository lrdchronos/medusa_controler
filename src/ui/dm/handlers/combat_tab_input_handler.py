import logging
from typing import Callable, Any
from ...utils.status_icon_atlas import StatusIconAtlas
from ....manager.session_manager import DisplayState

logger = logging.getLogger(__name__)


class CombatTabInputHandler:
    """
    Controlador especializado de eventos de entrada (mouse, teclado e scroll)
    para a Aba de Combate Ativo da DMWindow.
    """

    @staticmethod
    def handle_click(
        tab: Any,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        open_initiative_modal_callback: Callable[[], None],
    ) -> bool:
        """Processa cliques na aba de combate ativo."""
        # 0. Interceptação Modal de Criação e Inserção de Token (AddTokenModal)
        if tab.add_token_modal.is_open:
            win_w = tab.dm_window.width if tab.dm_window is not None else panel_w
            win_h = tab.dm_window.height if tab.dm_window is not None else top_y
            return tab.add_token_modal.handle_click(x, y, win_w, win_h)

        # Interceptação Modal de Encerramento com Save
        if tab.pending_end_combat_modal:
            modal_w = min(panel_w - 24, 460.0)
            modal_h = 190.0
            modal_cx = panel_w / 2
            modal_cy = top_y / 2
            btn_y = modal_cy - modal_h / 2 + 55
            btn_w = (modal_w - 32) / 2

            b_clean_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
            b_keep_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
            btn_can_y = modal_cy - modal_h / 2 + 20

            # Clique em [ 🗑️ Limpar Save & Sair ]
            if abs(y - btn_y) <= 16 and abs(x - b_clean_x) <= (btn_w - 4) / 2:
                logger.info("Encerrando combate e limpando save do disco.")
                tab.combat_manager.delete_save_state()
                tab.pending_end_combat_modal = False
                tab.session_manager.end_combat(DisplayState.IDLE)
                return True

            # Clique em [ 💾 Manter Save & Sair ]
            if abs(y - btn_y) <= 16 and abs(x - b_keep_x) <= (btn_w - 4) / 2:
                logger.info("Encerrando combate preservando save no disco.")
                tab.pending_end_combat_modal = False
                tab.session_manager.end_combat(DisplayState.IDLE)
                return True

            # Clique em [ ❌ Cancelar ]
            if abs(y - btn_can_y) <= 12 and abs(x - modal_cx) <= (modal_w - 28) / 2:
                logger.info("Encerramento de combate cancelado pelo usuário.")
                tab.pending_end_combat_modal = False
                return True

            # Clique fora fecha modal
            if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
                tab.pending_end_combat_modal = False
                return True

            return True

        # 1. Barra de Ações Rápidas de Combate (6 Botões OOD)
        bar_y = top_y - 20
        btn_w = (panel_w - 44) / 6
        btn_h = 28

        if abs(y - bar_y) <= btn_h / 2:
            # Botão 1: Rolar Iniciativas
            b1_x = 12 + 0 * (btn_w + 4) + btn_w / 2
            if abs(x - b1_x) <= btn_w / 2:
                open_initiative_modal_callback()
                return True

            # Botão 2: Adicionar Token Dinâmico
            b2_x = 12 + 1 * (btn_w + 4) + btn_w / 2
            if abs(x - b2_x) <= btn_w / 2:
                tab.add_token_modal.open()
                return True

            # Botão 3: Turno Anterior
            b3_x = 12 + 2 * (btn_w + 4) + btn_w / 2
            if abs(x - b3_x) <= btn_w / 2:
                tab.combat_manager.previous_turn()
                return True

            # Botão 4: Próximo Turno
            b4_x = 12 + 3 * (btn_w + 4) + btn_w / 2
            if abs(x - b4_x) <= btn_w / 2:
                tab.combat_manager.next_turn()
                return True

            # Botão 5: Pausar e Salvar Combate
            b5_x = 12 + 4 * (btn_w + 4) + btn_w / 2
            if abs(x - b5_x) <= btn_w / 2:
                tab.trigger_save_combat()
                return True

            # Botão 6: Finalizar Combate
            b6_x = 12 + 5 * (btn_w + 4) + btn_w / 2
            if abs(x - b6_x) <= btn_w / 2:
                if tab.combat_manager.has_save_state():
                    tab.pending_end_combat_modal = True
                    logger.info("Save detectado ao finalizar combate. Abrindo modal de confirmação.")
                else:
                    tab.session_manager.end_combat(DisplayState.IDLE)
                return True

        # 1.5 Clique no Botão [ 🔄 Reset Mov ]
        info_y = bar_y - 24
        if abs(y - info_y) <= 12:
            btn_rst_w = 88.0
            btn_rst_x = panel_w - 16 - btn_rst_w / 2
            if abs(x - btn_rst_x) <= btn_rst_w / 2:
                active_char = tab.combat_manager.active_character
                if active_char is not None:
                    tab.combat_manager.reset_combatant_movement(active_char.uid)
                    return True

        # 2. Cliques no Painel de Feitiços (SpellAoEPanel)
        if tab.spell_aoe_panel.handle_click(x, y, panel_w, info_y - 12):
            if tab.spell_aoe_panel.is_active and tab.fog_panel.is_tool_active:
                tab.fog_panel.active_tool = FogTool.NONE
                logger.info("Modo Spell ativado: Modo Fog desativado automaticamente (exclusividade mútua).")
            return True

        spell_body_h = 96 if not tab.spell_aoe_panel.is_collapsed else 0
        spell_next_y = info_y - 12 - (28 + spell_body_h) - 8

        # 3. Cliques no Painel de Névoa de Guerra (FogControlPanel)
        if tab.fog_panel.handle_click(x, y, panel_w, spell_next_y):
            if tab.fog_panel.is_tool_active and tab.spell_aoe_panel.is_active:
                tab.spell_aoe_panel.is_active = False
                tab.spell_aoe_panel.sync_to_combat_manager()
                logger.info("Modo Fog ativado: Modo Spell desativado automaticamente (exclusividade mútua).")
            return True

        if hasattr(tab.fog_panel, "get_next_y") and callable(tab.fog_panel.get_next_y):
            calc_y = tab.fog_panel.get_next_y(spell_next_y)
            if isinstance(calc_y, (int, float)):
                fog_next_y = float(calc_y)
            else:
                fog_body_h = 80.0 if not getattr(tab.fog_panel, "is_collapsed", False) else 0.0
                hdr_h = float(getattr(tab.fog_panel, "header_height", 28.0)) if isinstance(getattr(tab.fog_panel, "header_height", 28.0), (int, float)) else 28.0
                fog_next_y = spell_next_y - (hdr_h + fog_body_h) - 8.0
        else:
            fog_body_h = 80.0 if not getattr(tab.fog_panel, "is_collapsed", False) else 0.0
            hdr_h = float(getattr(tab.fog_panel, "header_height", 28.0)) if isinstance(getattr(tab.fog_panel, "header_height", 28.0), (int, float)) else 28.0
            fog_next_y = spell_next_y - (hdr_h + fog_body_h) - 8.0

        # 4. Cliques nas Linhas da Tabela de Combatentes (via DiscreteScrollList)
        table_top = fog_next_y
        table_h = 22
        panels_collapsed = (1 if tab.spell_aoe_panel.is_collapsed else 0) + (1 if tab.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2

        combatants = tab.combat_manager.turn_order if tab.combat_manager.has_combat_started else tab.combat_manager.combatants
        tab.scroll_list.items = combatants
        tab.scroll_list.visible_item_count = max_rows
        list_w = panel_w - 24
        list_h = max_rows * (tab._CombatTabView__item_height + tab._CombatTabView__spacing)
        list_x = 12
        list_top_y = table_top - table_h
        tab.scroll_list.set_bounds(list_x, list_top_y, list_w, list_h)

        for slot_idx, (actual_idx, combatant) in enumerate(tab.scroll_list.visible_items):
            slot_cx, slot_cy, slot_w, slot_h = tab.scroll_list.get_slot_rect(slot_idx)
            if abs(y - slot_cy) <= slot_h / 2:
                if abs(x - (panel_w - 40)) <= 20:
                    tab.combat_manager.toggle_combatant_visibility(combatant.uid)
                    return True

                if abs(x - slot_cx) <= slot_w / 2:
                    tab.selected_combatant_uid = combatant.uid
                    return True

        # 5. Cliques no Despachante de Dano e Cura
        rendered_rows = min(len(combatants), max_rows)
        disp_top = table_top - table_h - rendered_rows * (tab._CombatTabView__item_height + tab._CombatTabView__spacing) - 8

        sel_combatant = tab.combat_manager.get_combatant(tab.selected_combatant_uid or "")
        if sel_combatant:
            btn_dmg_y = disp_top - 68.0
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70.0) / 8.0

            # Dano Rápido
            if abs(y - btn_dmg_y) <= 11:
                for i, val in enumerate(dmg_vals):
                    bx = 30.0 + i * (dmg_btn_w + 4.0) + dmg_btn_w / 2.0
                    if abs(x - bx) <= dmg_btn_w / 2.0:
                        tab.combat_manager.apply_damage(sel_combatant.uid, abs(val))
                        return True

                # Cura Rápida
                heal_vals = [1, 5, 10, 20]
                for i, val in enumerate(heal_vals):
                    bx = 30.0 + (i + 4) * (dmg_btn_w + 4.0) + dmg_btn_w / 2.0
                    if abs(x - bx) <= dmg_btn_w / 2.0:
                        tab.combat_manager.apply_heal(sel_combatant.uid, val)
                        return True

            custom_y = disp_top - 96.0
            if abs(y - custom_y) <= 12:
                # Stepper [-]
                if abs(x - 45.0) <= 13:
                    tab.custom_hp_value = max(1, tab.custom_hp_value - 1)
                    return True

                # Stepper [+]
                if abs(x - 135.0) <= 13:
                    tab.custom_hp_value = min(999, tab.custom_hp_value + 1)
                    return True

                # Dano Customizado
                if abs(x - 215.0) <= 50:
                    tab.combat_manager.apply_damage(sel_combatant.uid, tab.custom_hp_value)
                    return True

                # Cura Customizada
                if abs(x - 325.0) <= 50:
                    tab.combat_manager.apply_heal(sel_combatant.uid, tab.custom_hp_value)
                    return True

                # Ocultar / Revelar
                if abs(x - (panel_w - 75.0)) <= 45:
                    tab.combat_manager.toggle_combatant_visibility(sel_combatant.uid)
                    return True

            # Cliques nas Condições Táticas D&D 5E (11 Toggles)
            cond_btn_y = disp_top - 148.0
            cond_btn_h = 24.0
            if abs(y - cond_btn_y) <= cond_btn_h / 2.0:
                cond_names = StatusIconAtlas.get_condition_names()
                cond_spacing = 3.0
                cond_total_w = panel_w - 48.0
                cond_btn_w = (cond_total_w - (len(cond_names) - 1) * cond_spacing) / len(cond_names)
                for idx, cond_name in enumerate(cond_names):
                    bx = 24.0 + idx * (cond_btn_w + cond_spacing) + cond_btn_w / 2.0
                    if abs(x - bx) <= cond_btn_w / 2.0:
                        tab.combat_manager.toggle_condition(sel_combatant.uid, cond_name)
                        return True

        return False

    @staticmethod
    def handle_mouse_scroll(tab: Any, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        if tab.pending_end_combat_modal or tab.add_token_modal.is_open:
            return False
        return tab.scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)

    @staticmethod
    def handle_mouse_drag(tab: Any, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        return tab.spell_aoe_panel.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)

    @staticmethod
    def handle_mouse_release(tab: Any, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        tab.spell_aoe_panel.handle_mouse_release(x, y, button, modifiers)

    @staticmethod
    def handle_key_press(tab: Any, symbol: int, modifiers: int = 0) -> bool:
        if tab.add_token_modal.is_open:
            if tab.add_token_modal.handle_key_press(symbol, modifiers):
                return True
        return tab.spell_aoe_panel.handle_key_press(symbol, modifiers)

    @staticmethod
    def handle_key_release(tab: Any, symbol: int, modifiers: int = 0) -> None:
        if tab.add_token_modal.is_open:
            tab.add_token_modal.handle_key_release(symbol, modifiers)
        tab.spell_aoe_panel.handle_key_release(symbol, modifiers)

    @staticmethod
    def handle_text_input(tab: Any, text: str) -> bool:
        if tab.add_token_modal.is_open:
            if tab.add_token_modal.handle_text_input(text):
                return True
        return tab.spell_aoe_panel.handle_text_input(text)
