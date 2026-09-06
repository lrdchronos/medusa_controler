import unittest
import sys
import json
import tempfile
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.builders.encounter_builder import EncounterBuilder
from src.domain.loaders.encounter_loader import EncounterLoader
from src.manager.session_manager import SessionManager
from src.ui.dm.encounter_creator_tab import EncounterCreatorTabView, EncounterBuilderView
from src.ui.dm.encounters_tab import EncountersTabView


class TestEncounterCRUD(unittest.TestCase):
    """
    Suíte de testes unitários para o ciclo completo de gerenciamento de encontros (CRUD):
      - Exclusão segura e física de arquivos de encontro.
      - Carregamento para edição com restauração de metadados, mapa, grid, combatentes e névoa.
      - Sobrescrita de arquivo preservando UID original sem duplicações.
      - Cancelamento de edição sem alterações no disco.
      - Fluxo do modal de confirmação (Poka-Yoke) e paginação com DiscreteScrollList.
    """

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.encounters_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _create_synthetic_encounter_file(
        self,
        uid: str = "encounter_synth_01",
        title: str = "Emboscada na Floresta Sintética",
        map_source: str = "assets/images/maps/open_field_grass_trees.jpg",
        map_type: str = "image",
    ) -> Path:
        """Cria um arquivo JSON de encontro sintético válido no diretório temporário."""
        data = {
            "uid": uid,
            "title": title,
            "description": "Kobolds preparam emboscada nas árvores.",
            "map_type": map_type,
            "map_source": map_source,
            "map_file": map_source,
            "environment": {
                "is_sunlight": True,
                "is_raining": False,
            },
            "grid": {
                "columns": 28,
                "feet_per_square": 5,
            },
            "fog_of_war": [
                {"x": 1, "y": 2},
                {"x": 3, "y": 4},
                {"x": 5, "y": 6},
            ],
            "combatants": [
                {
                    "entity_type": "monster",
                    "monster_id": "kobold",
                    "instance_name": "Kobold Alfa",
                    "is_hidden": True,
                    "position": {"col": 4, "row": 8},
                },
                {
                    "entity_type": "monster",
                    "monster_id": "kobold",
                    "instance_name": "Kobold Beta",
                    "is_hidden": False,
                    "position": {"col": 6, "row": 9},
                },
                {
                    "entity_type": "playable_character",
                    "character_id": "char_240820261336",
                    "name": "Bolo de Morango",
                    "is_hidden": False,
                    "position": {"col": 14, "row": 3},
                },
            ],
        }

        file_path = self.encounters_path / f"{uid}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        return file_path

    # --- 1. Testes de Exclusão Física ---

    def test_delete_encounter_physical_file_removal(self) -> None:
        """Valida que delete_encounter remove fisicamente o arquivo JSON do sistema de arquivos."""
        file_path = self._create_synthetic_encounter_file(uid="encounter_to_delete")
        self.assertTrue(file_path.is_file(), "Arquivo sintético deveria existir antes da exclusão.")

        loader = EncounterLoader(encounter_dirs=[str(self.encounters_path)])
        success = loader.delete_encounter("encounter_to_delete")

        self.assertTrue(success, "delete_encounter deveria retornar True.")
        self.assertFalse(file_path.exists(), "Arquivo não deveria mais existir no disco após exclusão.")

    def test_delete_encounter_non_existent_returns_false(self) -> None:
        """Valida que tentar excluir um encontro inexistente retorna False de forma segura."""
        loader = EncounterLoader(encounter_dirs=[str(self.encounters_path)])
        success = loader.delete_encounter("non_existent_encounter_uid_12345")
        self.assertFalse(success, "delete_encounter para UID inexistente deve retornar False.")

    def test_session_manager_delete_encounter_integration(self) -> None:
        """Valida a exclusão integrada via SessionManager com notificação de ouvintes."""
        file_path = self._create_synthetic_encounter_file(uid="encounter_sm_del")
        sm = SessionManager(encounters_dir=str(self.encounters_path))

        listener_called = []
        sm.add_listener(lambda: listener_called.append(True))

        available_before = sm.list_available_encounters()
        self.assertEqual(len(available_before), 1)

        success = sm.delete_encounter("encounter_sm_del")
        self.assertTrue(success)
        self.assertFalse(file_path.exists())
        self.assertTrue(len(listener_called) > 0, "Ouvintes da sessão deveriam ter sido notificados.")

        available_after = sm.list_available_encounters()
        self.assertEqual(len(available_after), 0)

    # --- 2. Testes de Carregamento para Edição (load_for_editing) ---

    def test_load_for_editing_restores_all_fields_with_high_fidelity(self) -> None:
        """Garante que load_for_editing restaura metadados, mapa, grid, combatentes e névoa idênticos ao JSON."""
        file_path = self._create_synthetic_encounter_file(uid="encounter_edit_test")

        with open(file_path, "r", encoding="utf-8") as f:
            encounter_data = json.load(f)
        encounter_data["path"] = str(file_path)

        sm = SessionManager(encounters_dir=str(self.encounters_path))
        builder_view = EncounterCreatorTabView(session_manager=sm)

        builder_view.load_for_editing(encounter_data)

        # 1. Estado do Builder
        self.assertTrue(builder_view.is_editing)
        self.assertEqual(builder_view.editing_encounter_uid, "encounter_edit_test")
        self.assertEqual(builder_view.editing_encounter_path, str(file_path))
        self.assertEqual(builder_view.stage, 1)

        # 2. Metadados e Grid na Etapa 1
        self.assertEqual(builder_view.title, "Emboscada na Floresta Sintética")
        self.assertEqual(builder_view.description, "Kobolds preparam emboscada nas árvores.")
        self.assertEqual(builder_view.columns, 28)
        self.assertEqual(builder_view.feet_per_square, 5)
        self.assertTrue(builder_view.form.is_sunlight)

        # 3. Combatentes: Seleção de PJs e Contagem de Monstros
        self.assertIn("char_240820261336", builder_view.selected_character_uids)
        self.assertEqual(builder_view.monster_counts.get("kobold", 0), 2)

        # 4. Palco Tático (Etapa 2) e Posições
        staging = builder_view.staging_combatants
        self.assertEqual(len(staging), 3)

        kobold1 = next(c for c in staging if c["name"] == "Kobold Alfa")
        self.assertTrue(kobold1["placed"])
        self.assertEqual(kobold1["col"], 4)
        self.assertEqual(kobold1["row"], 8)
        self.assertTrue(kobold1["is_hidden"])

        kobold2 = next(c for c in staging if c["name"] == "Kobold Beta")
        self.assertTrue(kobold2["placed"])
        self.assertEqual(kobold2["col"], 6)
        self.assertEqual(kobold2["row"], 9)
        self.assertFalse(kobold2["is_hidden"])

        pc = next(c for c in staging if c["is_player"])
        self.assertTrue(pc["placed"])
        self.assertEqual(pc["col"], 14)
        self.assertEqual(pc["row"], 3)
        self.assertFalse(pc["is_hidden"])

        # 5. Névoa de Guerra
        fogged_cells = builder_view.tactical_stage.fog_manager.get_fogged_cells()
        self.assertIn((1, 2), fogged_cells)
        self.assertIn((3, 4), fogged_cells)
        self.assertIn((5, 6), fogged_cells)

    # --- 3. Testes de Sobrescrita e Integridade de UID ---

    def test_save_encounter_edit_overwrites_existing_file_without_duplication(self) -> None:
        """Confirma que salvar alterações em modo de edição não altera o UID nem duplica arquivos."""
        file_path = self._create_synthetic_encounter_file(uid="encounter_overwrite_01")
        sm = SessionManager(encounters_dir=str(self.encounters_path))

        with open(file_path, "r", encoding="utf-8") as f:
            encounter_data = json.load(f)
        encounter_data["path"] = str(file_path)

        builder_view = EncounterCreatorTabView(session_manager=sm)
        builder_view.load_for_editing(encounter_data)

        # Modifica título e colunas da grade
        builder_view.title = "Emboscada Modificada (Edição)"
        builder_view.columns = 35

        # Move token do Kobold Alfa
        k1 = next(c for c in builder_view.staging_combatants if c["name"] == "Kobold Alfa")
        k1["col"] = 10
        k1["row"] = 12

        # Salva alterações no diretório temporário
        saved_path = builder_view.save_encounter_file(directory=str(self.encounters_path))
        self.assertIsNotNone(saved_path)
        self.assertEqual(saved_path.name, "encounter_overwrite_01.json")

        # Verifica arquivos no diretório: deve haver estritamente 1 arquivo
        json_files = list(self.encounters_path.glob("*.json"))
        self.assertEqual(len(json_files), 1, f"Não deve duplicar arquivos. Encontrados: {json_files}")

        # Recarrega do disco e valida alterações persistidas
        with open(saved_path, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        self.assertEqual(updated_data["uid"], "encounter_overwrite_01")
        self.assertEqual(updated_data["title"], "Emboscada Modificada (Edição)")
        self.assertEqual(updated_data["grid"]["columns"], 35)

        updated_k1 = next(c for c in updated_data["combatants"] if c.get("instance_name") == "Kobold Alfa")
        self.assertEqual(updated_k1["position"], {"col": 10, "row": 12})

    # --- 4. Teste de Cancelamento de Edição ---

    def test_cancel_editing_discards_modifications(self) -> None:
        """Garante que cancel_editing descarta alterações sem modificar o disco e reseta o builder."""
        file_path = self._create_synthetic_encounter_file(uid="encounter_cancel_test", title="Original Title")
        sm = SessionManager(encounters_dir=str(self.encounters_path))

        with open(file_path, "r", encoding="utf-8") as f:
            encounter_data = json.load(f)
        encounter_data["path"] = str(file_path)

        builder_view = EncounterCreatorTabView(session_manager=sm)
        builder_view.load_for_editing(encounter_data)

        # Altera título temporariamente
        builder_view.title = "Título que não deve ser salvo"
        self.assertTrue(builder_view.is_editing)

        # Cancela edição
        builder_view.cancel_editing()

        self.assertFalse(builder_view.is_editing)
        self.assertIsNone(builder_view.editing_encounter_uid)
        self.assertEqual(builder_view.stage, 1)

        # Arquivo no disco deve permanecer intocado
        with open(file_path, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data["title"], "Original Title")

    # --- 5. Testes de Modal de Confirmação Poka-Yoke & DiscreteScrollList ---

    def test_encounters_tab_discrete_scroll_list_pagination(self) -> None:
        """Valida que a EncountersTabView utiliza DiscreteScrollList para renderizar e paginar arquivos."""
        for i in range(12):
            self._create_synthetic_encounter_file(uid=f"encounter_page_{i:02d}", title=f"Encontro {i:02d}")

        sm = SessionManager(encounters_dir=str(self.encounters_path))
        tab_view = EncountersTabView(session_manager=sm)

        self.assertEqual(len(tab_view.encounters_list), 12)
        self.assertEqual(len(tab_view.scroll_list.items), 12)
        self.assertTrue(tab_view.scroll_list.can_scroll_down)

        # Simula rolagem com a roda do mouse
        tab_view.scroll_list.set_bounds(x=12.0, y=500.0, width=400.0, height=200.0)
        scrolled = tab_view.handle_mouse_scroll(x=100.0, y=400.0, scroll_x=0.0, scroll_y=-1.0)
        self.assertTrue(scrolled)
        self.assertGreater(tab_view.scroll_list.start_index, 0)

    def test_poka_yoke_delete_modal_cancellation_and_confirmation(self) -> None:
        """Valida que o modal de confirmação protege contra exclusão acidental e executa ao confirmar."""
        file_path = self._create_synthetic_encounter_file(uid="encounter_modal_test")
        sm = SessionManager(encounters_dir=str(self.encounters_path))
        tab_view = EncountersTabView(session_manager=sm)

        self.assertEqual(len(tab_view.encounters_list), 1)
        self.assertIsNone(tab_view.pending_delete_encounter)

        # 1. Simula clique no botão Excluir do Card
        enc = tab_view.encounters_list[0]
        tab_view.pending_delete_encounter = enc
        self.assertIsNotNone(tab_view.pending_delete_encounter)

        # 2. Simula clique em [ Cancelar ] no modal
        panel_w = 640.0
        top_y = 700.0
        modal_w = min(panel_w - 28, 420.0)
        modal_h = 175.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2
        btn_y = modal_cy - modal_h / 2 + 30
        btn_w = (modal_w - 36) / 2
        b_can_x = modal_cx - modal_w / 2 + 12 + btn_w / 2

        # Clica em Cancelar
        handled = tab_view.handle_click(
            x=b_can_x,
            y=btn_y,
            panel_w=panel_w,
            top_y=top_y,
            on_start_combat_callback=lambda enc_id: None,
        )
        self.assertTrue(handled)
        self.assertIsNone(tab_view.pending_delete_encounter, "Modal deveria ser fechado após cancelar.")
        self.assertTrue(file_path.is_file(), "Arquivo NÃO deveria ter sido excluído após cancelar.")

        # 3. Abre modal novamente e clica em [ Confirmar Exclusão ]
        tab_view.pending_delete_encounter = enc
        b_conf_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2

        handled_conf = tab_view.handle_click(
            x=b_conf_x,
            y=btn_y,
            panel_w=panel_w,
            top_y=top_y,
            on_start_combat_callback=lambda enc_id: None,
        )
        self.assertTrue(handled_conf)
        self.assertIsNone(tab_view.pending_delete_encounter)
        self.assertFalse(file_path.exists(), "Arquivo DEVE ser excluído do disco após confirmação.")
        self.assertEqual(len(tab_view.encounters_list), 0)


if __name__ == "__main__":
    unittest.main()
