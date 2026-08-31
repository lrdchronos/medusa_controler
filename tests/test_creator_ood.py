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
