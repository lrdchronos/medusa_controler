import unittest
import sys
import os
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager, DisplayState
from src.ui.dm_window import DMWindow
from src.ui.player_window import PlayerWindow
from src.ui.dm.dm_header import DMHeader


class TestPlayerWindowLifecycle(unittest.TestCase):
    """
    Testes automatizados do Ciclo de Vida da PlayerWindow,
    Fullscreen Toggle, integração com DMHeader e atalhos globais F10/F11.
    """

    def setUp(self):
        self.session = SessionManager()
        self.dm_window = DMWindow(session_manager=self.session, width=1280, height=768)
        self.player_window = PlayerWindow(
            session_manager=self.session,
            dm_window=self.dm_window,
            width=1024,
            height=768,
        )
        self.dm_window.player_window = self.player_window

    def tearDown(self):
        try:
            if self.player_window is not None:
                self.player_window.close()
        except Exception:
            pass
        try:
            if self.dm_window is not None and self.dm_window.player_window is not None:
                self.dm_window.player_window.close()
        except Exception:
            pass
        try:
            if self.dm_window is not None:
                self.dm_window.close()
        except Exception:
            pass

    def test_player_window_initialization_and_listeners(self):
        """Verifica se PlayerWindow é inicializada como resizable e conecta listeners."""
        self.assertTrue(self.player_window.resizable)
        self.assertEqual(self.player_window.width, 1024)
        self.assertEqual(self.player_window.height, 768)
        self.assertEqual(self.dm_window.player_window, self.player_window)
        self.assertTrue(self.dm_window.is_player_window_open)

        # Verifica se o listener foi adicionado
        self.assertIn(self.player_window._on_session_changed_listener, self.session._SessionManager__listeners)
        self.assertIn(self.player_window._on_combat_changed_listener, self.session.combat_manager._CombatManager__listeners)

    def test_toggle_fullscreen(self):
        """Testa o método semântico toggle_fullscreen na PlayerWindow."""
        initial_fs = self.player_window.fullscreen
        self.player_window.toggle_fullscreen()
        self.assertEqual(self.player_window.fullscreen, not initial_fs)

        # Alterna de volta
        self.player_window.toggle_fullscreen()
        self.assertEqual(self.player_window.fullscreen, initial_fs)

    def test_player_window_on_resize(self):
        """Verifica se on_resize recalcula a câmera e a viewport sem exceções."""
        self.player_window.on_resize(1920, 1080)
        self.player_window.set_size(1920, 1080)
        self.assertEqual(self.player_window.width, 1920)
        self.assertEqual(self.player_window.height, 1080)

    def test_graceful_close_and_listener_cleanup(self):
        """Verifica se o fechamento gracioso desinscreve listeners e limpa recursos."""
        listener_session = self.player_window._on_session_changed_listener
        listener_combat = self.player_window._on_combat_changed_listener

        # Fecha a PlayerWindow
        self.player_window.close()

        # Listeners devem ter sido removidos
        self.assertNotIn(listener_session, self.session._SessionManager__listeners)
        self.assertNotIn(listener_combat, self.session.combat_manager._CombatManager__listeners)
        self.assertTrue(self.player_window._listeners_cleaned)

    def test_dm_window_open_and_close_player_window(self):
        """Testa abertura e fechamento da PlayerWindow através da DMWindow com warm reuse."""
        self.assertTrue(self.dm_window.is_player_window_open)

        # 1. Fecha pela DMWindow (soft close)
        self.dm_window.close_player_window()
        self.assertFalse(self.dm_window.is_player_window_open)
        self.assertFalse(self.player_window.visible)
        self.assertTrue(self.player_window._listeners_cleaned)

        # 2. Reabre pela DMWindow (reutiliza instância aquecida sem perder contexto)
        self.dm_window.open_player_window()
        self.assertTrue(self.dm_window.is_player_window_open)
        self.assertTrue(self.player_window.visible)
        self.assertFalse(self.player_window._listeners_cleaned)
        self.assertIn(self.player_window._on_session_changed_listener, self.session._SessionManager__listeners)

        # 3. Toggle fecha
        self.dm_window.toggle_player_window()
        self.assertFalse(self.dm_window.is_player_window_open)
        self.assertFalse(self.player_window.visible)

        # 4. Toggle abre
        self.dm_window.toggle_player_window()
        self.assertTrue(self.dm_window.is_player_window_open)
        self.assertTrue(self.player_window.visible)

        # 5. Executa ciclo de update e draw na janela reaberta sem erros
        self.player_window.on_update(0.016)
        self.player_window.on_draw()

    def test_dm_window_toggle_fullscreen(self):
        """Testa comutação de fullscreen via DMWindow."""
        initial_fs = self.dm_window.is_player_fullscreen
        self.dm_window.toggle_player_fullscreen()
        self.assertEqual(self.dm_window.is_player_fullscreen, not initial_fs)

        self.dm_window.toggle_player_fullscreen()
        self.assertEqual(self.dm_window.is_player_fullscreen, initial_fs)

    def test_dm_header_buttons_and_click_handling(self):
        """Testa desenho dos botões no cabeçalho e seus disparos de clique."""
        header = self.dm_window.header
        panel_w = 640.0
        panel_h = 768.0

        # Desenho com PlayerWindow aberta
        header.draw(panel_w, panel_h, active_tab=0, player_window_open=True, is_fullscreen=False)

        # Clique no botão de fechar PlayerWindow (panel_w - 366, header_cy)
        header_h = 56
        header_cy = panel_h - header_h / 2
        player_btn_x = panel_w - 366

        # Simula clique no botão da PlayerWindow -> deve alternar estado
        handled = header.handle_click(
            x=player_btn_x,
            y=header_cy,
            panel_w=panel_w,
            panel_h=panel_h,
            set_tab_callback=lambda idx: None,
        )
        self.assertTrue(handled)
        self.assertFalse(self.dm_window.is_player_window_open)

        # Simula novo clique -> deve reabrir
        handled2 = header.handle_click(
            x=player_btn_x,
            y=header_cy,
            panel_w=panel_w,
            panel_h=panel_h,
            set_tab_callback=lambda idx: None,
        )
        self.assertTrue(handled2)
        self.assertTrue(self.dm_window.is_player_window_open)

        # Clique no botão de Fullscreen (panel_w - 235, header_cy)
        fs_btn_x = panel_w - 235
        initial_fs = self.dm_window.is_player_fullscreen
        handled_fs = header.handle_click(
            x=fs_btn_x,
            y=header_cy,
            panel_w=panel_w,
            panel_h=panel_h,
            set_tab_callback=lambda idx: None,
        )
        self.assertTrue(handled_fs)
        self.assertEqual(self.dm_window.is_player_fullscreen, not initial_fs)

    def test_keyboard_shortcuts_f10_and_f11(self):
        """Testa atalhos de teclado F10 (abrir/fechar) e F11 (fullscreen) na DMWindow."""
        self.assertTrue(self.dm_window.is_player_window_open)

        # Pressiona F10 -> Fecha PlayerWindow
        self.dm_window.on_key_press(arcade.key.F10, 0)
        self.assertFalse(self.dm_window.is_player_window_open)

        # Pressiona F10 novamente -> Abre PlayerWindow
        self.dm_window.on_key_press(arcade.key.F10, 0)
        self.assertTrue(self.dm_window.is_player_window_open)

        # Pressiona F11 -> Alterna fullscreen
        initial_fs = self.dm_window.is_player_fullscreen
        self.dm_window.on_key_press(arcade.key.F11, 0)
        self.assertEqual(self.dm_window.is_player_fullscreen, not initial_fs)

        self.dm_window.on_key_press(arcade.key.F11, 0)
        self.assertEqual(self.dm_window.is_player_fullscreen, initial_fs)

    def test_player_window_close_does_not_affect_dm_window(self):
        """Garante que fechar a PlayerWindow não encerra a DMWindow nem a sessão de combate."""
        self.session.start_encounter("encounter_01")
        self.assertEqual(self.session.display_state, DisplayState.COMBAT)

        # Fecha a PlayerWindow
        self.player_window.on_close()

        # DMWindow e Session permanecem perfeitamente ativas
        self.assertFalse(self.dm_window.is_player_window_open)
        self.assertEqual(self.session.display_state, DisplayState.COMBAT)
        self.assertGreaterEqual(len(self.session.combat_manager.combatants), 4)


if __name__ == "__main__":
    unittest.main()
