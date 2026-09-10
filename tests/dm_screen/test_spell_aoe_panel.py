"""
Testes unitários para o layout e renderização do painel de magias (SpellAoEPanel / SpellAoERenderer).

Valida:
- Desacoplamento de textos no cabeçalho via FlowRow (título e tag [DESATIVADO]/[ATIVADO]).
- Espaçamento de segurança (>= 12px) entre o título e a tag de status, impedindo sobreposição.
- Padronização rigorosa da linha de centro (row_y) para todos os labels, caixas de input e unidades na Linha 2.
- Alinhamento vertical com anchor_y="center".
"""

import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import arcade
from src.manager.session_manager import SessionManager
from src.domain.models.spell_template import AoEShape, SpellShape
from src.ui.dm.spell_aoe_panel import SpellAoEPanel
from src.ui.dm.renderers.spell_aoe_renderer import SpellAoERenderer
from src.ui.utils.ui_constants import Dimensions, Typography, Spacing


class TestSpellAoEPanelLayout(unittest.TestCase):
    """Testes de layout dinâmico e nivelamento de inputs no SpellAoEPanel."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.window = arcade.get_window()
        except RuntimeError:
            cls.window = arcade.open_window(800, 600, "Test Window", visible=False)

    def setUp(self):
        self.session = SessionManager()
        self.panel = SpellAoEPanel(session_manager=self.session)

    def test_header_title_and_badge_decoupling_inactive(self):
        """Verifica que a tag [DESATIVADO] fica à direita do título com pelo menos 12px de respiro."""
        panel_w = 640.0
        top_y = 500.0

        self.panel.is_active = False
        self.panel.draw(panel_w=panel_w, top_y=top_y)

        header_h = Dimensions.HEADER_HEIGHT_SUB
        expected_head_y = top_y - header_h / 2.0

        title_txt = self.panel._text_cache.get("sp_title")
        badge_txt = self.panel._text_cache.get("sp_badge")

        self.assertIsNotNone(title_txt)
        self.assertIsNotNone(badge_txt)

        # 1. Alinhamento vertical idêntico na baseline do cabeçalho
        self.assertEqual(title_txt.y, expected_head_y)
        self.assertEqual(badge_txt.y, expected_head_y)
        self.assertEqual(title_txt.anchor_y, "center")
        self.assertEqual(badge_txt.anchor_y, "center")

        # 2. Posição X e ausência de sobreposição
        self.assertEqual(title_txt.x, 24.0)
        self.assertEqual(badge_txt.text, "[DESATIVADO]")
        # A tag deve iniciar estritamente após o término do título + 12px
        self.assertGreaterEqual(badge_txt.x, title_txt.x + 12.0)

    def test_header_title_and_badge_decoupling_active(self):
        """Verifica que a tag [ATIVADO] é desenhada corretamente à direita com respiro."""
        panel_w = 640.0
        top_y = 500.0

        self.panel.is_active = True
        self.panel.draw(panel_w=panel_w, top_y=top_y)

        badge_txt = self.panel._text_cache.get("sp_badge")
        self.assertIsNotNone(badge_txt)
        self.assertEqual(badge_txt.text, "[ATIVADO]")
        self.assertGreaterEqual(badge_txt.x, 24.0 + 12.0)

    def test_row2_numeric_inputs_common_baseline(self):
        """Verifica se todos os labels, caixas de input e sufixos da linha 2 compartilham o mesmo row2_y."""
        panel_w = 640.0
        top_y = 500.0

        self.panel.current_shape = AoEShape.CIRCLE
        self.panel.draw(panel_w=panel_w, top_y=top_y)

        header_h = Dimensions.HEADER_HEIGHT_SUB
        expected_row2_y = top_y - header_h - 48.0

        # Rótulo de Raio, Unidade ft e Inputs
        lbl_size = self.panel._text_cache.get("sp_lbl_size")
        unit_size = self.panel._text_cache.get("sp_unit_size")
        lbl_z = self.panel._text_cache.get("sp_lbl_z")
        unit_z = self.panel._text_cache.get("sp_unit_z")
        lbl_pitch = self.panel._text_cache.get("sp_lbl_pitch")
        unit_pitch = self.panel._text_cache.get("sp_unit_pitch")

        self.assertIsNotNone(lbl_size)
        self.assertIsNotNone(unit_size)
        self.assertIsNotNone(lbl_z)
        self.assertIsNotNone(unit_z)
        self.assertIsNotNone(lbl_pitch)
        self.assertIsNotNone(unit_pitch)

        # Baseline vertical idêntica para todos os textos da linha 2
        for txt in (lbl_size, unit_size, lbl_z, unit_z, lbl_pitch, unit_pitch):
            self.assertEqual(txt.y, expected_row2_y)
            self.assertEqual(txt.anchor_y, "center")

        # Caixas de input centralizadas em expected_row2_y
        self.assertEqual(self.panel.size_input.bounds[1], expected_row2_y)
        self.assertEqual(self.panel.z_input.bounds[1], expected_row2_y)
        self.assertEqual(self.panel.pitch_input.bounds[1], expected_row2_y)

        # Sequenciamento horizontal da esquerda para a direita (FlowRow)
        self.assertLess(lbl_size.x, self.panel.size_input.bounds[0])
        self.assertLess(self.panel.size_input.bounds[0], unit_size.x)
        self.assertLess(unit_size.x, lbl_z.x)
        self.assertLess(lbl_z.x, self.panel.z_input.bounds[0])
        self.assertLess(self.panel.z_input.bounds[0], unit_z.x)
        self.assertLess(unit_z.x, lbl_pitch.x)
        self.assertLess(lbl_pitch.x, self.panel.pitch_input.bounds[0])
        self.assertLess(self.panel.pitch_input.bounds[0], unit_pitch.x)

    def test_row2_line_shape_includes_width_input(self):
        """Ao selecionar AoEShape.LINE, o input de largura deve ser inserido ordenadamente no FlowRow."""
        panel_w = 640.0
        top_y = 500.0

        self.panel.current_shape = AoEShape.LINE
        self.panel.draw(panel_w=panel_w, top_y=top_y)

        header_h = Dimensions.HEADER_HEIGHT_SUB
        expected_row2_y = top_y - header_h - 48.0

        lbl_w = self.panel._text_cache.get("sp_lbl_w")
        unit_w = self.panel._text_cache.get("sp_unit_w")

        self.assertIsNotNone(lbl_w)
        self.assertIsNotNone(unit_w)
        self.assertEqual(lbl_w.y, expected_row2_y)
        self.assertEqual(unit_w.y, expected_row2_y)
        self.assertEqual(self.panel.width_input.bounds[1], expected_row2_y)

        # Ordem: [Comprimento] -> [Largura] -> [Alt Z] -> [Pitch]
        self.assertLess(self.panel.size_input.bounds[0], lbl_w.x)
        self.assertLess(lbl_w.x, self.panel.width_input.bounds[0])
        self.assertLess(self.panel.width_input.bounds[0], self.panel.z_input.bounds[0])


if __name__ == "__main__":
    unittest.main()
