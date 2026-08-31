import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager, DisplayState
from src.ui.player_window import PlayerWindow
from src.ui.utils.sprite_utils import CombatToken


class TestTokenInterpolation(unittest.TestCase):
    """Testes unitários para o sistema de interpolação suave (Lerp) dos tokens."""

    def test_combat_token_initialization(self):
        token = CombatToken(
            uid="char-001",
            name="Bolo",
            is_player=True,
            target_x=150.0,
            target_y=250.0,
            lerp_speed=10.0,
        )
        self.assertEqual(token.uid, "char-001")
        self.assertEqual(token.name, "Bolo")
        self.assertTrue(token.is_player)
        self.assertEqual(token.target_x, 150.0)
        self.assertEqual(token.target_y, 250.0)
        self.assertEqual(token.center_x, 150.0)
        self.assertEqual(token.center_y, 250.0)
        self.assertEqual(token.current_x, 150.0)
        self.assertEqual(token.current_y, 250.0)
        self.assertEqual(token.lerp_speed, 10.0)

    def test_combat_token_lerp_formula(self):
        token = CombatToken(
            uid="char-001",
            name="Bolo",
            is_player=True,
            target_x=100.0,
            target_y=100.0,
            lerp_speed=10.0,
        )
        # Define novo alvo sem snap
        token.set_target(200.0, 300.0, snap_immediately=False)
        self.assertEqual(token.center_x, 100.0)
        self.assertEqual(token.center_y, 100.0)
        self.assertEqual(token.target_x, 200.0)
        self.assertEqual(token.target_y, 300.0)

        # Atualiza 1 quadro a 60 FPS (dt = 1/60)
        dt = 1.0 / 60.0
        factor = min(10.0 * dt, 1.0)  # 1/6 ~ 0.166667
        expected_x = 100.0 + (200.0 - 100.0) * factor
        expected_y = 100.0 + (300.0 - 100.0) * factor

        token.update_lerp(dt)
        self.assertAlmostEqual(token.center_x, expected_x, places=4)
        self.assertAlmostEqual(token.center_y, expected_y, places=4)

    def test_combat_token_jitter_prevention_snap(self):
        token = CombatToken(
            uid="char-001",
            name="Bolo",
            is_player=True,
            target_x=200.0,
            target_y=200.0,
            lerp_speed=10.0,
        )
        # Posição atual quase no alvo (diferença < 1.0px)
        token.center_x = 199.5
        token.center_y = 200.3

        token.update_lerp(1.0 / 60.0)
        # Deve cravar no destino exato para evitar jitter
        self.assertEqual(token.center_x, 200.0)
        self.assertEqual(token.center_y, 200.0)

    def test_combat_token_properties_and_immediate_snap(self):
        token = CombatToken(
            uid="char-001",
            name="Bolo",
            is_player=True,
            target_x=50.0,
            target_y=50.0,
        )
        token.current_x = 80.0
        token.current_y = 90.0
        self.assertEqual(token.center_x, 80.0)
        self.assertEqual(token.center_y, 90.0)

        token.set_target(400.0, 500.0, snap_immediately=True)
        self.assertEqual(token.target_x, 400.0)
        self.assertEqual(token.target_y, 500.0)
        self.assertEqual(token.center_x, 400.0)
        self.assertEqual(token.center_y, 500.0)

    def test_player_window_token_sync_and_lerp_integration(self):
        session = SessionManager()
        window = PlayerWindow(session_manager=session, width=1024, height=768)

        try:
            # 1. Inicia Encontro de Combate
            session.start_encounter("encounter_01")
            self.assertEqual(session.display_state, DisplayState.COMBAT)

            # Sincroniza tokens inicialmente
            window.on_update(0.0)
            self.assertGreaterEqual(len(window.token_sprites), 4)

            # Obtém primeiro combatente
            combatant = session.combat_manager.combatants[0]
            token = window.token_sprites[combatant.uid]
            initial_x = token.center_x
            initial_y = token.center_y

            # 2. O Mestre move o combatente para uma nova célula no Grid
            session.combat_manager.set_combatant_position(combatant.uid, 12, 10)

            # 3. Na PlayerWindow, apenas target_x e target_y mudam antes do próximo update com dt
            window._update_tokens(delta_time=0.0)
            self.assertNotEqual(token.target_x, initial_x)
            self.assertNotEqual(token.target_y, initial_y)
            self.assertEqual(token.center_x, initial_x)
            self.assertEqual(token.center_y, initial_y)

            # 4. Ao rodar múltiplos frames a 60 FPS, o token desliza suavemente até o destino
            for _ in range(60):
                window.on_update(1.0 / 60.0)

            # Após ~1 segundo, deve ter alcançado o destino com snapping
            self.assertEqual(token.center_x, token.target_x)
            self.assertEqual(token.center_y, token.target_y)

        finally:
            window.close()

    def test_player_window_token_cleanup_on_end_combat(self):
        session = SessionManager()
        window = PlayerWindow(session_manager=session, width=1024, height=768)

        try:
            session.start_encounter("encounter_01")
            window.on_update(0.0)
            self.assertGreaterEqual(len(window.token_sprites), 4)

            # Encerra o combate
            session.end_combat(DisplayState.IDLE)
            window.on_update(0.0)
            self.assertEqual(len(window.token_sprites), 0)

        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
