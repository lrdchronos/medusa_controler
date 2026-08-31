import unittest
import sys
import os
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.dm.creator.text_input import TextInputWidget
from src.ui.dm.creator.config_form import CreatorConfigForm
from src.ui.dm.creator.tactical_stage import CreatorTacticalStage
from src.manager.session_manager import SessionManager


class TestCreatorOOD(unittest.TestCase):
    """Testes dos componentes modulares OOD do Criador de Encontros."""

    def test_text_input_typing_and_cursor(self):
        widget = TextInputWidget("test_input", placeholder="Nome...", initial_text="Dragon")
        self.assertEqual(widget.text, "Dragon")
        self.assertEqual(widget.cursor_pos, 6)

        # Foco e inserção
        widget.focus()
        self.assertTrue(widget.is_focused)

        # Digitação
        widget.handle_text_input(" Cave")
        self.assertEqual(widget.text, "Dragon Cave")
        self.assertEqual(widget.cursor_pos, 11)

        # Movimento do cursor
        widget.handle_key_press(arcade.key.LEFT, 0)
        self.assertEqual(widget.cursor_pos, 10)

        # Inserção no meio (entre 'v' e 'e')
        widget.handle_text_input("X")
        self.assertEqual(widget.text, "Dragon CavXe")

        # Home e End
        widget.handle_key_press(arcade.key.HOME, 0)
        self.assertEqual(widget.cursor_pos, 0)
        widget.handle_key_press(arcade.key.END, 0)
        self.assertEqual(widget.cursor_pos, len("Dragon CavXe"))


    def test_text_input_backspace_and_hold_repeat(self):
        widget = TextInputWidget("test_input", initial_text="Testing123")
        widget.focus()

        # Backspace unitário
        widget.handle_key_press(arcade.key.BACKSPACE, 0)
        self.assertEqual(widget.text, "Testing12")
        self.assertTrue(widget.backspace_held)

        # Simula segurar a tecla por mais de 0.35s (delay inicial)
        widget.update(0.40)
        # Deve ter apagado pelo menos mais 1 caractere no tick
        self.assertTrue(len(widget.text) < len("Testing12"))

        # Solta tecla
        widget.handle_key_release(arcade.key.BACKSPACE, 0)
        self.assertFalse(widget.backspace_held)

    def test_config_form_fields_and_validation(self):
        session = SessionManager()
        maps = session.list_available_maps()
        chars = session.list_available_characters()
        mons = session.list_available_monster_presets()

        form = CreatorConfigForm(available_maps=maps, available_characters=chars, available_monsters=mons)
        self.assertTrue(len(form.title_input.text) > 0)
        self.assertTrue(len(form.description_input.text) > 0)

        # Edição dos campos
        form.title_input.set_text("Novo Título OOD")
        form.description_input.set_text("Nova Descrição OOD de Batalha")
        self.assertEqual(form.title_input.text, "Novo Título OOD")
        self.assertEqual(form.description_input.text, "Nova Descrição OOD de Batalha")

        # Validação positiva
        is_valid, err = form.validate()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # Validação negativa com título vazio
        form.title_input.clear()
        is_valid, err = form.validate()
        self.assertFalse(is_valid)
        self.assertIn("título", err.lower())

    def test_config_form_strict_encapsulation_and_poka_yoke(self):
        """Testa o encapsulamento estrito (__), validações defensivas e cópias defensivas."""
        maps = [{"path": "map1.jpg", "name": "Mapa 1"}, {"path": "map2.jpg", "name": "Mapa 2"}]
        chars = [{"uid": "c1", "name": "Guerreiro"}, {"uid": "c2", "name": "Mago"}]
        mons = [{"uid": "m1", "name": "Goblin"}, {"uid": "m2", "name": "Dragão"}]

        form = CreatorConfigForm(available_maps=maps, available_characters=chars, available_monsters=mons)

        # 1. Atributos privados com duplo underscore
        self.assertTrue(hasattr(form, "_CreatorConfigForm__available_maps"))
        self.assertTrue(hasattr(form, "_CreatorConfigForm__columns"))
        self.assertTrue(hasattr(form, "_CreatorConfigForm__monster_counts"))
        self.assertTrue(hasattr(form, "_CreatorConfigForm__selected_character_uids"))

        # 2. Poka-Yoke em columns
        form.columns = 30
        self.assertEqual(form.columns, 30)
        form.columns = -10  # Deve fazer clamp defensivo no mínimo (1)
        self.assertEqual(form.columns, 1)

        # 3. Poka-Yoke em feet_per_square
        form.feet_per_square = 10
        self.assertEqual(form.feet_per_square, 10)
        form.feet_per_square = 0  # Deve fazer clamp defensivo no mínimo (1)
        self.assertEqual(form.feet_per_square, 1)

        # 4. Poka-Yoke em selected_map_index
        form.selected_map_index = 1
        self.assertEqual(form.selected_map_index, 1)
        form.selected_map_index = 5  # Modulo/wrapping dentro dos limites
        self.assertEqual(form.selected_map_index, 1)

        # 5. Cópias defensivas em listas mutáveis
        ext_maps = form.available_maps
        ext_maps.clear()
        self.assertEqual(len(form.available_maps), 2)  # Permanece intacto internamente

        ext_chars = form.available_characters
        ext_chars.clear()
        self.assertEqual(len(form.available_characters), 2)

        # 6. Métodos de conveniência para personagens e monstros
        self.assertTrue(form.is_character_selected("c1"))
        toggled = form.toggle_character("c1")
        self.assertFalse(toggled)
        self.assertFalse(form.is_character_selected("c1"))
        toggled_back = form.toggle_character("c1")
        self.assertTrue(toggled_back)
        self.assertTrue(form.is_character_selected("c1"))

        form.set_monster_count("m1", 4)
        self.assertEqual(form.get_monster_count("m1"), 4)
        form.increment_monster("m1", 2)
        self.assertEqual(form.get_monster_count("m1"), 6)
        form.decrement_monster("m1", 3)
        self.assertEqual(form.get_monster_count("m1"), 3)

        # 7. Consolidação de dados com get_config_data
        config_data = form.get_config_data()
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["columns"], 1)
        self.assertIn("c1", config_data["selected_character_uids"])
        self.assertEqual(config_data["monster_counts"]["m1"], 3)

    def test_tactical_stage_lifecycle(self):
        stage = CreatorTacticalStage()
        config_data = {
            "title": "Batalha Épica",
            "description": "Heróis enfrentam monstros.",
            "map_path": "assets/images/maps/open_field_grass_trees.jpg",
            "map_name": "Open Field",
            "columns": 25,
            "feet_per_square": 5,
            "is_sunlight": False,
            "selected_character_uids": {"char_240820261336"},
            "monster_counts": {"kobold": 2},
        }
        chars = [{"uid": "char_240820261336", "name": "Bolo de Morango"}]
        mons = [{"uid": "kobold", "name": "Kobold"}]

        stage.initialize(config_data, chars, mons)
        self.assertEqual(len(stage.staging_combatants), 3)

        # Alterna visibilidade
        pc = stage.staging_combatants[0]
        self.assertFalse(pc["is_hidden"])
        pc["is_hidden"] = True
        self.assertTrue(pc["is_hidden"])


if __name__ == "__main__":
    unittest.main()

