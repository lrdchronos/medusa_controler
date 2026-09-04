import unittest
import sys
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager
from src.ui.dm.creator.config_form import CreatorConfigForm, filter_monster_presets


class TestMonsterSearchAndScroll(unittest.TestCase):
    """
    Suíte de testes unitários para o Sistema de Busca e Rolagem (Scrollable List com Filtro)
    na listagem de monstros do Encounter Builder (DMWindow).
    """

    def setUp(self):
        self.sample_monsters = [
            {
                "uid": "kobold",
                "name": "Kobold",
                "cr": 0.125,
                "max_hp": 5,
                "armor_class": 12,
                "type": "Humanoid",
                "sub_type": "dragonborn",
                "tags": ["reptilian", "minion", "trapmaker"],
            },
            {
                "uid": "basic_culstist",
                "name": "Cultista",
                "cr": 0.125,
                "max_hp": 9,
                "armor_class": 12,
                "type": "Humanoide",
                "sub_type": "Any",
                "tags": ["fanatic", "spellcaster"],
            },
            {
                "uid": "red_dragon_wyrmling",
                "name": "Dragão Vermelho Jovem",
                "cr": 4.0,
                "max_hp": 75,
                "armor_class": 17,
                "type": "Dragon",
                "sub_type": "chromatic",
                "tags": ["fire", "boss"],
            },
        ]

    # --- 1. Testes de Filtragem por Substring Parcial (LIKE '%query%') ---

    def test_filter_exact_match(self):
        """Correspondência exata por nome."""
        res = filter_monster_presets(self.sample_monsters, "Kobold")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["uid"], "kobold")

    def test_filter_partial_match(self):
        """Correspondência parcial (substring) no meio ou início do nome."""
        res = filter_monster_presets(self.sample_monsters, "drag")
        self.assertEqual(len(res), 2)  # Dragão Vermelho Jovem e Kobold (sub_type dragonborn)
        uids = {m["uid"] for m in res}
        self.assertIn("red_dragon_wyrmling", uids)
        self.assertIn("kobold", uids)

    def test_filter_case_insensitive(self):
        """Busca insensível a maiúsculas/minúsculas."""
        res1 = filter_monster_presets(self.sample_monsters, "CULTISTA")
        res2 = filter_monster_presets(self.sample_monsters, "cultista")
        res3 = filter_monster_presets(self.sample_monsters, "cUlTiStA")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1, res2)
        self.assertEqual(res1, res3)

    def test_filter_empty_query(self):
        """Busca vazia ou com apenas espaços em branco restaura a listagem completa."""
        res_empty = filter_monster_presets(self.sample_monsters, "")
        res_spaces = filter_monster_presets(self.sample_monsters, "   ")
        self.assertEqual(len(res_empty), 3)
        self.assertEqual(len(res_spaces), 3)
        self.assertEqual(res_empty, self.sample_monsters)

    def test_filter_by_uid(self):
        """Busca pelo identificador único (uid)."""
        res = filter_monster_presets(self.sample_monsters, "basic_culstist")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "Cultista")

    def test_filter_by_type_and_subtype(self):
        """Busca por tipo (ex: Humanoide, Dragon) ou subtipo (ex: chromatic)."""
        res_type = filter_monster_presets(self.sample_monsters, "humanoid")
        self.assertEqual(len(res_type), 2)  # Humanoid e Humanoide

        res_subtype = filter_monster_presets(self.sample_monsters, "chromatic")
        self.assertEqual(len(res_subtype), 1)
        self.assertEqual(res_subtype[0]["uid"], "red_dragon_wyrmling")

    def test_filter_by_tags(self):
        """Busca por tags atribuídas ao monstro (ex: trapmaker, spellcaster, fire)."""
        res_trap = filter_monster_presets(self.sample_monsters, "trapmaker")
        self.assertEqual(len(res_trap), 1)
        self.assertEqual(res_trap[0]["uid"], "kobold")

        res_fire = filter_monster_presets(self.sample_monsters, "fire")
        self.assertEqual(len(res_fire), 1)
        self.assertEqual(res_fire[0]["uid"], "red_dragon_wyrmling")

    def test_filter_no_match(self):
        """Busca sem correspondência retorna lista vazia."""
        res = filter_monster_presets(self.sample_monsters, "Tarrasque Impossivel 999")
        self.assertEqual(len(res), 0)

    # --- 2. Preservação de Quantidades Selecionadas na Sessão ---

    def test_quantity_preservation_during_filtering(self):
        """Garante que as contagens selecionadas persistem intactas após sucessivas filtragens."""
        form = CreatorConfigForm(
            available_maps=[{"path": "dummy.jpg", "name": "Mapa"}],
            available_characters=[],
            available_monsters=self.sample_monsters,
        )

        # Configura quantidades personalizadas
        form.monster_counts["kobold"] = 5
        form.monster_counts["basic_culstist"] = 3
        form.monster_counts["red_dragon_wyrmling"] = 1

        # Aplica filtro para Cultista
        form.apply_monster_filter("cultista")
        self.assertEqual(len(form.filtered_monsters), 1)
        self.assertEqual(form.filtered_monsters[0]["uid"], "basic_culstist")
        # Quantidades devem continuar existindo no dicionário global
        self.assertEqual(form.monster_counts["kobold"], 5)
        self.assertEqual(form.monster_counts["basic_culstist"], 3)
        self.assertEqual(form.monster_counts["red_dragon_wyrmling"], 1)

        # Restaura listagem
        form.apply_monster_filter("")
        self.assertEqual(len(form.filtered_monsters), 3)
        self.assertEqual(form.monster_counts["kobold"], 5)
        self.assertEqual(form.monster_counts["basic_culstist"], 3)
        self.assertEqual(form.monster_counts["red_dragon_wyrmling"], 1)

    # --- 3. Integração com SmartTextInput e Botão de Lupa ---

    def test_search_input_typing_and_enter(self):
        """Digitação no SmartTextInput de busca e submissão por ENTER."""
        form = CreatorConfigForm(
            available_maps=[{"path": "dummy.jpg", "name": "Mapa"}],
            available_characters=[],
            available_monsters=self.sample_monsters,
        )

        form.search_input.focus()
        self.assertTrue(form.search_input.is_focused)

        form.handle_text_input("drag")
        self.assertEqual(form.search_input.text, "drag")

        # Pressiona ENTER no campo
        handled = form.handle_key_press(arcade.key.ENTER, 0)
        self.assertTrue(handled)
        self.assertEqual(form.search_query, "drag")
        self.assertEqual(len(form.filtered_monsters), 2)

    def test_search_magnifier_click(self):
        """Clique no botão com ícone de lupa [🔍] executa a consulta."""
        form = CreatorConfigForm(
            available_maps=[{"path": "dummy.jpg", "name": "Mapa"}],
            available_characters=[],
            available_monsters=self.sample_monsters,
        )

        panel_w = 640.0
        top_y = 670.0
        # Simula renderização para calcular bounds
        text_cache = {}
        form.draw_form(panel_w, top_y, text_cache)

        form.search_input.set_text("kobold")

        # Coordenada do botão de busca [🔍] (panel_w - 32, search_bar_y)
        mon_sec_y = (top_y - 18 - 24 - 18 - 22 - 18 - 24 - 20 - 24 - 28 - 28 - 16) - 10
        search_bar_y = mon_sec_y - 20
        btn_search_x = panel_w - 32

        form.handle_mouse_press(btn_search_x, search_bar_y, panel_w, top_y)
        self.assertEqual(form.search_query, "kobold")
        self.assertEqual(len(form.filtered_monsters), 1)

    # --- 4. Matemática de Rolagem (Scrollable Container e Mouse Scroll) ---

    def test_scrolling_math_and_mouse_scroll(self):
        """Valida o cálculo de max_start_index e a rolagem discreta via on_mouse_scroll."""
        many_monsters = [
            {
                "uid": f"mon_{i}",
                "name": f"Monstro {i}",
                "cr": 1,
                "max_hp": 20,
                "armor_class": 10,
            }
            for i in range(15)
        ]

        form = CreatorConfigForm(
            available_maps=[{"path": "dummy.jpg", "name": "Mapa"}],
            available_characters=[],
            available_monsters=many_monsters,
        )

        # Configura dimensões do container (altura 160: 160 // (38+4) = 3 visíveis -> max_start = 12)
        form.last_list_bounds = (16.0, 400.0, 608.0, 160.0)
        self.assertTrue(form.max_scroll > 0.0)
        self.assertEqual(form.start_index, 0)
        self.assertEqual(form.scroll_offset, 0.0)

        # Rola para baixo (scroll_y = -1) -> avança 1 item no start_index
        scrolled = form.handle_mouse_scroll(x=200.0, y=350.0, scroll_x=0.0, scroll_y=-1.0)
        self.assertTrue(scrolled)
        self.assertEqual(form.start_index, 1)
        self.assertEqual(form.scroll_offset, 42.0)  # 1 * (38 + 4)

        # Rola além do topo (scroll_y = 5) -> clamp em 0
        form.handle_mouse_scroll(x=200.0, y=350.0, scroll_x=0.0, scroll_y=5.0)
        self.assertEqual(form.start_index, 0)
        self.assertEqual(form.scroll_offset, 0.0)

        # Rola até o final
        for _ in range(20):
            form.handle_mouse_scroll(x=200.0, y=350.0, scroll_x=0.0, scroll_y=-1.0)
        self.assertEqual(form.start_index, form.scroll_list.max_start_index)
        self.assertEqual(form.scroll_offset, form.max_scroll)

        # Rolagem fora dos limites da lista não faz nada
        outside = form.handle_mouse_scroll(x=999.0, y=999.0, scroll_x=0.0, scroll_y=-1.0)
        self.assertFalse(outside)

    def test_session_manager_monster_loader_fields(self):
        """Verifica se list_available_monster_presets do SessionManager inclui os campos enriquecidos."""
        session = SessionManager()
        presets = session.list_available_monster_presets()
        self.assertTrue(len(presets) >= 2)
        for p in presets:
            self.assertIn("uid", p)
            self.assertIn("name", p)
            self.assertIn("type", p)
            self.assertIn("sub_type", p)
            self.assertIn("tags", p)
            self.assertIsInstance(p["tags"], list)


if __name__ == "__main__":
    unittest.main()
