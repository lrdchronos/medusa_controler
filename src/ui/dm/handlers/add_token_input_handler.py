import logging
from typing import Any
import arcade
from ....domain.models.entity import EntityType

logger = logging.getLogger(__name__)


class AddTokenInputHandler:
    """
    Controlador de eventos de entrada (mouse, teclado, validação) para AddTokenModal.
    """

    @staticmethod
    def handle_click(modal: Any, x: float, y: float, screen_w: float, screen_h: float) -> bool:
        """Processa cliques no modal."""
        if not modal.is_open:
            return False

        modal_w = min(screen_w - 40, 520.0)
        modal_h = 490.0
        modal_cx = screen_w / 2
        modal_cy = screen_h / 2

        # 1. Clique no campo de texto
        f1_y = modal_cy + modal_h / 2 - 20 - 16 - 26
        input_w = modal_w - 48
        input_h = 24
        if abs(x - modal_cx) <= input_w / 2 and abs(y - (f1_y - 16)) <= input_h / 2:
            modal.name_input.handle_mouse_press(x, y)
            return True
        else:
            modal.name_input.blur()

        # 2. Seleção de Tipo de Entidade (Jogador, Monstro, Neutro)
        f2_y = f1_y - 44
        btn_type_w = (modal_w - 56) / 3
        btn_type_h = 24
        btn_type_y = f2_y - 16

        if abs(y - btn_type_y) <= btn_type_h / 2:
            # Jogador
            b_p_x = modal_cx - modal_w / 2 + 24 + 0 * (btn_type_w + 4) + btn_type_w / 2
            if abs(x - b_p_x) <= btn_type_w / 2:
                modal.selected_type = EntityType.PLAYER
                return True

            # Monstro
            b_m_x = modal_cx - modal_w / 2 + 24 + 1 * (btn_type_w + 4) + btn_type_w / 2
            if abs(x - b_m_x) <= btn_type_w / 2:
                modal.selected_type = EntityType.MONSTER
                return True

            # Neutro
            b_n_x = modal_cx - modal_w / 2 + 24 + 2 * (btn_type_w + 4) + btn_type_w / 2
            if abs(x - b_n_x) <= btn_type_w / 2:
                modal.selected_type = EntityType.NEUTRAL
                return True

        # 3. Seleção de Porte / Tamanho (Miúdo, Médio, Grande, Enorme, Imenso)
        f_sz_y = btn_type_y - 30
        sz_count = len(modal.SIZE_OPTIONS)
        btn_sz_w = (modal_w - 48 - (sz_count - 1) * 4) / sz_count
        btn_sz_h = 24
        btn_sz_y = f_sz_y - 16

        if abs(y - btn_sz_y) <= btn_sz_h / 2:
            for idx, (sz_code, _, _) in enumerate(modal.SIZE_OPTIONS):
                bx = modal_cx - modal_w / 2 + 24 + idx * (btn_sz_w + 4) + btn_sz_w / 2
                if abs(x - bx) <= btn_sz_w / 2:
                    modal.selected_size = sz_code
                    logger.info(f"Porte selecionado no modal: '{modal.selected_size}'.")
                    return True

        # 4. Steppers de HP e CA
        f3_y = btn_sz_y - 28
        hp_step_y = f3_y - 16
        half_w = (modal_w - 56) / 2
        hp_cx = modal_cx - modal_w / 2 + 24 + half_w / 2
        ca_cx = modal_cx + 4 + half_w / 2

        if abs(y - hp_step_y) <= 12:
            # HP [-]
            if abs(x - (hp_cx - 45)) <= 14:
                modal.hp_value = max(1, modal.hp_value - 1)
                return True
            # HP [+]
            if abs(x - (hp_cx + 45)) <= 14:
                modal.hp_value = min(999, modal.hp_value + 1)
                return True

            # CA [-]
            if abs(x - (ca_cx - 45)) <= 14:
                modal.ac_value = max(0, modal.ac_value - 1)
                return True
            # CA [+]
            if abs(x - (ca_cx + 45)) <= 14:
                modal.ac_value = min(40, modal.ac_value + 1)
                return True

        # 5. Seleção de Slot de Iniciativa ('next' vs 'end')
        f4_y = hp_step_y - 28
        slot_btn_w = (modal_w - 52) / 2
        slot_btn_h = 24
        slot_y = f4_y - 16

        if abs(y - slot_y) <= slot_btn_h / 2:
            # Próximo
            b_nxt_x = modal_cx - modal_w / 2 + 24 + slot_btn_w / 2
            if abs(x - b_nxt_x) <= slot_btn_w / 2:
                modal.initiative_slot = "next"
                return True

            # Final
            b_end_x = modal_cx + 4 + slot_btn_w / 2
            if abs(x - b_end_x) <= slot_btn_w / 2:
                modal.initiative_slot = "end"
                return True

        # 6. Botões de Ação do Rodapé
        btn_foot_y = modal_cy - modal_h / 2 + 26
        btn_action_w = (modal_w - 52) / 2

        # [ ❌ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 24 + btn_action_w / 2
        if abs(y - btn_foot_y) <= 14 and abs(x - b_can_x) <= btn_action_w / 2:
            modal.close()
            return True

        # [ 📍 Posicionar no Mapa ]
        b_pos_x = modal_cx + 4 + btn_action_w / 2
        if abs(y - btn_foot_y) <= 14 and abs(x - b_pos_x) <= btn_action_w / 2:
            modal._handle_confirm()
            return True

        # Clique fora da caixa fecha o modal
        if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
            modal.close()
            return True

        return True

    @staticmethod
    def handle_key_press(modal: Any, symbol: int, modifiers: int = 0) -> bool:
        """Processa teclas no modal."""
        if not modal.is_open:
            return False

        if symbol == arcade.key.ESCAPE:
            modal.close()
            return True

        if symbol == arcade.key.ENTER:
            modal._handle_confirm()
            return True

        return modal.name_input.handle_key_press(symbol, modifiers)
