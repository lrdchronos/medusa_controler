import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.utils.ui_constants import (
    Spacing,
    Dimensions,
    Typography,
    Colors,
    with_alpha,
    lighten,
    darken,
    apply_disabled,
)
import src.ui.utils as ui_utils


class TestUIConstants(unittest.TestCase):
    """Testes unitários rigorosos para os Design Tokens e constantes de UI do Medusa VTT."""

    def test_spacing_8pt_grid_scale(self):
        """Valida que todos os tokens de espaçamento respeitam a escala de 8pt / 4pt."""
        self.assertEqual(Spacing.TINY, 4)
        self.assertEqual(Spacing.SM, 8)
        self.assertEqual(Spacing.MD, 16)
        self.assertEqual(Spacing.LG, 24)
        self.assertEqual(Spacing.XL, 32)

        # Aliases semânticos
        self.assertEqual(Spacing.GAP_TINY, 4)
        self.assertEqual(Spacing.GAP_SMALL, 8)
        self.assertEqual(Spacing.GAP_MEDIUM, 16)
        self.assertEqual(Spacing.GAP_LARGE, 24)
        self.assertEqual(Spacing.GAP_XLARGE, 32)
        self.assertEqual(Spacing.CONTAINER_PADDING, 16)

        # Todos devem ser múltiplos estritos de 4
        for val in [Spacing.TINY, Spacing.SM, Spacing.MD, Spacing.LG, Spacing.XL]:
            self.assertEqual(val % 4, 0)
            self.assertGreater(val, 0)

    def test_dimensions_conventions(self):
        """Valida dimensões canônicas de botões, inputs, raios e bordas."""
        # Botões
        self.assertEqual(Dimensions.BTN_HEIGHT_DEFAULT, 36.0)
        self.assertEqual(Dimensions.BTN_HEIGHT_LARGE, 40.0)
        self.assertEqual(Dimensions.BTN_HEIGHT_COMPACT, 28.0)
        self.assertEqual(Dimensions.BTN_SIZE_COMPACT_SM, 28.0)
        self.assertEqual(Dimensions.BTN_SIZE_COMPACT_MD, 32.0)
        self.assertGreaterEqual(Dimensions.BTN_PADDING_X_MIN, 12.0)

        # Gaps de ação e isolamento destrutivo
        self.assertEqual(Dimensions.BTN_GAP_INLINE, 8.0)
        self.assertEqual(Dimensions.BTN_GAP_DESTRUCTIVE, 16.0)

        # Raios de cantos
        self.assertEqual(Dimensions.CORNER_RADIUS_SM, 4.0)
        self.assertEqual(Dimensions.CORNER_RADIUS_DEFAULT, 6.0)
        self.assertEqual(Dimensions.CORNER_RADIUS_CARD, 8.0)
        self.assertEqual(Dimensions.CORNER_RADIUS_MODAL, 10.0)

        # Bordas
        self.assertEqual(Dimensions.BORDER_WIDTH_DEFAULT, 1.0)
        self.assertEqual(Dimensions.BORDER_WIDTH_ACTIVE, 1.5)
        self.assertEqual(Dimensions.BORDER_WIDTH_THICK, 2.0)

        # Inputs e Modais
        self.assertEqual(Dimensions.INPUT_HEIGHT_DEFAULT, 36.0)
        self.assertEqual(Dimensions.HEADER_HEIGHT, 56.0)
        self.assertEqual(Dimensions.MODAL_MIN_WIDTH, 360.0)
        self.assertEqual(Dimensions.MODAL_PADDING, 16.0)

    def test_typography_scale(self):
        """Valida hierarquia tipográfica proporcional e fontes canônicas."""
        self.assertEqual(Typography.SIZE_TAB_TITLE_LG, 20)
        self.assertEqual(Typography.SIZE_TAB_TITLE, 18)
        self.assertEqual(Typography.SIZE_HEADER, 16)
        self.assertEqual(Typography.SIZE_SUBHEADER, 14)
        self.assertEqual(Typography.SIZE_BODY, 12)
        self.assertEqual(Typography.SIZE_LABEL, 11)
        self.assertEqual(Typography.SIZE_BADGE, 10)
        self.assertEqual(Typography.SIZE_MICRO, 9)

        # Font stacks
        self.assertIsInstance(Typography.FONT_FAMILY_PRIMARY, tuple)
        self.assertIn("Segoe UI", Typography.FONT_FAMILY_PRIMARY)
        self.assertIsInstance(Typography.FONT_FAMILY_UI, tuple)
        self.assertIn("Consolas", Typography.FONT_FAMILY_UI)

    def test_colors_dark_fantasy_identity(self):
        """Valida que a paleta de cores respeita as premissas inegociáveis de PREMISES.md."""
        self.assertEqual(Colors.BG_DARK, (14, 18, 24, 255))      # #0E1218
        self.assertEqual(Colors.ACCENT_GOLD, (241, 196, 15, 255))# #F1C40F
        self.assertEqual(Colors.PC_BLUE, (41, 128, 185, 255))    # #2980B9
        self.assertEqual(Colors.NPC_RED, (192, 57, 43, 255))     # #C0392B

        # Valida que todas as cores são tuplas RGBA válidas (4 canais entre 0 e 255)
        color_attrs = [
            Colors.BG_DARK, Colors.BG_PANEL, Colors.BG_CARD, Colors.BG_MODAL,
            Colors.ACCENT_GOLD, Colors.PC_BLUE, Colors.NPC_RED,
            Colors.BORDER_DEFAULT, Colors.BORDER_SUBTLE, Colors.BORDER_FOCUS,
            Colors.TEXT_PRIMARY, Colors.TEXT_SECONDARY, Colors.TEXT_MUTED, Colors.TEXT_HIGHLIGHT,
            Colors.SUCCESS, Colors.WARNING, Colors.DANGER, Colors.INFO,
        ]
        for color in color_attrs:
            self.assertEqual(len(color), 4)
            for channel in color:
                self.assertGreaterEqual(channel, 0)
                self.assertLessEqual(channel, 255)

    def test_color_utilities(self):
        """Valida funções puras de manipulação de cor (with_alpha, lighten, darken, apply_disabled)."""
        base = (100, 100, 100, 255)

        # with_alpha
        self.assertEqual(with_alpha(base, 128), (100, 100, 100, 128))
        self.assertEqual(with_alpha(base, 300), (100, 100, 100, 255))
        self.assertEqual(with_alpha(base, -50), (100, 100, 100, 0))

        # lighten (+15% padrão)
        light = lighten(base, factor=0.15)
        self.assertGreater(light[0], base[0])
        self.assertGreater(light[1], base[1])
        self.assertGreater(light[2], base[2])
        self.assertEqual(light[3], base[3])  # Alfa inalterado

        # darken (-10% padrão)
        dark = darken(base, factor=0.10)
        self.assertLess(dark[0], base[0])
        self.assertLess(dark[1], base[1])
        self.assertLess(dark[2], base[2])
        self.assertEqual(dark[3], base[3])  # Alfa inalterado

        # apply_disabled (40% alpha)
        disabled = apply_disabled(base, alpha_factor=0.40)
        self.assertEqual(disabled[0], base[0])
        self.assertEqual(disabled[1], base[1])
        self.assertEqual(disabled[2], base[2])
        self.assertEqual(disabled[3], int(255 * 0.40))

    def test_reexport_in_ui_utils_package(self):
        """Valida que src.ui.utils exporta todos os tokens e funções de constantes."""
        self.assertTrue(hasattr(ui_utils, "Spacing"))
        self.assertTrue(hasattr(ui_utils, "Dimensions"))
        self.assertTrue(hasattr(ui_utils, "Typography"))
        self.assertTrue(hasattr(ui_utils, "Colors"))
        self.assertTrue(hasattr(ui_utils, "with_alpha"))
        self.assertTrue(hasattr(ui_utils, "lighten"))
        self.assertTrue(hasattr(ui_utils, "darken"))
        self.assertTrue(hasattr(ui_utils, "apply_disabled"))


if __name__ == "__main__":
    unittest.main()
