import logging
from typing import Any
import arcade

logger = logging.getLogger(__name__)


class CombatActionsPanel:
    """
    Subpainel especializado na Barra Superior de Ações Rápidas de Combate,
    Informações de Rodada/Turno, Notificação Toast e Modal de Confirmação de Finalização.
    """

    @staticmethod
    def draw_action_bar(tab: Any, panel_w: float, top_y: float) -> float:
        """Desenha os 6 botões rápidos no topo do painel de combate."""
        bar_y = top_y - 20
        btn_w = (panel_w - 44) / 6
        btn_h = 28

        # Botão 1: Rolar Iniciativas
        b1_x = 12 + 0 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b1_x, bar_y, btn_w, btn_h), (142, 68, 173, 255))
        arcade.draw_rect_outline(arcade.XYWH(b1_x, bar_y, btn_w, btn_h), (155, 89, 182, 255), 1)
        tab._get_text("cm_b_init", "🎲 Inic", b1_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 2: Adicionar Token Dinâmico
        b2_x = 12 + 1 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b2_x, bar_y, btn_w, btn_h), (243, 156, 18, 255))
        arcade.draw_rect_outline(arcade.XYWH(b2_x, bar_y, btn_w, btn_h), (241, 196, 15, 255), 1)
        tab._get_text("cm_b_add_tkn", "➕ Token", b2_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 3: Turno Anterior
        b3_x = 12 + 2 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b3_x, bar_y, btn_w, btn_h), (41, 128, 185, 255))
        arcade.draw_rect_outline(arcade.XYWH(b3_x, bar_y, btn_w, btn_h), (52, 152, 219, 255), 1)
        tab._get_text("cm_b_prev", "◀ Turno", b3_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 4: Próximo Turno
        b4_x = 12 + 3 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b4_x, bar_y, btn_w, btn_h), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b4_x, bar_y, btn_w, btn_h), (46, 204, 113, 255), 1)
        tab._get_text("cm_b_next", "▶ Turno", b4_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 5: Pausar e Salvar Combate
        b5_x = 12 + 4 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b5_x, bar_y, btn_w, btn_h), (211, 84, 0, 255))
        arcade.draw_rect_outline(arcade.XYWH(b5_x, bar_y, btn_w, btn_h), (230, 126, 34, 255), 1)
        tab._get_text("cm_b_save", "💾 Salvar", b5_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 6: Finalizar Combate
        b6_x = 12 + 5 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b6_x, bar_y, btn_w, btn_h), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b6_x, bar_y, btn_w, btn_h), (231, 76, 60, 255), 1)
        tab._get_text("cm_b_end", "🏁 Sair", b6_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        return bar_y

    @staticmethod
    def draw_round_info(tab: Any, panel_w: float, bar_y: float) -> float:
        """Desenha a informação de rodada, combatente do turno e o toast de salvamento."""
        info_y = bar_y - 24
        active_char = tab.combat_manager.active_character
        round_num = getattr(tab.combat_manager, "round_number", getattr(tab.combat_manager, "current_round", 1))
        turn_str = f"⚔️ Rodada: {round_num} • Turno Ativo: {active_char.name if active_char else 'Nenhum'}"
        tab._get_text("cm_info_turn", turn_str, 16, info_y, (241, 196, 15, 255), 9, bold=True).draw()

        # Notificação Toast Flutuante de Salvamento
        if tab.toast_timer > 0 and tab.toast_message:
            toast_alpha = min(255, int((tab.toast_timer / 0.4) * 255)) if tab.toast_timer < 0.4 else 255
            toast_bg = (20, 60, 35, min(240, toast_alpha))
            toast_bd = (46, 204, 113, toast_alpha)
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, info_y, panel_w - 30, 22), toast_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, info_y, panel_w - 30, 22), toast_bd, 1.2)
            tab._get_text("cm_toast", f"💾 {tab.toast_message}", panel_w / 2, info_y, (255, 255, 255, toast_alpha), 8.5, bold=True, anchor_x="center").draw()

        return info_y

    @staticmethod
    def draw_end_combat_modal(tab: Any, panel_w: float, top_y: float) -> None:
        """Renderiza o modal de confirmação para finalizar combate e limpar ou manter o save."""
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, top_y / 2, panel_w, top_y), (10, 14, 20, 220))

        modal_w = min(panel_w - 24, 460.0)
        modal_h = 190.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2

        # Caixa do Diálogo Dark Fantasy
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (22, 28, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (192, 57, 43, 255), 2.0)

        # Cabeçalho de Alerta
        tab._get_text("end_mod_hdr", "🏁 FINALIZAR COMBATE TÁTICO", modal_cx, modal_cy + modal_h / 2 - 20, (241, 196, 15, 255), 10, bold=True, anchor_x="center").draw()

        # Mensagem do Modal
        msg_line1 = "Deseja encerrar o combate e limpar o save residual do disco,"
        msg_line2 = "ou manter o arquivo de progresso salvo para consultas futuras?"
        tab._get_text("end_mod_m1", msg_line1, modal_cx, modal_cy + 22, (220, 225, 235, 255), 8.5, bold=False, anchor_x="center").draw()
        tab._get_text("end_mod_m2", msg_line2, modal_cx, modal_cy + 5, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()

        # Botões de Ação
        btn_y = modal_cy - modal_h / 2 + 55
        btn_w = (modal_w - 32) / 2

        # 1. [ 🗑️ Limpar Save & Sair ]
        b_clean_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_clean_x, btn_y, btn_w - 4, 32), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_clean_x, btn_y, btn_w - 4, 32), (231, 76, 60, 255), 2)
        tab._get_text("end_mod_b_clean", "🗑️ Limpar Save & Sair", b_clean_x, btn_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # 2. [ 💾 Manter Save & Sair ]
        b_keep_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_keep_x, btn_y, btn_w - 4, 32), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_keep_x, btn_y, btn_w - 4, 32), (46, 204, 113, 255), 2)
        tab._get_text("end_mod_b_keep", "💾 Manter Save & Sair", b_keep_x, btn_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # 3. [ ❌ Cancelar ]
        btn_can_y = modal_cy - modal_h / 2 + 20
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (70, 90, 120, 200), 1)
        tab._get_text("end_mod_b_can", "❌ Cancelar", modal_cx, btn_can_y, (200, 210, 225, 255), 8, bold=True, anchor_x="center").draw()
