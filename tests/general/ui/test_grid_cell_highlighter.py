import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.grid_manager import GridManager
from src.ui.components.grid_cell_highlighter import GridCellHighlighter


class TestGridCellHighlighter(unittest.TestCase):
    """Suíte de testes unitários para o componente reutilizável GridCellHighlighter."""

    def setUp(self):
        self.grid = GridManager(map_width=1000.0, map_height=800.0, columns=25, feet_per_square=5.0)
        self.highlighter = GridCellHighlighter(grid_manager=self.grid)

    def test_initial_state_empty(self):
        self.assertEqual(len(self.highlighter), 0)
        self.assertEqual(self.highlighter.cell_count, 0)
        self.assertEqual(self.highlighter.highlighted_cells, {})
        self.assertFalse(self.highlighter.is_highlighted(0, 0))
        self.assertIsNone(self.highlighter.get_color(0, 0))

    def test_add_and_remove_cell(self):
        color = GridCellHighlighter.COLOR_SPELL_AOE
        self.highlighter.add_cell(2, 3, color)

        self.assertEqual(len(self.highlighter), 1)
        self.assertTrue(self.highlighter.is_highlighted(2, 3))
        self.assertFalse(self.highlighter.is_highlighted(2, 4))
        self.assertEqual(self.highlighter.get_color(2, 3), color)

        # Adiciona segunda célula com cor de alcance de movimento
        color_move = GridCellHighlighter.COLOR_MOVEMENT_RANGE
        self.highlighter.add_cell(5, 5, color_move)
        self.assertEqual(len(self.highlighter), 2)
        self.assertEqual(self.highlighter.get_color(5, 5), color_move)

        # Remove célula existente
        removed = self.highlighter.remove_cell(2, 3)
        self.assertTrue(removed)
        self.assertEqual(len(self.highlighter), 1)
        self.assertFalse(self.highlighter.is_highlighted(2, 3))

        # Remove célula inexistente
        removed_non = self.highlighter.remove_cell(99, 99)
        self.assertFalse(removed_non)

    def test_set_cells_with_set_and_list(self):
        cells_set = {(1, 1), (1, 2), (2, 1), (2, 2)}
        color = (100, 150, 200, 120)
        self.highlighter.set_cells(cells_set, color=color)

        self.assertEqual(len(self.highlighter), 4)
        for c, r in cells_set:
            self.assertTrue(self.highlighter.is_highlighted(c, r))
            self.assertEqual(self.highlighter.get_color(c, r), color)

        # Substitui por lista
        cells_list = [(0, 0), (5, 5)]
        self.highlighter.set_cells(cells_list)
        self.assertEqual(len(self.highlighter), 2)
        self.assertTrue(self.highlighter.is_highlighted(0, 0))
        self.assertTrue(self.highlighter.is_highlighted(5, 5))
        self.assertFalse(self.highlighter.is_highlighted(1, 1))

    def test_set_cells_with_dict(self):
        cells_dict = {
            (0, 0): (255, 0, 0, 100),
            (1, 1): (0, 255, 0, 100),
            (2, 2): (0, 0, 255, 100),
        }
        self.highlighter.set_cells(cells_dict)
        self.assertEqual(len(self.highlighter), 3)
        self.assertEqual(self.highlighter.get_color(0, 0), (255, 0, 0, 100))
        self.assertEqual(self.highlighter.get_color(1, 1), (0, 255, 0, 100))
        self.assertEqual(self.highlighter.get_color(2, 2), (0, 0, 255, 100))

    def test_clear_cells(self):
        self.highlighter.set_cells([(1, 1), (2, 2), (3, 3)])
        self.assertEqual(len(self.highlighter), 3)

        self.highlighter.clear()
        self.assertEqual(len(self.highlighter), 0)
        self.assertEqual(self.highlighter.highlighted_cells, {})

    def test_defensive_copies(self):
        """Garante que highlighted_cells retorna uma cópia defensiva imutável externamente."""
        self.highlighter.add_cell(1, 1)
        cells = self.highlighter.highlighted_cells
        cells[(9, 9)] = (0, 0, 0, 0)

        self.assertFalse(self.highlighter.is_highlighted(9, 9))
        self.assertEqual(len(self.highlighter), 1)

    def test_safe_headless_draw(self):
        """Garante que a chamada a draw() não lance exceção mesmo em ambiente sem janela ativa."""
        self.highlighter.set_cells([(0, 0), (1, 1)])
        # Não deve lançar erro
        try:
            self.highlighter.draw(draw_x=0.0, draw_y=0.0, scale=1.0)
        except Exception as e:
            self.fail(f"draw() lançou exceção inesperada em modo headless: {e}")


if __name__ == "__main__":
    unittest.main()
