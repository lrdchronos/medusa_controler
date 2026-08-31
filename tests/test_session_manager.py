import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager, DisplayState


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.session = SessionManager()

    def test_initial_state_is_idle(self):
        self.assertEqual(self.session.display_state, DisplayState.IDLE)
        self.assertTrue(self.session.is_idle)
        self.assertFalse(self.session.is_combat_active)
        self.assertFalse(self.session.is_projecting)
        self.assertIsNone(self.session.projected_image_path)

    def test_project_image_transition(self):
        # Testa projeção com imagem existente
        sample_img = "assets/images/showcase/taverna_do_dragao.png"
        success = self.session.project_image(sample_img)
        self.assertTrue(success)
        self.assertEqual(self.session.display_state, DisplayState.PROJECTION)
        self.assertTrue(self.session.is_projecting)
        self.assertIsNotNone(self.session.projected_image_path)

        # Retorna para IDLE
        self.session.clear_display_to_idle()
        self.assertEqual(self.session.display_state, DisplayState.IDLE)
        self.assertIsNone(self.session.projected_image_path)

    def test_start_encounter_and_end_combat(self):
        self.session.start_encounter("encounter_240820261511")
        self.assertEqual(self.session.display_state, DisplayState.COMBAT)
        self.assertTrue(self.session.is_combat_active)
        self.assertGreater(len(self.session.combat_manager.combatants), 0)

        # Encerra o combate e retorna para IDLE
        self.session.end_combat(DisplayState.IDLE)
        self.assertEqual(self.session.display_state, DisplayState.IDLE)
        self.assertTrue(self.session.is_idle)
        self.assertFalse(self.session.is_combat_active)
        self.assertEqual(len(self.session.combat_manager.combatants), 0)
        self.assertEqual(len(self.session.combat_manager.turn_order), 0)

    def test_return_to_idle_alias_and_cleanup(self):
        self.session.start_encounter("encounter_240820261511")
        self.assertTrue(self.session.is_combat_active)

        self.session.return_to_idle()
        self.assertEqual(self.session.display_state, DisplayState.IDLE)
        self.assertTrue(self.session.is_idle)
        self.assertEqual(len(self.session.combat_manager.combatants), 0)

    def test_list_encounters_discovery(self):
        encounters = self.session.list_available_encounters()
        self.assertGreater(len(encounters), 0)
        uids = [e["uid"] for e in encounters]
        self.assertTrue(any("encounter" in u for u in uids))

    def test_list_showcase_images_discovery(self):
        images = self.session.list_available_showcase_images()
        self.assertGreater(len(images), 0)
        filenames = [img["filename"] for img in images]
        self.assertTrue(any("taverna" in f or "grass" in f for f in filenames))

    def test_observer_notifications_on_transitions(self):
        events = []

        def on_change():
            events.append(self.session.display_state)

        self.session.add_listener(on_change)

        self.session.project_image("assets/images/showcase/taverna_do_dragao.png")
        self.assertEqual(events[-1], DisplayState.PROJECTION)

        self.session.start_encounter("encounter_240820261511")
        self.assertEqual(events[-1], DisplayState.COMBAT)

        self.session.clear_display_to_idle()
        self.assertEqual(events[-1], DisplayState.IDLE)


if __name__ == "__main__":
    unittest.main()
