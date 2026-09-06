import logging
from typing import Optional, List, Dict, Any, Callable, Tuple
import arcade
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.playablechar import PlayableCharacter
from ...domain.models.entity import Entity
from .spell_aoe_panel import SpellAoEPanel
from .fog_control_panel import FogControlPanel

logger = logging.getLogger(__name__)

class CombatTabView:
    """
    Componente da Aba de Combate Ativo (Barra de Ações de Turno, Painel de Feitiços AoE,
    Painel de Névoa de Guerra, Roster de Combatentes, Despachante de Dano/Cura e Save State).
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.selected_combatant_uid: Optional[str] = None
        self.custom_hp_value: int = 8
        self.text_cache: Dict[str, arcade.Text] = {}
        self.spell_aoe_panel = SpellAoEPanel(session_manager=self.session_manager)
        self.fog_panel = FogControlPanel(
            fog_manager=self.combat_manager.fog_manager,
            dimensions_provider=self._get_grid_dimensions,
            save_callback=self.combat_manager.save_fog_to_encounter_file,
        )

        # Notificação Toast de Confirmação de Salvamento
        self.toast_message: Optional[str] = None
        self.toast_timer: float = 0.0

        # Modal de Confirmação ao Finalizar Combate (Limpar ou Manter Save)
        self.pending_end_combat_modal: bool = False

    def _get_grid_dimensions(self) -> Tuple[int, int]:
        """Retorna dimensões (colunas, linhas) da grade tática ativa."""
        grid_mgr = self.combat_manager.grid_manager
        if grid_mgr is not None:
            return (grid_mgr.columns, grid_mgr.rows)
        return (25, 14)


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
            cached.text = text
        return cached

    def ensure_valid_selection(self) -> None:
        """Garante que haja um combatente válido selecionado."""
        combatants = self.combat_manager.combatants
        if combatants:
            if not self.selected_combatant_uid or not any(c.uid == self.selected_combatant_uid for c in combatants):
                self.selected_combatant_uid = combatants[0].uid
        else:
            self.selected_combatant_uid = None

    def trigger_save_combat(self) -> None:
        """Salva o estado atual de combate e dispara toast de confirmação."""
        success = self.combat_manager.save_combat_state()
        if success:
            self.toast_message = "Progresso do combate salvo com sucesso!"
            self.toast_timer = 3.0
            logger.info("Progresso do combate salvo com sucesso pelo usuário.")
        else:
            self.toast_message = "Falha ao salvar progresso do combate!"
            self.toast_timer = 3.0

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha todo o painel de combate ativo."""
        self.ensure_valid_selection()
        
        # Atualiza timer do toast
        if self.toast_timer > 0:
            self.toast_timer -= 1/60 # Simplificação: assumindo 60fps

        # 1. Barra de Ações Rápidas de Combate (5 Botões OOD)
        bar_y = top_y - 20
        btn_w = (panel_w - 40) / 5
        btn_h = 28

        # Botão 1: Rolar Iniciativas (Abre Modal de Staging)
        b1_x = 12 + 0 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b1_x, bar_y, btn_w, btn_h), (142, 68, 173, 255))
        arcade.draw_rect_outline(arcade.XYWH(b1_x, bar_y, btn_w, btn_h), (155, 89, 182, 255), 1)
        self._get_text("cm_b_init", "🎲 Inic", b1_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 2: Turno Anterior
        b2_x = 12 + 1 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b2_x, bar_y, btn_w, btn_h), (41, 128, 185, 255))
        arcade.draw_rect_outline(arcade.XYWH(b2_x, bar_y, btn_w, btn_h), (52, 152, 219, 255), 1)
        self._get_text("cm_b_prev", "◀ Turno", b2_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 3: Próximo Turno
        b3_x = 12 + 2 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b3_x, bar_y, btn_w, btn_h), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b3_x, bar_y, btn_w, btn_h), (46, 204, 113, 255), 1)
        self._get_text("cm_b_next", "▶ Turno", b3_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 4: Pausar e Salvar Combate
        b4_x = 12 + 3 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b4_x, bar_y, btn_w, btn_h), (211, 84, 0, 255))
        arcade.draw_rect_outline(arcade.XYWH(b4_x, bar_y, btn_w, btn_h), (230, 126, 34, 255), 1)
        self._get_text("cm_b_save", "💾 Salvar", b4_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão 5: Finalizar Combate
        b5_x = 12 + 4 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b5_x, bar_y, btn_w, btn_h), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b5_x, bar_y, btn_w, btn_h), (231, 76, 60, 255), 1)
        self._get_text("cm_b_end", "🏁 Sair", b5_x, bar_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 2. Informação de Rodada e Turno Ativo
        info_y = bar_y - 24
        active_char = self.combat_manager.active_character
        round_num = getattr(self.combat_manager, "round_number", getattr(self.combat_manager, "current_round", 1))
        turn_str = f"⚔️ Rodada: {round_num} • Turno Ativo: {active_char.name if active_char else 'Nenhum'}"
        self._get_text("cm_info_turn", turn_str, 16, info_y, (241, 196, 15, 255), 9, bold=True).draw()

        # Notificação Toast Flutuante de Salvamento
        if self.toast_timer > 0 and self.toast_message:
            toast_alpha = min(255, int((self.toast_timer / 0.4) * 255)) if self.toast_timer < 0.4 else 255
            toast_bg = (20, 60, 35, min(240, toast_alpha))
            toast_bd = (46, 204, 113, toast_alpha)
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, info_y, panel_w - 30, 22), toast_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, info_y, panel_w - 30, 22), toast_bd, 1.2)
            self._get_text("cm_toast", f"💾 {self.toast_message}", panel_w / 2, info_y, (255, 255, 255, toast_alpha), 8.5, bold=True, anchor_x="center").draw()

        # 3. Painel de Feitiços (Spell AoE Overlay)
        spell_next_y = self.spell_aoe_panel.draw(panel_w, info_y - 12)

        # 4. Painel de Névoa de Guerra (Fog of War Control Panel)
        fog_next_y = self.fog_panel.draw(panel_w, spell_next_y)

        # 5. Tabela de Combatentes (Roster)
        table_top = fog_next_y
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
        panels_collapsed = (1 if self.spell_aoe_panel.is_collapsed else 0) + (1 if self.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2

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
                row_bg = (18, 24, 34, 255) if idx % 2 == 0 else (22, 28, 40, 255)
                row_border = (50, 65, 90, 150)

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, cy, panel_w - 24, row_h), row_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, cy, panel_w - 24, row_h), row_border, 1.2 if (is_selected or is_active) else 0.8)

            # Turn Indicator
            turn_mark = "▶" if is_active else str(idx + 1)
            turn_color = (46, 204, 113, 255) if is_active else (140, 155, 175, 255)
            self._get_text(f"r_turn_{idx}", turn_mark, 28, cy, turn_color, 8, bold=True, anchor_x="center").draw()

            # Name
            name_color = (100, 200, 255, 255) if isinstance(combatant, PlayableCharacter) else (255, 138, 128, 255)
            self._get_text(f"r_name_{idx}", combatant.name[:18], 55, cy, name_color, 8, bold=True).draw()

            # Type
            type_str = "PJ" if isinstance(combatant, PlayableCharacter) else "NPC"
            self._get_text(f"r_type_{idx}", type_str, 240, cy, (160, 175, 195, 255), 8, bold=False, anchor_x="center").draw()

            # HP
            hp_str = f"{combatant.current_hp}/{combatant.max_hp}"
            hp_c = (46, 204, 113, 255) if combatant.current_hp > (combatant.max_hp / 2) else (231, 76, 60, 255)
            self._get_text(f"r_hp_{idx}", hp_str, 305, cy, hp_c, 8, bold=True, anchor_x="center").draw()

            # CA
            self._get_text(f"r_ca_{idx}", str(combatant.armor_class), 365, cy, (241, 196, 15, 255), 8, bold=True, anchor_x="center").draw()

            # Mod
            mod_str = f"{combatant.initiative_mod:+d}"
            self._get_text(f"r_mod_{idx}", mod_str, 405, cy, (180, 190, 205, 255), 8, bold=False, anchor_x="center").draw()

            # Init
            self._get_text(f"r_init_{idx}", str(combatant.initiative_score), 445, cy, (230, 235, 245, 255), 8, bold=True, anchor_x="center").draw()

            # Status
            status_str = "Vivo" if combatant.is_alive else "Incapacitado"
            status_c = (46, 204, 113, 255) if combatant.is_alive else (192, 57, 43, 255)
            self._get_text(f"r_stat_{idx}", status_str, 500, cy, status_c, 7, bold=False, anchor_x="center").draw()

            # Visibility Toggle Icon
            vis_icon = "👁️❌" if combatant.is_hidden else "👁️"
            self._get_text(f"r_vis_{idx}", vis_icon, panel_w - 40, cy, (255, 255, 255, 255), 9, bold=False, anchor_x="center").draw()

        # 5. Painel Inferior: Despachante de Dano / Cura do Alvo Selecionado
        disp_top = table_top - table_h - min(len(combatants), max_rows) * (row_h + 2) - 8
        disp_h = 130
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, disp_top - disp_h / 2, panel_w - 24, disp_h), (18, 24, 34, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, disp_top - disp_h / 2, panel_w - 24, disp_h), (50, 65, 90, 200), 1)

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

        # 6. Modal de Confirmação ao Finalizar Combate (Limpar ou Manter Save)
        if self.pending_end_combat_modal:
            self._draw_end_combat_modal(panel_w, top_y)

    def _draw_end_combat_modal(self, panel_w: float, top_y: float) -> None:
        """Renderiza o modal de confirmação para finalizar combate e limpar ou manter o save."""
        # Backdrop semitransparente
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, top_y / 2, panel_w, top_y), (10, 14, 20, 220))

        modal_w = min(panel_w - 24, 460.0)
        modal_h = 190.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2

        # Caixa do Diálogo Dark Fantasy
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (22, 28, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (192, 57, 43, 255), 2.0)

        # Cabeçalho de Alerta
        self._get_text("end_mod_hdr", "🏁 FINALIZAR COMBATE TÁTICO", modal_cx, modal_cy + modal_h / 2 - 20, (241, 196, 15, 255), 10, bold=True, anchor_x="center").draw()

        # Mensagem do Modal
        msg_line1 = "Deseja encerrar o combate e limpar o save residual do disco,"
        msg_line2 = "ou manter o arquivo de progresso salvo para consultas futuras?"
        self._get_text("end_mod_m1", msg_line1, modal_cx, modal_cy + 22, (220, 225, 235, 255), 8.5, bold=False, anchor_x="center").draw()
        self._get_text("end_mod_m2", msg_line2, modal_cx, modal_cy + 5, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()

        # Botões de Ação
        btn_y = modal_cy - modal_h / 2 + 55
        btn_w = (modal_w - 32) / 2

        # 1. [ 🗑️ Limpar Save & Sair ]
        b_clean_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_clean_x, btn_y, btn_w - 4, 32), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_clean_x, btn_y, btn_w - 4, 32), (231, 76, 60, 255), 2)
        self._get_text("end_mod_b_clean", "🗑️ Limpar Save & Sair", b_clean_x, btn_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # 2. [ 💾 Manter Save & Sair ]
        b_keep_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_keep_x, btn_y, btn_w - 4, 32), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_keep_x, btn_y, btn_w - 4, 32), (46, 204, 113, 255), 2)
        self._get_text("end_mod_b_keep", "💾 Manter Save & Sair", b_keep_x, btn_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # 3. [ ❌ Cancelar ]
        btn_can_y = modal_cy - modal_h / 2 + 20
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (70, 90, 120, 200), 1)
        self._get_text("end_mod_b_can", "❌ Cancelar", modal_cx, btn_can_y, (200, 210, 225, 255), 8, bold=True, anchor_x="center").draw()

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        open_initiative_modal_callback: Callable[[], None],
    ) -> bool:
        """Processa cliques na aba de combate ativo."""
        # Interceptação Modal de Encerramento com Save
        if self.pending_end_combat_modal:
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
                self.combat_manager.delete_save_state()
                self.pending_end_combat_modal = False
                self.session_manager.end_combat(DisplayState.IDLE)
                return True

            # Clique em [ 💾 Manter Save & Sair ]
            if abs(y - btn_y) <= 16 and abs(x - b_keep_x) <= (btn_w - 4) / 2:
                logger.info("Encerrando combate preservando save no disco.")
                self.pending_end_combat_modal = False
                self.session_manager.end_combat(DisplayState.IDLE)
                return True

            # Clique em [ ❌ Cancelar ]
            if abs(y - btn_can_y) <= 12 and abs(x - modal_cx) <= (modal_w - 28) / 2:
                logger.info("Encerramento de combate cancelado pelo usuário.")
                self.pending_end_combat_modal = False
                return True

            # Clique fora fecha modal
            if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
                self.pending_end_combat_modal = False
                return True

            return True

        # 1. Barra de Ações Rápidas de Combate (5 Botões OOD)
        bar_y = top_y - 20
        btn_w = (panel_w - 40) / 5
        btn_h = 28

        if abs(y - bar_y) <= btn_h / 2:
            # Botão 1: Rolar Iniciativas
            b1_x = 12 + 0 * (btn_w + 4) + btn_w / 2
            if abs(x - b1_x) <= btn_w / 2:
                open_initiative_modal_callback()
                return True

            # Botão 2: Turno Anterior
            b2_x = 12 + 1 * (btn_w + 4) + btn_w / 2
            if abs(x - b2_x) <= btn_w / 2:
                self.combat_manager.previous_turn()
                return True

            # Botão 3: Próximo Turno
            b3_x = 12 + 2 * (btn_w + 4) + btn_w / 2
            if abs(x - b3_x) <= btn_w / 2:
                self.combat_manager.next_turn()
                return True

            # Botão 4: Pausar e Salvar Combate
            b4_x = 12 + 3 * (btn_w + 4) + btn_w / 2
            if abs(x - b4_x) <= btn_w / 2:
                self.trigger_save_combat()
                return True

            # Botão 5: Finalizar Combate
            b5_x = 12 + 4 * (btn_w + 4) + btn_w / 2
            if abs(x - b5_x) <= btn_w / 2:
                if self.combat_manager.has_save_state():
                    self.pending_end_combat_modal = True
                    logger.info("Save detectado ao finalizar combate. Abrindo modal de confirmação.")
                else:
                    self.session_manager.end_combat(DisplayState.IDLE)
                return True

        # 2. Cliques no Painel de Feitiços (SpellAoEPanel)
        info_y = bar_y - 24
        if self.spell_aoe_panel.handle_click(x, y, panel_w, info_y - 12):
            return True

        spell_body_h = 82 if not self.spell_aoe_panel.is_collapsed else 0
        spell_next_y = info_y - 12 - (28 + spell_body_h) - 8

        # 3. Cliques no Painel de Névoa de Guerra (FogControlPanel)
        if self.fog_panel.handle_click(x, y, panel_w, spell_next_y):
            return True

        fog_body_h = 68 if not self.fog_panel.is_collapsed else 0
        fog_next_y = spell_next_y - (26 + fog_body_h) - 8

        # 4. Cliques nas Linhas da Tabela de Combatentes
        table_top = fog_next_y
        table_h = 22
        row_h = 24
        panels_collapsed = (1 if self.spell_aoe_panel.is_collapsed else 0) + (1 if self.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2

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

        # 5. Cliques no Despachante de Dano e Cura
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
        """Atualiza animações e inputs do painel de feitiços, névoa e toast de salvamento."""
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
            if self.toast_timer == 0:
                self.toast_message = None

        self.spell_aoe_panel.on_update(dt)
        self.fog_panel.fog_manager = self.combat_manager.fog_manager
        self.fog_panel.on_update(dt)

