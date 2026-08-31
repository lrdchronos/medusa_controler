import unittest
import sys
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.utils.text_input import SmartTextInput


class TestSmartTextInput(unittest.TestCase):
    """Testes unitários rigorosos para o componente SmartTextInput."""

    def setUp(self):
        self.widget = SmartTextInput(
            widget_id="test_widget",
            placeholder="Digite algo...",
            initial_text="Hello World",
            max_length=50,
            font_size=10,
            x=100,
            y=100,
            width=200,
            height=30,
        )
        self.widget.focus()

    def test_initial_state(self):
        self.assertEqual(self.widget.text, "Hello World")
        self.assertEqual(self.widget.cursor_index, 11)
        self.assertEqual(self.widget.cursor_pos, 11)
        self.assertTrue(self.widget.is_focused)
        self.assertFalse(self.widget.has_selection)
        self.assertIsNone(self.widget.selection_start)
        self.assertIsNone(self.widget.selection_end)
        self.assertTrue(self.widget.cursor_visible)

    def test_insert_text_at_cursor_and_middle(self):
        # Inserção no final
        self.widget.handle_text_input("!")
        self.assertEqual(self.widget.text, "Hello World!")
        self.assertEqual(self.widget.cursor_index, 12)

        # Move cursor 6 posições para a esquerda (após 'Hello ')
        for _ in range(6):
            self.widget.handle_key_press(arcade.key.LEFT, 0)
        self.assertEqual(self.widget.cursor_index, 6)

        # Inserção no meio
        self.widget.handle_text_input("Brave ")
        self.assertEqual(self.widget.text, "Hello Brave World!")
        self.assertEqual(self.widget.cursor_index, 12)

    def test_arrow_navigation_and_boundaries(self):
        # Move para o início
        self.widget.handle_key_press(arcade.key.HOME, 0)
        self.assertEqual(self.widget.cursor_index, 0)

        # Não deve ultrapassar o limite esquerdo
        self.widget.handle_key_press(arcade.key.LEFT, 0)
        self.assertEqual(self.widget.cursor_index, 0)

        # Move para a direita
        self.widget.handle_key_press(arcade.key.RIGHT, 0)
        self.assertEqual(self.widget.cursor_index, 1)

        # Move para o final
        self.widget.handle_key_press(arcade.key.END, 0)
        self.assertEqual(self.widget.cursor_index, len("Hello World"))

        # Não deve ultrapassar o limite direito
        self.widget.handle_key_press(arcade.key.RIGHT, 0)
        self.assertEqual(self.widget.cursor_index, len("Hello World"))

    def test_shift_selection_navigation(self):
        # Posiciona no início
        self.widget.handle_key_press(arcade.key.HOME, 0)
        self.assertEqual(self.widget.cursor_index, 0)

        # Shift + Right 5 vezes para selecionar "Hello"
        for _ in range(5):
            self.widget.handle_key_press(arcade.key.RIGHT, arcade.key.MOD_SHIFT)

        self.assertTrue(self.widget.has_selection)
        self.assertEqual(self.widget.selection_start, 0)
        self.assertEqual(self.widget.selection_end, 5)
        self.assertEqual(self.widget.cursor_index, 5)
        self.assertEqual(self.widget.get_selected_text(), "Hello")

        # Shift + End seleciona até o final ("Hello World")
        self.widget.handle_key_press(arcade.key.END, arcade.key.MOD_SHIFT)
        self.assertEqual(self.widget.get_selected_text(), "Hello World")

        # Pressionar Left sem Shift limpa a seleção e posiciona no início do range
        self.widget.handle_key_press(arcade.key.LEFT, 0)
        self.assertFalse(self.widget.has_selection)
        self.assertEqual(self.widget.cursor_index, 0)

    def test_ctrl_a_select_all(self):
        self.widget.handle_key_press(arcade.key.A, arcade.key.MOD_CTRL)
        self.assertTrue(self.widget.has_selection)
        self.assertEqual(self.widget.selection_start, 0)
        self.assertEqual(self.widget.selection_end, len("Hello World"))
        self.assertEqual(self.widget.cursor_index, len("Hello World"))
        self.assertEqual(self.widget.get_selected_text(), "Hello World")

    def test_backspace_without_selection(self):
        # Cursor no final de "Hello World"
        self.assertEqual(self.widget.cursor_index, 11)
        self.widget.handle_key_press(arcade.key.BACKSPACE, 0)
        self.assertEqual(self.widget.text, "Hello Worl")
        self.assertEqual(self.widget.cursor_index, 10)

        # Move para o início
        self.widget.handle_key_press(arcade.key.HOME, 0)
        # Backspace no início não faz nada e não dá erro
        self.widget.handle_key_press(arcade.key.BACKSPACE, 0)
        self.assertEqual(self.widget.text, "Hello Worl")
        self.assertEqual(self.widget.cursor_index, 0)

    def test_backspace_with_selection(self):
        # Seleciona " World" (índices 5 a 11)
        self.widget.selection_start = 5
        self.widget.selection_end = 11
        self.widget.cursor_index = 11

        self.widget.handle_key_press(arcade.key.BACKSPACE, 0)
        self.assertEqual(self.widget.text, "Hello")
        self.assertEqual(self.widget.cursor_index, 5)
        self.assertFalse(self.widget.has_selection)

    def test_delete_with_and_without_selection(self):
        # Delete sem seleção no início
        self.widget.handle_key_press(arcade.key.HOME, 0)
        self.widget.handle_key_press(arcade.key.DELETE, 0)
        self.assertEqual(self.widget.text, "ello World")
        self.assertEqual(self.widget.cursor_index, 0)

        # Delete com seleção
        self.widget.selection_start = 0
        self.widget.selection_end = 4  # "ello"
        self.widget.handle_key_press(arcade.key.DELETE, 0)
        self.assertEqual(self.widget.text, " World")
        self.assertEqual(self.widget.cursor_index, 0)
        self.assertFalse(self.widget.has_selection)

    def test_typing_replaces_active_selection(self):
        # Seleciona "World"
        self.widget.selection_start = 6
        self.widget.selection_end = 11
        self.widget.cursor_index = 11

        # Digita "Medusa"
        self.widget.handle_text_input("Medusa")
        self.assertEqual(self.widget.text, "Hello Medusa")
        self.assertEqual(self.widget.cursor_index, 12)
        self.assertFalse(self.widget.has_selection)

    def test_clipboard_operations(self):
        # Seleciona "Hello"
        self.widget.selection_start = 0
        self.widget.selection_end = 5
        self.widget.cursor_index = 5

        # Ctrl+C
        self.widget.handle_key_press(arcade.key.C, arcade.key.MOD_CTRL)

        # Move para o final
        self.widget.handle_key_press(arcade.key.END, 0)
        self.widget.handle_text_input(" ")

        # Ctrl+V
        self.widget.handle_key_press(arcade.key.V, arcade.key.MOD_CTRL)
        self.assertEqual(self.widget.text, "Hello World Hello")

        # Ctrl+X na palavra final "Hello"
        self.widget.selection_start = 12
        self.widget.selection_end = 17
        self.widget.cursor_index = 17
        self.widget.handle_key_press(arcade.key.X, arcade.key.MOD_CTRL)
        self.assertEqual(self.widget.text, "Hello World ")

        # Cola de volta o recortado
        self.widget.handle_key_press(arcade.key.V, arcade.key.MOD_CTRL)
        self.assertEqual(self.widget.text, "Hello World Hello")

    def test_mouse_click_and_drag_selection(self):
        # Bounds do widget: x=100, y=100, width=200, height=30
        # start_x = 100 - 100 + 10 = 10
        # Clique no início (x=10, y=100)
        self.widget.handle_mouse_press(10, 100)
        self.assertEqual(self.widget.cursor_index, 0)
        self.assertFalse(self.widget.has_selection)

        # Arraste para a direita (x=150, y=100)
        self.widget.handle_mouse_drag(150, 100)
        self.assertTrue(self.widget.has_selection)
        self.assertEqual(self.widget.selection_start, 0)
        self.assertGreater(self.widget.selection_end, 0)

        # Release
        self.widget.handle_mouse_release(150, 100)
        self.assertTrue(self.widget.has_selection)

    def test_cursor_blink_cycle(self):
        self.assertTrue(self.widget.cursor_visible)
        # Avança 0.5s no timer
        self.widget.update(0.50)
        self.assertFalse(self.widget.cursor_visible)
        # Avança mais 0.5s
        self.widget.update(0.50)
        self.assertTrue(self.widget.cursor_visible)

    def test_backspace_hold_repeat(self):
        self.widget.handle_key_press(arcade.key.BACKSPACE, 0)
        self.assertTrue(self.widget.backspace_held)
        # Atualiza tempo superior ao delay inicial (0.35s)
        initial_len = len(self.widget.text)
        self.widget.update(0.45)
        self.assertLess(len(self.widget.text), initial_len)

        self.widget.handle_key_release(arcade.key.BACKSPACE, 0)
        self.assertFalse(self.widget.backspace_held)

    def test_max_length_enforcement(self):
        short_widget = SmartTextInput("short", initial_text="12345", max_length=5)
        short_widget.focus()
        # Não deve permitir inserir além do limite
        result = short_widget.handle_text_input("678")
        self.assertFalse(result)
        self.assertEqual(short_widget.text, "12345")


if __name__ == "__main__":
    unittest.main()
