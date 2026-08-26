import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager, DisplayState
from src.ui.player_window import PlayerWindow


class TestPlayerWindowIdleAnimation(unittest.TestCase):

    def setUp(self):
        self.session = SessionManager()
        self.window = PlayerWindow(session_manager=self.session, width=800, height=600)

    def tearDown(self):
        try:
            self.window.close()
        except Exception:
            pass

    def test_idle_sigil_sprite_initialization(self):
        # 1. Deve possuir 5 texturas carregadas da spritesheet
        self.assertEqual(len(self.window.sigil_sprite.textures), 5)
        # 2. Escala proporcional de 48px para 92px
        expected_scale = 92.0 / 48.0
        self.assertAlmostEqual(self.window.sigil_sprite.scale_x, expected_scale, places=4)
        self.assertAlmostEqual(self.window.sigil_sprite.scale_y, expected_scale, places=4)
        # 3. Presente na lista de sprites
        self.assertIn(self.window.sigil_sprite, self.window.idle_sprites)
        self.assertEqual(self.window._idle_cur_frame, 0)

    def test_idle_animation_circular_cycling(self):
        # Avança 0.20s -> avança 1 quadro
        self.window.on_update(0.20)
        self.assertEqual(self.window._idle_cur_frame, 1)

        self.window.on_update(0.20)
        self.assertEqual(self.window._idle_cur_frame, 2)

        self.window.on_update(0.20)
        self.assertEqual(self.window._idle_cur_frame, 3)

        self.window.on_update(0.20)
        self.assertEqual(self.window._idle_cur_frame, 4)

        # Volta circularmente para o frame 0
        self.window.on_update(0.20)
        self.assertEqual(self.window._idle_cur_frame, 0)

    def test_animation_only_runs_on_idle(self):
        # Transiciona para PROJECTION
        self.session.set_display_state(DisplayState.PROJECTION)
        initial_frame = self.window._idle_cur_frame

        # Atualiza 1.0s
        self.window.on_update(1.0)
        # Não deve avançar fora do estado IDLE
        self.assertEqual(self.window._idle_cur_frame, initial_frame)


if __name__ == "__main__":
    unittest.main()
