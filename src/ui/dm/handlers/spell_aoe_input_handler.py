import logging
from typing import Any
from ....domain.models.spell_template import AoEShape

logger = logging.getLogger(__name__)


class SpellAoEInputHandler:
    """
    Tratador de eventos de entrada (mouse e teclado) para o Painel de Magias / AoE.
    """

    @staticmethod
    def handle_click(panel: Any, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """Trata cliques nos controles do painel de feitiços."""
        header_h = 28
        body_h = 96 if not panel.is_collapsed else 0
        total_h = header_h + body_h

        # 1. Clique no Cabeçalho (Colapsar / Expandir)
        head_y = top_y - header_h / 2
        if abs(y - head_y) <= header_h / 2 and 12 <= x <= panel_w - 12:
            if abs(x - (panel_w - 32)) <= 20 or x >= panel_w - 60:
                panel.is_collapsed = not panel.is_collapsed
                return True

        if panel.is_collapsed:
            return False

        # 2. Linha 1: Formatos e Botão Ativar
        row1_y = top_y - header_h - 18
        shapes = [
            AoEShape.CIRCLE,
            AoEShape.SQUARE,
            AoEShape.SPHERE,
            AoEShape.CUBE,
            AoEShape.CONE,
            AoEShape.LINE,
        ]

        act_btn_w = 100
        btn_margin = 4
        avail_shapes_w = panel_w - 36 - act_btn_w - 12
        btn_w = (avail_shapes_w - (len(shapes) - 1) * btn_margin) / len(shapes)
        btn_h = 22

        if abs(y - row1_y) <= btn_h / 2:
            # 6 Botões de Formatos
            for i, shape_enum in enumerate(shapes):
                bx = 18 + i * (btn_w + btn_margin) + btn_w / 2
                if abs(x - bx) <= btn_w / 2:
                    panel.current_shape = shape_enum
                    panel.sync_to_combat_manager()
                    return True

            # Botão Ativar / Desativar
            act_btn_x = panel_w - 18 - act_btn_w / 2
            if abs(x - act_btn_x) <= act_btn_w / 2:
                panel.is_active = not panel.is_active
                panel.sync_to_combat_manager()
                return True

        # 3. Linha 2: Inputs de Texto
        row2_y = top_y - header_h - 48
        if abs(y - row2_y) <= 16:
            if panel.size_input.handle_mouse_press(x, y):
                panel.width_input.blur()
                panel.z_input.blur()
                panel.pitch_input.blur()
                return True

            if panel.current_shape == AoEShape.LINE and panel.width_input.handle_mouse_press(x, y):
                panel.size_input.blur()
                panel.z_input.blur()
                panel.pitch_input.blur()
                return True

            if panel.z_input.handle_mouse_press(x, y):
                panel.size_input.blur()
                panel.width_input.blur()
                panel.pitch_input.blur()
                return True

            if panel.pitch_input.handle_mouse_press(x, y):
                panel.size_input.blur()
                panel.width_input.blur()
                panel.z_input.blur()
                return True

        # Clique fora dos inputs mas dentro do painel
        if abs(y - (top_y - total_h / 2)) <= total_h / 2 and 12 <= x <= panel_w - 12:
            panel.size_input.blur()
            panel.width_input.blur()
            panel.z_input.blur()
            panel.pitch_input.blur()
            return True

        return False

    @staticmethod
    def handle_mouse_drag(panel: Any, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        """Repassa arrasto do mouse para os SmartTextInputs."""
        for inp in (panel.size_input, panel.width_input, panel.z_input, panel.pitch_input):
            if inp.is_focused:
                return inp.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)
        return False

    @staticmethod
    def handle_mouse_release(panel: Any, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        panel.size_input.handle_mouse_release(x, y, button, modifiers)
        panel.width_input.handle_mouse_release(x, y, button, modifiers)
        panel.z_input.handle_mouse_release(x, y, button, modifiers)
        panel.pitch_input.handle_mouse_release(x, y, button, modifiers)

    @staticmethod
    def handle_key_press(panel: Any, symbol: int, modifiers: int = 0) -> bool:
        """Processa digitação e navegação nos SmartTextInputs."""
        for inp in (panel.size_input, panel.width_input, panel.z_input, panel.pitch_input):
            if inp.is_focused:
                handled = inp.handle_key_press(symbol, modifiers)
                if handled:
                    panel.sync_to_combat_manager()
                return handled
        return False

    @staticmethod
    def handle_key_release(panel: Any, symbol: int, modifiers: int = 0) -> None:
        panel.size_input.handle_key_release(symbol, modifiers)
        panel.width_input.handle_key_release(symbol, modifiers)
        panel.z_input.handle_key_release(symbol, modifiers)
        panel.pitch_input.handle_key_release(symbol, modifiers)

    @staticmethod
    def handle_text_input(panel: Any, text: str) -> bool:
        """Processa inserção de caracteres nos SmartTextInputs."""
        for inp in (panel.size_input, panel.width_input, panel.z_input, panel.pitch_input):
            if inp.is_focused:
                clean = "".join(c for c in text if c.isdigit() or c in (".", "-"))
                if clean and inp.handle_text_input(clean):
                    panel.sync_to_combat_manager()
                    return True
        return False

    @staticmethod
    def on_update(panel: Any, dt: float) -> None:
        """Atualização de ciclo de blink e key-repeat nos inputs."""
        panel.size_input.update(dt)
        panel.width_input.update(dt)
        panel.z_input.update(dt)
        panel.pitch_input.update(dt)
