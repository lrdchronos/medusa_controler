import unittest
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster
from src.ui.dm.initiative_modal import InitiativeStagingModal

logger = logging.getLogger(__name__)


class TestHiddenInitiativeAndAmbushers(unittest.TestCase):
    """
    Suíte de testes unitários para validação de iniciativa e ciclo de turnos
    com criaturas ocultas (hidden == True), garantindo ausência de 'turnos fantasmas',
    inserção cirúrgica de emboscadores via reveal_combatant() e persistência de save state.
    """

    def setUp(self) -> None:
        self.combat_manager = CombatManager()

        # Cria 2 PJs e 3 Monstros (sendo 2 monstros marcados como hidden: True)
        self.pc1 = PlayableCharacter(
            name="Guerreiro Thorin",
            uid="pc_thorin",
            level=3,
            max_hp=30,
            armor_class=16,
            ability_scores={"DEX": 14},  # MOD +2
        )
        self.pc2 = PlayableCharacter(
            name="Mago Elrond",
            uid="pc_elrond",
            level=3,
            max_hp=20,
            armor_class=12,
            ability_scores={"DEX": 12},  # MOD +1
        )
        self.mob_visible = Monster(
            name="Orc Vanguarda",
            uid="mob_orc_visible",
            max_hp=15,
            armor_class=13,
            ability_scores={"DEX": 10},  # MOD +0
            is_hidden=False,
        )
        self.mob_hidden1 = Monster(
            name="Goblin Emboscador 1",
            uid="mob_goblin_hidden_1",
            max_hp=8,
            armor_class=14,
            ability_scores={"DEX": 16},  # MOD +3
            is_hidden=True,
        )
        self.mob_hidden2 = Monster(
            name="Goblin Emboscador 2",
            uid="mob_goblin_hidden_2",
            max_hp=8,
            armor_class=14,
            ability_scores={"DEX": 16},  # MOD +3
            is_hidden=True,
        )

        self.all_combatants = [
            self.pc1,
            self.pc2,
            self.mob_visible,
            self.mob_hidden1,
            self.mob_hidden2,
        ]

    def test_start_combat_excludes_hidden_tokens_and_ghost_turns(self) -> None:
        """
        Garante que o início de combate com 2 PJs e 3 monstros (2 ocultos):
        1. Popula turn_order exclusivamente com 3 combatentes revelados.
        2. Mantém os 2 monstros ocultos no repositório hidden_combatants.
        3. Ao avançar 5 rodadas via next_turn(), os turnos circulam estritamente entre os 3 revelados.
        """
        # Configura combatentes e inicia combate
        self.combat_manager.start_combat(self.all_combatants)

        # 1. Verifica contagem de turn_order e hidden_combatants
        self.assertEqual(len(self.combat_manager.turn_order), 3)
        self.assertEqual(len(self.combat_manager.hidden_combatants), 2)
        self.assertEqual(len(self.combat_manager.combatants), 5)

        # Garante que nenhum hidden está em turn_order
        turn_order_uids = self.combat_manager.turn_order_uids
        self.assertIn(self.pc1.uid, turn_order_uids)
        self.assertIn(self.pc2.uid, turn_order_uids)
        self.assertIn(self.mob_visible.uid, turn_order_uids)
        self.assertNotIn(self.mob_hidden1.uid, turn_order_uids)
        self.assertNotIn(self.mob_hidden2.uid, turn_order_uids)

        # 2. Rola iniciativas controladas para ordenar a fita
        manual = {
            self.pc1.uid: 20,
            self.pc2.uid: 15,
            self.mob_visible.uid: 10,
        }
        self.combat_manager.roll_initiatives(manual_rolls=manual)

        self.assertEqual(len(self.combat_manager.turn_order), 3)
        self.assertEqual(self.combat_manager.round_number, 1)
        self.assertEqual(self.combat_manager.current_turn_index, 0)
        self.assertEqual(self.combat_manager.active_character.uid, self.pc1.uid)

        # 3. Avança 5 rodadas completas (5 * 3 = 15 chamadas a next_turn)
        expected_sequence = [self.pc1.uid, self.pc2.uid, self.mob_visible.uid]

        for round_idx in range(1, 6):
            self.assertEqual(self.combat_manager.round_number, round_idx)
            for turn_idx in range(3):
                active = self.combat_manager.active_character
                self.assertIsNotNone(active)
                self.assertEqual(active.uid, expected_sequence[turn_idx])
                self.assertFalse(active.is_hidden, "Combatente no turno não pode ser oculto (sem turnos fantasmas).")
                self.combat_manager.next_turn()

        # Ao final de 5 rodadas completas, estamos na rodada 6, turno 0
        self.assertEqual(self.combat_manager.round_number, 6)
        self.assertEqual(self.combat_manager.current_turn_index, 0)
        self.assertEqual(self.combat_manager.active_character.uid, self.pc1.uid)

    def test_reveal_ambusher_during_round_2_inserts_as_next_turn(self) -> None:
        """
        Garante que ao revelar uma criatura oculta durante a rodada 2:
        1. A entidade sai de hidden_combatants.
        2. Entra em turn_order no índice exato current_turn_index + 1.
        3. Recebe o turno na próxima chamada a next_turn().
        """
        self.combat_manager.start_combat(self.all_combatants)
        manual = {
            self.pc1.uid: 20,
            self.pc2.uid: 15,
            self.mob_visible.uid: 10,
        }
        self.combat_manager.roll_initiatives(manual_rolls=manual)

        # Avança para a Rodada 2, Turno 0 (Turno de Thorin / pc1)
        self.combat_manager.next_turn()  # Rodada 1, Turno 1 (pc2)
        self.combat_manager.next_turn()  # Rodada 1, Turno 2 (mob_visible)
        self.combat_manager.next_turn()  # Rodada 2, Turno 0 (pc1)

        self.assertEqual(self.combat_manager.round_number, 2)
        self.assertEqual(self.combat_manager.current_turn_index, 0)
        self.assertEqual(self.combat_manager.active_character.uid, self.pc1.uid)

        # Verifica que o Goblin 1 está inicialmente em hidden_combatants
        self.assertIn(self.mob_hidden1.uid, self.combat_manager.hidden_combatants)
        self.assertTrue(self.mob_hidden1.hidden)
        self.assertFalse(self.mob_hidden1.is_visible)

        # O Mestre revela o Goblin 1 (Emboscador)
        revealed = self.combat_manager.reveal_combatant(self.mob_hidden1.uid)

        self.assertEqual(revealed, self.mob_hidden1)
        self.assertFalse(self.mob_hidden1.hidden)
        self.assertTrue(self.mob_hidden1.is_visible)

        # 1. Saiu de hidden_combatants
        self.assertNotIn(self.mob_hidden1.uid, self.combat_manager.hidden_combatants)
        self.assertEqual(len(self.combat_manager.hidden_combatants), 1)

        # 2. Inserido no índice current_turn_index + 1 (índice 1)
        self.assertEqual(len(self.combat_manager.turn_order), 4)
        self.assertEqual(self.combat_manager.turn_order[1], self.mob_hidden1)
        self.assertEqual(self.combat_manager.current_turn_index, 0)  # pc1 ainda está agindo

        # 3. Na próxima chamada de next_turn(), o Goblin recém-revelado recebe a ação
        next_active = self.combat_manager.next_turn()
        self.assertEqual(next_active, self.mob_hidden1)
        self.assertEqual(self.combat_manager.current_turn_index, 1)
        self.assertEqual(self.combat_manager.round_number, 2)

    def test_save_and_load_combat_state_with_hidden_combatants(self) -> None:
        """
        Garante a persistência e restauração segregada de saves com criaturas ocultas e visíveis:
        1. Carrega encounter_01 e define 2 kobolds como ocultos.
        2. Inicia combate, rola iniciativas para os 3 revelados e avança turno.
        3. Salva estado e restaura via load_combat_state.
        4. Valida que turn_order possui apenas 3 entidades e hidden_combatants possui 2.
        """
        encounter_uid = "encounter_01"
        save_path = self.combat_manager.get_save_path(encounter_uid)
        if save_path.is_file():
            save_path.unlink()

        try:
            self.combat_manager.load_encounter(encounter_uid)
            # Define Kobold A e Kobold B como ocultos
            self.combat_manager.set_combatant_visibility("Kobold A", is_hidden=True)
            self.combat_manager.set_combatant_visibility("Kobold B", is_hidden=True)

            self.assertEqual(len(self.combat_manager.hidden_combatants), 2)
            self.assertEqual(len(self.combat_manager.turn_order), 3)

            # Rola iniciativas
            self.combat_manager.roll_initiatives()
            self.combat_manager.next_turn()  # Rodada 1, Turno 1

            active_before = self.combat_manager.active_character
            self.assertIsNotNone(active_before)

            # Salva combate
            saved = self.combat_manager.save_combat_state(encounter_uid)
            self.assertTrue(saved)
            self.assertTrue(self.combat_manager.has_save_state(encounter_uid))

            # Reseta o combate
            self.combat_manager.reset_combat()
            self.assertEqual(len(self.combat_manager.combatants), 0)
            self.assertEqual(len(self.combat_manager.turn_order), 0)
            self.assertEqual(len(self.combat_manager.hidden_combatants), 0)

            # Restaura via load_combat_state
            loaded = self.combat_manager.load_combat_state(encounter_uid)
            self.assertTrue(loaded)

            # Valida que apenas visíveis estão em turn_order (3 participantes)
            self.assertEqual(len(self.combat_manager.turn_order), 3)
            self.assertEqual(len(self.combat_manager.hidden_combatants), 2)

            hidden_names = [c.name for c in self.combat_manager.hidden_combatants.values()]
            self.assertIn("Kobold A", hidden_names)
            self.assertIn("Kobold B", hidden_names)

            # Valida turno ativo restaurado
            self.assertEqual(self.combat_manager.current_turn_index, 1)
            self.assertEqual(self.combat_manager.round_number, 1)
            self.assertEqual(self.combat_manager.active_character.uid, active_before.uid)

        finally:
            if save_path.is_file():
                save_path.unlink()

    def test_initiative_modal_filters_hidden_combatants(self) -> None:
        """
        Valida que o InitiativeStagingModal filtra entidades ocultas,
        não gerando rolagens e listando estritamente os combatentes revelados.
        """
        session = SessionManager(combat_manager=self.combat_manager)
        self.combat_manager.start_combat(self.all_combatants)

        modal = InitiativeStagingModal(session_manager=session)
        modal.open()
        self.assertTrue(modal.is_open)

        # 1. Draft de iniciativas deve conter apenas os 3 participantes visíveis
        self.assertEqual(len(modal.draft_initiatives), 3)
        self.assertIn(self.pc1.uid, modal.draft_initiatives)
        self.assertIn(self.pc2.uid, modal.draft_initiatives)
        self.assertIn(self.mob_visible.uid, modal.draft_initiatives)
        self.assertNotIn(self.mob_hidden1.uid, modal.draft_initiatives)
        self.assertNotIn(self.mob_hidden2.uid, modal.draft_initiatives)

        # 2. Scroll list deve ter exatamente 3 itens
        self.assertEqual(len(modal.scroll_list.items), 3)
        for item in modal.scroll_list.items:
            self.assertFalse(item.is_hidden)


if __name__ == "__main__":
    unittest.main()
