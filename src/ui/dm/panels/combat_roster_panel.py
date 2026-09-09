import logging
from typing import Any, Tuple
import arcade
from ....domain.models.playablechar import PlayableCharacter
from ....domain.models.entity import EntityType
from ...utils.status_icon_atlas import StatusIconAtlas

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
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), (28, 36, 48, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), (50, 65, 90, 200), 1)

        tab._get_text("th_turn", "TURNO", 28, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="left").draw()
        tab._get_text("th_name", "NOME", 85, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="left").draw()
        tab._get_text("th_type", "TIPO", 240, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        tab._get_text("th_hp", "HP", 305, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        tab._get_text("th_ca", "CA", 365, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        tab._get_text("th_mod", "MOD", 405, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        tab._get_text("th_init", "INIC", 445, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        tab._get_text("th_status", "STATUS", 500, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        tab._get_text("th_vis", "VIS", panel_w - 40, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()

        active_char = tab.combat_manager.active_character
        combatants = tab.combat_manager.turn_order if tab.combat_manager.has_combat_started else tab.combat_manager.combatants
        panels_collapsed = (1 if tab.spell_aoe_panel.is_collapsed else 0) + (1 if tab.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2

        tab.scroll_list.items = combatants
        tab.scroll_list.visible_item_count = max_rows
        list_w = panel_w - 24
        list_h = max_rows * (tab._CombatTabView__item_height + tab._CombatTabView__spacing)
        list_x = 12
        list_top_y = table_top - table_h
        tab.scroll_list.set_bounds(list_x, list_top_y, list_w, list_h)
        tab.scroll_list.set_style(draw_frame=False)

        visible_list = tab.scroll_list.visible_items
        for slot_idx, (actual_idx, combatant) in enumerate(visible_list):
            slot_cx, slot_cy, slot_w, slot_h = tab.scroll_list.get_slot_rect(slot_idx)
            is_active = (combatant == active_char)
            is_selected = (combatant.uid == tab.selected_combatant_uid)

            if is_selected:
                row_bg = (45, 62, 85, 255)
                row_border = (241, 196, 15, 255)
            elif is_active:
                row_bg = (24, 50, 40, 255)
                row_border = (46, 204, 113, 200)
            else:
                row_bg = (18, 24, 34, 255) if actual_idx % 2 == 0 else (22, 28, 40, 255)
                row_border = (50, 65, 90, 150)

            arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), row_bg)
            arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), row_border, 1.2 if (is_selected or is_active) else 0.8)

            # Turn Indicator
            turn_mark = "▶" if is_active else str(actual_idx + 1)
            turn_color = (46, 204, 113, 255) if is_active else (140, 155, 175, 255)
            tab._get_text(f"r_turn_{actual_idx}", turn_mark, 28, slot_cy, turn_color, 8, bold=True, anchor_x="center").draw()

            # Name & Type Logic (Player / Monster / Neutral)
            etype = getattr(combatant, "entity_type", EntityType.PLAYER if isinstance(combatant, PlayableCharacter) else EntityType.MONSTER)
            is_neu = getattr(combatant, "is_neutral", False) or etype == EntityType.NEUTRAL or str(etype).lower() == "neutral"
            is_ply = getattr(combatant, "is_player", False) or isinstance(combatant, PlayableCharacter) or etype == EntityType.PLAYER or str(etype).lower() == "player"

            if is_neu:
                name_color = (241, 196, 15, 255)
                type_str = "NEUTRO"
                type_color = (241, 196, 15, 255)
            elif is_ply:
                name_color = (100, 200, 255, 255)
                type_str = "PJ"
                type_color = (100, 200, 255, 255)
            else:
                name_color = (255, 138, 128, 255)
                type_str = "NPC"
                type_color = (255, 138, 128, 255)

            tab._get_text(f"r_name_{actual_idx}", combatant.name[:18], 55, slot_cy, name_color, 8, bold=True).draw()
            tab._get_text(f"r_type_{actual_idx}", type_str, 240, slot_cy, type_color, 7.5, bold=False, anchor_x="center").draw()

            # HP
            hp_str = f"{combatant.current_hp}/{combatant.max_hp}"
            hp_c = (46, 204, 113, 255) if combatant.current_hp > (combatant.max_hp / 2) else (231, 76, 60, 255)
            tab._get_text(f"r_hp_{actual_idx}", hp_str, 305, slot_cy, hp_c, 8, bold=True, anchor_x="center").draw()

            # CA
            tab._get_text(f"r_ca_{actual_idx}", str(combatant.armor_class), 365, slot_cy, (241, 196, 15, 255), 8, bold=True, anchor_x="center").draw()

            # Mod
            mod_str = f"{combatant.initiative_mod:+d}"
            tab._get_text(f"r_mod_{actual_idx}", mod_str, 405, slot_cy, (180, 190, 205, 255), 8, bold=False, anchor_x="center").draw()

            # Init
            tab._get_text(f"r_init_{actual_idx}", str(combatant.initiative_score), 445, slot_cy, (230, 235, 245, 255), 8, bold=True, anchor_x="center").draw()

            # Status
            status_str = "Vivo" if combatant.is_alive else "Incapacitado"
            status_c = (46, 204, 113, 255) if combatant.is_alive else (192, 57, 43, 255)
            tab._get_text(f"r_stat_{actual_idx}", status_str, 500, slot_cy, status_c, 7, bold=False, anchor_x="center").draw()

            # Visibility Toggle Icon
            vis_icon = "👁️❌" if combatant.is_hidden else "👁️"
            tab._get_text(f"r_vis_{actual_idx}", vis_icon, panel_w - 40, slot_cy, (255, 255, 255, 255), 9, bold=False, anchor_x="center").draw()

        if len(combatants) > tab.scroll_list.visible_item_count:
            tab.scroll_list._draw_scroll_indicator(tab.text_cache)

        return table_top - table_h, len(combatants)

    @staticmethod
    def draw_hp_dispatcher(tab: Any, panel_w: float, disp_top: float) -> None:
        """Desenha o painel despachante de dano, cura e condições do combatente selecionado."""
        disp_h = 168
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, disp_top - disp_h / 2, panel_w - 24, disp_h), (18, 24, 34, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, disp_top - disp_h / 2, panel_w - 24, disp_h), (50, 65, 90, 200), 1)

        sel_combatant = tab.combat_manager.get_combatant(tab.selected_combatant_uid or "")
        if sel_combatant:
            # Resumo do Alvo
            size_str = getattr(sel_combatant, "size", "Medium")
            tab._get_text("disp_title", f"ALVO SELECIONADO: {sel_combatant.name.upper()} ({size_str})", 24, disp_top - 14, (241, 196, 15, 255), 9, bold=True).draw()
            hp_info = f"HP: {sel_combatant.current_hp}/{sel_combatant.max_hp} • CA: {sel_combatant.armor_class} • Inic: {sel_combatant.initiative_score} • Tam: {size_str}"
            tab._get_text("disp_hp_info", hp_info, 24, disp_top - 28, (200, 210, 225, 255), 8, bold=False).draw()

            # Barra de Vida Visual
            bar_w = panel_w - 60
            bar_h = 8
            bar_y = disp_top - 40
            pct = max(0.0, min(1.0, sel_combatant.current_hp / max(1, sel_combatant.max_hp)))

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, bar_y, bar_w, bar_h), (40, 45, 55, 255))
            if pct > 0:
                fill_w = bar_w * pct
                hp_bar_color = (46, 204, 113, 255) if pct > 0.5 else ((241, 196, 15, 255) if pct > 0.2 else (231, 76, 60, 255))
                arcade.draw_rect_filled(arcade.XYWH(30 + fill_w / 2, bar_y, fill_w, bar_h), hp_bar_color)

            # Botões Rápidos de Dano (-1, -5, -10, -20)
            btn_dmg_y = disp_top - 62
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70) / 8

            for i, val in enumerate(dmg_vals):
                bx = 30 + i * (dmg_btn_w + 4) + dmg_btn_w / 2
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (192, 57, 43, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (231, 76, 60, 255), 1)
                tab._get_text(f"b_dmg_{val}", str(val), bx, btn_dmg_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botões Rápidos de Cura (+1, +5, +10, +20)
            heal_vals = [1, 5, 10, 20]
            for i, val in enumerate(heal_vals):
                bx = 30 + (i + 4) * (dmg_btn_w + 4) + dmg_btn_w / 2
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (39, 174, 96, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (46, 204, 113, 255), 1)
                tab._get_text(f"b_heal_{val}", f"+{val}", bx, btn_dmg_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Linha Customizada de Dano/Cura
            custom_y = disp_top - 90

            # Stepper [-]
            arcade.draw_rect_filled(arcade.XYWH(45, custom_y, 26, 22), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(45, custom_y, 26, 22), (70, 90, 120, 200), 1)
            tab._get_text("b_cust_minus", "[-]", 45, custom_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Caixa do Valor
            arcade.draw_rect_filled(arcade.XYWH(90, custom_y, 48, 22), (15, 20, 28, 255))
            arcade.draw_rect_outline(arcade.XYWH(90, custom_y, 48, 22), (241, 196, 15, 200), 1)
            tab._get_text("cust_val_t", str(tab.custom_hp_value), 90, custom_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

            # Stepper [+]
            arcade.draw_rect_filled(arcade.XYWH(135, custom_y, 26, 22), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(135, custom_y, 26, 22), (70, 90, 120, 200), 1)
            tab._get_text("b_cust_plus", "[+]", 135, custom_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Botão Aplicar Dano Customizado
            arcade.draw_rect_filled(arcade.XYWH(215, custom_y, 100, 22), (192, 57, 43, 255))
            arcade.draw_rect_outline(arcade.XYWH(215, custom_y, 100, 22), (231, 76, 60, 255), 1)
            tab._get_text("b_apply_dmg", f"⚔️ Dano ({tab.custom_hp_value})", 215, custom_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botão Aplicar Cura Customizada
            arcade.draw_rect_filled(arcade.XYWH(325, custom_y, 100, 22), (39, 174, 96, 255))
            arcade.draw_rect_outline(arcade.XYWH(325, custom_y, 100, 22), (46, 204, 113, 255), 1)
            tab._get_text("b_apply_heal", f"💚 Cura ({tab.custom_hp_value})", 325, custom_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botão Ocultar / Revelar no Grid
            vis_str = "👁️ Revelar" if sel_combatant.is_hidden else "👁️ Ocultar"
            vis_bg = (120, 40, 31, 255) if sel_combatant.is_hidden else (52, 73, 94, 255)
            arcade.draw_rect_filled(arcade.XYWH(panel_w - 75, custom_y, 90, 22), vis_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w - 75, custom_y, 90, 22), (100, 120, 150, 200), 1)
            tab._get_text("b_toggle_vis", vis_str, panel_w - 75, custom_y, (240, 240, 245, 255), 8, bold=True, anchor_x="center").draw()

            # Condições Táticas D&D 5E (11 Toggles)
            cond_title_y = disp_top - 114
            tab._get_text("disp_cond_title", "CONDIÇÕES TÁTICAS (D&D 5E):", 24, cond_title_y, (180, 190, 205, 255), 7.5, bold=True).draw()

            cond_names = StatusIconAtlas.get_condition_names()
            cond_btn_y = disp_top - 140
            cond_btn_h = 24
            cond_spacing = 3
            cond_total_w = panel_w - 48
            cond_btn_w = (cond_total_w - (len(cond_names) - 1) * cond_spacing) / len(cond_names)

            for idx, cond_name in enumerate(cond_names):
                bx = 24 + idx * (cond_btn_w + cond_spacing) + cond_btn_w / 2
                is_active = sel_combatant.has_condition(cond_name)
                tex = StatusIconAtlas.get_condition_texture(cond_name)

                if is_active:
                    bg_color = (65, 50, 15, 255)
                    border_color = (241, 196, 15, 255)
                    border_w = 2.0
                else:
                    bg_color = (24, 30, 42, 255)
                    border_color = (50, 65, 88, 180)
                    border_w = 1.0

                arcade.draw_rect_filled(arcade.XYWH(bx, cond_btn_y, cond_btn_w, cond_btn_h), bg_color)
                arcade.draw_rect_outline(arcade.XYWH(bx, cond_btn_y, cond_btn_w, cond_btn_h), border_color, border_w)

                if tex is not None:
                    arcade.draw_texture_rect(
                        tex,
                        arcade.XYWH(bx, cond_btn_y, 13, 13),
                        pixelated=True,
                    )
