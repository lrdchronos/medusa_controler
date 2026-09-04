import unittest
import sys
import json
import tempfile
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.builders.encounter_builder import EncounterBuilder, EncounterSerializer
from src.domain.loaders.encounter_loader import EncounterLoader
from src.domain.models.monster import Monster
from src.domain.models.playablechar import PlayableCharacter


class TestEncounterBuilder(unittest.TestCase):
    """Testes unitários para o EncounterBuilder e Serializador de Encontros."""

    def setUp(self):
        self.builder = EncounterBuilder()

    def test_fluent_creation_and_to_dict(self):
        self.builder.with_metadata(
            title="Emboscada na Floresta Sombria",
            description="Kobolds e um líder cultista atacam o grupo.",
        )
        self.builder.with_map("assets/images/maps/open_field_grass_trees.jpg")
        self.builder.with_grid(columns=30, feet_per_square=5)
        self.builder.with_environment(is_sunlight=True)

        self.builder.add_monster(
            monster_id="kobold",
            instance_name="Kobold 1",
            col=4,
            row=10,
            is_hidden=True,
        )
        self.builder.add_monster(
            monster_id="kobold",
            instance_name="Kobold 2",
            col=5,
            row=10,
            is_hidden=False,
        )
        self.builder.add_character(
            character_id="char_240820261336",
            col=12,
            row=2,
            is_hidden=False,
        )

        is_valid, errors = self.builder.validate()
        self.assertTrue(is_valid, f"Validação falhou com erros: {errors}")
        self.assertEqual(len(errors), 0)

        data = self.builder.to_dict()
        self.assertEqual(data["title"], "Emboscada na Floresta Sombria")
        self.assertEqual(data["description"], "Kobolds e um líder cultista atacam o grupo.")
        self.assertEqual(data["grid"]["columns"], 30)
        self.assertEqual(data["grid"]["feet_per_square"], 5)
        self.assertTrue(data["environment"]["is_sunlight"])
        self.assertEqual(len(data["combatants"]), 3)

        # Verifica combatente 0 (Monstro)
        c0 = data["combatants"][0]
        self.assertEqual(c0["entity_type"], "monster")
        self.assertEqual(c0["monster_id"], "kobold")
        self.assertEqual(c0["instance_name"], "Kobold 1")
        self.assertTrue(c0["is_hidden"])
        self.assertEqual(c0["position"], {"col": 4, "row": 10})

        # Verifica combatente 2 (PJ)
        c2 = data["combatants"][2]
        self.assertEqual(c2["entity_type"], "playable_character")
        self.assertEqual(c2["character_id"], "char_240820261336")
        self.assertFalse(c2["is_hidden"])
        self.assertEqual(c2["position"], {"col": 12, "row": 2})

    def test_validation_rules(self):
        # 1. Sem título
        self.builder.reset()
        self.builder._title = ""
        is_valid, errors = self.builder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("título" in err.lower() for err in errors))

        # 2. Sem combatentes
        self.builder.reset()
        self.builder.with_metadata(title="Teste")
        is_valid, errors = self.builder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("combatente" in err.lower() for err in errors))

        # 3. Grid inválido
        self.builder.add_monster("kobold")
        self.builder.with_grid(columns=0, feet_per_square=0)
        is_valid, errors = self.builder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("colunas" in err.lower() for err in errors))

    def test_save_and_roundtrip_with_encounter_loader(self):
        """Testa o ciclo completo: construção -> salvamento em arquivo -> leitura via EncounterLoader."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.builder.reset()
            self.builder.with_metadata(
                title="Encontro de Teste Roundtrip",
                description="Teste de integridade serializador/loader.",
                uid="encounter_test_roundtrip",
            )
            self.builder.with_map("assets/images/maps/open_field_grass_trees.jpg")
            self.builder.with_grid(columns=22, feet_per_square=5)
            self.builder.with_environment(is_sunlight=False)

            self.builder.add_monster(
                monster_id="kobold",
                instance_name="Kobold Sentinela",
                col=3,
                row=7,
                is_hidden=True,
            )
            self.builder.add_monster(
                monster_id="basic_cultist",
                instance_name="Cultista Arcano",
                col=6,
                row=9,
                is_hidden=False,
            )
            self.builder.add_character(
                character_id="char_240820261336",
                col=15,
                row=3,
                is_hidden=False,
            )

            # Salva no diretório temporário
            saved_path = self.builder.save_to_file(directory=tmp_dir)
            self.assertTrue(saved_path.is_file())

            # Carrega via EncounterLoader apontando para o diretório temporário
            loader = EncounterLoader(encounter_dirs=[tmp_dir, "creations/encounters"])
            loaded = loader.load_encounter(str(saved_path))

            self.assertEqual(loaded["uid"], "encounter_test_roundtrip")
            self.assertEqual(loaded["title"], "Encontro de Teste Roundtrip")
            self.assertEqual(loaded["grid"]["columns"], 22)
            self.assertEqual(len(loaded["combatants"]), 3)

            # Verifica instâncias
            combatants = loaded["combatants"]
            k = next(c for c in combatants if c.name == "Kobold Sentinela")
            self.assertIsInstance(k, Monster)
            self.assertTrue(k.is_hidden)
            self.assertEqual(k.position, {"x": 3, "y": 7})

            cult = next(c for c in combatants if c.name == "Cultista Arcano")
            self.assertIsInstance(cult, Monster)
            self.assertFalse(cult.is_hidden)
            self.assertEqual(cult.position, {"x": 6, "y": 9})

            pc = next(c for c in combatants if c.name == "Bolo de Morango")
            self.assertIsInstance(pc, PlayableCharacter)
            self.assertFalse(pc.is_hidden)
            self.assertEqual(pc.position, {"x": 15, "y": 3})

    def test_monster_counts_initial_state_zero(self):
        """Garante que todos os monstros carregados do catálogo iniciem com contagem estritamente 0."""
        from src.ui.dm.creator.config_form import CreatorConfigForm

        sample_monsters = [
            {"uid": "kobold", "name": "Kobold", "cr": 0.125},
            {"uid": "winged_kobold", "name": "Kobold Alado", "cr": 0.25},
            {"uid": "basic_cultist", "name": "Cultista", "cr": 0.125},
            {"uid": "red_dragon", "name": "Dragão Vermelho", "cr": 10},
        ]
        form = CreatorConfigForm(
            available_maps=[{"path": "dummy.jpg", "name": "Mapa"}],
            available_characters=[],
            available_monsters=sample_monsters,
        )

        counts = form.monster_counts
        for m in sample_monsters:
            mid = m["uid"]
            self.assertIn(mid, counts)
            self.assertEqual(counts[mid], 0, f"Monstro {mid} deveria iniciar com quantidade 0, mas iniciou com {counts[mid]}")

    def test_character_list_discrete_scroll_pagination_and_mouse_scroll(self):
        """Valida a paginação de 5 itens visíveis e rolagem discreta por mouse_scroll quando há 6+ PJs."""
        from src.ui.dm.creator.config_form import CreatorConfigForm

        many_characters = [
            {"uid": f"char_{i}", "name": f"Heroi {i}", "level": 3, "class_summary": "Guerreiro"}
            for i in range(8)  # 8 personagens
        ]
        form = CreatorConfigForm(
            available_maps=[{"path": "dummy.jpg", "name": "Mapa"}],
            available_characters=many_characters,
            available_monsters=[],
        )

        # 1. Deve acomodar 5 jogadores visíveis simultaneamente
        self.assertEqual(form.pc_scroll_list.visible_item_count, 5)
        self.assertEqual(form.pc_scroll_list.max_start_index, 8 - 5)  # 3
        self.assertEqual(form.pc_scroll_list.start_index, 0)

        # 2. Primeira página exibe os 5 primeiros
        vis_uids = [char["uid"] for _, char in form.pc_scroll_list.visible_items]
        self.assertEqual(vis_uids, ["char_0", "char_1", "char_2", "char_3", "char_4"])

        # 3. Simula desenho para configurar bounds da lista de PJs
        text_cache = {}
        form.draw_form(panel_w=640.0, top_y=670.0, text_cache=text_cache)

        # 4. Rola para baixo (scroll_y = -1.0) sobre a área de PJs
        pc_x, pc_y, pc_w, pc_h = form.pc_scroll_list.bounds
        inside_x = pc_x + pc_w / 2.0
        inside_y = pc_y - pc_h / 2.0

        scrolled = form.handle_mouse_scroll(x=inside_x, y=inside_y, scroll_x=0.0, scroll_y=-1.0)
        self.assertTrue(scrolled)
        self.assertEqual(form.pc_scroll_list.start_index, 1)

        vis_uids_scrolled = [char["uid"] for _, char in form.pc_scroll_list.visible_items]
        self.assertEqual(vis_uids_scrolled, ["char_1", "char_2", "char_3", "char_4", "char_5"])

        # 5. Rola além do limite máximo (clamp em 3)
        for _ in range(10):
            form.handle_mouse_scroll(x=inside_x, y=inside_y, scroll_x=0.0, scroll_y=-1.0)
        self.assertEqual(form.pc_scroll_list.start_index, 3)
        vis_uids_end = [char["uid"] for _, char in form.pc_scroll_list.visible_items]
        self.assertEqual(vis_uids_end, ["char_3", "char_4", "char_5", "char_6", "char_7"])

        # 6. Rola de volta para o topo (scroll_y = 1.0)
        for _ in range(10):
            form.handle_mouse_scroll(x=inside_x, y=inside_y, scroll_x=0.0, scroll_y=1.0)
        self.assertEqual(form.pc_scroll_list.start_index, 0)


if __name__ == "__main__":
    unittest.main()
