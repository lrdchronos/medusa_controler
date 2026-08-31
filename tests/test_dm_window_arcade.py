import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager, DisplayState
from src.ui.dm_window import DMWindow
from src.ui.player_window import PlayerWindow


class TestDMWindowArcade(unittest.TestCase):
    """Testes de inicialização, abas, modal de staging e integração da DMWindow com Arcade."""

    def setUp(self):
        self.session = SessionManager()
        self.dm_window = DMWindow(session_manager=self.session, width=1280, height=768)
        self.player_window = PlayerWindow(session_manager=self.session, dm_window=self.dm_window, width=1024, height=768)

    def tearDown(self):
        try:
            self.dm_window.close()
        except Exception:
            pass
        try:
            self.player_window.close()
        except Exception:
            pass

    def test_dm_window_initialization(self):
        self.assertEqual(self.dm_window.width, 1280)
        self.assertEqual(self.dm_window.height, 768)
        self.assertEqual(self.dm_window.active_tab, 0)
        self.assertFalse(self.dm_window.show_initiative_modal)
        self.assertGreaterEqual(len(self.dm_window.encounters_list), 1)
        self.assertGreaterEqual(len(self.dm_window.showcase_list), 1)

    def test_tab_switching_and_start_encounter(self):
        # Inicia encontro
        self.session.start_encounter("encounter_01")
        self.assertEqual(self.session.display_state, DisplayState.COMBAT)
        self.assertEqual(self.dm_window.active_tab, 2)  # Muda automaticamente para a aba de combate
        self.assertGreaterEqual(len(self.session.combat_manager.combatants), 4)

    def test_initiative_staging_modal_flow(self):
        self.session.start_encounter("encounter_01")

        # 1. Simula abertura do modal de staging
        self.dm_window.draft_initiatives = self.session.combat_manager.generate_draft_initiatives()
        self.dm_window.show_initiative_modal = True

        self.assertTrue(self.dm_window.show_initiative_modal)
        self.assertGreater(len(self.dm_window.draft_initiatives), 0)

        # 2. Edição manual de valor no draft
        first_uid = list(self.dm_window.draft_initiatives.keys())[0]
        self.dm_window.draft_initiatives[first_uid] = 25

        # 3. Confirmação
        self.session.combat_manager.apply_initiatives(self.dm_window.draft_initiatives)
        self.dm_window.show_initiative_modal = False

        self.assertFalse(self.dm_window.show_initiative_modal)
        self.assertTrue(self.session.combat_manager.has_combat_started)
        # O combatente com iniciativa 25 deve ser o primeiro na ordem de turnos
        self.assertEqual(self.session.combat_manager.turn_order[0].initiative_score, 25)

    def test_tactical_visibility_and_player_filtering(self):
        self.session.start_encounter("encounter_01")
        kobold = self.session.combat_manager.get_combatant("Kobold A")
        self.assertIsNotNone(kobold)

        # Oculta o combatente
        self.session.combat_manager.set_combatant_visibility(kobold.uid, True)
        self.assertTrue(kobold.is_hidden)

        # Na DMWindow, combatente oculto é mantido e marcado
        self.assertTrue(any(c.uid == kobold.uid and c.is_hidden for c in self.session.combat_manager.combatants))

        # Revela o combatente
        self.session.combat_manager.toggle_combatant_visibility(kobold.uid)
        self.assertFalse(kobold.is_hidden)

    def test_end_combat_ui_flow(self):
        self.session.start_encounter("encounter_01")
        self.assertEqual(self.dm_window.active_tab, 2)
        self.assertTrue(self.session.is_combat_active)

        # Encerra o combate
        self.session.end_combat(DisplayState.IDLE)
        self.assertEqual(self.session.display_state, DisplayState.IDLE)
        self.assertEqual(self.dm_window.active_tab, 0)
        self.assertEqual(len(self.session.combat_manager.combatants), 0)


if __name__ == "__main__":
    unittest.main()
