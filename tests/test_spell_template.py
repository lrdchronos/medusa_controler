import unittest
import math
import sys
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.spell_template import SpellTemplate, SpellShape
from src.manager.grid_manager import GridManager
from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager
from src.ui.dm.spell_aoe_panel import SpellAoEPanel
from src.ui.utils.aoe_renderer import AoERenderer


class TestSpellTemplate(unittest.TestCase):
    """Testes unitários para o modelo de domínio SpellTemplate e cálculos geométricos desacoplados."""

    def test_default_initialization_and_immutability(self):
        tpl = SpellTemplate()
        self.assertEqual(tpl.shape, SpellShape.CIRCLE)
        self.assertEqual(tpl.size_feet, 20.0)
        self.assertEqual(tpl.width_feet, 5.0)
        self.assertEqual(tpl.rotation_degrees, 0.0)
        self.assertEqual(tpl.origin_world, (0.0, 0.0))
        self.assertFalse(tpl.is_active)
        self.assertTrue(tpl.is_visible)

        # Imutabilidade funcional via métodos with_*
        tpl2 = tpl.with_origin((100.0, 200.0))
        self.assertEqual(tpl.origin_world, (0.0, 0.0))
        self.assertEqual(tpl2.origin_world, (100.0, 200.0))

        tpl3 = tpl.with_rotation(45.0)
        self.assertEqual(tpl.rotation_degrees, 0.0)
        self.assertEqual(tpl3.rotation_degrees, 45.0)

        tpl4 = tpl.with_shape(SpellShape.CONE)
        self.assertEqual(tpl.shape, SpellShape.CIRCLE)
        self.assertEqual(tpl4.shape, SpellShape.CONE)

        tpl5 = tpl.with_active(True)
        self.assertFalse(tpl.is_active)
        self.assertTrue(tpl5.is_active)

    def test_string_shape_parsing(self):
        tpl1 = SpellTemplate(shape="cone")
        self.assertEqual(tpl1.shape, SpellShape.CONE)

        tpl2 = SpellTemplate(shape="SQUARE")
        self.assertEqual(tpl2.shape, SpellShape.SQUARE)

        tpl3 = SpellTemplate(shape="line")
        self.assertEqual(tpl3.shape, SpellShape.LINE)

    def test_rotation_wrap_around_30_degrees(self):
        """Verifica a rotação com wrap-around cíclico de 30° em 30°."""
        tpl = SpellTemplate(rotation_degrees=0.0)

        # Passo positivo: 0 -> 30 -> 60 -> ... -> 360 (0)
        for expected in range(30, 360, 30):
            tpl = tpl.with_rotation(tpl.rotation_degrees + 30.0)
            self.assertAlmostEqual(tpl.rotation_degrees, float(expected))

        # Wrap-around de 330 + 30 -> 0
        tpl = tpl.with_rotation(tpl.rotation_degrees + 30.0)
        self.assertAlmostEqual(tpl.rotation_degrees, 0.0)

        # Passo negativo: 0 - 30 -> 330
        tpl_neg = tpl.with_rotation(tpl.rotation_degrees - 30.0)
        self.assertAlmostEqual(tpl_neg.rotation_degrees, 330.0)

        tpl_neg2 = tpl_neg.with_rotation(tpl_neg.rotation_degrees - 30.0)
        self.assertAlmostEqual(tpl_neg2.rotation_degrees, 300.0)

    def test_dynamic_physical_scale_conversion(self):
        """Verifica conversão de pés para pixels com grids de diferentes pés por quadrado (5ft, 10ft, 15ft, 1.5ft)."""
        # Mapa padrão: 1000px, 25 colunas -> cell_size = 40px
        # 1. feet_per_square = 5.0 -> pixels_per_foot = 40 / 5 = 8.0 px/ft
        grid_5ft = GridManager(map_width=1000.0, map_height=800.0, columns=25, feet_per_square=5.0)
        self.assertAlmostEqual(grid_5ft.cell_size, 40.0)
        self.assertAlmostEqual(grid_5ft.feet_per_square, 5.0)
        self.assertAlmostEqual(grid_5ft.pixels_per_foot, 8.0)

        # 2. feet_per_square = 10.0 (mapa em escala regional) -> pixels_per_foot = 40 / 10 = 4.0 px/ft
        grid_10ft = GridManager(map_width=1000.0, map_height=800.0, columns=25, feet_per_square=10.0)
        self.assertAlmostEqual(grid_10ft.pixels_per_foot, 4.0)

        # 3. feet_per_square = 15.0 -> pixels_per_foot = 40 / 15 = 2.6666... px/ft
        grid_15ft = GridManager(map_width=1000.0, map_height=800.0, columns=25, feet_per_square=15.0)
        self.assertAlmostEqual(grid_15ft.pixels_per_foot, 40.0 / 15.0)

        # 4. feet_per_square = 1.5 (escala tática de alta precisão) -> pixels_per_foot = 40 / 1.5 = 26.666... px/ft
        grid_1_5ft = GridManager(map_width=1000.0, map_height=800.0, columns=25, feet_per_square=1.5)
        self.assertAlmostEqual(grid_1_5ft.pixels_per_foot, 40.0 / 1.5)

    def test_square_geometry_and_rotation(self):
        """Verifica o cálculo de vértices para quadrado em 0° e rotacionado em 90° e 45°."""
        # 10ft lado, ppf = 4.0 -> lado em pixels = 40px, half_side = 20px
        tpl = SpellTemplate(
            shape=SpellShape.SQUARE,
            size_feet=10.0,
            origin_world=(100.0, 100.0),
            rotation_degrees=0.0,
        )
        vertices = tpl.get_vertices_world(pixels_per_foot=4.0)
        self.assertEqual(len(vertices), 4)

        # Em 0°: cantos (-20, -20), (20, -20), (20, 20), (-20, 20) a partir de (100, 100)
        expected_0 = [(80.0, 80.0), (120.0, 80.0), (120.0, 120.0), (80.0, 120.0)]
        for v, exp in zip(vertices, expected_0):
            self.assertAlmostEqual(v[0], exp[0])
            self.assertAlmostEqual(v[1], exp[1])

        # Em 90°
        tpl_90 = tpl.with_rotation(90.0)
        vertices_90 = tpl_90.get_vertices_world(pixels_per_foot=4.0)
        self.assertEqual(len(vertices_90), 4)
        # Rotacionado 90° no sentido trigonométrico:
        # (-20, -20) -> (20, -20) + (100, 100) = (120, 80)
        self.assertAlmostEqual(vertices_90[0][0], 120.0)
        self.assertAlmostEqual(vertices_90[0][1], 80.0)

    def test_cone_geometry_and_dnd5e_aperture(self):
        """Verifica geometria do cone D&D 5E com abertura angular de 53.13° (semi-ângulo atan(0.5))."""
        # Alcance 30ft, ppf = 2.0 -> comprimento = 60px
        # Origem (0, 0), rotação 0° (apontando para a direita ao longo do eixo +X)
        tpl = SpellTemplate(
            shape=SpellShape.CONE,
            size_feet=30.0,
            origin_world=(0.0, 0.0),
            rotation_degrees=0.0,
        )
        vertices = tpl.get_vertices_world(pixels_per_foot=2.0)
        self.assertEqual(len(vertices), 3)

        # Vértice 0: origem (0, 0)
        self.assertAlmostEqual(vertices[0][0], 0.0)
        self.assertAlmostEqual(vertices[0][1], 0.0)

        # Semi-ângulo alpha = atan(0.5)
        # cos(alpha) = 1 / sqrt(1 + 0.25) = 2 / sqrt(5) ~ 0.894427
        # sin(alpha) = 0.5 / sqrt(1.25) = 1 / sqrt(5) ~ 0.447213
        # Pontas: (L * cos(alpha), -L * sin(alpha)) e (L * cos(alpha), L * sin(alpha))
        alpha = math.atan(0.5)
        exp_x = 60.0 * math.cos(alpha)
        exp_y = 60.0 * math.sin(alpha)

        self.assertAlmostEqual(vertices[1][0], exp_x)
        self.assertAlmostEqual(vertices[1][1], -exp_y)
        self.assertAlmostEqual(vertices[2][0], exp_x)
        self.assertAlmostEqual(vertices[2][1], exp_y)

        # O alcance dos raios a partir da origem é exatamente 60px
        range_v1 = math.hypot(vertices[1][0], vertices[1][1])
        range_v2 = math.hypot(vertices[2][0], vertices[2][1])
        self.assertAlmostEqual(range_v1, 60.0)
        self.assertAlmostEqual(range_v2, 60.0)

        # Abertura total angular do cone é 53.13° (2 * atan(0.5))
        opening_angle_deg = math.degrees(2 * alpha)
        self.assertAlmostEqual(opening_angle_deg, 53.13010235, places=4)

    def test_line_geometry_and_dimensions(self):
        """Verifica a geometria da linha projetada a partir da base."""
        # Comprimento 60ft, largura 5ft, ppf = 2.0 -> L = 120px, W = 10px, hw = 5px
        # Origem (50, 50), rotação 0° (ao longo de +X)
        tpl = SpellTemplate(
            shape=SpellShape.LINE,
            size_feet=60.0,
            width_feet=5.0,
            origin_world=(50.0, 50.0),
            rotation_degrees=0.0,
        )
        vertices = tpl.get_vertices_world(pixels_per_foot=2.0)
        self.assertEqual(len(vertices), 4)

        # Base left, Base right, Tip right, Tip left
        # Em 0°: Base left = (50, 50 - 5) = (50, 45)
        # Base right = (50, 50 + 5) = (50, 55)
        # Tip right = (50 + 120, 50 + 5) = (170, 55)
        # Tip left = (50 + 120, 50 - 5) = (170, 45)
        self.assertAlmostEqual(vertices[0][0], 50.0)
        self.assertAlmostEqual(vertices[0][1], 45.0)

        self.assertAlmostEqual(vertices[1][0], 50.0)
        self.assertAlmostEqual(vertices[1][1], 55.0)

        self.assertAlmostEqual(vertices[2][0], 170.0)
        self.assertAlmostEqual(vertices[2][1], 55.0)

        self.assertAlmostEqual(vertices[3][0], 170.0)
        self.assertAlmostEqual(vertices[3][1], 45.0)


class TestCombatManagerSpellSync(unittest.TestCase):
    """Testes unitários para sincronização do CombatManager e padrão Observer."""

    def setUp(self):
        self.combat_manager = CombatManager()
        self.notification_count = 0

    def _on_notified(self):
        self.notification_count += 1

    def test_set_and_update_spell_template_notifies_listeners(self):
        self.combat_manager.add_listener(self._on_notified)

        tpl = SpellTemplate(shape=SpellShape.CIRCLE, size_feet=20.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)
        self.assertEqual(self.notification_count, 1)
        self.assertEqual(self.combat_manager.active_spell_template, tpl)

        # Atualização de origem
        self.combat_manager.update_spell_origin(150.0, 250.0)
        self.assertEqual(self.notification_count, 2)
        self.assertEqual(self.combat_manager.active_spell_template.origin_world, (150.0, 250.0))

        # Rotação
        self.combat_manager.rotate_spell(30.0)
        self.assertEqual(self.notification_count, 3)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 30.0)

        # Toggle active
        is_act = self.combat_manager.toggle_spell_active()
        self.assertEqual(self.notification_count, 4)
        self.assertFalse(is_act)

        # Reset combat limpa template
        self.combat_manager.reset_combat()
        self.assertIsNone(self.combat_manager.active_spell_template)

    def test_toggle_spell_active_creates_default_when_none(self):
        self.assertIsNone(self.combat_manager.active_spell_template)
        is_act = self.combat_manager.toggle_spell_active()
        self.assertTrue(is_act)
        self.assertIsNotNone(self.combat_manager.active_spell_template)
        self.assertTrue(self.combat_manager.active_spell_template.is_active)


class TestSpellAoEPanelAndRenderer(unittest.TestCase):
    """Testes de integração do painel SpellAoEPanel e utilitário AoERenderer em modo headless."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.window = arcade.get_window()
        except RuntimeError:
            cls.window = arcade.open_window(800, 600, "Test Window", visible=False)

    def setUp(self):
        self.session_manager = SessionManager()
        self.combat_manager = self.session_manager.combat_manager
        self.panel = SpellAoEPanel(session_manager=self.session_manager)

    def test_panel_shape_selection_and_sync(self):
        self.panel.current_shape = SpellShape.CONE
        self.panel.is_active = True
        self.panel.size_input.text = "30"
        self.panel.sync_to_combat_manager()

        tpl = self.combat_manager.active_spell_template
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl.shape, SpellShape.CONE)
        self.assertAlmostEqual(tpl.size_feet, 30.0)
        self.assertTrue(tpl.is_active)

    def test_aoe_renderer_safe_when_none_or_inactive(self):
        # Não deve lançar exceção quando template for None ou inativo
        grid = GridManager(map_width=1000, map_height=800, columns=25, feet_per_square=5)
        AoERenderer.draw(template=None, grid_manager=grid, draw_x=0, draw_y=0, scale=1.0)

        inactive_tpl = SpellTemplate(is_active=False)
        AoERenderer.draw(template=inactive_tpl, grid_manager=grid, draw_x=0, draw_y=0, scale=1.0)

    def test_minimap_scroll_step_standard_and_ctrl(self):
        """Verifica que o scroll aplica 2° no modo padrão e 15° quando Ctrl estiver pressionado."""
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        minimap = TacticalMiniMap(window=self.window, session_manager=self.session_manager)
        minimap._last_draw_rect = (640.0, 100.0, 500.0, 400.0)

        # Configura grid e template ativo no CombatManager
        self.combat_manager.update_grid_manager_dimensions(1000.0, 800.0)
        tpl = SpellTemplate(shape=SpellShape.LINE, rotation_degrees=0.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)

        # 1. Scroll padrão (is_ctrl=False): delta = +2°
        handled = minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=1.0, is_ctrl=False)
        self.assertTrue(handled)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 2.0)

        # 2. Scroll reverso padrão: delta = -2° -> 0°
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=False)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 0.0)

        # 3. Scroll com Ctrl (is_ctrl=True): delta = +15°
        handled_ctrl = minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=1.0, is_ctrl=True)
        self.assertTrue(handled_ctrl)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 15.0)

        # 4. Scroll com Ctrl negativo: 15° - 15° = 0° -> -15° = 345°
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=True)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 0.0)
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=True)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 345.0)


if __name__ == "__main__":
    unittest.main()
