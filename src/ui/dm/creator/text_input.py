import time
from typing import Optional, Dict, Any, Tuple
import arcade


class TextInputWidget:
    """
    Componente desacoplado e reutilizável de entrada de texto (Text Input Widget) para Arcade.
    Suporta:
      - Clique para focar e posicionar cursor.
      - Digitação direta com inserção no ponto do cursor.
      - Cursor piscante suave (Cursor Blink).
      - Backspace contínuo ao segurar a tecla (Key Repeat / Hold-to-delete).
      - Navegação via setas (Esquerda/Direita), Home e End.
      - Botão rápido de limpar [×].
      - Suporte a textos longos e limites configuráveis.
    """

    def __init__(
        self,
        widget_id: str,
        placeholder: str = "",
        initial_text: str = "",
        max_length: int = 150,
        font_size: int = 9,
    ) -> None:
        self.widget_id = widget_id
        self.placeholder = placeholder
        self.text: str = initial_text
        self.max_length = max_length
        self.font_size = font_size

        self.is_focused: bool = False
        self.cursor_pos: int = len(self.text)
        self.cursor_blink_time: float = 0.0
        self.cursor_visible: bool = True

        # Key Repeat Engine (Backspace contínuo ao segurar)
        self.backspace_held: bool = False
        self.backspace_delay: float = 0.35  # Delay inicial antes do repeat contínuo
        self.backspace_rate: float = 0.035  # Taxa de repetição rápida
        self.backspace_timer: float = 0.0

        # Bounding box cache: (x, y, w, h)
        self.bounds: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

    def set_text(self, new_text: str) -> None:
        self.text = new_text[:self.max_length]
        self.cursor_pos = min(self.cursor_pos, len(self.text))

    def clear(self) -> None:
        self.text = ""
        self.cursor_pos = 0

    def focus(self) -> None:
        self.is_focused = True
        self.cursor_pos = len(self.text)
        self.cursor_blink_time = 0.0
        self.cursor_visible = True

    def blur(self) -> None:
        self.is_focused = False
        self.backspace_held = False

    def update(self, delta_time: float) -> None:
        """Atualização de quadro para animação do cursor e repetição de backspace."""
        if not self.is_focused:
            self.backspace_held = False
            return

        # 1. Cursor blink
        self.cursor_blink_time += delta_time
        if self.cursor_blink_time >= 0.5:
            self.cursor_blink_time = 0.0
            self.cursor_visible = not self.cursor_visible

        # 2. Backspace hold repeat
        if self.backspace_held:
            self.backspace_timer -= delta_time
            while self.backspace_timer <= 0.0:
                self._delete_backspace_char()
                self.backspace_timer += self.backspace_rate

    def _delete_backspace_char(self) -> bool:
        """Apaga o caractere imediatamente anterior ao cursor."""
        if self.cursor_pos > 0 and self.text:
            self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
            self.cursor_pos -= 1
            self.cursor_visible = True
            self.cursor_blink_time = 0.0
            return True
        return False

    def handle_mouse_press(self, x: float, y: float) -> bool:
        """Processa clique do mouse para foco ou limpeza."""
        bx, by, bw, bh = self.bounds
        if abs(x - bx) <= bw / 2 and abs(y - by) <= bh / 2:
            # Checa clique no botão de limpar [×] (canto direito)
            clear_btn_x = bx + bw / 2 - 14
            if abs(x - clear_btn_x) <= 10 and bool(self.text):
                self.clear()
                self.focus()
                return True

            self.focus()
            # Estimativa de posição do cursor com base no clique horizontal
            text_start_x = bx - bw / 2 + 10
            click_offset = max(0.0, x - text_start_x)
            char_w = max(6.0, float(self.font_size) * 0.62)
            estimated_idx = int(round(click_offset / char_w))
            self.cursor_pos = max(0, min(len(self.text), estimated_idx))
            return True

        self.blur()
        return False

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        """Processa atalhos de navegação e acionamento de teclas."""
        if not self.is_focused:
            return False

        if symbol == arcade.key.BACKSPACE:
            self._delete_backspace_char()
            self.backspace_held = True
            self.backspace_timer = self.backspace_delay
            return True

        elif symbol == arcade.key.DELETE:
            if self.cursor_pos < len(self.text):
                self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                self.cursor_visible = True
                return True

        elif symbol == arcade.key.LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
                self.cursor_visible = True
                self.cursor_blink_time = 0.0
            return True

        elif symbol == arcade.key.RIGHT:
            if self.cursor_pos < len(self.text):
                self.cursor_pos += 1
                self.cursor_visible = True
                self.cursor_blink_time = 0.0
            return True

        elif symbol == arcade.key.HOME:
            self.cursor_pos = 0
            self.cursor_visible = True
            return True

        elif symbol == arcade.key.END:
            self.cursor_pos = len(self.text)
            self.cursor_visible = True
            return True

        elif symbol == arcade.key.ESCAPE:
            self.blur()
            return True

        return False

    def handle_key_release(self, symbol: int, modifiers: int) -> None:
        """Interrompe a repetição contínua ao soltar a tecla."""
        if symbol == arcade.key.BACKSPACE:
            self.backspace_held = False

    def handle_text_input(self, text: str) -> bool:
        """Insere o texto digitado na posição exata do cursor."""
        if not self.is_focused or not text:
            return False

        # Ignora caracteres de controle não imprimíveis
        clean = "".join(ch for ch in text if ord(ch) >= 32)
        if not clean:
            return False

        available_space = self.max_length - len(self.text)
        if available_space <= 0:
            return False

        to_insert = clean[:available_space]
        self.text = self.text[:self.cursor_pos] + to_insert + self.text[self.cursor_pos:]
        self.cursor_pos += len(to_insert)
        self.cursor_visible = True
        self.cursor_blink_time = 0.0
        return True

    def draw(
        self,
        cx: float,
        cy: float,
        width: float,
        height: float,
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        """Desenha a caixa de entrada, texto, cursor piscante e botão de limpar."""
        self.bounds = (cx, cy, width, height)

        bg_col = (26, 36, 52, 255) if self.is_focused else (18, 24, 34, 255)
        bd_col = (241, 196, 15, 255) if self.is_focused else (50, 68, 95, 200)

        # Fundo e Borda
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, width, height), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, width, height), bd_col, 2 if self.is_focused else 1)

        # Renderização do Texto
        start_x = cx - width / 2 + 10
        visible_max_chars = max(10, int((width - 36) / (self.font_size * 0.62)))

        if not self.text:
            # Placeholder
            ph_key = f"{self.widget_id}_ph"
            self._render_text(ph_key, self.placeholder, start_x, cy, (115, 130, 150, 255), self.font_size, False, text_cache)
            if self.is_focused and self.cursor_visible:
                arcade.draw_line(start_x, cy - height * 0.3, start_x, cy + height * 0.3, (241, 196, 15, 255), 1.8)
        else:
            # Calcula janela de rolagem do texto caso ultrapasse a largura visível
            if len(self.text) > visible_max_chars:
                offset_start = max(0, self.cursor_pos - visible_max_chars + 3)
                offset_end = offset_start + visible_max_chars
                disp_text = self.text[offset_start:offset_end]
                relative_cursor = self.cursor_pos - offset_start
            else:
                disp_text = self.text
                relative_cursor = self.cursor_pos

            txt_key = f"{self.widget_id}_txt"
            txt_color = (255, 255, 255, 255) if self.is_focused else (230, 235, 245, 255)
            self._render_text(txt_key, disp_text, start_x, cy, txt_color, self.font_size, True, text_cache)

            # Cursor piscante na posição exata
            if self.is_focused and self.cursor_visible:
                char_w = max(6.0, float(self.font_size) * 0.62)
                cursor_x = start_x + (relative_cursor * char_w)
                arcade.draw_line(cursor_x, cy - height * 0.3, cursor_x, cy + height * 0.3, (241, 196, 15, 255), 1.8)

            # Botão de limpar [×]
            if self.is_focused and self.text:
                clear_btn_x = cx + width / 2 - 14
                arcade.draw_circle_filled(clear_btn_x, cy, 8, (45, 58, 78, 200))
                self._render_text(f"{self.widget_id}_clr", "×", clear_btn_x, cy, (200, 210, 225, 255), 10, True, text_cache, anchor_x="center")

    def _render_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool,
        cache: Dict[str, arcade.Text],
        anchor_x: str = "left",
    ) -> None:
        cached = cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y="center",
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        cached.draw()
