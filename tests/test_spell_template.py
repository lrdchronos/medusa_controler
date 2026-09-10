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

    def test_minimap_scroll_step_standard_ctrl_and_alt(self):
        """Verifica que o scroll aplica 2° para yaw no modo livre, 15° com Ctrl e 15° para pitch com Alt."""
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        minimap = TacticalMiniMap(window=self.window, session_manager=self.session_manager)
        minimap._last_draw_rect = (640.0, 100.0, 500.0, 400.0)

        # Configura grid e template ativo no CombatManager
        self.combat_manager.update_grid_manager_dimensions(1000.0, 800.0)
        tpl = SpellTemplate(shape=SpellShape.LINE, rotation_degrees=0.0, pitch_degrees=0.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)

        # 1. Scroll simples (livre): delta = +2° yaw
        handled = minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=1.0, is_ctrl=False, is_alt=False)
        self.assertTrue(handled)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 2.0)

        # 2. Scroll reverso simples: delta = -2° -> 0° yaw
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=False, is_alt=False)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 0.0)

        # 3. Ctrl + Scroll: delta = +15° yaw
        handled_ctrl = minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=1.0, is_ctrl=True, is_alt=False)
        self.assertTrue(handled_ctrl)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 15.0)

        # 4. Ctrl + Scroll reverso: delta = -15° -> 0°
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=True, is_alt=False)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 0.0)

        # 5. Alt + Scroll: delta = +15° pitch
        handled_alt = minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=1.0, is_ctrl=False, is_alt=True)
        self.assertTrue(handled_alt)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.pitch_degrees, 15.0)

        # 6. Alt + Scroll negativo: 15° - 15° = 0° -> -15° = 345°
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=False, is_alt=True)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.pitch_degrees, 0.0)
        minimap.handle_mouse_scroll(x=700.0, y=200.0, scroll_x=0.0, scroll_y=-1.0, is_ctrl=False, is_alt=True)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.pitch_degrees, 345.0)

    def test_minimap_cursor_click_sets_exact_origin_and_aoe_cells(self):
        """Simula clique do cursor no Mini-Mapa definindo a âncora da magia na célula clicada e calculando células atingidas."""
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        minimap = TacticalMiniMap(window=self.window, session_manager=self.session_manager)
        # Configura layout do minimapa: draw_rect = (50px, 50px, 500px, 500px), 25 colunas -> 20px por célula no minimapa
        minimap._last_draw_rect = (50.0, 50.0, 500.0, 500.0)

        # Grid de mundo: 1000px x 1000px, 25 colunas -> 40px por célula no mundo (5ft por célula -> 8px/ft)
        self.combat_manager.update_grid_manager_dimensions(1000.0, 1000.0)
        grid_mgr = self.combat_manager.grid_manager
        self.assertIsNotNone(grid_mgr)
        self.assertEqual(grid_mgr.columns, 25)
        self.assertAlmostEqual(grid_mgr.cell_size, 40.0)

        # Ativa feitiço de círculo (raio 10ft = 2 quadrados)
        tpl = SpellTemplate(shape=SpellShape.CIRCLE, size_feet=10.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)

        # Simula clique do mouse no centro da célula (10, 8) no minimapa:
        # mx = draw_x + (10 + 0.5) * 20.0 = 50 + 210 = 260.0
        # my = draw_y + (8 + 0.5) * 20.0 = 50 + 170 = 220.0
        handled = minimap.on_mouse_press(x=260.0, y=220.0, button=arcade.MOUSE_BUTTON_LEFT, modifiers=0)
        self.assertTrue(handled)

        # No mundo contínuo:
        # col_frac = 210 / 20 = 10.5 -> world_x = 10.5 * 40.0 = 420.0
        # row_frac = 170 / 20 = 8.5 -> world_y = 8.5 * 40.0 = 340.0
        active_tpl = self.combat_manager.active_spell_template
        self.assertIsNotNone(active_tpl)
        self.assertAlmostEqual(active_tpl.origin_world[0], 420.0)
        self.assertAlmostEqual(active_tpl.origin_world[1], 340.0)

        # Verifica cálculo de células atingidas:
        cells = self.combat_manager.get_spell_aoe_cells()
        self.assertIn((10, 8), cells)   # Célula central
        self.assertIn((10, 9), cells)   # 1 quadrado acima
        self.assertIn((10, 7), cells)   # 1 quadrado abaixo
        self.assertIn((11, 8), cells)   # 1 quadrado à direita
        self.assertIn((9, 8), cells)    # 1 quadrado à esquerda
        self.assertIn((10, 10), cells)  # 2 quadrados acima (10ft)
        self.assertNotIn((10, 12), cells) # 4 quadrados acima (fora do alcance de 10ft)

    def test_minimap_cursor_drag_updates_origin_in_realtime(self):
        """Simula clique e arraste com o mouse atualizando dinamicamente a âncora da magia em tempo real."""
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        minimap = TacticalMiniMap(window=self.window, session_manager=self.session_manager)
        minimap._last_draw_rect = (0.0, 0.0, 500.0, 500.0)
        self.combat_manager.update_grid_manager_dimensions(1000.0, 1000.0)

        tpl = SpellTemplate(shape=SpellShape.SPHERE, size_feet=15.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)

        # 1. Clique inicial em (100, 100) -> célula (5, 5) no minimapa (20px/cell)
        minimap.on_mouse_press(x=100.0, y=100.0, button=arcade.MOUSE_BUTTON_LEFT, modifiers=0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.origin_world[0], 200.0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.origin_world[1], 200.0)

        # 2. Arraste contínuo para (200, 300) -> célula (10, 15) no minimapa
        minimap.on_mouse_drag(x=200.0, y=300.0, dx=100.0, dy=200.0, buttons=arcade.MOUSE_BUTTON_LEFT, modifiers=0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.origin_world[0], 400.0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.origin_world[1], 600.0)

        # 3. Soltura do mouse
        minimap.on_mouse_release(x=200.0, y=300.0, button=arcade.MOUSE_BUTTON_LEFT, modifiers=0)
        self.assertFalse(minimap._is_dragging_spell)

    def test_minimap_cursor_right_click_aims_rotation_to_cursor(self):
        """Simula clique com botão direito mirando a rotação horizontal (yaw) do feitiço em direção ao cursor."""
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        minimap = TacticalMiniMap(window=self.window, session_manager=self.session_manager)
        minimap._last_draw_rect = (0.0, 0.0, 500.0, 500.0)
        self.combat_manager.update_grid_manager_dimensions(1000.0, 1000.0)

        # Origem do feitiço em world=(200.0, 200.0), minimap screen=(100.0, 100.0)
        tpl = SpellTemplate(shape=SpellShape.CONE, size_feet=30.0, origin_world=(200.0, 200.0), rotation_degrees=0.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)

        # 1. Botão direito apontando para a direita no minimapa (200.0, 100.0) -> dx > 0, dy = 0 -> 0°
        minimap.on_mouse_press(x=200.0, y=100.0, button=arcade.MOUSE_BUTTON_RIGHT, modifiers=0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 0.0, places=1)

        # 2. Botão direito apontando para cima no minimapa (100.0, 200.0) -> dx = 0, dy > 0 -> 90°
        minimap.on_mouse_press(x=100.0, y=200.0, button=arcade.MOUSE_BUTTON_RIGHT, modifiers=0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 90.0, places=1)

        # 3. Arraste com botão direito apontando para a esquerda (0.0, 100.0) -> dx < 0, dy = 0 -> 180°
        minimap.on_mouse_drag(x=0.0, y=100.0, dx=-100.0, dy=-100.0, buttons=arcade.MOUSE_BUTTON_RIGHT, modifiers=0)
        self.assertAlmostEqual(self.combat_manager.active_spell_template.rotation_degrees, 180.0, places=1)

    def test_mutual_exclusivity_fog_and_spell(self):
        """Verifica que o Modo Fog e o Modo Spell não podem estar ativos simultaneamente."""
        from src.ui.dm.handlers.combat_tab_input_handler import CombatTabInputHandler
        from src.ui.dm.fog_control_panel import FogControlPanel, FogTool
        from src.ui.dm.combat_tab import CombatTabView

        tab = CombatTabView(session_manager=self.session_manager)
        self.assertFalse(tab.spell_aoe_panel.is_active)
        self.assertFalse(tab.fog_panel.is_tool_active)

        # 1. Ativa Modo Spell
        tab.spell_aoe_panel.is_active = True
        tab.spell_aoe_panel.sync_to_combat_manager()
        self.assertTrue(tab.spell_aoe_panel.is_active)
        self.assertTrue(self.combat_manager.active_spell_template.is_active)

        # 2. Ativa ferramenta no FogPanel -> Modo Spell deve ser desativado automaticamente
        tab.fog_panel.active_tool = FogTool.ADD
        # Simula despacho via CombatTabInputHandler
        if tab.fog_panel.is_tool_active and tab.spell_aoe_panel.is_active:
            tab.spell_aoe_panel.is_active = False
            tab.spell_aoe_panel.sync_to_combat_manager()

        self.assertTrue(tab.fog_panel.is_tool_active)
        self.assertFalse(tab.spell_aoe_panel.is_active)
        self.assertFalse(self.combat_manager.active_spell_template.is_active)

        # 3. Reativa Modo Spell -> Ferramenta do FogPanel deve ser desativada automaticamente
        tab.spell_aoe_panel.is_active = True
        tab.spell_aoe_panel.sync_to_combat_manager()
        if tab.spell_aoe_panel.is_active and tab.fog_panel.is_tool_active:
            tab.fog_panel.active_tool = FogTool.NONE

        self.assertTrue(tab.spell_aoe_panel.is_active)
        self.assertFalse(tab.fog_panel.is_tool_active)
        self.assertEqual(tab.fog_panel.active_tool, FogTool.NONE)

    def test_mode_hierarchy_suppresses_movement_overlay(self):
        """Verifica que quando o modo Spell ou o modo Fog estão ativos, a zona azul de movimento é suprimida."""
        from src.ui.components.grid_cell_highlighter import GridCellHighlighter
        from src.domain.models.entity import DynamicToken, EntityType

        self.combat_manager.update_grid_manager_dimensions(1000.0, 800.0)
        char = DynamicToken(name="Guerreiro", max_hp=20, armor_class=15, speed=30, entity_type=EntityType.PLAYER)
        self.combat_manager.spawn_combatant(char, (5, 5))
        self.combat_manager.start_combat()

        mov_hl = GridCellHighlighter(grid_manager=self.combat_manager.grid_manager)

        # 1. Modo Normal: Spell inativo, Fog inativo -> zona de movimento permitida
        is_spell_active = bool(self.combat_manager.active_spell_template and self.combat_manager.active_spell_template.is_active)
        is_fog_active = False
        self.assertFalse(is_spell_active)
        self.assertFalse(is_fog_active)

        # 2. Ativa Spell -> hierarquia suprime movimento
        tpl = SpellTemplate(shape=SpellShape.CIRCLE, size_feet=20.0, is_active=True)
        self.combat_manager.set_spell_template(tpl)
        is_spell_active = bool(self.combat_manager.active_spell_template and self.combat_manager.active_spell_template.is_active)
        self.assertTrue(is_spell_active)

        # 3. Limpeza do highlighter de movimento
        if is_spell_active or is_fog_active:
            mov_hl.clear()
        self.assertEqual(len(mov_hl), 0)

    def test_player_view_renderer_spell_and_mode_hierarchy(self):
        """Valida que PlayerViewRenderer renderiza o feitiço ativo e respeita a supressão de movimento."""
        from src.ui.renderers.player_view_renderer import PlayerViewRenderer
        from src.ui.components.grid_cell_highlighter import GridCellHighlighter
        from src.domain.models.entity import DynamicToken, EntityType
        from src.ui.initiative_hud import InitiativeHUD

        self.combat_manager.update_grid_manager_dimensions(1000.0, 800.0)
        char = DynamicToken(name="Mago", max_hp=15, armor_class=12, speed=30, entity_type=EntityType.PLAYER)
        self.combat_manager.spawn_combatant(char, (5, 5))
        self.combat_manager.start_combat()

        aoe_hl = GridCellHighlighter(grid_manager=self.combat_manager.grid_manager)
        mov_hl = GridCellHighlighter(grid_manager=self.combat_manager.grid_manager)
        hud = InitiativeHUD(combat_manager=self.combat_manager)

        # 1. Modo Normal: Spell inativo -> movimento ativo
        PlayerViewRenderer.draw_combat(
            window_width=1024,
            window_height=768,
            combat_manager=self.combat_manager,
            texture_cache={},
            text_cache={},
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            token_sprites={},
            hud=hud,
            movement_highlighter=mov_hl,
            is_fog_active=False,
        )
        self.assertGreater(len(mov_hl), 0)
        self.assertEqual(len(aoe_hl), 0)

        # 2. Modo Spell ativo -> aoe_hl populado, mov_hl limpo
        tpl = SpellTemplate(shape=SpellShape.CIRCLE, size_feet=15.0, origin_world=(200.0, 200.0), is_active=True)
        self.combat_manager.set_spell_template(tpl)

        PlayerViewRenderer.draw_combat(
            window_width=1024,
            window_height=768,
            combat_manager=self.combat_manager,
            texture_cache={},
            text_cache={},
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            token_sprites={},
            hud=hud,
            movement_highlighter=mov_hl,
            is_fog_active=False,
        )
        self.assertGreater(len(aoe_hl), 0)
        self.assertEqual(len(mov_hl), 0)

        # 3. Modo Fog ativo (Spell desativado) -> aoe_hl limpo, mov_hl limpo
        self.combat_manager.set_spell_template(tpl.with_active(False))
        PlayerViewRenderer.draw_combat(
            window_width=1024,
            window_height=768,
            combat_manager=self.combat_manager,
            texture_cache={},
            text_cache={},
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            token_sprites={},
            hud=hud,
            movement_highlighter=mov_hl,
            is_fog_active=True,
        )
        self.assertEqual(len(aoe_hl), 0)
        self.assertEqual(len(mov_hl), 0)

    def test_minimap_renderer_spell_and_mode_hierarchy(self):
        """Valida que MiniMapRenderer renderiza o feitiço ativo e respeita a supressão de movimento."""
        from src.ui.renderers.minimap_renderer import MiniMapRenderer
        from src.ui.components.grid_cell_highlighter import GridCellHighlighter
        from src.domain.models.entity import DynamicToken, EntityType
        from src.manager.session_manager import DisplayState

        self.session_manager.set_display_state(DisplayState.COMBAT)
        self.combat_manager.update_grid_manager_dimensions(1000.0, 800.0)
        char = DynamicToken(name="Mago", max_hp=15, armor_class=12, speed=30, entity_type=EntityType.PLAYER)
        self.combat_manager.spawn_combatant(char, (5, 5))
        self.combat_manager.start_combat()

        aoe_hl = GridCellHighlighter(grid_manager=self.combat_manager.grid_manager)
        mov_hl = GridCellHighlighter(grid_manager=self.combat_manager.grid_manager)

        # Ativa Spell
        tpl = SpellTemplate(shape=SpellShape.CONE, size_feet=30.0, origin_world=(200.0, 200.0), is_active=True)
        self.combat_manager.set_spell_template(tpl)

        MiniMapRenderer.draw_content(
            window_width=1280,
            window_height=768,
            draw_rect=(640.0, 100.0, 500.0, 400.0),
            session_manager=self.session_manager,
            texture_cache={},
            text_cache={},
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            movement_highlighter=mov_hl,
        )
        self.assertGreater(len(aoe_hl), 0)
        self.assertEqual(len(mov_hl), 0)


if __name__ == "__main__":
    unittest.main()
