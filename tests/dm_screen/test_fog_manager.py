import unittest
import json
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.fog_manager import FogManager
from src.domain.builders.encounter_builder import EncounterBuilder
from src.domain.loaders.encounter_loader import EncounterLoader
from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager
from src.ui.dm.fog_control_panel import FogControlPanel, FogTool, BrushMode


class TestFogManager(unittest.TestCase):
    """Testes unitários para o modelo de domínio FogManager."""

    def setUp(self):
        self.fog = FogManager()

    def test_initial_state_empty(self):
        """Testa estado inicial vazio do FogManager."""
        self.assertEqual(self.fog.count, 0)
        self.assertFalse(self.fog.is_fogged(0, 0))
        self.assertFalse(self.fog.is_fogged(5, 10))
        self.assertEqual(self.fog.get_fogged_cells(), set())
        self.assertEqual(self.fog.export_state(), [])

    def test_add_and_remove_fog(self):
        """Testa adição e remoção unitária de células de névoa."""
        self.fog.add_fog(2, 3)
        self.assertTrue(self.fog.is_fogged(2, 3))
        self.assertFalse(self.fog.is_fogged(2, 4))
        self.assertEqual(self.fog.count, 1)

        self.fog.add_fog(5, 7)
        self.assertEqual(self.fog.count, 2)
        self.assertTrue(self.fog.is_fogged(5, 7))

        self.fog.remove_fog(2, 3)
        self.assertFalse(self.fog.is_fogged(2, 3))
        self.assertTrue(self.fog.is_fogged(5, 7))
        self.assertEqual(self.fog.count, 1)

    def test_idempotency_in_brush_painting(self):
        """Garante que pintar repetidamente a mesma célula não duplique dados no conjunto."""
        for _ in range(10):
            self.fog.add_fog(4, 4)

        self.assertEqual(self.fog.count, 1)
        self.assertEqual(self.fog.get_fogged_cells(), {(4, 4)})

        # Remover célula não-existente não altera o estado
        self.fog.remove_fog(99, 99)
        self.assertEqual(self.fog.count, 1)

    def test_fill_all_and_clear_all(self):
        """Testa preenchimento global e limpeza total do grid."""
        cols, rows = 6, 4
        self.fog.fill_all(cols, rows)
        self.assertEqual(self.fog.count, cols * rows)

        for c in range(cols):
            for r in range(rows):
                self.assertTrue(self.fog.is_fogged(c, r))

        self.assertFalse(self.fog.is_fogged(6, 0))
        self.assertFalse(self.fog.is_fogged(0, 4))

        self.fog.clear_all()
        self.assertEqual(self.fog.count, 0)
        self.assertFalse(self.fog.is_fogged(0, 0))

    def test_serialization_and_deserialization(self):
        """Testa exportação para JSON e carregamento a partir de dicionários estruturados."""
        cells_to_add = [(0, 0), (2, 1), (1, 3)]
        for c, r in cells_to_add:
            self.fog.add_fog(c, r)

        exported = self.fog.export_state()
        self.assertEqual(len(exported), 3)
        # Ordenado por (row, col)
        self.assertEqual(exported, [{"x": 0, "y": 0}, {"x": 2, "y": 1}, {"x": 1, "y": 3}])

        new_fog = FogManager()
        new_fog.load_state(exported)
        self.assertEqual(new_fog.count, 3)
        for c, r in cells_to_add:
            self.assertTrue(new_fog.is_fogged(c, r))

    def test_load_state_defensive_validation(self):
        """Testa robustez defensiva (Poka-Yoke) ao carregar dados imperfeitos ou com formatos alternativos."""
        raw_data = [
            {"x": 1, "y": 2},
            {"col": 3, "row": 4},  # Chaves alternativas
            {"x": "5", "y": "6"},  # Strings numéricas
            {"invalid": "data"},    # Ignorado
            "not_a_dict",          # Ignorado
            {"x": "abc", "y": 1},   # Ignorado
        ]
        self.fog.load_state(raw_data)
        self.assertEqual(self.fog.count, 3)
        self.assertTrue(self.fog.is_fogged(1, 2))
        self.assertTrue(self.fog.is_fogged(3, 4))
        self.assertTrue(self.fog.is_fogged(5, 6))

        # Carga com None ou vazio limpa o estado
        self.fog.load_state([])
        self.assertEqual(self.fog.count, 0)

    def test_observer_pattern_notifications(self):
        """Testa se ouvintes inscritos são notificados a cada alteração de estado."""
        call_count = 0

        def listener():
            nonlocal call_count
            call_count += 1

        self.fog.add_listener(listener)

        self.fog.add_fog(1, 1)
        self.assertEqual(call_count, 1)

        # Adicionar a mesma célula novamente não deve disparar notificação redundante
        self.fog.add_fog(1, 1)
        self.assertEqual(call_count, 1)

        self.fog.remove_fog(1, 1)
        self.assertEqual(call_count, 2)

        self.fog.fill_all(3, 3)
        self.assertEqual(call_count, 3)

        self.fog.clear_all()
        self.assertEqual(call_count, 4)

        self.fog.load_state([{"x": 0, "y": 0}])
        self.assertEqual(call_count, 5)

        # Unsubscribe
        self.fog.remove_listener(listener)
        self.fog.add_fog(2, 2)
        self.assertEqual(call_count, 5)


class TestEncounterFogIntegration(unittest.TestCase):
    """Testes de integração para Builder, Loader e CombatManager com Fog of War."""

    def test_encounter_builder_with_fog_of_war(self):
        """Testa inclusão de névoa de guerra no EncounterBuilder."""
        builder = EncounterBuilder()
        builder.with_metadata("Encontro com Névoa")
        builder.with_map("assets/images/maps/open_field_grass_trees.jpg", "image")
        builder.add_monster("kobold", "Kobold 1", 2, 2)
        builder.with_fog_of_war([{"x": 0, "y": 0}, {"x": 1, "y": 0}])

        enc_dict = builder.to_dict()
        self.assertIn("fog_of_war", enc_dict)
        self.assertEqual(len(enc_dict["fog_of_war"]), 2)
        self.assertEqual(enc_dict["fog_of_war"][0], {"x": 0, "y": 0})
        self.assertEqual(enc_dict["fog_of_war"][1], {"x": 1, "y": 0})

    def test_encounter_loader_parses_fog_of_war_and_handles_missing(self):
        """Testa se EncounterLoader lê fog_of_war e assume [] quando ausente."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # 1. Arquivo sem fog_of_war
            file_no_fog = tmp_path / "enc_no_fog.json"
            data_no_fog = {
                "uid": "enc_no_fog",
                "title": "Sem Névoa",
                "map_type": "image",
                "map_source": "assets/images/maps/open_field_grass_trees.jpg",
                "grid": {"columns": 25, "feet_per_square": 5},
                "combatants": [],
            }
            with open(file_no_fog, "w", encoding="utf-8") as f:
                json.dump(data_no_fog, f)

            # 2. Arquivo com fog_of_war
            file_with_fog = tmp_path / "enc_with_fog.json"
            data_with_fog = {
                "uid": "enc_with_fog",
                "title": "Com Névoa",
                "map_type": "image",
                "map_source": "assets/images/maps/open_field_grass_trees.jpg",
                "grid": {"columns": 25, "feet_per_square": 5},
                "fog_of_war": [{"x": 10, "y": 5}, {"x": 11, "y": 5}],
                "combatants": [],
            }
            with open(file_with_fog, "w", encoding="utf-8") as f:
                json.dump(data_with_fog, f)

            loader = EncounterLoader(encounter_dirs=[str(tmp_path)])

            res_no_fog = loader.load_encounter(str(file_no_fog))
            self.assertIn("fog_of_war", res_no_fog)
            self.assertEqual(res_no_fog["fog_of_war"], [])

            res_with_fog = loader.load_encounter(str(file_with_fog))
            self.assertIn("fog_of_war", res_with_fog)
            self.assertEqual(res_with_fog["fog_of_war"], [{"x": 10, "y": 5}, {"x": 11, "y": 5}])

    def test_combat_manager_fog_lifecycle_and_save(self):
        """Testa ciclo de vida do FogManager dentro do CombatManager e persistência em disco."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            enc_file = tmp_path / "encounter_fog_test.json"
            enc_data = {
                "uid": "encounter_fog_test",
                "title": "Teste de Névoa CombatManager",
                "map_type": "image",
                "map_source": "assets/images/maps/open_field_grass_trees.jpg",
                "grid": {"columns": 20, "feet_per_square": 5},
                "fog_of_war": [{"x": 1, "y": 1}],
                "combatants": [
                    {
                        "entity_type": "monster",
                        "monster_id": "kobold",
                        "instance_name": "Kobold Teste",
                        "position": {"col": 5, "row": 5},
                    }
                ],
            }
            with open(enc_file, "w", encoding="utf-8") as f:
                json.dump(enc_data, f)

            loader = EncounterLoader(encounter_dirs=[str(tmp_path)])
            cm = CombatManager(encounter_loader=loader)

            # 1. Carrega encontro
            cm.load_encounter("encounter_fog_test")
            self.assertTrue(cm.fog_manager.is_fogged(1, 1))
            self.assertEqual(cm.fog_manager.count, 1)

            # 2. Modifica a névoa durante o combate
            cm.fog_manager.add_fog(2, 2)
            cm.fog_manager.add_fog(3, 3)
            self.assertEqual(cm.fog_manager.count, 3)

            # 3. Salva no arquivo
            saved = cm.save_fog_to_encounter_file()
            self.assertTrue(saved)

            # 4. Verifica o arquivo no disco
            with open(enc_file, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            self.assertEqual(len(disk_data["fog_of_war"]), 3)
            self.assertIn({"x": 1, "y": 1}, disk_data["fog_of_war"])
            self.assertIn({"x": 2, "y": 2}, disk_data["fog_of_war"])
            self.assertIn({"x": 3, "y": 3}, disk_data["fog_of_war"])

            # 5. Reset limpa a névoa
            cm.reset_combat()
            self.assertEqual(cm.fog_manager.count, 0)


class TestFogControlPanel(unittest.TestCase):
    """Testes unitários para o componente de interface FogControlPanel."""

    def setUp(self):
        self.fog = FogManager()
        self.save_called = False

        def mock_save() -> bool:
            self.save_called = True
            return True

        self.panel = FogControlPanel(
            fog_manager=self.fog,
            dimensions_provider=lambda: (10, 8),
            save_callback=mock_save,
        )

    def test_initial_panel_state(self):
        self.assertEqual(self.panel.active_tool, FogTool.NONE)
        self.assertFalse(self.panel.is_tool_active)
        self.assertEqual(self.panel.brush_mode, BrushMode.SINGLE)
        self.assertFalse(self.panel.is_collapsed)
        self.assertEqual(self.panel.header_height, 28.0)
        self.assertEqual(self.panel.body_height, 80.0)
        self.assertEqual(self.panel.total_height, 108.0)

    def test_panel_tool_selection_and_toggling(self):
        self.panel.active_tool = FogTool.ADD
        self.assertTrue(self.panel.is_tool_active)
        self.assertEqual(self.panel.active_tool, FogTool.ADD)

        self.panel.active_tool = FogTool.REVEAL
        self.assertTrue(self.panel.is_tool_active)
        self.assertEqual(self.panel.active_tool, FogTool.REVEAL)

        self.panel.active_tool = FogTool.NONE
        self.assertFalse(self.panel.is_tool_active)

    def test_panel_brush_mode_toggling(self):
        self.panel.brush_mode = BrushMode.CONTINUOUS
        self.assertEqual(self.panel.brush_mode, BrushMode.CONTINUOUS)

        self.panel.brush_mode = BrushMode.SINGLE
        self.assertEqual(self.panel.brush_mode, BrushMode.SINGLE)

    def test_panel_layout_two_rows_geometry(self):
        """Valida que o layout em 2 linhas possui geometria desacoplada sem sobreposições."""
        panel_w = 560.0
        top_y = 600.0
        layout = self.panel._compute_layout(panel_w, top_y)

        # Alturas e dimensões
        self.assertEqual(layout.btn_h, 28.0)
        self.assertEqual(layout.panel_h, 108.0)

        # Linha 1 e Linha 2 possuem Ys diferentes e isolados
        self.assertTrue(layout.row1_y > layout.row2_y)
        vertical_distance = layout.row1_y - layout.row2_y
        self.assertGreaterEqual(vertical_distance, layout.btn_h + 8.0)

        # Linha 1: 4 botões na mesma baseline
        for rect in [layout.btn_fill_rect, layout.btn_clear_rect, layout.btn_add_rect, layout.btn_reveal_rect]:
            cx, cy, w, h = rect
            self.assertEqual(cy, layout.row1_y)
            self.assertEqual(h, layout.btn_h)
            self.assertGreater(w, 0.0)

        # Linha 2: 2 botões na mesma baseline
        for rect in [layout.btn_mode_rect, layout.btn_save_rect]:
            cx, cy, w, h = rect
            self.assertEqual(cy, layout.row2_y)
            self.assertEqual(h, layout.btn_h)
            self.assertGreater(w, 0.0)

        # Botão salvar não colide em Y com Linha 1
        save_top = layout.btn_save_rect[1] + layout.btn_save_rect[3] / 2.0
        row1_bottom = layout.row1_y - layout.btn_h / 2.0
        self.assertLessEqual(save_top, row1_bottom - 8.0)

        # next_y calculado fielmente
        self.assertEqual(layout.next_y, self.panel.get_next_y(top_y))

    def test_panel_handle_click_row1_buttons(self):
        """Valida acionamento individual dos botões da Linha 1."""
        panel_w = 560.0
        top_y = 600.0
        layout = self.panel._compute_layout(panel_w, top_y)

        # 1. Clique em [ Cobrir Tudo ]
        fill_cx, fill_cy, _, _ = layout.btn_fill_rect
        self.assertEqual(self.fog.count, 0)
        consumed = self.panel.handle_click(fill_cx, fill_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.fog.count, 80)  # 10x8

        # 2. Clique em [ Revelar Tudo ]
        clr_cx, clr_cy, _, _ = layout.btn_clear_rect
        consumed = self.panel.handle_click(clr_cx, clr_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.fog.count, 0)

        # 3. Clique em [ ✏️ Adicionar ] (Toggle)
        add_cx, add_cy, _, _ = layout.btn_add_rect
        self.assertEqual(self.panel.active_tool, FogTool.NONE)
        consumed = self.panel.handle_click(add_cx, add_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.panel.active_tool, FogTool.ADD)

        # Toggle off
        consumed = self.panel.handle_click(add_cx, add_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.panel.active_tool, FogTool.NONE)

        # 4. Clique em [ 🧹 Revelar ] (Toggle)
        rev_cx, rev_cy, _, _ = layout.btn_reveal_rect
        consumed = self.panel.handle_click(rev_cx, rev_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.panel.active_tool, FogTool.REVEAL)

    def test_panel_handle_click_row2_buttons(self):
        """Valida acionamento individual dos botões da Linha 2."""
        panel_w = 560.0
        top_y = 600.0
        layout = self.panel._compute_layout(panel_w, top_y)

        # 1. Alternador de Modo de Pincel
        mode_cx, mode_cy, _, _ = layout.btn_mode_rect
        self.assertEqual(self.panel.brush_mode, BrushMode.SINGLE)
        consumed = self.panel.handle_click(mode_cx, mode_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.panel.brush_mode, BrushMode.CONTINUOUS)

        consumed = self.panel.handle_click(mode_cx, mode_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertEqual(self.panel.brush_mode, BrushMode.SINGLE)

        # 2. Botão Salvar Névoa
        save_cx, save_cy, _, _ = layout.btn_save_rect
        self.assertFalse(self.save_called)
        consumed = self.panel.handle_click(save_cx, save_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertTrue(self.save_called)

    def test_panel_click_isolation_no_cross_firing(self):
        """Valida que cliques no gap entre linhas e coordenadas cruzadas não disparam ações erradas."""
        panel_w = 560.0
        top_y = 600.0
        layout = self.panel._compute_layout(panel_w, top_y)

        # Clique na coordenada X do Salvar, mas na altura da Linha 1 (onde não há botão de salvar)
        save_cx = layout.btn_save_rect[0]
        self.save_called = False
        self.panel.handle_click(save_cx, layout.row1_y, panel_w, top_y)
        # Pode ter clicado no botão 4 da Linha 1 (Revelar), mas NÃO no salvar
        self.assertFalse(self.save_called)

        # Clique no gap vertical entre Linha 1 e Linha 2
        gap_y = (layout.row1_y + layout.row2_y) / 2.0
        consumed = self.panel.handle_click(save_cx, gap_y, panel_w, top_y)
        self.assertFalse(consumed)

    def test_panel_collapsed_and_header_toggle(self):
        """Valida recolhimento e expansão do painel."""
        panel_w = 560.0
        top_y = 600.0
        layout = self.panel._compute_layout(panel_w, top_y)

        # Clica no cabeçalho para recolher
        hdr_cx = panel_w / 2.0
        consumed = self.panel.handle_click(hdr_cx, layout.hdr_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertTrue(self.panel.is_collapsed)
        self.assertEqual(self.panel.body_height, 0.0)
        self.assertEqual(self.panel.total_height, 28.0)

        # Quando recolhido, clique na antiga posição dos botões deve ser ignorado
        consumed = self.panel.handle_click(layout.btn_fill_rect[0], layout.row1_y, panel_w, top_y)
        self.assertFalse(consumed)

        # Clica novamente no cabeçalho para expandir
        consumed = self.panel.handle_click(hdr_cx, layout.hdr_cy, panel_w, top_y)
        self.assertTrue(consumed)
        self.assertFalse(self.panel.is_collapsed)


if __name__ == "__main__":
    unittest.main()
