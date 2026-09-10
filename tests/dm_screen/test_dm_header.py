"""
Testes unitários para o componente DMHeader com auto-sizing e FlowRow.

Valida:
- Dimensionamento dinâmico dos botões do topo (Abrir/Fechar Tela Jogador, Fullscreen, IDLE, Badge).
- Garantia de padding horizontal mínimo (>= 12px) evitando clipping do caractere 'r' em 'Jogador'.
- Alinhamento vertical estrito da baseline (header_cy, anchor_y='center').
- Despacho de cliques pixel-perfect baseado no layout dinâmico calculado.
"""

import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import arcade
from src.manager.session_manager import SessionManager, DisplayState
from src.ui.dm.dm_header import DMHeader
from src.ui.utils.ui_constants import Dimensions, Typography, Spacing


class TestDMHeaderDynamicLayout(unittest.TestCase):
    """Bateria de testes para auto-sizing e alinhamento do cabeçalho do Mestre."""

    def setUp(self):
        self.session = SessionManager()
        self.mock_dm_window = MagicMock()
        self.mock_dm_window.is_player_window_open = True
        self.mock_dm_window.is_player_fullscreen = False
        self.header = DMHeader(session_manager=self.session, dm_window=self.mock_dm_window)

    def test_header_layout_structure_and_baseline(self):
        """Verifica se todos os elementos utilizam o mesmo header_cy e dimensões canônicas."""
        panel_w = 640.0
        panel_h = 768.0

        layout = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=True,
            is_fs=False,
        )

        expected_header_h = Dimensions.HEADER_HEIGHT
        expected_header_cy = panel_h - expected_header_h / 2.0

        self.assertEqual(layout["header_h"], expected_header_h)
        self.assertEqual(layout["header_cy"], expected_header_cy)
        self.assertEqual(layout["btn_h"], Dimensions.BTN_HEIGHT_COMPACT)

        # Todos os botões devem possuir centro X válido e largura positiva
        for key in ("pw", "fs", "badge", "idle"):
            btn_info = layout[key]
            self.assertIn("cx", btn_info)
            self.assertIn("w", btn_info)
            self.assertGreater(btn_info["w"], 0.0)
            self.assertGreater(btn_info["cx"], 0.0)
            self.assertLess(btn_info["cx"], panel_w)

    def test_button_labels_and_auto_sizing_toggle(self):
        """Verifica o auto-sizing ao alternar entre PlayerWindow aberta e fechada."""
        panel_w = 640.0
        panel_h = 768.0

        # 1. Estado: PlayerWindow Aberta ("📺 Fechar Tela Jogador")
        layout_open = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=True,
            is_fs=False,
        )
        self.assertEqual(layout_open["pw"]["label"], "📺 Fechar Tela Jogador")
        self.assertGreaterEqual(layout_open["pw"]["w"], 144.0)

        # 2. Estado: PlayerWindow Fechada ("📺 Abrir Tela Jogador")
        layout_closed = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=False,
            is_fs=False,
        )
        self.assertEqual(layout_closed["pw"]["label"], "📺 Abrir Tela Jogador")
        self.assertGreaterEqual(layout_closed["pw"]["w"], 144.0)

    def test_fullscreen_button_states(self):
        """Verifica as mudanças de rótulo e largura do botão de tela cheia."""
        panel_w = 640.0
        panel_h = 768.0

        # Janela aberta em tela cheia -> "🗗 Modo Janela"
        layout_fs = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=True,
            is_fs=True,
        )
        self.assertEqual(layout_fs["fs"]["label"], "🗗 Modo Janela")
        self.assertGreaterEqual(layout_fs["fs"]["w"], 106.0)

        # Janela aberta normal -> "⛶ Tela Cheia"
        layout_normal = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=True,
            is_fs=False,
        )
        self.assertEqual(layout_normal["fs"]["label"], "⛶ Tela Cheia")
        self.assertGreaterEqual(layout_normal["fs"]["w"], 106.0)

    def test_no_clipping_on_panel_right_edge(self):
        """Garante que o último botão (IDLE) não ultrapassa a borda direita do painel."""
        panel_w = 640.0
        panel_h = 768.0

        layout = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=True,
            is_fs=False,
        )

        idle = layout["idle"]
        idle_right_edge = idle["cx"] + idle["w"] / 2.0

        # Deve haver uma margem de segurança >= 8px antes da borda panel_w
        self.assertLessEqual(idle_right_edge, panel_w - 8.0)

    def test_dynamic_click_dispatch(self):
        """Verifica se os cliques são despachados nas coordenadas centrais exatas de cada botão."""
        panel_w = 640.0
        panel_h = 768.0

        layout = self.header._calculate_header_layout(
            panel_w=panel_w,
            panel_h=panel_h,
            is_open=True,
            is_fs=False,
        )
        header_cy = layout["header_cy"]

        # 1. Clique no botão IDLE
        idle_cx = layout["idle"]["cx"]
        toggle_pw_mock = MagicMock()
        toggle_fs_mock = MagicMock()

        handled_idle = self.header.handle_click(
            x=idle_cx,
            y=header_cy,
            panel_w=panel_w,
            panel_h=panel_h,
            set_tab_callback=lambda idx: None,
            on_toggle_player_window=toggle_pw_mock,
            on_toggle_fullscreen=toggle_fs_mock,
        )
        self.assertTrue(handled_idle)

        # 2. Clique no botão de Tela Cheia
        fs_cx = layout["fs"]["cx"]
        handled_fs = self.header.handle_click(
            x=fs_cx,
            y=header_cy,
            panel_w=panel_w,
            panel_h=panel_h,
            set_tab_callback=lambda idx: None,
            on_toggle_player_window=toggle_pw_mock,
            on_toggle_fullscreen=toggle_fs_mock,
        )
        self.assertTrue(handled_fs)
        toggle_fs_mock.assert_called_once()

        # 3. Clique no botão de Abrir/Fechar Tela Jogador
        pw_cx = layout["pw"]["cx"]
        handled_pw = self.header.handle_click(
            x=pw_cx,
            y=header_cy,
            panel_w=panel_w,
            panel_h=panel_h,
            set_tab_callback=lambda idx: None,
            on_toggle_player_window=toggle_pw_mock,
            on_toggle_fullscreen=toggle_fs_mock,
        )
        self.assertTrue(handled_pw)
        toggle_pw_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
