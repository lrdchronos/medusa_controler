import logging
from typing import Any, Tuple
import arcade
from ....domain.models.playablechar import PlayableCharacter
from ....domain.models.entity import EntityType
from ...utils.status_icon_atlas import StatusIconAtlas
from ...utils.ui_constants import Colors, Typography, Dimensions, Spacing, with_alpha
from ...utils.ui_layout import PixelIconDrawer

logger = logging.getLogger(__name__)


class CombatRosterPanel:
    """
    Subpainel especializado no Roster de Combatentes com paginação discreta
    e no Despachante de Dano/Cura, Condições Táticas e Visibilidade.
    """

    @staticmethod
    def draw_roster_table(tab: Any, panel_w: float, fog_next_y: float) -> Tuple[float, int]:
        """Desenha o cabeçalho e a lista paginada de combatentes do encontro."""
        table_top = fog_next_y
        table_h = 22
        table_y = table_top - table_h / 2

        # Cabeçalho da Tabela
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), Colors.BG_PANEL_ALT)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        tab._get_text("th_turn", "TURNO", 28, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="left").draw()
        tab._get_text("th_name", "NOME", 85, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="left").draw()
        tab._get_text("th_type", "TIPO", 240, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        tab._get_text("th_hp", "HP", 305, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        tab._get_text("th_ca", "CA", 365, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        tab._get_text("th_mod", "MOD", 405, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        tab._get_text("th_init", "INIC", 445, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        tab._get_text("th_status", "STATUS", 500, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        tab._get_text("th_vis", "VIS", panel_w - 40, table_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        active_char = tab.combat_manager.active_character
        combatants = tab.combat_manager.turn_order if tab.combat_manager.has_combat_started else tab.combat_manager.combatants

        if not combatants:
            tab._get_text("r_empty", "Nenhum combatente ativo no encontro.", panel_w / 2, table_top - 30, Colors.TEXT_MUTED, Typography.SIZE_BODY, bold=False, anchor_x="center").draw()
            return table_top - 50, 0

        # Atualiza a lista com os dados dinâmicos do combate e limites de rolagem
        panels_collapsed = (1 if tab.spell_aoe_panel.is_collapsed else 0) + (1 if tab.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2
        tab.scroll_list.items = combatants
        tab.scroll_list.visible_item_count = max_rows
        list_w = panel_w - 24.0
        list_h = max_rows * (tab._CombatTabView__item_height + tab._CombatTabView__spacing)
        list_x = 12.0
        list_top_y = table_top - table_h
        tab.scroll_list.set_bounds(list_x, list_top_y, list_w, list_h)

        # Renderiza a fatia de combatentes visíveis
        visible_items = tab.scroll_list.visible_items

        for slot_idx, (actual_idx, combatant) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = tab.scroll_list.get_slot_rect(slot_idx)

            is_active_turn = (active_char is not None and combatant.uid == active_char.uid)
            is_selected = (combatant.uid == tab.selected_combatant_uid)

            # 1. Fundo do Card
            if is_active_turn:
                bg_col = (45, 60, 85, 255)
                bd_col = Colors.ACCENT_GOLD
                bd_thick = Dimensions.BORDER_WIDTH_THICK
            elif is_selected:
                bg_col = (35, 48, 68, 255)
                bd_col = Colors.INFO_BORDER
                bd_thick = Dimensions.BORDER_WIDTH_ACTIVE
            else:
                bg_col = Colors.BG_CARD if actual_idx % 2 == 0 else (24, 32, 44, 255)
                bd_col = Colors.BORDER_SUBTLE
                bd_thick = Dimensions.BORDER_WIDTH_DEFAULT

            arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), bg_col)
            arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), bd_col, bd_thick)

            # 2. Indicador de Turno Ativo
            turn_icon = "▶" if is_active_turn else ""
            turn_col = Colors.ACCENT_GOLD if is_active_turn else Colors.TEXT_MUTED
            tab._get_text(f"r_turn_{actual_idx}", turn_icon, 28, slot_cy, turn_col, Typography.SIZE_MICRO, bold=True, anchor_x="left").draw()

            # 3. Nome do Combatente
            name_col = Colors.TEXT_GOLD if is_active_turn else (Colors.TEXT_PRIMARY if not combatant.is_hidden else with_alpha(Colors.TEXT_MUTED, 160))
            name_str = combatant.name[:18]
            tab._get_text(f"r_name_{actual_idx}", name_str, 85, slot_cy, name_col, Typography.SIZE_MICRO, bold=is_active_turn, anchor_x="left").draw()

            # 4. Tipo / Porte
            is_pc = (combatant.entity_type == EntityType.PLAYER or isinstance(combatant, PlayableCharacter))
            type_str = "PC" if is_pc else "NPC"
            type_col = Colors.PC_BLUE if is_pc else Colors.NPC_RED
            tab._get_text(f"r_type_{actual_idx}", type_str, 240, slot_cy, type_col, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

            # 5. HP Atual / Máximo
            hp_str = f"{combatant.current_hp}/{combatant.max_hp}"
            hp_pct = max(0.0, min(1.0, combatant.current_hp / max(1, combatant.max_hp)))
            hp_col = Colors.SUCCESS if hp_pct > 0.5 else (Colors.WARNING if hp_pct > 0.2 else Colors.DANGER)
            tab._get_text(f"r_hp_{actual_idx}", hp_str, 305, slot_cy, hp_col, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

            # 6. CA (Classe de Armadura)
            tab._get_text(f"r_ca_{actual_idx}", str(combatant.armor_class), 365, slot_cy, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=False, anchor_x="center").draw()

            # 7. Modificador de Iniciativa
            mod_str = f"{combatant.initiative_mod:+d}"
            tab._get_text(f"r_mod_{actual_idx}", mod_str, 405, slot_cy, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False, anchor_x="center").draw()

            # 8. Score de Iniciativa
            init_val_str = str(combatant.initiative_score) if combatant.initiative_score is not None else "-"
            tab._get_text(f"r_init_{actual_idx}", init_val_str, 445, slot_cy, Colors.TEXT_GOLD if is_active_turn else Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

            # 9. Condições / Badges Ativos
            cond_count = len(combatant.conditions)
            cond_str = f"[{cond_count}]" if cond_count > 0 else "-"
            cond_col = Colors.WARNING if cond_count > 0 else Colors.TEXT_MUTED
            tab._get_text(f"r_st_{actual_idx}", cond_str, 500, slot_cy, cond_col, Typography.SIZE_MICRO, bold=cond_count > 0, anchor_x="center").draw()

            # 10. Visibilidade (Olho Aberto / Fechado)
            vis_icon = "👁️" if not combatant.is_hidden else "🙈"
            tab._get_text(f"r_vis_{actual_idx}", vis_icon, panel_w - 40, slot_cy, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=False, anchor_x="center").draw()

        if len(combatants) > tab.scroll_list.visible_item_count:
            tab.scroll_list._draw_scroll_indicator(tab.text_cache)

        return table_top - table_h, len(combatants)

    @staticmethod
    def draw_hp_dispatcher(tab: Any, panel_w: float, disp_top: float) -> None:
        """Desenha o painel despachante de dano, cura e condições do combatente selecionado."""
        disp_h = 176.0
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2.0, disp_top - disp_h / 2.0, panel_w - 24.0, disp_h), Colors.BG_MODAL)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2.0, disp_top - disp_h / 2.0, panel_w - 24.0, disp_h), Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        sel_combatant = tab.combat_manager.get_combatant(tab.selected_combatant_uid or "")
        if sel_combatant:
            # 1. Resumo do Alvo
            size_str = getattr(sel_combatant, "size", "Medium")
            tab._get_text("disp_title", f"ALVO SELECIONADO: {sel_combatant.name.upper()} ({size_str})", 24.0, disp_top - 14.0, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_y="center").draw()
            hp_info = f"HP: {sel_combatant.current_hp}/{sel_combatant.max_hp} • CA: {sel_combatant.armor_class} • Inic: {sel_combatant.initiative_score} • Tam: {size_str}"
            tab._get_text("disp_hp_info", hp_info, 24.0, disp_top - 28.0, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_y="center").draw()

            # 2. Barra de Vida Visual com margens verticais padronizadas
            # margin_top = 10.0 abaixo do texto de HP e margin_bottom = 12.0 antes dos botões de dano
            bar_w = panel_w - 60.0
            bar_h = 8.0
            margin_top = 10.0
            bar_y = (disp_top - 28.0) - margin_top - bar_h / 2.0  # disp_top - 42.0
            pct = max(0.0, min(1.0, sel_combatant.current_hp / max(1, sel_combatant.max_hp)))

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2.0, bar_y, bar_w, bar_h), (40, 45, 55, 255))
            if pct > 0.0:
                fill_w = bar_w * pct
                hp_bar_color = Colors.SUCCESS if pct > 0.5 else (Colors.WARNING if pct > 0.2 else Colors.DANGER)
                arcade.draw_rect_filled(arcade.XYWH(30.0 + fill_w / 2.0, bar_y, fill_w, bar_h), hp_bar_color)

            # 3. Botões Rápidos de Dano (-1, -5, -10, -20) e Cura (+1, +5, +10, +20)
            # margin_bottom = 12.0 após a barra de vida
            margin_bottom = 12.0
            dmg_btn_h = 20.0
            btn_dmg_y = (bar_y - bar_h / 2.0) - margin_bottom - dmg_btn_h / 2.0  # disp_top - 68.0
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70.0) / 8.0

            for i, val in enumerate(dmg_vals):
                bx = 30.0 + i * (dmg_btn_w + 4.0) + dmg_btn_w / 2.0
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, dmg_btn_h), Colors.NPC_RED)
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, dmg_btn_h), Colors.DANGER, Dimensions.BORDER_WIDTH_DEFAULT)
                tab._get_text(f"b_dmg_{val}", str(val), bx, btn_dmg_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            heal_vals = [1, 5, 10, 20]
            for i, val in enumerate(heal_vals):
                bx = 30.0 + (i + 4) * (dmg_btn_w + 4.0) + dmg_btn_w / 2.0
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, dmg_btn_h), (39, 174, 96, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, dmg_btn_h), Colors.SUCCESS, Dimensions.BORDER_WIDTH_DEFAULT)
                tab._get_text(f"b_heal_{val}", f"+{val}", bx, btn_dmg_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # 4. Linha Customizada de Dano/Cura
            custom_y = disp_top - 96.0

            # Stepper [-]
            arcade.draw_rect_filled(arcade.XYWH(45.0, custom_y, 26.0, 22.0), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(45.0, custom_y, 26.0, 22.0), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("b_cust_minus", "[-]", 45.0, custom_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # Caixa do Valor
            arcade.draw_rect_filled(arcade.XYWH(90.0, custom_y, 48.0, 22.0), (15, 20, 28, 255))
            arcade.draw_rect_outline(arcade.XYWH(90.0, custom_y, 48.0, 22.0), Colors.BORDER_FOCUS, Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("cust_val_t", str(tab.custom_hp_value), 90.0, custom_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # Stepper [+]
            arcade.draw_rect_filled(arcade.XYWH(135.0, custom_y, 26.0, 22.0), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(135.0, custom_y, 26.0, 22.0), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("b_cust_plus", "[+]", 135.0, custom_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # Botão Aplicar Dano Customizado
            arcade.draw_rect_filled(arcade.XYWH(215.0, custom_y, 100.0, 22.0), Colors.NPC_RED)
            arcade.draw_rect_outline(arcade.XYWH(215.0, custom_y, 100.0, 22.0), Colors.DANGER, Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("b_apply_dmg", f"⚔️ Dano ({tab.custom_hp_value})", 215.0, custom_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # Botão Aplicar Cura Customizada
            arcade.draw_rect_filled(arcade.XYWH(325.0, custom_y, 100.0, 22.0), (39, 174, 96, 255))
            arcade.draw_rect_outline(arcade.XYWH(325.0, custom_y, 100.0, 22.0), Colors.SUCCESS, Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("b_apply_heal", f"💚 Cura ({tab.custom_hp_value})", 325.0, custom_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # Botão Ocultar / Revelar no Grid
            vis_str = "👁️ Revelar" if sel_combatant.is_hidden else "👁️ Ocultar"
            vis_bg = (120, 40, 31, 255) if sel_combatant.is_hidden else (52, 73, 94, 255)
            arcade.draw_rect_filled(arcade.XYWH(panel_w - 75.0, custom_y, 90.0, 22.0), vis_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w - 75.0, custom_y, 90.0, 22.0), (100, 120, 150, 200), Dimensions.BORDER_WIDTH_DEFAULT)
            tab._get_text("b_toggle_vis", vis_str, panel_w - 75.0, custom_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

            # 5. Condições Táticas D&D 5E (11 Toggles)
            cond_title_y = disp_top - 122.0
            tab._get_text("disp_cond_title", "CONDIÇÕES TÁTICAS (D&D 5E):", 24.0, cond_title_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_y="center").draw()

            cond_names = StatusIconAtlas.get_condition_names()
            cond_btn_y = disp_top - 148.0
            cond_btn_h = 24.0
            cond_spacing = 3.0
            cond_total_w = panel_w - 48.0
            cond_btn_w = (cond_total_w - (len(cond_names) - 1) * cond_spacing) / len(cond_names)

            for idx, cond_name in enumerate(cond_names):
                bx = 24.0 + idx * (cond_btn_w + cond_spacing) + cond_btn_w / 2.0
                is_active = sel_combatant.has_condition(cond_name)
                tex = StatusIconAtlas.get_condition_texture(cond_name)

                if is_active:
                    bg_color = (65, 50, 15, 255)
                    border_color = Colors.ACCENT_GOLD
                    border_w = Dimensions.BORDER_WIDTH_THICK
                else:
                    bg_color = (24, 30, 42, 255)
                    border_color = Colors.BORDER_DEFAULT
                    border_w = Dimensions.BORDER_WIDTH_DEFAULT

                arcade.draw_rect_filled(arcade.XYWH(bx, cond_btn_y, cond_btn_w, cond_btn_h), bg_color)
                arcade.draw_rect_outline(arcade.XYWH(bx, cond_btn_y, cond_btn_w, cond_btn_h), border_color, border_w)

                if tex is not None:
                    PixelIconDrawer.draw_pixel_icon(
                        texture=tex,
                        center_x=bx,
                        center_y=cond_btn_y,
                        target_size=20.0,
                    )
