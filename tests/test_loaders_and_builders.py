import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.loaders.character_loader import CharacterLoader
from src.domain.loaders.monster_loader import MonsterLoader
from src.domain.loaders.encounter_loader import EncounterLoader
from src.domain.builders.character_builder import CharacterBuilder
from src.domain.builders.monster_builder import MonsterBuilder
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster


class TestLoadersAndBuilders(unittest.TestCase):

    def test_character_loader_existing_file(self):
        loader = CharacterLoader()
        char = loader.load_by_id("char_240820261336")

        self.assertIsInstance(char, PlayableCharacter)
        self.assertEqual(char.name, "Bolo de Morango")
        self.assertEqual(char.level, 3)
        self.assertEqual(char.max_hp, 38)
        self.assertEqual(char.current_hp, 38)
        self.assertEqual(char.ability_scores["STR"], 18)
        self.assertEqual(char.ability_scores["DEX"], 12)
        # DEX mod = (12 - 10) // 2 = 1
        self.assertEqual(char.initiative_mod, 1)
        self.assertIn("rage", char.resources)
        self.assertEqual(char.resources["rage"]["current_uses"], 3)

    def test_monster_loader_existing_presets(self):
        loader = MonsterLoader()

        # Kobold
        kobold = loader.create_instance("kobold", instance_name="Kobold Alpha", position={"x": 2, "y": 3})
        self.assertIsInstance(kobold, Monster)
        self.assertEqual(kobold.name, "Kobold Alpha")
        self.assertEqual(kobold.max_hp, 5)
        self.assertEqual(kobold.armor_class, 12)
        self.assertEqual(kobold.ability_scores["DEX"], 15)
        self.assertEqual(kobold.initiative_mod, 2)
        self.assertEqual(kobold.position, {"x": 2, "y": 3})

        # Cultist (tolerante à grafia basic_culstist / basic_cultist)
        cultist = loader.create_instance("basic_cultist", instance_name="Cultista Chefe")
        self.assertIsInstance(cultist, Monster)
        self.assertEqual(cultist.name, "Cultista Chefe")
        self.assertEqual(cultist.max_hp, 9)
        self.assertEqual(cultist.armor_class, 12)

    def test_encounter_loader_full_encounter(self):
        loader = EncounterLoader()
        enc = loader.load_encounter("encounter_240820261511")

        self.assertIn("Emboscada", enc["title"])
        self.assertEqual(len(enc["combatants"]), 5)

        # 3 Kobolds, 1 Cultist, 1 PC
        names = [c.name for c in enc["combatants"]]
        self.assertIn("Kobold A", names)
        self.assertIn("Kobold B", names)
        self.assertIn("Kobold C", names)
        self.assertIn("Cultista Líder", names)
        self.assertIn("Bolo de Morango", names)

    def test_fluent_builders(self):
        pc = (
            CharacterBuilder()
            .with_name("Legolas")
            .with_vitality(28)
            .with_ability_scores({"DEX": 18, "STR": 12})
            .with_armor_class(15)
            .with_level(4)
            .build()
        )
        self.assertEqual(pc.name, "Legolas")
        self.assertEqual(pc.max_hp, 28)
        self.assertEqual(pc.initiative_mod, 4)  # (18 - 10) // 2 = 4
        self.assertEqual(pc.level, 4)

        mon = (
            MonsterBuilder()
            .with_name("Goblin Arqueiro")
            .with_vitality(7)
            .with_ability_scores({"DEX": 14})
            .with_armor_class(13)
            .with_challenge_rating(0.25)
            .build()
        )
        self.assertEqual(mon.name, "Goblin Arqueiro")
        self.assertEqual(mon.initiative_mod, 2)
        self.assertEqual(mon.challenge_rating, 0.25)


if __name__ == "__main__":
    unittest.main()
