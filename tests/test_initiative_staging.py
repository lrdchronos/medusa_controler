import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster


class TestInitiativeStagingAndVisibility(unittest.TestCase):
    """Testes unitários para o fluxo de Staging de Iniciativas, Visibilidade e Posicionamento."""

    def setUp(self):
        self.manager = CombatManager()
        self.manager.load_encounter("encounter_01")

    def test_generate_draft_initiatives_does_not_mutate_combat_state(self):
        # 1. Antes de aplicar, o combate não deve estar iniciado
        self.assertFalse(self.manager.has_combat_started)
        self.assertIsNone(self.manager.active_character)

        # 2. Gera rascunho temporário
        draft = self.manager.generate_draft_initiatives()
        self.assertEqual(len(draft), len(self.manager.combatants))

        # 3. O estado do combate continua inalterado (staging puro)
        self.assertFalse(self.manager.has_combat_started)
        self.assertIsNone(self.manager.active_character)
        self.assertEqual(self.manager.current_turn_index, -1)

        # 4. Todos os combatentes têm um score no draft
        for c in self.manager.combatants:
            self.assertIn(c.uid, draft)
            # 1 <= 1d20 <= 20 + initiative_mod
            self.assertGreaterEqual(draft[c.uid], 1 + c.initiative_mod)
            self.assertLessEqual(draft[c.uid], 20 + c.initiative_mod)

    def test_apply_initiatives_with_tiebreaker(self):
        # Cria rascunho com empates controlados
        # Kobold A (DEX mod +2) e Bolo (DEX mod +1) ambos com score 18
        # Kobold B (DEX mod +2) com score 15, Cultista (DEX mod +1) com score 15
        kobold_a = self.manager.get_combatant("Kobold A")
        kobold_b = self.manager.get_combatant("Kobold B")
        kobold_c = self.manager.get_combatant("Kobold C")
        cultist = self.manager.get_combatant("Cultista Líder")
        bolo = self.manager.get_combatant("Bolo de Morango")

        custom_scores = {
            kobold_a.uid: 18,
            bolo.uid: 18,        # Empate com Kobold A, mas DEX mod é +1 (menor que +2 do Kobold)
            kobold_b.uid: 15,
            cultist.uid: 15,     # Empate com Kobold B, mas DEX mod é +1
            kobold_c.uid: 8,
        }

        # Aplica iniciativas consolidadas
        self.manager.apply_initiatives(custom_scores)

        # Estado oficial de combate agora está ativo
        self.assertTrue(self.manager.has_combat_started)
        self.assertEqual(self.manager.current_turn_index, 0)
        self.assertEqual(self.manager.round_number, 1)

        turn_names = [c.name for c in self.manager.turn_order]
        # Ordem esperada:
        # 1. Kobold A (Score 18, Mod +2)
        # 2. Bolo de Morango (Score 18, Mod +1)
        # 3. Kobold B (Score 15, Mod +2)
        # 4. Cultista Líder (Score 15, Mod +1)
        # 5. Kobold C (Score 8, Mod +2)
        self.assertEqual(turn_names[0], "Kobold A")
        self.assertEqual(turn_names[1], "Bolo de Morango")
        self.assertEqual(turn_names[2], "Kobold B")
        self.assertEqual(turn_names[3], "Cultista Líder")
        self.assertEqual(turn_names[4], "Kobold C")

    def test_visibility_toggle_and_set(self):
        kobold = self.manager.get_combatant("Kobold A")
        self.assertFalse(kobold.is_hidden)

        # Alterna para oculto
        new_state = self.manager.toggle_combatant_visibility("Kobold A")
        self.assertTrue(new_state)
        self.assertTrue(kobold.is_hidden)

        # Alterna de volta para visível
        new_state2 = self.manager.toggle_combatant_visibility("Kobold A")
        self.assertFalse(new_state2)
        self.assertFalse(kobold.is_hidden)

        # Define explicitamente
        self.manager.set_combatant_visibility("Kobold A", True)
        self.assertTrue(kobold.is_hidden)

    def test_combatant_position_update(self):
        kobold = self.manager.get_combatant("Kobold A")
        self.manager.set_combatant_position(kobold.uid, 7, 12)
        self.assertEqual(kobold.position, {"x": 7, "y": 12})


if __name__ == "__main__":
    unittest.main()
