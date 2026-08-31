import unittest
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.entity import Entity
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster


class TestDomainModels(unittest.TestCase):

    def test_entity_encapsulation_and_defensive_copies(self):
        scores = {"STR": 16, "DEX": 14, "CON": 15, "INT": 10, "WIS": 12, "CHA": 8}
        char = PlayableCharacter(name="Guerreira", max_hp=20, ability_scores=scores, armor_class=16)

        # 1. Leitura via properties
        self.assertEqual(char.name, "Guerreira")
        self.assertEqual(char.max_hp, 20)
        self.assertEqual(char.current_hp, 20)
        self.assertEqual(char.armor_class, 16)
        self.assertTrue(char.is_alive)

        # 2. Modificador de iniciativa calculado via DEX (14 -> +2)
        self.assertEqual(char.initiative_mod, 2)

        # 3. Cópia defensiva: modificar o retorno não afeta o estado interno
        abilities = char.ability_scores
        abilities["DEX"] = 99
        self.assertEqual(char.ability_scores["DEX"], 14)
        self.assertEqual(char.initiative_mod, 2)

        # 4. Vitality dict copy
        vit = char.vitality
        vit["current_hp"] = -999
        self.assertEqual(char.current_hp, 20)

    def test_damage_and_heal_mechanics(self):
        entity = PlayableCharacter(name="Heroi", max_hp=30)
        entity.set_temporary_hp(10)

        # 1. Dano absorvido por temp_hp primeiro
        entity.take_damage(6)
        self.assertEqual(entity.temp_hp, 4)
        self.assertEqual(entity.current_hp, 30)

        # 2. Dano excedendo temp_hp afeta current_hp
        entity.take_damage(8)  # 4 de temp + 4 de vida
        self.assertEqual(entity.temp_hp, 0)
        self.assertEqual(entity.current_hp, 26)

        # 3. Cura com teto em max_hp
        entity.heal(10)
        self.assertEqual(entity.current_hp, 30)

        # 4. Dano letal zera vida e altera is_alive
        entity.take_damage(50)
        self.assertEqual(entity.current_hp, 0)
        self.assertFalse(entity.is_alive)

        # 5. Cura revive entidade
        entity.heal(5)
        self.assertEqual(entity.current_hp, 5)
        self.assertTrue(entity.is_alive)

    def test_playable_character_poka_yoke_level(self):
        pc = PlayableCharacter(name="Mago", level=5)
        self.assertEqual(pc.level, 5)

        # Tentativa de atribuir nível fora de [1, 20]
        pc.starter_level(25)
        self.assertEqual(pc.level, 5)

        pc.starter_level(0)
        self.assertEqual(pc.level, 5)

    def test_playable_character_resources(self):
        pc = PlayableCharacter(
            name="Barbaro",
            resources={"rage": {"max_uses": 3, "current_uses": 3, "recharge_on": "LONG_REST"}},
        )
        self.assertEqual(pc.resources["rage"]["current_uses"], 3)

        # Consome 1 carga
        success = pc.consume_resource("rage", 1)
        self.assertTrue(success)
        self.assertEqual(pc.resources["rage"]["current_uses"], 2)

        # Restaura recursos
        pc.restore_resources("LONG_REST")
        self.assertEqual(pc.resources["rage"]["current_uses"], 3)

    def test_monster_conditions_and_features(self):
        kobold_features = [
            {
                "name": "Sensibilidade à Luz Solar",
                "disadvantages": [{"type": "attack_roll", "self_condition": "in_sunlight"}],
            },
            {
                "name": "Tática de Matilha",
                "advantages": [{"type": "attack_roll", "target_condition": "has_engaged_ally"}],
            },
        ]
        monster = Monster(
            name="Kobold Guerreiro",
            max_hp=5,
            ability_scores={"DEX": 15},
            features=kobold_features,
            challenge_rating=0.125,
        )

        # Modificador de DEX: (15 - 10) // 2 = 2
        self.assertEqual(monster.initiative_mod, 2)

        # Vantagem contextual (aliado engajado)
        self.assertTrue(monster.check_advantage("attack_roll", {"target_condition": "has_engaged_ally"}))
        self.assertFalse(monster.check_advantage("attack_roll", {"target_condition": "alone"}))

        # Desvantagem contextual (sob a luz solar)
        self.assertTrue(monster.check_disadvantage("attack_roll", {"self_condition": "in_sunlight"}))
        self.assertFalse(monster.check_disadvantage("attack_roll", {"self_condition": "in_darkness"}))

    def test_vitality_percentage_and_status_brackets(self):
        monster = Monster(name="Goblin", max_hp=100)

        # 1. 100% de vida -> HEALTHY / Verde
        self.assertAlmostEqual(monster.hp_percentage, 100.0)
        self.assertAlmostEqual(monster.health_percentage, 100.0)
        self.assertAlmostEqual(monster.health_ratio, 1.0)
        self.assertEqual(monster.vitality_status, "HEALTHY")
        self.assertEqual(monster.vitality_color, (46, 204, 113, 255))
        self.assertEqual(monster.vitality["vitality_status"], "HEALTHY")
        self.assertAlmostEqual(monster.vitality["hp_percentage"], 100.0)

        # 2. 85% de vida (> 80%) -> HEALTHY / Verde
        monster.set_current_hp(85)
        self.assertAlmostEqual(monster.hp_percentage, 85.0)
        self.assertEqual(monster.vitality_status, "HEALTHY")
        self.assertEqual(monster.vitality_color, (46, 204, 113, 255))

        # 3. 80% de vida (30% < HP <= 80%) -> WOUNDED / Amarelo
        monster.set_current_hp(80)
        self.assertAlmostEqual(monster.hp_percentage, 80.0)
        self.assertEqual(monster.vitality_status, "WOUNDED")
        self.assertEqual(monster.vitality_color, (241, 196, 15, 255))

        # 4. 31% de vida (30% < HP <= 80%) -> WOUNDED / Amarelo
        monster.set_current_hp(31)
        self.assertAlmostEqual(monster.hp_percentage, 31.0)
        self.assertEqual(monster.vitality_status, "WOUNDED")
        self.assertEqual(monster.vitality_color, (241, 196, 15, 255))

        # 5. 30% de vida (0% < HP <= 30%) -> CRITICAL / Vermelho
        monster.set_current_hp(30)
        self.assertAlmostEqual(monster.hp_percentage, 30.0)
        self.assertEqual(monster.vitality_status, "CRITICAL")
        self.assertEqual(monster.vitality_color, (231, 76, 60, 255))

        # 6. 5% de vida (0% < HP <= 30%) -> CRITICAL / Vermelho
        monster.set_current_hp(5)
        self.assertAlmostEqual(monster.hp_percentage, 5.0)
        self.assertEqual(monster.vitality_status, "CRITICAL")
        self.assertEqual(monster.vitality_color, (231, 76, 60, 255))

        # 7. 0% de vida (HP <= 0) -> DEAD / Cinza
        monster.set_current_hp(0)
        self.assertAlmostEqual(monster.hp_percentage, 0.0)
        self.assertEqual(monster.vitality_status, "DEAD")
        self.assertEqual(monster.vitality_color, (120, 120, 120, 255))
        self.assertFalse(monster.is_alive)


if __name__ == "__main__":
    unittest.main()
