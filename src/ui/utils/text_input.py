import time
from typing import Optional, Dict, Any, Tuple, List, Union
import arcade
import arcade.gui as gui


# Fallback clipboard compartilhado em memória
_INTERNAL_CLIPBOARD: str = ""


def _copy_to_system_clipboard(text: str) -> bool:
    """Copia o texto para a área de transferência do sistema operacional com fallback seguro."""
    global _INTERNAL_CLIPBOARD
    _INTERNAL_CLIPBOARD = text
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return True


def _paste_from_system_clipboard() -> str:
    """Obtém o texto da área de transferência do sistema operacional ou fallback de memória."""
    global _INTERNAL_CLIPBOARD
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        if text is not None:
            return str(text)
    except Exception:
        pass
    return _INTERNAL_CLIPBOARD


class SmartTextInput(gui.UIInputText):
    """
    Componente customizado e inteligente de entrada de texto (Smart Text Input) para Arcade.
    Supera as limitações nativas do arcade.gui.UIInputText ao fornecer:
      - Cursor posicional preciso com ciclo de piscamento (0.5s).
      - Posicionamento de cursor e seleção de texto por clique e arrasto do mouse.
      - Seleção de texto com renderização translúcida Dark Fantasy (azul suave).
      - Navegação avançada (Left, Right, Home, End) com suporte a Shift para seleção.
      - Edição e deleção rápida (Backspace, Delete) com suporte a fatias de seleção.
      - Atalhos de produtividade: Ctrl+A (selecionar tudo), Ctrl+C (copiar), Ctrl+V (colar), Ctrl+X (recortar).
      - Motor de repetição rápida ao segurar Backspace (Hold-to-delete / Key Repeat).
      - Suporte aos paradigmas de UI do Arcade (UIWidget/UIManager) e renderização direta via draw().
      - Inicialização defensiva para execução confiável tanto com janela ativa quanto em testes headless.
    """

    def __init__(
        self,
        widget_id: str = "smart_input",
        placeholder: str = "",
        initial_text: str = "",
        max_length: int = 150,
        font_size: int = 10,
        font_name: Union[str, Tuple[str, ...]] = ("Consolas", "Calibri", "Segoe UI", "Arial"),
        text_color: tuple = (255, 255, 255, 255),
        caret_color: tuple = (241, 196, 15, 255),
        selection_color: tuple = (41, 128, 185, 160),
        bg_color: tuple = (26, 36, 52, 255),
        border_color: tuple = (241, 196, 15, 255),
        border_width: int = 2,
        padding_left: float = 10.0,
        padding_right: float = 10.0,
        x: float = 0.0,
        y: float = 0.0,
        width: float = 200.0,
        height: float = 30.0,
        **kwargs: Any,
    ) -> None:
        self.widget_id: str = widget_id
        self.placeholder: str = placeholder
        self._custom_text: str = initial_text[:max_length]
        self.max_length: int = max_length
        self.font_size: int = font_size
        self.font_name: Union[str, Tuple[str, ...]] = font_name
        self.text_color: tuple = text_color
        self.caret_color: tuple = caret_color
        self.selection_color: tuple = selection_color
        self.bg_color: tuple = bg_color
        self.border_color: tuple = border_color
        self.border_width: int = border_width
        self.padding_left: float = padding_left
        self.padding_right: float = padding_right

        # Estado do Cursor e Seleção
        self.cursor_index: int = len(self._custom_text)
        self.selection_start: Optional[int] = None
        self.selection_end: Optional[int] = None
        self._blink_timer: float = 0.0
        self._cursor_visible: bool = True
        self._is_focused: bool = False
        self._mouse_selecting: bool = False

        # Motor de Key Repeat (Backspace contínuo ao segurar)
        self.backspace_held: bool = False
        self.backspace_delay: float = 0.35
        self.backspace_rate: float = 0.035
        self.backspace_timer: float = 0.0

        # Bounding box cache: (cx, cy, w, h)
        self.bounds: Tuple[float, float, float, float] = (x, y, width, height)

        # Inicialização da classe base UIInputText (se contexto Arcade/OpenGL disponível)
        self._headless: bool = False
        try:
            super().__init__(
                x=x,
                y=y,
                width=width,
                height=height,
                text=self._custom_text,
                font_name=font_name if isinstance(font_name, tuple) else (font_name,),
                font_size=font_size,
                **kwargs,
            )
        except Exception:
            self._headless = True
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    # --- Propriedades e Aliases de Compatibilidade ---

    @property
    def text(self) -> str:
        """Texto atual do campo de entrada."""
        if hasattr(self, "doc") and self.doc is not None and not self._headless:
            return self.doc.text
        return self._custom_text

    @text.setter
    def text(self, value: str) -> None:
        new_val = value[:self.max_length]
        if hasattr(self, "doc") and self.doc is not None and not self._headless:
            self.doc.text = new_val
        self._custom_text = new_val
        self.cursor_index = min(self.cursor_index, len(new_val))
        if self.selection_start is not None and self.selection_start > len(new_val):
            self.selection_start = len(new_val)
        if self.selection_end is not None and self.selection_end > len(new_val):
            self.selection_end = len(new_val)

    @property
    def cursor_pos(self) -> int:
        """Alias para cursor_index (compatibilidade retroativa)."""
        return self.cursor_index

    @cursor_pos.setter
    def cursor_pos(self, value: int) -> None:
        self.cursor_index = max(0, min(len(self.text), value))

    @property
    def is_focused(self) -> bool:
        """Indica se o componente possui o foco ativo."""
        return self._is_focused or getattr(self, "focused", False)

    @is_focused.setter
    def is_focused(self, value: bool) -> None:
        self._is_focused = bool(value)
        if hasattr(self, "_focused"):
            try:
                self._focused = bool(value)
            except Exception:
                pass

    @property
    def cursor_visible(self) -> bool:
        """Visibilidade atual do cursor na fase de blink."""
        return self._cursor_visible

    # --- Controle de Foco e Seleção ---

    def focus(self) -> None:
        """Ativa o foco no campo de texto."""
        self.is_focused = True
        self._cursor_visible = True
        self._blink_timer = 0.0

    def blur(self) -> None:
        """Remove o foco e interrompe estados de seleção/repetição."""
        self.is_focused = False
        self.backspace_held = False
        self._mouse_selecting = False
        self.clear_selection()

    @property
    def has_selection(self) -> bool:
        """Retorna True se houver uma fatia não vazia de texto selecionada."""
        return (
            self.selection_start is not None
            and self.selection_end is not None
            and self.selection_start != self.selection_end
        )

    def get_selection_range(self) -> Tuple[int, int]:
        """Retorna o intervalo ordenado (start, end) da seleção ativa."""
        if not self.has_selection:
            return (self.cursor_index, self.cursor_index)
        assert self.selection_start is not None
        assert self.selection_end is not None
        start = max(0, min(self.selection_start, self.selection_end, len(self.text)))
        end = max(0, min(max(self.selection_start, self.selection_end), len(self.text)))
        return (start, end)

    def get_selected_text(self) -> str:
        """Retorna o trecho de texto atualmente selecionado."""
        if not self.has_selection:
            return ""
        start, end = self.get_selection_range()
        return self.text[start:end]

    def clear_selection(self) -> None:
        """Limpa o intervalo de seleção de texto."""
        self.selection_start = None
        self.selection_end = None

    def select_all(self) -> None:
        """Seleciona todo o texto do campo de entrada."""
        self.selection_start = 0
        self.selection_end = len(self.text)
        self.cursor_index = len(self.text)
        self._cursor_visible = True
        self._blink_timer = 0.0

    def delete_selection(self) -> bool:
        """Remove a fatia de texto selecionada e posiciona o cursor."""
        if not self.has_selection:
            return False
        start, end = self.get_selection_range()
        cur_text = self.text
        self.cursor_index = start
        self.text = cur_text[:start] + cur_text[end:]
        self.cursor_index = start
        self.clear_selection()
        self._cursor_visible = True
        self._blink_timer = 0.0
        return True

    # --- Operações de Área de Transferência ---

    def copy_to_clipboard(self) -> bool:
        """Copia o texto selecionado para a área de transferência."""
        selected = self.get_selected_text()
        if selected:
            return _copy_to_system_clipboard(selected)
        return False

    def cut_to_clipboard(self) -> bool:
        """Recorta o texto selecionado (copia e deleta)."""
        if self.has_selection:
            self.copy_to_clipboard()
            self.delete_selection()
            return True
        return False

    def paste_from_clipboard(self) -> bool:
        """Cola o texto da área de transferência na posição atual do cursor."""
        pasted = _paste_from_system_clipboard()
        if pasted:
            return self.handle_text_input(pasted)
        return False

    # --- Atualização de Quadro (Update / Blink / Key Repeat) ---

    def update(self, delta_time: float) -> None:
        """Atualização de quadro para ciclo de blink do cursor e repetição de teclas."""
        if not self.is_focused:
            self.backspace_held = False
            return

        # 1. Temporizador do cursor piscante (0.5s)
        self._blink_timer += delta_time
        if self._blink_timer >= 0.5:
            self._blink_timer = 0.0
            self._cursor_visible = not self._cursor_visible

        # 2. Motor de repetição rápida ao segurar Backspace
        if self.backspace_held:
            self.backspace_timer -= delta_time
            while self.backspace_timer <= 0.0:
                self._delete_backspace_char()
                self.backspace_timer += self.backspace_rate

    def on_update(self, dt: float) -> None:
        """Hook de atualização compatível com Arcade GUI."""
        self.update(dt)
        if hasattr(super(), "on_update"):
            try:
                super().on_update(dt)
            except Exception:
                pass

    # --- Matemática de Posição de Caracteres e Medição de Fonte ---

    def _get_char_cumulative_widths(self, text: str) -> List[float]:
        """
        Calcula as posições X acumuladas de cada caractere [0.0, w1, w2, ..., wN].
        Utiliza arcade.Text quando há janela gráfica disponível, com fallback métrico preciso para modo headless.
        """
        if not text:
            return [0.0]

        widths: List[float] = [0.0]
        has_window = False
        try:
            if arcade.get_window() is not None:
                has_window = True
        except Exception:
            has_window = False

        if has_window:
            try:
                running_w = 0.0
                for ch in text:
                    t = arcade.Text(
                        text=ch,
                        x=0,
                        y=0,
                        font_size=self.font_size,
                        font_name=self.font_name,
                    )
                    running_w += t.content_width
                    widths.append(running_w)
                return widths
            except Exception:
                pass

        # Fallback métrico proporcional de alta precisão
        base_w = float(self.font_size) * 0.60
        running_w = 0.0
        for ch in text:
            if ch in ("i", "l", "j", "!", "|", ":", ";", ".", "'", "`", ",", " "):
                ch_w = base_w * 0.50
            elif ch in ("w", "m", "W", "M", "@", "%", "&"):
                ch_w = base_w * 1.45
            elif ch.isupper() or ch in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
                ch_w = base_w * 1.15
            else:
                ch_w = base_w
            running_w += ch_w
            widths.append(running_w)
        return widths

    def _index_from_local_x(self, local_x: float) -> int:
        """Determina o índice do cursor mais próximo da coordenada local X."""
        if local_x <= 0 or not self.text:
            return 0

        cum_widths = self._get_char_cumulative_widths(self.text)
        n = len(self.text)

        if local_x >= cum_widths[n]:
            return n

        for i in range(n):
            x_left = cum_widths[i]
            x_right = cum_widths[i + 1]
            mid = (x_left + x_right) / 2.0
            if local_x < mid:
                return i
            elif local_x <= x_right:
                return i + 1

        return n

    # --- Tratamento de Eventos de Mouse ---

    def handle_mouse_press(self, x: float, y: float, button: int = arcade.MOUSE_BUTTON_LEFT, modifiers: int = 0) -> bool:
        """Processa clique do mouse para foco, posicionamento do cursor ou limpeza [×]."""
        bx, by, bw, bh = self.bounds
        is_inside = (abs(x - bx) <= bw / 2 and abs(y - by) <= bh / 2)

        if is_inside:
            # Checa clique no botão de limpar [×] (canto direito)
            clear_btn_x = bx + bw / 2 - 14
            if abs(x - clear_btn_x) <= 10 and bool(self.text):
                self.clear()
                self.focus()
                return True

            self.focus()
            start_x = bx - bw / 2 + self.padding_left
            local_x = x - start_x
            clicked_idx = self._index_from_local_x(local_x)

            self.cursor_index = clicked_idx
            self.selection_start = clicked_idx
            self.selection_end = None
            self._mouse_selecting = True
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        self.blur()
        return False

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = arcade.MOUSE_BUTTON_LEFT, modifiers: int = 0) -> bool:
        """Atualiza a seleção de texto conforme o mouse é arrastado horizontalmente."""
        if not self.is_focused and not self._mouse_selecting:
            return False

        bx, by, bw, bh = self.bounds
        start_x = bx - bw / 2 + self.padding_left
        local_x = x - start_x
        dragged_idx = self._index_from_local_x(local_x)

        if self.selection_start is None:
            self.selection_start = self.cursor_index

        self.selection_end = dragged_idx
        self.cursor_index = dragged_idx
        self._cursor_visible = True
        self._blink_timer = 0.0
        return True

    def handle_mouse_release(self, x: float, y: float, button: int = arcade.MOUSE_BUTTON_LEFT, modifiers: int = 0) -> None:
        """Finaliza a operação de seleção por arraste de mouse."""
        self._mouse_selecting = False
        if self.selection_start is not None and self.selection_end is not None:
            if self.selection_start == self.selection_end:
                self.clear_selection()

    # Aliases de mouse
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> bool:
        return self.handle_mouse_press(x, y, button, modifiers)

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int) -> bool:
        return self.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.handle_mouse_release(x, y, button, modifiers)

    # --- Tratamento de Teclado e Atalhos ---

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Processa atalhos de navegação, modifiers globais (Ctrl+A/C/V/X) e teclas de deleção."""
        if not self.is_focused:
            return False

        is_ctrl = bool(modifiers & (arcade.key.MOD_CTRL | arcade.key.MOD_COMMAND | getattr(arcade.key, "MOD_ACCEL", 0)))
        is_shift = bool(modifiers & arcade.key.MOD_SHIFT)

        # 1. Atalhos Globais com Ctrl / Cmd
        if is_ctrl:
            if symbol == arcade.key.A:
                self.select_all()
                return True
            elif symbol == arcade.key.C:
                self.copy_to_clipboard()
                return True
            elif symbol == arcade.key.V:
                self.paste_from_clipboard()
                return True
            elif symbol == arcade.key.X:
                self.cut_to_clipboard()
                return True

        # 2. Navegação com Setas e Shift
        if symbol == arcade.key.LEFT:
            if is_shift:
                if self.selection_start is None:
                    self.selection_start = self.cursor_index
                self.cursor_index = max(0, self.cursor_index - 1)
                self.selection_end = self.cursor_index
            else:
                if self.has_selection:
                    start, _ = self.get_selection_range()
                    self.cursor_index = start
                    self.clear_selection()
                else:
                    self.cursor_index = max(0, self.cursor_index - 1)
                    self.clear_selection()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        elif symbol == arcade.key.RIGHT:
            if is_shift:
                if self.selection_start is None:
                    self.selection_start = self.cursor_index
                self.cursor_index = min(len(self.text), self.cursor_index + 1)
                self.selection_end = self.cursor_index
            else:
                if self.has_selection:
                    _, end = self.get_selection_range()
                    self.cursor_index = end
                    self.clear_selection()
                else:
                    self.cursor_index = min(len(self.text), self.cursor_index + 1)
                    self.clear_selection()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        elif symbol == arcade.key.HOME:
            if is_shift:
                if self.selection_start is None:
                    self.selection_start = self.cursor_index
                self.cursor_index = 0
                self.selection_end = 0
            else:
                self.cursor_index = 0
                self.clear_selection()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        elif symbol == arcade.key.END:
            if is_shift:
                if self.selection_start is None:
                    self.selection_start = self.cursor_index
                self.cursor_index = len(self.text)
                self.selection_end = len(self.text)
            else:
                self.cursor_index = len(self.text)
                self.clear_selection()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        # 3. Deleção (Backspace e Delete)
        elif symbol == arcade.key.BACKSPACE:
            if self.has_selection:
                self.delete_selection()
            else:
                self._delete_backspace_char()
            self.backspace_held = True
            self.backspace_timer = self.backspace_delay
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        elif symbol == arcade.key.DELETE:
            if self.has_selection:
                self.delete_selection()
            else:
                self._delete_forward_char()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True

        elif symbol == arcade.key.ESCAPE:
            self.blur()
            return True

        return False

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        """Interrompe repetição contínua ao soltar teclas."""
        if symbol == arcade.key.BACKSPACE:
            self.backspace_held = False

    def handle_text_input(self, text: str) -> bool:
        """Insere o texto digitado na posição exata do cursor ou substituindo a seleção."""
        if not self.is_focused or not text:
            return False

        # Ignora caracteres não imprimíveis de controle (ex: \x01, \x03, \x16)
        clean = "".join(ch for ch in text if ord(ch) >= 32 or ch == "\t")
        if not clean:
            return False

        if self.has_selection:
            start, end = self.get_selection_range()
            remaining_len = len(self.text) - (end - start)
            available = max(0, self.max_length - remaining_len)
            to_insert = clean[:available]
            if not to_insert and available <= 0:
                return False
            cur_text = self.text
            new_idx = start + len(to_insert)
            self.cursor_index = new_idx
            self.text = cur_text[:start] + to_insert + cur_text[end:]
            self.cursor_index = new_idx
            self.clear_selection()
        else:
            available = max(0, self.max_length - len(self.text))
            if available <= 0:
                return False
            to_insert = clean[:available]
            cur_text = self.text
            cur_idx = self.cursor_index
            new_idx = cur_idx + len(to_insert)
            self.cursor_index = new_idx
            self.text = cur_text[:cur_idx] + to_insert + cur_text[cur_idx:]
            self.cursor_index = new_idx

        self._cursor_visible = True
        self._blink_timer = 0.0
        return True

    # Aliases de teclado
    def on_key_press(self, symbol: int, modifiers: int) -> bool:
        return self.handle_key_press(symbol, modifiers)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        self.handle_key_release(symbol, modifiers)

    def on_text(self, text: str) -> bool:
        return self.handle_text_input(text)

    def on_text_input(self, text: str) -> bool:
        return self.handle_text_input(text)

    def set_text(self, new_text: str) -> None:
        """Define o texto do campo respeitando o comprimento máximo."""
        self.text = new_text

    def clear(self) -> None:
        """Limpa o campo de texto por completo."""
        self.cursor_index = 0
        self.text = ""
        self.cursor_index = 0
        self.clear_selection()

    # --- Ações de Deleção Interna ---

    def _delete_backspace_char(self) -> bool:
        """Remove o caractere imediatamente anterior ao cursor."""
        if self.cursor_index > 0 and self.text:
            cur_text = self.text
            new_idx = self.cursor_index - 1
            self.cursor_index = new_idx
            self.text = cur_text[:new_idx] + cur_text[new_idx + 1:]
            self.cursor_index = new_idx
            self.clear_selection()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True
        return False

    def _delete_forward_char(self) -> bool:
        """Remove o caractere imediatamente posterior ao cursor."""
        if self.cursor_index < len(self.text):
            cur_text = self.text
            idx = self.cursor_index
            self.text = cur_text[:idx] + cur_text[idx + 1:]
            self.cursor_index = idx
            self.clear_selection()
            self._cursor_visible = True
            self._blink_timer = 0.0
            return True
        return False


    # --- Renderização Visual Customizada (Estilo Dark Fantasy / High-Contrast) ---

    def draw(
        self,
        cx: Optional[float] = None,
        cy: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        text_cache: Optional[Dict[str, arcade.Text]] = None,
    ) -> None:
        """
        Desenha o widget completo:
          - Fundo e Borda Dark Fantasy / Ouro
          - Fundo da Seleção Translúcida
          - Texto / Placeholder
          - Cursor piscante vertical (1.5px)
          - Botão de limpar [×]
        """
        # Se coordenadas não fornecidas, utiliza bounds armazenados
        if cx is None or cy is None or width is None or height is None:
            cx, cy, width, height = self.bounds
        else:
            self.bounds = (cx, cy, width, height)

        cache = text_cache if text_cache is not None else {}

        # Cores de Fundo e Borda
        bg_col = (26, 36, 52, 255) if self.is_focused else (18, 24, 34, 255)
        bd_col = (241, 196, 15, 255) if self.is_focused else (50, 68, 95, 200)
        bd_thick = 2 if self.is_focused else 1

        # 1. Fundo e Borda
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, width, height), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, width, height), bd_col, bd_thick)

        start_x = cx - width / 2 + self.padding_left
        cum_widths = self._get_char_cumulative_widths(self.text)

        # 2. Fundo da Seleção de Texto (Translúcido Dark Fantasy)
        if self.is_focused and self.has_selection:
            start_sel, end_sel = self.get_selection_range()
            if start_sel < len(cum_widths) and end_sel < len(cum_widths):
                x_start = start_x + cum_widths[start_sel]
                x_end = start_x + cum_widths[end_sel]
                sel_w = max(2.0, x_end - x_start)
                sel_cx = x_start + sel_w / 2.0
                sel_h = max(10.0, height - 6.0)
                arcade.draw_rect_filled(
                    arcade.XYWH(sel_cx, cy, sel_w, sel_h),
                    self.selection_color,
                )

        # 3. Renderização do Texto ou Placeholder
        if not self.text:
            ph_key = f"{self.widget_id}_ph"
            self._render_cached_text(
                ph_key,
                self.placeholder,
                start_x,
                cy,
                (115, 130, 150, 255),
                self.font_size,
                False,
                cache,
            )
            # Cursor inicial se focado
            if self.is_focused and self._cursor_visible:
                arcade.draw_line(
                    start_x,
                    cy - height * 0.30,
                    start_x,
                    cy + height * 0.30,
                    (241, 196, 15, 255),
                    1.8,
                )
        else:
            txt_key = f"{self.widget_id}_txt"
            txt_color = (255, 255, 255, 255) if self.is_focused else (230, 235, 245, 255)
            self._render_cached_text(
                txt_key,
                self.text,
                start_x,
                cy,
                txt_color,
                self.font_size,
                True,
                cache,
            )

            # 4. Cursor (Caret) piscante na coordenada calculada do cursor_index
            if self.is_focused and self._cursor_visible:
                cur_x = start_x + (cum_widths[self.cursor_index] if self.cursor_index < len(cum_widths) else cum_widths[-1])
                arcade.draw_line(
                    cur_x,
                    cy - height * 0.30,
                    cur_x,
                    cy + height * 0.30,
                    (241, 196, 15, 255),
                    1.8,
                )

            # 5. Botão Limpar [×]
            if self.is_focused and self.text:
                clear_btn_x = cx + width / 2 - 14
                arcade.draw_circle_filled(clear_btn_x, cy, 8, (45, 58, 78, 200))
                self._render_cached_text(
                    f"{self.widget_id}_clr",
                    "×",
                    clear_btn_x,
                    cy,
                    (200, 210, 225, 255),
                    10,
                    True,
                    cache,
                    anchor_x="center",
                )

    def _render_cached_text(
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
        """Renderiza texto utilizando cache do arcade.Text para alta performance."""
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
                font_name=self.font_name,
            )
            cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        cached.draw()
