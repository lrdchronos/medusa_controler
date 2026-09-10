import unittest
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager, DisplayState
from src.domain.loaders.encounter_loader import EncounterLoader


class TestCombatSaveState(unittest.TestCase):

    def setUp(self) -> None:
        self.combat_manager = CombatManager()
        self.session_manager = SessionManager(combat_manager=self.combat_manager)
        self.encounter_uid = "encounter_01"

        # Garante limpeza prévia de saves de teste
        save_path = self.combat_manager.get_save_path(self.encounter_uid)
        if save_path.is_file():
            save_path.unlink()

    def tearDown(self) -> None:
        # Limpeza pós-teste
        save_path = self.combat_manager.get_save_path(self.encounter_uid)
        if save_path.is_file():
            save_path.unlink()

    def test_save_combat_state_serialization_mid_round(self) -> None:
        """
        Garante que o snapshot dinâmico do combate durante o turno 2 de uma rodada
        com dano aplicado, movimentação, condições e névoa seja gravado com precisão no schema.
        """
        self.combat_manager.load_encounter(self.encounter_uid)
        self.assertFalse(self.combat_manager.has_save_state(self.encounter_uid))

        # Rola iniciativas e avança para a Rodada 2, Turno 1
        self.combat_manager.roll_initiatives()
        num_combatants = len(self.combat_manager.turn_order)

        # Completa a Rodada 1 e avança para Rodada 2, Turno 1
        for _ in range(num_combatants):
            self.combat_manager.next_turn()  # Chega na Rodada 2, Turno 0
        self.combat_manager.next_turn()      # Chega na Rodada 2, Turno 1

        self.assertEqual(self.combat_manager.round_number, 2)
        self.assertEqual(self.combat_manager.current_turn_index, 1)

        # Aplica mutações táticas no estado de combate
        first_combatant = self.combat_manager.combatants[0]
        second_combatant = self.combat_manager.combatants[1]

        init_hp_1 = first_combatant.current_hp
        self.combat_manager.apply_damage(first_combatant.uid, 6)
        self.assertEqual(first_combatant.current_hp, max(0, init_hp_1 - 6))

        first_combatant.add_condition("poisoned")
        self.combat_manager.set_combatant_position(first_combatant.uid, 8, 4)
        self.combat_manager.set_combatant_visibility(second_combatant.uid, is_hidden=True)

        # Névoa de Guerra
        self.combat_manager.fog_manager.clear_all()
        self.combat_manager.fog_manager.add_fog(5, 2)
        self.combat_manager.fog_manager.add_fog(5, 3)

        # Executa salvamento
        saved = self.combat_manager.save_combat_state(self.encounter_uid)
        self.assertTrue(saved)
        self.assertTrue(self.combat_manager.has_save_state(self.encounter_uid))

        # Inspeciona arquivo JSON físico em creations/encounters/saves/
        save_path = self.combat_manager.get_save_path(self.encounter_uid)
        self.assertTrue(save_path.is_file())

        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["encounter_uid"], self.encounter_uid)
        self.assertEqual(data["round"], 2)
        self.assertEqual(data["current_turn_index"], self.combat_manager.current_turn_index)
        self.assertEqual(len(data["turn_order"]), len(self.combat_manager.turn_order))
        self.assertEqual(data["turn_order"], [c.uid for c in self.combat_manager.turn_order])

        # Valida Névoa de Guerra no Save
        fog_list = data["fog_of_war"]
        self.assertEqual(len(fog_list), 2)
        self.assertIn({"x": 5, "y": 2}, fog_list)
        self.assertIn({"x": 5, "y": 3}, fog_list)

        # Valida Combatentes no Save
        c_state_map = {c["uid"]: c for c in data["combatants_state"]}
        self.assertEqual(c_state_map[first_combatant.uid]["current_hp"], max(0, init_hp_1 - 6))
        self.assertIn("poisoned", c_state_map[first_combatant.uid]["conditions"])
        self.assertEqual(c_state_map[first_combatant.uid]["position"], {"x": 8, "y": 4})
        self.assertTrue(c_state_map[second_combatant.uid]["hidden"])

    def test_load_combat_state_restoration(self) -> None:
        """
        Garante a reconstrução exata da rodada, combatente ativo na vez, fita de turnos,
        HP reduzido, posições no grid, condições e células de névoa.
        """
        # 1. Monta um combate com estado alterado e salva
        self.combat_manager.load_encounter(self.encounter_uid)
        self.combat_manager.roll_initiatives()
        self.combat_manager.next_turn()  # Rodada 1, Turno 1

        active_before = self.combat_manager.active_character
        self.assertIsNotNone(active_before)

        target = self.combat_manager.combatants[0]
        self.combat_manager.apply_damage(target.uid, 5)
        target.add_condition("stunned")
        self.combat_manager.set_combatant_position(target.uid, 12, 10)
        self.combat_manager.fog_manager.clear_all()
        self.combat_manager.fog_manager.add_fog(7, 7)

        saved = self.combat_manager.save_combat_state(self.encounter_uid)
        self.assertTrue(saved)

        # 2. Reseta o CombatManager e restaura via load_combat_state
        self.combat_manager.reset_combat()
        self.assertEqual(len(self.combat_manager.combatants), 0)
        self.assertFalse(self.combat_manager.has_combat_started)

        notified = []
        self.combat_manager.add_listener(lambda: notified.append(True))

        loaded = self.combat_manager.load_combat_state(self.encounter_uid)
        self.assertTrue(loaded)
        self.assertGreater(len(notified), 0)

        # 3. Valida integridade do estado restaurado
        self.assertEqual(self.combat_manager.round_number, 1)
        self.assertEqual(self.combat_manager.current_turn_index, 1)
        self.assertEqual(self.combat_manager.active_character.uid, active_before.uid)

        restored_target = self.combat_manager.get_combatant(target.uid)
        self.assertIsNotNone(restored_target)
        self.assertEqual(restored_target.current_hp, target.current_hp)
        self.assertIn("stunned", restored_target.conditions)
        self.assertEqual(restored_target.position, {"x": 12, "y": 10})

        self.assertEqual(self.combat_manager.fog_manager.count, 1)
        self.assertTrue(self.combat_manager.fog_manager.is_fogged(7, 7))

    def test_has_save_state_and_delete_save_state(self) -> None:
        """Valida detecção has_save_state() e remoção segura delete_save_state()."""
        self.assertFalse(self.combat_manager.has_save_state(self.encounter_uid))

        self.combat_manager.load_encounter(self.encounter_uid)
        self.combat_manager.save_combat_state(self.encounter_uid)
        self.assertTrue(self.combat_manager.has_save_state(self.encounter_uid))

        self.combat_manager.delete_save_state(self.encounter_uid)
        self.assertFalse(self.combat_manager.has_save_state(self.encounter_uid))

    def test_idempotent_base_encounter_file(self) -> None:
        """Garante que o arquivo de encontro base JSON não seja alterado ao salvar o snapshot."""
        base_loader = EncounterLoader()
        resolved = base_loader.resolve_encounter_path(self.encounter_uid)
        self.assertIsNotNone(resolved)

        with open(resolved, "r", encoding="utf-8") as f:
            original_content = f.read()

        self.combat_manager.load_encounter(self.encounter_uid)
        self.combat_manager.roll_initiatives()
        self.combat_manager.apply_damage(self.combat_manager.combatants[0].uid, 10)
        self.combat_manager.save_combat_state(self.encounter_uid)

        with open(resolved, "r", encoding="utf-8") as f:
            after_save_content = f.read()

        self.assertEqual(original_content, after_save_content)

    def test_session_manager_integration(self) -> None:
        """Valida conveniências de save state através do SessionManager."""
        self.assertFalse(self.session_manager.has_encounter_save(self.encounter_uid))

        self.session_manager.start_encounter(self.encounter_uid)
        self.assertEqual(self.session_manager.display_state, DisplayState.COMBAT)

        self.combat_manager.save_combat_state(self.encounter_uid)
        self.assertTrue(self.session_manager.has_encounter_save(self.encounter_uid))

        self.session_manager.end_combat(DisplayState.IDLE)
        self.assertEqual(self.session_manager.display_state, DisplayState.IDLE)
        self.assertEqual(len(self.combat_manager.combatants), 0)

        # Retomada via SessionManager
        resumed = self.session_manager.resume_encounter_save(self.encounter_uid)
        self.assertTrue(resumed)
        self.assertEqual(self.session_manager.display_state, DisplayState.COMBAT)
        self.assertGreater(len(self.combat_manager.combatants), 0)

        # Exclusão via SessionManager
        self.session_manager.delete_encounter_save(self.encounter_uid)
        self.assertFalse(self.session_manager.has_encounter_save(self.encounter_uid))

    def test_dead_combatant_restoration(self) -> None:
        """Garante que combatentes abatidos (0 HP, is_alive=False) permaneçam abatidos ao restaurar."""
        self.combat_manager.load_encounter(self.encounter_uid)
        c = self.combat_manager.combatants[0]
        self.combat_manager.apply_damage(c.uid, 9999)  # Dano letal
        self.assertEqual(c.current_hp, 0)
        self.assertFalse(c.is_alive)

        self.combat_manager.save_combat_state(self.encounter_uid)
        self.combat_manager.reset_combat()

        self.combat_manager.load_combat_state(self.encounter_uid)
        restored = self.combat_manager.get_combatant(c.uid)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.current_hp, 0)
        self.assertFalse(restored.is_alive)


if __name__ == "__main__":
    unittest.main()
