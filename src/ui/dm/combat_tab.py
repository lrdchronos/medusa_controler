from typing import Optional, List, Dict, Any, Callable
import arcade
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.playablechar import PlayableCharacter
from ...domain.models.entity import Entity
from .spell_aoe_panel import SpellAoEPanel


class CombatTabView:
    """
    Componente da Aba de Combate Ativo (Barra de Ações de Turno, Painel de Feitiços AoE,
    Roster de Combatentes e Despachante de Dano/Cura).
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.selected_combatant_uid: Optional[str] = None
        self.custom_hp_value: int = 8
        self.text_cache: Dict[str, arcade.Text] = {}
        self.spell_aoe_panel = SpellAoEPanel(session_manager=self.session_manager)

    def _get_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool = True,
        anchor_x: str = "left",
        anchor_y: str = "center",
    ) -> arcade.Text:
        cached = self.text_cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            self.text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
        return cached

    def ensure_valid_selection(self) -> None:
        """Garante que haja um combatente válido selecionado."""
        combatants = self.combat_manager.combatants
        if combatants:
            if not self.selected_combatant_uid or not any(c.uid == self.selected_combatant_uid for c in combatants):
                self.selected_combatant_uid = combatants[0].uid
        else:
            self.selected_combatant_uid = None

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha todo o painel de combate ativo."""
        self.ensure_valid_selection()

        # 1. Barra de Ações Rápidas de Combate
        bar_y = top_y - 20
        btn_w = (panel_w - 36) / 4
        btn_h = 28

        # Botão 1: Rolar Iniciativas (Abre Modal de Staging)
        b1_x = 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b1_x, bar_y, btn_w - 4, btn_h), (142, 68, 173, 255))
        arcade.draw_rect_outline(arcade.XYWH(b1_x, bar_y, btn_w - 4, btn_h), (155, 89, 182, 255), 1)
        self._get_text("cm_b_init", "🎲 Rolar Iniciativas", b1_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 2: Turno Anterior
        b2_x = 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b2_x, bar_y, btn_w - 4, btn_h), (41, 128, 185, 255))
        arcade.draw_rect_outline(arcade.XYWH(b2_x, bar_y, btn_w - 4, btn_h), (52, 152, 219, 255), 1)
        self._get_text("cm_b_prev", "◀ Turno Anterior", b2_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 3: Próximo Turno
        b3_x = 12 + 2 * btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b3_x, bar_y, btn_w - 4, btn_h), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b3_x, bar_y, btn_w - 4, btn_h), (46, 204, 113, 255), 1)
        self._get_text("cm_b_next", "▶ Próximo Turno", b3_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 4: Finalizar Combate
        b4_x = 12 + 3 * btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b4_x, bar_y, btn_w - 4, btn_h), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b4_x, bar_y, btn_w - 4, btn_h), (231, 76, 60, 255), 1)
        self._get_text("cm_b_end", "🏁 Finalizar Combate", b4_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 2. Informação de Rodada e Turno Ativo
        info_y = bar_y - 24
        active_char = self.combat_manager.active_character
        round_num = getattr(self.combat_manager, "round_number", getattr(self.combat_manager, "current_round", 1))
        turn_str = f"⚔️ Rodada: {round_num} • Turno Ativo: {active_char.name if active_char else 'Nenhum'}"
        self._get_text("cm_info_turn", turn_str, 16, info_y, (241, 196, 15, 255), 9, bold=True).draw()

        # 3. Painel de Feitiços (Spell AoE Overlay)
        spell_next_y = self.spell_aoe_panel.draw(panel_w, info_y - 12)

        # 4. Tabela de Combatentes (Roster)
        table_top = spell_next_y
        table_h = 22
        table_y = table_top - table_h / 2

        # Cabeçalho da Tabela
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), (28, 36, 48, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), (50, 65, 90, 200), 1)

        self._get_text("th_turn", "TURNO", 28, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="left").draw()
        self._get_text("th_name", "NOME", 85, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="left").draw()
        self._get_text("th_type", "TIPO", 240, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_hp", "HP", 305, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_ca", "CA", 365, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_mod", "MOD", 405, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_init", "INIC", 445, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_status", "STATUS", 500, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_vis", "VIS", panel_w - 40, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()

        # Linhas de Combatentes (Turn Order ou Lista Geral)
        combatants = self.combat_manager.turn_order if self.combat_manager.has_combat_started else self.combat_manager.combatants
        row_h = 24
        max_rows = 6 if not self.spell_aoe_panel.is_collapsed else 8

        for idx, combatant in enumerate(combatants[:max_rows]):
            cy = table_top - table_h - idx * (row_h + 2) - row_h / 2
            is_active = (combatant == active_char)
            is_selected = (combatant.uid == self.selected_combatant_uid)

            if is_selected:
                row_bg = (45, 62, 85, 255)
                row_border = (241, 196, 15, 255)
            elif is_active:
                row_bg = (24, 50, 40, 255)
                row_border = (46, 204, 113, 200)
            else:
                row_bg = (20, 26, 36, 255) if idx % 2 == 0 else (16, 21, 30, 255)
                row_border = (40, 50, 70, 150)

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, cy, panel_w - 24, row_h), row_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, cy, panel_w - 24, row_h), row_border, 1)

            # Turno
            turn_str_val = "▶ ATIVO" if is_active else f"#{idx + 1}"
            turn_col = (241, 196, 15, 255) if is_active else (160, 175, 195, 255)
            self._get_text(f"r_{idx}_t", turn_str_val, 28, cy, turn_col, 8, bold=True, anchor_x="left").draw()

            # Nome
            name_col = (100, 200, 255, 255) if isinstance(combatant, PlayableCharacter) else (255, 138, 128, 255)
            self._get_text(f"r_{idx}_n", combatant.name[:16], 85, cy, name_col, 8, bold=True, anchor_x="left").draw()

            # Tipo
            ctype = "Jogador" if isinstance(combatant, PlayableCharacter) else "Monstro"
            self._get_text(f"r_{idx}_ty", ctype, 240, cy, (200, 210, 225, 255), 7, bold=False, anchor_x="center").draw()

            # HP
            hp_s = f"{combatant.current_hp}/{combatant.max_hp}"
            hp_c = (46, 204, 113, 255) if combatant.current_hp > combatant.max_hp * 0.5 else (231, 76, 60, 255)
            self._get_text(f"r_{idx}_hp", hp_s, 305, cy, hp_c, 8, bold=True, anchor_x="center").draw()

            # CA
            self._get_text(f"r_{idx}_ca", str(combatant.armor_class), 365, cy, (240, 240, 240, 255), 8, bold=False, anchor_x="center").draw()

            # Mod
            mod_s = f"+{combatant.initiative_mod}" if combatant.initiative_mod >= 0 else str(combatant.initiative_mod)
            self._get_text(f"r_{idx}_mod", mod_s, 405, cy, (180, 190, 205, 255), 8, bold=False, anchor_x="center").draw()

            # Inic
            self._get_text(f"r_{idx}_init", str(combatant.initiative_score), 445, cy, (241, 196, 15, 255), 8, bold=True, anchor_x="center").draw()

            # Status
            if not combatant.is_alive:
                st_s = "💀 Morto"
            elif combatant.is_hidden:
                st_s = "🥷 Oculto"
            elif is_active:
                st_s = "⚡ Turno"
            else:
                st_s = "🟢 Pronto"
            self._get_text(f"r_{idx}_st", st_s, 500, cy, (220, 220, 220, 255), 7, bold=False, anchor_x="center").draw()

            # Oculto Toggle (is_hidden)
            eye_s = "👁️❌" if combatant.is_hidden else "👁️"
            self._get_text(f"r_{idx}_eye", eye_s, panel_w - 40, cy, (255, 255, 255, 255), 8, bold=False, anchor_x="center").draw()

        # 5. Despachante Rápido de Dano e Cura
        rendered_rows = min(len(combatants), max_rows)
        disp_top = table_top - table_h - rendered_rows * (row_h + 2) - 8
        disp_h = 135
        disp_cy = disp_top - disp_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, disp_cy, panel_w - 24, disp_h), (20, 25, 35, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, disp_cy, panel_w - 24, disp_h), (60, 75, 100, 200), 1)

        sel_combatant = self.combat_manager.get_combatant(self.selected_combatant_uid or "")
        if sel_combatant:
            # Resumo do Alvo
            self._get_text("disp_title", f"ALVO SELECIONADO: {sel_combatant.name.upper()}", 24, disp_top - 14, (241, 196, 15, 255), 9, bold=True).draw()
            hp_info = f"HP: {sel_combatant.current_hp}/{sel_combatant.max_hp} • CA: {sel_combatant.armor_class} • Inic: {sel_combatant.initiative_score}"
            self._get_text("disp_hp_info", hp_info, 24, disp_top - 28, (200, 210, 225, 255), 8, bold=False).draw()

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
            btn_dmg_y = disp_top - 66
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70) / 8

            for i, val in enumerate(dmg_vals):
                bx = 30 + i * (dmg_btn_w + 4) + dmg_btn_w / 2
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 22), (192, 57, 43, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 22), (231, 76, 60, 255), 1)
                self._get_text(f"b_dmg_{val}", str(val), bx, btn_dmg_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botões Rápidos de Cura (+1, +5, +10, +20)
            heal_vals = [1, 5, 10, 20]
            for i, val in enumerate(heal_vals):
                bx = 30 + (i + 4) * (dmg_btn_w + 4) + dmg_btn_w / 2
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 22), (39, 174, 96, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 22), (46, 204, 113, 255), 1)
                self._get_text(f"b_heal_{val}", f"+{val}", bx, btn_dmg_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Linha Customizada de Dano/Cura
            custom_y = disp_top - 100

            # Stepper [-]
            arcade.draw_rect_filled(arcade.XYWH(45, custom_y, 26, 24), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(45, custom_y, 26, 24), (70, 90, 120, 200), 1)
            self._get_text("b_cust_minus", "[-]", 45, custom_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Caixa do Valor
            arcade.draw_rect_filled(arcade.XYWH(90, custom_y, 48, 24), (15, 20, 28, 255))
            arcade.draw_rect_outline(arcade.XYWH(90, custom_y, 48, 24), (241, 196, 15, 200), 1)
            self._get_text("cust_val_t", str(self.custom_hp_value), 90, custom_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

            # Stepper [+]
            arcade.draw_rect_filled(arcade.XYWH(135, custom_y, 26, 24), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(135, custom_y, 26, 24), (70, 90, 120, 200), 1)
            self._get_text("b_cust_plus", "[+]", 135, custom_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Botão Aplicar Dano Customizado
            arcade.draw_rect_filled(arcade.XYWH(215, custom_y, 100, 24), (192, 57, 43, 255))
            arcade.draw_rect_outline(arcade.XYWH(215, custom_y, 100, 24), (231, 76, 60, 255), 1)
            self._get_text("b_apply_dmg", f"⚔️ Dano ({self.custom_hp_value})", 215, custom_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botão Aplicar Cura Customizada
            arcade.draw_rect_filled(arcade.XYWH(325, custom_y, 100, 24), (39, 174, 96, 255))
            arcade.draw_rect_outline(arcade.XYWH(325, custom_y, 100, 24), (46, 204, 113, 255), 1)
            self._get_text("b_apply_heal", f"💚 Cura ({self.custom_hp_value})", 325, custom_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botão Ocultar / Revelar no Grid
            vis_str = "👁️ Revelar" if sel_combatant.is_hidden else "👁️ Ocultar"
            vis_bg = (120, 40, 31, 255) if sel_combatant.is_hidden else (52, 73, 94, 255)
            arcade.draw_rect_filled(arcade.XYWH(panel_w - 75, custom_y, 90, 24), vis_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w - 75, custom_y, 90, 24), (100, 120, 150, 200), 1)
            self._get_text("b_toggle_vis", vis_str, panel_w - 75, custom_y, (240, 240, 245, 255), 8, bold=True, anchor_x="center").draw()

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        open_initiative_modal_callback: Callable[[], None],
    ) -> bool:
        """Processa cliques na aba de combate ativo."""
        # 1. Barra de Ações Rápidas de Combate
        bar_y = top_y - 20
        btn_w = (panel_w - 36) / 4
        btn_h = 28

        if abs(y - bar_y) <= btn_h / 2:
            # Botão 1: Rolar Iniciativas
            b1_x = 12 + btn_w / 2
            if abs(x - b1_x) <= (btn_w - 4) / 2:
                open_initiative_modal_callback()
                return True

            # Botão 2: Turno Anterior
            b2_x = 12 + btn_w + btn_w / 2
            if abs(x - b2_x) <= (btn_w - 4) / 2:
                self.combat_manager.previous_turn()
                return True

            # Botão 3: Próximo Turno
            b3_x = 12 + 2 * btn_w + btn_w / 2
            if abs(x - b3_x) <= (btn_w - 4) / 2:
                self.combat_manager.next_turn()
                return True

            # Botão 4: Finalizar Combate
            b4_x = 12 + 3 * btn_w + btn_w / 2
            if abs(x - b4_x) <= (btn_w - 4) / 2:
                self.session_manager.end_combat(DisplayState.IDLE)
                return True

        # 2. Cliques no Painel de Feitiços (SpellAoEPanel)
        info_y = bar_y - 24
        if self.spell_aoe_panel.handle_click(x, y, panel_w, info_y - 12):
            return True

        # 3. Cliques nas Linhas da Tabela de Combatentes
        spell_body_h = 82 if not self.spell_aoe_panel.is_collapsed else 0
        spell_next_y = info_y - 12 - (28 + spell_body_h) - 8
        table_top = spell_next_y
        table_h = 22
        row_h = 24
        max_rows = 6 if not self.spell_aoe_panel.is_collapsed else 8

        combatants = self.combat_manager.turn_order if self.combat_manager.has_combat_started else self.combat_manager.combatants

        for idx, combatant in enumerate(combatants[:max_rows]):
            cy = table_top - table_h - idx * (row_h + 2) - row_h / 2
            if abs(y - cy) <= row_h / 2:
                # Clique no ícone de visibilidade (lado direito)
                if abs(x - (panel_w - 40)) <= 20:
                    self.combat_manager.toggle_combatant_visibility(combatant.uid)
                    return True

                # Clique para selecionar o combatente
                if abs(x - panel_w / 2) <= (panel_w - 24) / 2:
                    self.selected_combatant_uid = combatant.uid
                    return True

        # 4. Cliques no Despachante de Dano e Cura
        rendered_rows = min(len(combatants), max_rows)
        disp_top = table_top - table_h - rendered_rows * (row_h + 2) - 8

        sel_combatant = self.combat_manager.get_combatant(self.selected_combatant_uid or "")
        if sel_combatant:
            btn_dmg_y = disp_top - 66
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70) / 8

            # Dano Rápido
            if abs(y - btn_dmg_y) <= 11:
                for i, val in enumerate(dmg_vals):
                    bx = 30 + i * (dmg_btn_w + 4) + dmg_btn_w / 2
                    if abs(x - bx) <= dmg_btn_w / 2:
                        self.combat_manager.apply_damage(sel_combatant.uid, abs(val))
                        return True

                # Cura Rápida
                heal_vals = [1, 5, 10, 20]
                for i, val in enumerate(heal_vals):
                    bx = 30 + (i + 4) * (dmg_btn_w + 4) + dmg_btn_w / 2
                    if abs(x - bx) <= dmg_btn_w / 2:
                        self.combat_manager.apply_heal(sel_combatant.uid, val)
                        return True

            custom_y = disp_top - 100
            if abs(y - custom_y) <= 12:
                # Stepper [-]
                if abs(x - 45) <= 13:
                    self.custom_hp_value = max(1, self.custom_hp_value - 1)
                    return True

                # Stepper [+]
                if abs(x - 135) <= 13:
                    self.custom_hp_value = min(999, self.custom_hp_value + 1)
                    return True

                # Dano Customizado
                if abs(x - 215) <= 50:
                    self.combat_manager.apply_damage(sel_combatant.uid, self.custom_hp_value)
                    return True

                # Cura Customizada
                if abs(x - 325) <= 50:
                    self.combat_manager.apply_heal(sel_combatant.uid, self.custom_hp_value)
                    return True

                # Ocultar / Revelar
                if abs(x - (panel_w - 75)) <= 45:
                    self.combat_manager.toggle_combatant_visibility(sel_combatant.uid)
                    return True

        return False

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        """Repassa evento de arraste do mouse para o painel de magias."""
        return self.spell_aoe_panel.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def handle_mouse_release(self, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        """Repassa evento de liberação de clique para o painel de magias."""
        self.spell_aoe_panel.handle_mouse_release(x, y, button, modifiers)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Repassa teclas para os inputs do painel de magias."""
        return self.spell_aoe_panel.handle_key_press(symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        """Repassa liberação de teclas para o painel de magias."""
        self.spell_aoe_panel.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        """Repassa texto digitado para os inputs do painel de magias."""
        return self.spell_aoe_panel.handle_text_input(text)

    def on_update(self, dt: float) -> None:
        """Atualiza animações e inputs do painel de feitiços."""
        self.spell_aoe_panel.on_update(dt)
