"""
Testes unitários rigorosos para o módulo src/ui/utils/ui_layout.py.

Valida:
- Avanço de coordenadas e cálculo métrico do FlowRow (centralizado e esquerdo).
- Acúmulo de total_width e total_span com gaps configuráveis.
- Cálculo de bounding box de botões no SmartButton (respeito a min_width e padding_x).
- Chamadas seguras e defensivas do PixelIconDrawer e draw_pixel_icon.
- Encapsulamento OOD estrito (cópias defensivas e atributos privados).
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import arcade
from src.ui.utils.ui_constants import Spacing, Dimensions, Typography
from src.ui.utils.ui_layout import (
    FlowRow,
    SmartButton,
    calculate_button_bounds,
    PixelIconDrawer,
    draw_pixel_icon,
)


class TestFlowRow(unittest.TestCase):
    """Bateria de testes unitários para a classe utilitária FlowRow."""

    def test_initial_state_and_defaults(self):
        """Verifica a inicialização padrão e os valores das propriedades."""
        row = FlowRow(start_x=100.0, center_y=250.0)

        self.assertEqual(row.start_x, 100.0)
        self.assertEqual(row.center_y, 250.0)
        self.assertEqual(row.gap, float(Spacing.SM))
        self.assertEqual(row.cursor_x, 100.0)
        self.assertEqual(row.total_width, 0.0)
        self.assertEqual(row.total_span, 0.0)
        self.assertEqual(row.item_count, 0)
        self.assertEqual(row.item_widths, [])
        self.assertEqual(row.item_positions, [])

    def test_custom_gap_initialization(self):
        """Verifica inicialização com gap customizado."""
        row = FlowRow(start_x=50.0, center_y=150.0, gap=16.0)
        self.assertEqual(row.gap, 16.0)
        self.assertEqual(row.cursor_x, 50.0)

    def test_add_single_item_centered(self):
        """Verifica adição de um único elemento com posicionamento centralizado."""
        row = FlowRow(start_x=20.0, center_y=100.0, gap=8.0, align_center=True)
        # Item com largura 60px ocupará o intervalo [20.0, 80.0] -> centro em 50.0
        pos = row.add(60.0)

        self.assertEqual(pos, (50.0, 100.0))
        # Cursor avança: 20.0 + 60.0 + 8.0 = 88.0
        self.assertEqual(row.cursor_x, 88.0)
        self.assertEqual(row.total_width, 60.0)
        self.assertEqual(row.total_span, 60.0)
        self.assertEqual(row.item_count, 1)
        self.assertEqual(row.item_widths, [60.0])
        self.assertEqual(row.item_positions, [(50.0, 100.0)])

    def test_add_multiple_items_progression(self):
        """Verifica a progressão exata de coordenadas para múltiplos itens consecutivos."""
        row = FlowRow(start_x=0.0, center_y=50.0, gap=10.0, align_center=True)

        # Item 1: largura 100px -> intervalo [0, 100] -> centro 50.0
        # Cursor avança para: 0 + 100 + 10 = 110.0
        pos1 = row.add(100.0)
        self.assertEqual(pos1, (50.0, 50.0))
        self.assertEqual(row.cursor_x, 110.0)

        # Item 2: largura 40px -> intervalo [110, 150] -> centro 130.0
        # Cursor avança para: 110 + 40 + 10 = 160.0
        pos2 = row.add(40.0)
        self.assertEqual(pos2, (130.0, 50.0))
        self.assertEqual(row.cursor_x, 160.0)

        # Item 3: largura 60px -> intervalo [160, 220] -> centro 190.0
        # Cursor avança para: 160 + 60 + 10 = 230.0
        pos3 = row.add(60.0)
        self.assertEqual(pos3, (190.0, 50.0))
        self.assertEqual(row.cursor_x, 230.0)

        # Métricas agregadas
        self.assertEqual(row.item_count, 3)
        self.assertEqual(row.total_width, 200.0)  # 100 + 40 + 60
        self.assertEqual(row.total_span, 220.0)   # 200 + 2 * 10
        self.assertEqual(row.item_widths, [100.0, 40.0, 60.0])
        self.assertEqual(row.item_positions, [(50.0, 50.0), (130.0, 50.0), (190.0, 50.0)])

    def test_add_left_aligned(self):
        """Verifica o comportamento quando align_center=False (retorna borda esquerda)."""
        row = FlowRow(start_x=10.0, center_y=80.0, gap=5.0, align_center=False)

        # Item 1: largura 50px -> retorna 10.0, cursor vai para 10 + 50 + 5 = 65.0
        pos1 = row.add(50.0)
        self.assertEqual(pos1, (10.0, 80.0))
        self.assertEqual(row.cursor_x, 65.0)

        # Item 2: largura 30px -> retorna 65.0, cursor vai para 65 + 30 + 5 = 100.0
        pos2 = row.add(30.0)
        self.assertEqual(pos2, (65.0, 80.0))
        self.assertEqual(row.cursor_x, 100.0)

    def test_add_negative_width_clamping(self):
        """Verifica proteção contra larguras negativas (Poka-Yoke)."""
        row = FlowRow(start_x=0.0, center_y=10.0, gap=4.0)
        pos = row.add(-20.0)

        self.assertEqual(pos, (0.0, 10.0))
        self.assertEqual(row.cursor_x, 4.0)  # 0.0 + 0.0 + 4.0
        self.assertEqual(row.total_width, 0.0)
        self.assertEqual(row.item_widths, [0.0])

    def test_reset(self):
        """Verifica se o reset reinicializa corretamente o cursor e o histórico."""
        row = FlowRow(start_x=10.0, center_y=20.0, gap=8.0)
        row.add(100.0)
        row.add(50.0)
        self.assertEqual(row.item_count, 2)

        row.reset()
        self.assertEqual(row.cursor_x, 10.0)
        self.assertEqual(row.item_count, 0)
        self.assertEqual(row.total_width, 0.0)
        self.assertEqual(row.total_span, 0.0)
        self.assertEqual(row.item_widths, [])
        self.assertEqual(row.item_positions, [])

        # Reset com novos parâmetros
        row.reset(start_x=50.0, center_y=100.0, gap=12.0)
        self.assertEqual(row.start_x, 50.0)
        self.assertEqual(row.center_y, 100.0)
        self.assertEqual(row.gap, 12.0)
        self.assertEqual(row.cursor_x, 50.0)

    def test_defensive_copies(self):
        """Verifica se as propriedades retornam cópias defensivas que não afetam o estado interno."""
        row = FlowRow(start_x=0.0, center_y=0.0, gap=8.0)
        row.add(50.0)

        widths = row.item_widths
        widths.append(999.0)
        self.assertEqual(row.item_widths, [50.0])

        positions = row.item_positions
        positions.append((999.0, 999.0))
        self.assertEqual(row.item_positions, [(25.0, 0.0)])


class TestSmartButton(unittest.TestCase):
    """Bateria de testes unitários para o cálculo de bounding boxes do SmartButton."""

    def test_empty_text_respects_min_width(self):
        """Texto vazio deve retornar min_width."""
        width = calculate_button_bounds("", font_size=12, padding_x=12.0, min_width=80.0)
        self.assertEqual(width, 80.0)

    def test_short_text_respects_min_width(self):
        """Texto curto com largura menor que min_width deve ser limitado a min_width."""
        width = calculate_button_bounds("OK", font_size=10, padding_x=8.0, min_width=80.0)
        self.assertEqual(width, 80.0)

    def test_long_text_expands_beyond_min_width(self):
        """Texto longo deve expandir o botão além do min_width."""
        long_text = "CONFIRMAR E INICIAR COMBATE COM TODOS OS MONSTROS"
        width = calculate_button_bounds(long_text, font_size=14, padding_x=16.0, min_width=80.0)
        self.assertGreater(width, 80.0)
        # O valor calculado deve acomodar o padding horizontal de 2 * 16.0 = 32.0
        self.assertGreater(width, 32.0)

    def test_custom_padding_and_min_width(self):
        """Verifica a aplicação estrita de padding_x e min_width customizados."""
        min_w = 120.0
        pad_x = 24.0
        width = calculate_button_bounds("X", font_size=12, padding_x=pad_x, min_width=min_w)
        self.assertEqual(width, min_w)

    def test_class_method_matches_function(self):
        """Garante consistência entre a chamada funcional e a classe SmartButton."""
        text = "Salvar Encontro"
        res_func = calculate_button_bounds(text, font_size=12, padding_x=12.0, min_width=90.0)
        res_class = SmartButton.calculate_button_bounds(text, font_size=12, padding_x=12.0, min_width=90.0)
        self.assertEqual(res_func, res_class)

    def test_active_window_text_measurement(self):
        """Testa o cálculo quando há um arcade.Text com content_width simulado."""
        with patch("arcade.get_window", return_value=MagicMock()):
            with patch("arcade.Text") as mock_text_cls:
                mock_text_inst = MagicMock()
                mock_text_inst.content_width = 150.0
                mock_text_cls.return_value = mock_text_inst

                calculated = calculate_button_bounds("Texto Teste", font_size=14, padding_x=10.0, min_width=80.0)
                # 150.0 + 2 * 10.0 = 170.0
                self.assertEqual(calculated, 170.0)


class TestPixelIconDrawer(unittest.TestCase):
    """Bateria de testes unitários para a renderização proporcional de ícones."""

    def test_draw_with_none_texture(self):
        """Chamar com textura nula (None) não deve levantar exceção."""
        try:
            draw_pixel_icon(None, center_x=100.0, center_y=100.0, target_size=24.0)
            PixelIconDrawer.draw_pixel_icon(None, center_x=100.0, center_y=100.0, target_size=24.0)
        except Exception as e:
            self.fail(f"draw_pixel_icon levantou exceção inesperada com None: {e}")

    def test_draw_pixel_icon_scale_and_params(self):
        """Verifica o cálculo de escala proporcional e os parâmetros de chamada para arcade.draw_texture_rect."""
        mock_texture = MagicMock(spec=arcade.Texture)
        mock_texture.width = 16
        mock_texture.height = 16

        with patch("arcade.draw_texture_rect") as mock_draw:
            draw_pixel_icon(mock_texture, center_x=50.0, center_y=60.0, target_size=32.0)

            # Escala: 32 / 16 = 2.0 -> draw_w = 32.0, draw_h = 32.0
            mock_draw.assert_called_once()
            args, kwargs = mock_draw.call_args
            self.assertEqual(args[0], mock_texture)
            xywh = args[1]
            self.assertEqual(xywh.x, 50.0)
            self.assertEqual(xywh.y, 60.0)
            self.assertEqual(xywh.width, 32.0)
            self.assertEqual(xywh.height, 32.0)
            self.assertTrue(kwargs.get("pixelated", False))

    def test_draw_pixel_icon_non_square_aspect_ratio(self):
        """Verifica a preservação de proporção para texturas não quadradas."""
        mock_texture = MagicMock(spec=arcade.Texture)
        mock_texture.width = 16
        mock_texture.height = 8

        with patch("arcade.draw_texture_rect") as mock_draw:
            PixelIconDrawer.draw_pixel_icon(mock_texture, center_x=100.0, center_y=200.0, target_size=32.0)

            # Escala: 32 / 16 = 2.0 -> draw_w = 32.0, draw_h = 16.0
            mock_draw.assert_called_once()
            args, kwargs = mock_draw.call_args
            xywh = args[1]
            self.assertEqual(xywh.x, 100.0)
            self.assertEqual(xywh.y, 200.0)
            self.assertEqual(xywh.width, 32.0)
            self.assertEqual(xywh.height, 16.0)
            self.assertTrue(kwargs.get("pixelated", False))


if __name__ == "__main__":
    unittest.main()
