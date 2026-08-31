import unittest
import math
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.grid_manager import GridManager


class TestGridManager(unittest.TestCase):
    """Testes unitários para o GridManager e utilitário matricial do Grid Tático."""

    def setUp(self):
        self.map_w = 1000.0
        self.map_h = 800.0
        self.columns = 25
        self.feet_per_square = 5
        self.grid = GridManager(
            map_width=self.map_w,
            map_height=self.map_h,
            columns=self.columns,
            feet_per_square=self.feet_per_square,
        )

    def test_grid_initialization_and_cell_size(self):
        # cell_size = 1000 / 25 = 40.0 px
        expected_cell_size = 1000.0 / 25.0
        self.assertEqual(self.grid.cell_size, expected_cell_size)
        self.assertEqual(self.grid.columns, 25)

        # rows = ceil(800 / 40.0) = 20
        expected_rows = math.ceil(800.0 / expected_cell_size)
        self.assertEqual(self.grid.rows, expected_rows)
        self.assertEqual(self.grid.feet_per_square, 5)

    def test_world_to_grid_conversion(self):
        # (0, 0) -> (0, 0)
        col, row = self.grid.world_to_grid(0.0, 0.0)
        self.assertEqual((col, row), (0, 0))

        # (55, 95) -> (55 // 40, 95 // 40) = (1, 2)
        col, row = self.grid.world_to_grid(55.0, 95.0)
        self.assertEqual((col, row), (1, 2))

        # (120, 240) -> (3, 6)
        col, row = self.grid.world_to_grid(120.0, 240.0)
        self.assertEqual((col, row), (3, 6))

    def test_world_to_grid_clamping(self):
        # Fora dos limites negativos
        col, row = self.grid.world_to_grid(-50.0, -100.0)
        self.assertEqual((col, row), (0, 0))

        # Fora dos limites superiores
        col, row = self.grid.world_to_grid(9999.0, 9999.0)
        self.assertEqual((col, row), (self.grid.columns - 1, self.grid.rows - 1))

    def test_grid_to_world_center(self):
        # Célula (0, 0) -> centro (20.0, 20.0)
        cx, cy = self.grid.grid_to_world_center(0, 0)
        self.assertAlmostEqual(cx, 20.0)
        self.assertAlmostEqual(cy, 20.0)

        # Célula (2, 5) -> centro ((2 + 0.5) * 40, (5 + 0.5) * 40) = (100.0, 220.0)
        cx, cy = self.grid.grid_to_world_center(2, 5)
        self.assertAlmostEqual(cx, 100.0)
        self.assertAlmostEqual(cy, 220.0)

    def test_snap_to_grid_roundtrip(self):
        # Qualquer ponto dentro da célula (2, 5), como (85, 210), deve sofrer snap para (100.0, 220.0)
        snapped_x, snapped_y = self.grid.snap_to_grid(85.0, 210.0)
        self.assertAlmostEqual(snapped_x, 100.0)
        self.assertAlmostEqual(snapped_y, 220.0)

    def test_distance_calculation_in_feet(self):
        # Distância reta de 3 quadrados: 3 * 5 = 15 ft
        dist = self.grid.calculate_distance_feet(0, 0, 3, 0)
        self.assertAlmostEqual(dist, 15.0)

        # Distância diagonal (3, 4) quadrados: 5 quadrados * 5 = 25 ft
        dist_diag = self.grid.calculate_distance_feet(0, 0, 3, 4)
        self.assertAlmostEqual(dist_diag, 25.0)

    def test_is_valid_cell(self):
        self.assertTrue(self.grid.is_valid_cell(0, 0))
        self.assertTrue(self.grid.is_valid_cell(24, 19))
        self.assertFalse(self.grid.is_valid_cell(-1, 0))
        self.assertFalse(self.grid.is_valid_cell(25, 10))
        self.assertFalse(self.grid.is_valid_cell(5, 20))


if __name__ == "__main__":
    unittest.main()
