import unittest
import sys
import tempfile
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.entity import Entity, EntityType, DynamicToken
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster
from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager
from src.ui.utils.sprite_utils import SpriteFactory
from src.ui.dm.add_token_modal import AddTokenModal


class TestCombatTokenSpawn(unittest.TestCase):
    """
    Testes unitários e de integração para a funcionalidade de
    Inserção Dinâmica de Tokens durante o Combate (Mid-Combat Token Spawning),
    categoria Neutra/Feitiços e persistência completa de estado.
    """

    def setUp(self):
        self.combat_manager = CombatManager()
        self.combat_manager.load_encounter("encounter_240820261511")

    def test_entity_type_enum_and_properties(self):
        """Valida valores do enum EntityType e flags booleanas nas subclasses."""
        self.assertEqual(EntityType.PLAYER.value, "player")
        self.assertEqual(EntityType.MONSTER.value, "monster")
        self.assertEqual(EntityType.NEUTRAL.value, "neutral")

        pc = PlayableCharacter(name="Valeros", max_hp=30)
        self.assertEqual(pc.entity_type, EntityType.PLAYER)
        self.assertTrue(pc.is_player)
        self.assertFalse(pc.is_monster)
        self.assertFalse(pc.is_neutral)

        monster = Monster(name="Goblin", max_hp=7)
        self.assertEqual(monster.entity_type, EntityType.MONSTER)
        self.assertFalse(monster.is_player)
        self.assertTrue(monster.is_monster)
        self.assertFalse(monster.is_neutral)

        neutral = DynamicToken(name="Arma Espiritual", max_hp=1, armor_class=15, entity_type=EntityType.NEUTRAL)
        self.assertEqual(neutral.entity_type, EntityType.NEUTRAL)
        self.assertFalse(neutral.is_player)
        self.assertFalse(neutral.is_monster)
        self.assertTrue(neutral.is_neutral)

    def test_dynamic_token_mutation_and_combat_behavior(self):
        """Valida que DynamicToken se comporta como Entity com dano, cura e setters."""
        token = DynamicToken(
            name="Guardião Espiritual",
            max_hp=20,
            armor_class=14,
            entity_type=EntityType.NEUTRAL,
            token_sprite="assets/sprites/tokens/guardian.png"
        )
        self.assertEqual(token.name, "Guardião Espiritual")
        self.assertEqual(token.max_hp, 20)
        self.assertEqual(token.current_hp, 20)
        self.assertEqual(token.armor_class, 14)
        self.assertEqual(token.token_sprite, "assets/sprites/tokens/guardian.png")

        token.take_damage(5)
        self.assertEqual(token.current_hp, 15)
        token.heal(10)
        self.assertEqual(token.current_hp, 20)

        token.set_entity_type(EntityType.MONSTER)
        self.assertEqual(token.entity_type, EntityType.MONSTER)
        self.assertTrue(token.is_monster)

        token.set_token_sprite("assets/sprites/tokens/custom.png")
        self.assertEqual(token.token_sprite, "assets/sprites/tokens/custom.png")

    def test_spawn_combatant_before_combat_start(self):
        """Valida inserção de token antes da rolagem de iniciativas."""
        initial_count = len(self.combat_manager.combatants)
        token = DynamicToken(name="Armadilha de Espinhos", max_hp=10, armor_class=12, entity_type=EntityType.NEUTRAL)
        
        self.combat_manager.spawn_combatant(token, position=(4, 5))
        self.assertEqual(len(self.combat_manager.combatants), initial_count + 1)
        self.assertEqual(token.position, {"x": 4, "y": 5})
        self.assertIn(token, self.combat_manager.combatants)

    def test_spawn_combatant_mid_combat_slot_next(self):
        """Valida inserção de combatente no slot 'next' (imediatamente após o turno ativo)."""
        self.combat_manager.roll_initiatives()
        self.assertTrue(self.combat_manager.has_combat_started)
        
        active_before = self.combat_manager.active_character
        turn_idx_before = self.combat_manager.current_turn_index
        total_before = len(self.combat_manager.turn_order)

        # Cria e insere token para agir a seguir (slot="next")
        token = DynamicToken(name="Espada Espiritual", max_hp=5, armor_class=16, entity_type=EntityType.NEUTRAL)
        self.combat_manager.spawn_combatant(token, position=(6, 7), initiative_slot="next")

        # Verifica que o total de combatentes aumentou
        self.assertEqual(len(self.combat_manager.turn_order), total_before + 1)
        # O personagem ativo deve permanecer inalterado
        self.assertEqual(self.combat_manager.active_character, active_before)
        self.assertEqual(self.combat_manager.current_turn_index, turn_idx_before)

        # O novo token deve estar posicionado no índice turn_idx_before + 1
        self.assertEqual(self.combat_manager.turn_order[turn_idx_before + 1], token)

        # Ao avançar o turno, o novo token deve se tornar o personagem ativo
        self.combat_manager.next_turn()
        self.assertEqual(self.combat_manager.active_character, token)

    def test_spawn_combatant_mid_combat_slot_end(self):
        """Valida inserção de combatente no slot 'end' (final da rodada de iniciativas)."""
        self.combat_manager.roll_initiatives()
        total_before = len(self.combat_manager.turn_order)

        token = DynamicToken(name="Invocação de Lobo", max_hp=11, armor_class=13, entity_type=EntityType.NEUTRAL)
        self.combat_manager.spawn_combatant(token, position=(2, 3), initiative_slot="end")

        self.assertEqual(len(self.combat_manager.turn_order), total_before + 1)
        # O token deve ser o último da turn_order
        self.assertEqual(self.combat_manager.turn_order[-1], token)

    def test_save_and_load_combat_state_with_spawned_tokens(self):
        """Valida persistência e restauração completa de tokens dinâmicos no save state."""
        self.combat_manager.roll_initiatives()
        
        # Insere um token neutro dinâmico
        spell_token = DynamicToken(
            name="Muralha de Fogo",
            max_hp=25,
            armor_class=15,
            entity_type=EntityType.NEUTRAL,
            token_sprite="assets/sprites/tokens/firewall.png"
        )
        self.combat_manager.spawn_combatant(spell_token, position=(8, 9), initiative_slot="next")
        
        # Aplica dano ao token
        spell_token.take_damage(10)
        self.assertEqual(spell_token.current_hp, 15)

        # Salva o estado de combate
        save_success = self.combat_manager.save_combat_state()
        self.assertTrue(save_success)
        self.assertTrue(self.combat_manager.has_save_state())

        # Instancia novo CombatManager e restaura estado
        new_manager = CombatManager()
        load_success = new_manager.load_combat_state()
        self.assertTrue(load_success)
        self.assertTrue(new_manager.has_combat_started)

        # Verifica se o token dinâmico foi restaurado
        restored_token = new_manager.get_combatant(spell_token.uid)
        self.assertIsNotNone(restored_token)
        self.assertEqual(restored_token.name, "Muralha de Fogo")
        self.assertEqual(restored_token.max_hp, 25)
        self.assertEqual(restored_token.current_hp, 15)
        self.assertEqual(restored_token.armor_class, 15)
        self.assertEqual(restored_token.entity_type, EntityType.NEUTRAL)
        self.assertTrue(restored_token.is_neutral)
        self.assertEqual(restored_token.position, {"x": 8, "y": 9})
        self.assertEqual(restored_token.token_sprite, "assets/sprites/tokens/firewall.png")

        # Limpa arquivo de save residual
        new_manager.delete_save_state()
        self.assertFalse(new_manager.has_save_state())

    def test_add_token_modal_validation_and_confirm(self):
        """Valida lógica de validação e confirmação no AddTokenModal."""
        results = []
        modal = AddTokenModal(on_confirm=lambda data: results.append(data))

        modal.open()
        self.assertTrue(modal.is_open)

        # Confirmação com nome vazio deve gerar erro de validação
        modal.name_input.set_text("   ")
        modal._handle_confirm()
        self.assertIsNotNone(modal.validation_error)
        self.assertEqual(len(results), 0)

        # Confirmação com dados válidos
        modal.name_input.set_text("Tentáculo Negro")
        modal.selected_type = EntityType.NEUTRAL
        modal.hp_value = 18
        modal.ac_value = 12
        modal.initiative_slot = "next"

        modal._handle_confirm()
        self.assertFalse(modal.is_open)
        self.assertEqual(len(results), 1)
        data = results[0]
        self.assertEqual(data["name"], "Tentáculo Negro")
        self.assertEqual(data["entity_type"], EntityType.NEUTRAL)
        self.assertEqual(data["max_hp"], 18)
        self.assertEqual(data["current_hp"], 18)
        self.assertEqual(data["armor_class"], 12)
        self.assertEqual(data["initiative_slot"], "next")


if __name__ == "__main__":
    unittest.main()
