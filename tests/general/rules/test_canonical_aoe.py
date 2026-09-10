import unittest
import math
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.spell_template import SpellTemplate, AoEShape, SpellShape
from src.domain.models.tile_map import TileMap, TileProperties
from src.domain.rules.aoe_calculator import AoECalculator, calculate_aoe_cells
from src.manager.grid_manager import GridManager


class TestCanonicalAoE(unittest.TestCase):
    """
    Suíte de testes analíticos para as 6 Formas Canônicas de D&D 5E
    (Círculo, Quadrado, Esfera, Cubo, Cone e Linha) do Medusa VTT.
    """

    def setUp(self):
        # Grid: 1000x1000px, 20 colunas -> cell_size = 50px, feet_per_square = 5.0ft (10px/ft)
        self.grid = GridManager(
            map_width=1000.0,
            map_height=1000.0,
            columns=20,
            feet_per_square=5.0,
            offset_x=0.0,
            offset_y=0.0,
        )
        self.ppf = self.grid.pixels_per_foot  # 50 / 5 = 10.0 px/ft

    # --- 1. Teste: Círculo (2D) ---

    def test_circle_aoe_2d(self):
        # Origem no centro da célula (10, 10): x = (10 + 0.5)*50 = 525px, y = 525px
        cx, cy = self.grid.grid_to_world_center(10, 10)
        tpl = SpellTemplate(
            shape=AoEShape.CIRCLE,
            size_feet=10.0,  # Raio de 10ft = 2 quadrados de raio a partir do centro
            origin_world=(cx, cy),
            is_active=True,
        )

        cells = calculate_aoe_cells(tpl, self.grid)
        self.assertIn((10, 10), cells)  # Centro da magia

        # Células ortogonais a 1 quadrado de distância (5ft)
        self.assertIn((10, 11), cells)
        self.assertIn((10, 9), cells)
        self.assertIn((11, 10), cells)
        self.assertIn((9, 10), cells)

        # Células a 2 quadrados ortogonais (10ft)
        self.assertIn((10, 12), cells)
        self.assertIn((10, 8), cells)
        self.assertIn((12, 10), cells)
        self.assertIn((8, 10), cells)

        # Células distantes a 4 quadrados (20ft) NÃO devem ser afetadas
        self.assertNotIn((10, 15), cells)
        self.assertNotIn((15, 10), cells)

    def test_circle_2d_invariance_under_z(self):
        """Formas 2D (Círculo) operam exclusivamente no plano da grade independentemente de altitude Z."""
        cx, cy = self.grid.grid_to_world_center(5, 5)
        tpl_ground = SpellTemplate(
            shape=AoEShape.CIRCLE,
            size_feet=15.0,
            origin_world=(cx, cy),
            origin_z_feet=0.0,
            is_active=True,
        )
        tpl_high = SpellTemplate(
            shape=AoEShape.CIRCLE,
            size_feet=15.0,
            origin_world=(cx, cy),
            origin_z_feet=100.0,  # Altitude Z arbitrária elevada
            is_active=True,
        )

        cells_ground = calculate_aoe_cells(tpl_ground, self.grid)
        cells_high = calculate_aoe_cells(tpl_high, self.grid)

        self.assertEqual(cells_ground, cells_high)
        self.assertGreater(len(cells_ground), 0)

    # --- 2. Teste: Quadrado (2D) ---

    def test_square_aoe_2d_and_rotation(self):
        cx, cy = self.grid.grid_to_world_center(10, 10)
        # Quadrado de lado 10ft (cobre 2x2 células quando centrado em uma interseção)
        tpl = SpellTemplate(
            shape=AoEShape.SQUARE,
            size_feet=10.0,
            origin_world=(cx, cy),
            rotation_degrees=0.0,
            is_active=True,
        )

        cells = calculate_aoe_cells(tpl, self.grid)
        self.assertIn((10, 10), cells)

        # Quadrado 2D é invariante a Z
        tpl_z = tpl.with_origin_z(50.0)
        cells_z = calculate_aoe_cells(tpl_z, self.grid)
        self.assertEqual(cells, cells_z)

    # --- 3. Teste: Esfera (3D) e Interseção com Altitudes ---

    def test_sphere_aoe_3d_ground_and_air(self):
        cx, cy = self.grid.grid_to_world_center(10, 10)
        # 1. Esfera de raio 15ft no solo (Z=0ft)
        tpl_ground = SpellTemplate(
            shape=AoEShape.SPHERE,
            size_feet=15.0,
            origin_world=(cx, cy),
            origin_z_feet=0.0,
            is_active=True,
        )
        cells_ground = calculate_aoe_cells(tpl_ground, self.grid)
        self.assertIn((10, 10), cells_ground)
        self.assertIn((10, 12), cells_ground)

        # 2. Esfera no ar (Z=30ft, raio 15ft): alcance vertical [15ft..45ft]
        # Como o solo está em Z=0ft (coluna da célula 0..5ft), a esfera não toca o chão!
        tpl_air = SpellTemplate(
            shape=AoEShape.SPHERE,
            size_feet=15.0,
            origin_world=(cx, cy),
            origin_z_feet=30.0,
            is_active=True,
        )
        cells_air = calculate_aoe_cells(tpl_air, self.grid)
        self.assertEqual(len(cells_air), 0)

        # 3. Esfera no ar tocando o solo (Z=12ft, raio 15ft): intervalo vertical [-3ft..27ft]
        # Intersecta a coluna do solo [0ft..5ft]!
        tpl_touching = SpellTemplate(
            shape=AoEShape.SPHERE,
            size_feet=15.0,
            origin_world=(cx, cy),
            origin_z_feet=12.0,
            is_active=True,
        )
        cells_touching = calculate_aoe_cells(tpl_touching, self.grid)
        self.assertIn((10, 10), cells_touching)

    def test_sphere_aoe_3d_with_terrain_elevation(self):
        """Esfera a 30ft de altitude intersecta células em platôs elevados do TileMap."""
        cx, cy = self.grid.grid_to_world_center(10, 10)
        # Cria TileMap com um platô elevado na célula (10, 10) com altura 6 quadrados = 30ft
        grid_data = {
            (10, 10): TileProperties(height=6),  # Platô em Z = 6 * 5ft = 30ft..35ft
            (10, 11): TileProperties(height=0),  # Solo em Z = 0ft..5ft
        }
        tile_map = TileMap(width=20, height=20, tileset_name="default", tactical_grid=grid_data)

        # Esfera centrada em Z=30ft com raio 10ft
        tpl = SpellTemplate(
            shape=AoEShape.SPHERE,
            size_feet=10.0,
            origin_world=(cx, cy),
            origin_z_feet=30.0,
            is_active=True,
        )

        cells = calculate_aoe_cells(tpl, self.grid, tilemap_engine=tile_map)

        # A célula (10, 10) no platô (Z=30ft) é atingida
        self.assertIn((10, 10), cells)
        # A célula vizinha no solo (Z=0ft) NÃO é atingida pois está a 30ft de distância vertical
        self.assertNotIn((10, 11), cells)

    # --- 4. Teste: Cubo (3D) ---

    def test_cube_aoe_3d(self):
        cx, cy = self.grid.grid_to_world_center(8, 8)
        tpl = SpellTemplate(
            shape=AoEShape.CUBE,
            size_feet=20.0,
            origin_world=(cx, cy),
            origin_z_feet=0.0,
            rotation_degrees=0.0,
            pitch_degrees=0.0,
            is_active=True,
        )
        cells = calculate_aoe_cells(tpl, self.grid)
        self.assertIn((8, 8), cells)
        self.assertGreater(len(cells), 1)

    # --- 5. Teste: Cone (3D) ---

    def test_cone_aoe_3d_aperture_and_direction(self):
        # Origem na célula (5, 5) apontando horizontalmente para a direita (yaw=0°, pitch=0°)
        cx, cy = self.grid.grid_to_world_center(5, 5)
        tpl = SpellTemplate(
            shape=AoEShape.CONE,
            size_feet=30.0,  # Alcance de 30ft = 6 células
            origin_world=(cx, cy),
            origin_z_feet=0.0,
            rotation_degrees=0.0,
            pitch_degrees=0.0,
            is_active=True,
        )

        cells = calculate_aoe_cells(tpl, self.grid)
        self.assertIn((5, 5), cells)

        # Deve atingir células à frente (+X, col > 5)
        self.assertIn((6, 5), cells)
        self.assertIn((7, 5), cells)
        self.assertIn((8, 5), cells)

        # NÃO deve atingir células atrás (-X, col < 5)
        self.assertNotIn((4, 5), cells)
        self.assertNotIn((3, 5), cells)

    def test_cone_aoe_3d_pitch_aiming_upwards(self):
        """Cone apontado quase verticalmente para cima (pitch=85°) não atinge células distantes no chão."""
        cx, cy = self.grid.grid_to_world_center(5, 5)
        tpl_steep = SpellTemplate(
            shape=AoEShape.CONE,
            size_feet=30.0,
            origin_world=(cx, cy),
            origin_z_feet=0.0,
            rotation_degrees=0.0,
            pitch_degrees=85.0,  # Apontando quase para o céu
            is_active=True,
        )
        cells_steep = calculate_aoe_cells(tpl_steep, self.grid)

        # A célula da origem ainda é atingida
        self.assertIn((5, 5), cells_steep)
        # Célula a 4 quadrados de distância horizontal no chão NÃO é atingida
        self.assertNotIn((9, 5), cells_steep)

    # --- 6. Teste: Linha (3D) ---

    def test_line_aoe_3d_direction_and_width(self):
        # Origem em (5, 5) projetando para a direita (yaw=0°)
        cx, cy = self.grid.grid_to_world_center(5, 5)
        tpl = SpellTemplate(
            shape=AoEShape.LINE,
            size_feet=40.0,  # 8 células
            width_feet=5.0,   # 1 célula
            origin_world=(cx, cy),
            origin_z_feet=0.0,
            rotation_degrees=0.0,
            pitch_degrees=0.0,
            is_active=True,
        )

        cells = calculate_aoe_cells(tpl, self.grid)
        self.assertIn((5, 5), cells)
        self.assertIn((6, 5), cells)
        self.assertIn((7, 5), cells)
        self.assertIn((8, 5), cells)
        self.assertIn((9, 5), cells)

        # Células atrás NÃO são atingidas
        self.assertNotIn((3, 5), cells)
        # Células laterais distantes NÃO são atingidas
        self.assertNotIn((7, 8), cells)


if __name__ == "__main__":
    unittest.main()
