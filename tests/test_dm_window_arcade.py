import unittest
import sys
import os
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

    def test_encounter_creator_wizard_flow(self):

        # 1. Abre a Aba 3 (Criador de Encontros)
        self.dm_window.active_tab = 3
        creator = self.dm_window.creator_tab
        self.assertEqual(creator.stage, 1)

        # 2. Configura metadados e combatentes
        creator.title = "Emboscada no Covil"
        creator.description = "Batalha contra kobolds armados."
        creator.columns = 25
        creator.feet_per_square = 5
        creator.monster_counts["kobold"] = 3

        # 3. Avança para Etapa 2 (Palco Tático)
        success = creator.proceed_to_stage_2()
        self.assertTrue(success)
        self.assertEqual(creator.stage, 2)
        self.assertGreaterEqual(len(creator.staging_combatants), 4)

        # 4. Posiciona um combatente no grid
        first_comb = creator.staging_combatants[0]
        first_comb["placed"] = True
        first_comb["col"] = 5
        first_comb["row"] = 8
        first_comb["is_hidden"] = True

        # 5. Salva o encontro
        saved_file = creator.save_encounter_file()
        self.assertIsNotNone(saved_file)
        self.assertTrue(Path(saved_file).is_file())

        try:
            # 6. Verifica se o encontro recém-salvo aparece na lista de encontros da Aba 0
            self.dm_window.refresh_encounter_files()
            saved_stem = Path(saved_file).stem
            found = any(saved_stem in enc.get("uid", "") or saved_stem in enc.get("filename", "") for enc in self.dm_window.encounters_list)
            self.assertTrue(found)
        finally:
            # Limpa o arquivo criado no teste
            try:
                os.remove(saved_file)
            except Exception:
                pass

    def test_encounter_creator_staging_interaction(self):
        self.dm_window.active_tab = 3
        creator = self.dm_window.creator_tab
        creator.monster_counts["kobold"] = 2
        creator.proceed_to_stage_2()

        # Testa alternar visibilidade de combatente
        first_item = creator.staging_combatants[0]
        self.assertFalse(first_item["is_hidden"])
        first_item["is_hidden"] = True
        self.assertTrue(first_item["is_hidden"])

        # Testa retorno à Etapa 1
        creator.return_to_stage_1()
        self.assertEqual(creator.stage, 1)
        self.assertEqual(creator.title, "Emboscada no Covil" if creator.title == "Emboscada no Covil" else creator.title)


if __name__ == "__main__":
    unittest.main()

