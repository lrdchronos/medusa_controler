import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster


class TestCombatManager(unittest.TestCase):

    def setUp(self):
        self.manager = CombatManager()
        self.manager.load_encounter("encounter_240820261511")

    def test_load_encounter_state(self):
        self.assertEqual(len(self.manager.combatants), 5)
        self.assertFalse(self.manager.has_combat_started)
        self.assertIsNone(self.manager.active_character)

    def test_roll_initiatives_and_tiebreaker_sorting(self):
        # Override manual para testar ordenação e desempate rigorosamente
        # Kobold A (DEX=15 -> mod=+2), Kobold B (DEX=15 -> mod=+2), Bolo (DEX=12 -> mod=+1)
        manual = {
            "Kobold A": 18,
            "Kobold B": 18,
            "Kobold C": 12,
            "Cultista Líder": 15,
            "Bolo de Morango": 18,  # Empate em 18, mas mod é 1 (inferior ao mod 2 dos kobolds)
        }

        turn_order = self.manager.roll_initiatives(manual_rolls=manual)
        self.assertTrue(self.manager.has_combat_started)
        self.assertEqual(self.manager.current_turn_index, 0)
        self.assertEqual(self.manager.round_number, 1)

        # Ordem esperada:
        # 1. Kobold A ou Kobold B (Init 18, Mod +2)
        # 2. Kobold B ou Kobold A (Init 18, Mod +2)
        # 3. Bolo de Morango (Init 18, Mod +1) - desempate por Mod
        # 4. Cultista Líder (Init 15, Mod +1)
        # 5. Kobold C (Init 12, Mod +2)
        names = [c.name for c in turn_order]
        self.assertEqual(names[2], "Bolo de Morango")
        self.assertEqual(names[3], "Cultista Líder")
        self.assertEqual(names[4], "Kobold C")

        # O primeiro da lista é o personagem ativo
        self.assertEqual(self.manager.active_character.name, names[0])

    def test_circular_turn_progression(self):
        self.manager.roll_initiatives()
        num_combatants = len(self.manager.turn_order)

        self.assertEqual(self.manager.round_number, 1)
        self.assertEqual(self.manager.current_turn_index, 0)

        # Avança todos os turnos da rodada 1
        for i in range(1, num_combatants):
            self.manager.next_turn()
            self.assertEqual(self.manager.current_turn_index, i)
            self.assertEqual(self.manager.round_number, 1)

        # Próximo turno completa a volta circular e avança para a Rodada 2
        self.manager.next_turn()
        self.assertEqual(self.manager.current_turn_index, 0)
        self.assertEqual(self.manager.round_number, 2)

        # Retrocede turno
        self.manager.previous_turn()
        self.assertEqual(self.manager.current_turn_index, num_combatants - 1)
        self.assertEqual(self.manager.round_number, 1)

    def test_damage_and_heal_dispatch(self):
        pc = self.manager.get_combatant("Bolo de Morango")
        self.assertIsNotNone(pc)
        initial_hp = pc.current_hp

        # Aplica 10 de dano
        success = self.manager.apply_damage("Bolo de Morango", 10)
        self.assertTrue(success)
        self.assertEqual(pc.current_hp, initial_hp - 10)

        # Aplica 5 de cura
        success_heal = self.manager.apply_heal("Bolo de Morango", 5)
        self.assertTrue(success_heal)
        self.assertEqual(pc.current_hp, initial_hp - 5)

    def test_observer_listener_notifications(self):
        notified = []

        def on_change():
            notified.append(True)

        self.manager.add_listener(on_change)
        self.manager.roll_initiatives()
        self.assertGreater(len(notified), 0)

        prev_count = len(notified)
        self.manager.next_turn()
        self.assertGreater(len(notified), prev_count)

    def test_reset_combat_clears_state(self):
        self.manager.roll_initiatives()
        self.assertTrue(self.manager.has_combat_started)
        self.assertGreater(len(self.manager.combatants), 0)
        self.assertGreater(len(self.manager.turn_order), 0)

        notified = []
        self.manager.add_listener(lambda: notified.append(True))

        # Executa reset do combate
        self.manager.reset_combat()

        self.assertEqual(len(self.manager.combatants), 0)
        self.assertEqual(len(self.manager.turn_order), 0)
        self.assertEqual(self.manager.current_turn_index, -1)
        self.assertEqual(self.manager.round_number, 1)
        self.assertFalse(self.manager.has_combat_started)
        self.assertIsNone(self.manager.active_character)
        self.assertIsNone(self.manager.map_file)
        self.assertIsNone(self.manager.grid_manager)
        self.assertEqual(self.manager.encounter_uid, "")
        self.assertGreater(len(notified), 0)

    def test_reveal_combatant_inserts_as_next_turn(self):
        """Ao ser revelado no meio do combate, a criatura é inserida imediatamente na próxima posição da fila."""
        manual = {
            "Bolo de Morango": 20,
            "Cultista Líder": 15,
            "Kobold A": 12,
            "Kobold B": 10,
            "Kobold C": 5,
        }
        self.manager.roll_initiatives(manual_rolls=manual)
        self.assertTrue(self.manager.has_combat_started)
        self.assertEqual(self.manager.current_turn_index, 0)
        self.assertEqual(self.manager.active_character.name, "Bolo de Morango")

        # Oculta Kobold C (que está no índice 4)
        kobold_c = self.manager.get_combatant("Kobold C")
        self.assertIsNotNone(kobold_c)
        self.manager.set_combatant_visibility("Kobold C", is_hidden=True)
        self.assertTrue(kobold_c.is_hidden)

        # Revela Kobold C durante o turno ativo de Bolo (índice 0)
        notified = []
        self.manager.add_listener(lambda: notified.append(True))
        revealed = self.manager.reveal_combatant("Kobold C")

        self.assertEqual(revealed, kobold_c)
        self.assertFalse(kobold_c.is_hidden)
        self.assertGreater(len(notified), 0)

        # Deve ser o próximo na fila de iniciativas (posição 1)
        self.assertEqual(self.manager.turn_order[1], kobold_c)

        # Avançar o turno ativa imediatamente o combatente recém-revelado
        next_char = self.manager.next_turn()
        self.assertEqual(next_char, kobold_c)
        self.assertEqual(self.manager.active_character, kobold_c)

    def test_reveal_combatant_when_active_is_last_in_round(self):
        """Revelar combatente quando o turno ativo é o último da rodada insere no final antes do wrap."""
        manual = {
            "Bolo de Morango": 20,
            "Cultista Líder": 15,
            "Kobold A": 12,
            "Kobold B": 10,
            "Kobold C": 5,
        }
        self.manager.roll_initiatives(manual_rolls=manual)
        num_combatants = len(self.manager.turn_order)

        # Avança até o último combatente (Kobold C, índice 4)
        for _ in range(num_combatants - 1):
            self.manager.next_turn()
        self.assertEqual(self.manager.current_turn_index, num_combatants - 1)
        self.assertEqual(self.manager.active_character.name, "Kobold C")

        # Oculta o primeiro combatente (Bolo de Morango, índice 0) e revela
        bolo = self.manager.get_combatant("Bolo de Morango")
        bolo.set_hidden(True)

        self.manager.reveal_combatant(bolo.uid)
        self.assertFalse(bolo.is_hidden)

        # Bolo agora foi reposicionado para o final da fila (novo próximo após Kobold C)
        self.assertEqual(self.manager.turn_order[-1], bolo)

        # Avançar o turno passa para ele ainda na rodada 1
        active = self.manager.next_turn()
        self.assertEqual(active, bolo)

    def test_toggle_visibility_triggers_reveal_when_hidden(self):
        """Alternar visibilidade de uma criatura oculta invoca o pipeline de revelação."""
        manual = {
            "Bolo de Morango": 20,
            "Cultista Líder": 15,
            "Kobold A": 12,
            "Kobold B": 10,
            "Kobold C": 5,
        }
        self.manager.roll_initiatives(manual_rolls=manual)
        kobold = self.manager.get_combatant("Kobold B")
        self.assertIsNotNone(kobold)

        # Oculta Kobold B
        self.manager.set_combatant_visibility("Kobold B", is_hidden=True)
        self.assertTrue(kobold.is_hidden)

        # Toggle -> revela e posiciona como próximo (índice 1)
        res = self.manager.toggle_combatant_visibility("Kobold B")
        self.assertFalse(res)  # False significa que is_hidden agora é False
        self.assertFalse(kobold.is_hidden)
        self.assertEqual(self.manager.turn_order[1], kobold)


if __name__ == "__main__":
    unittest.main()
