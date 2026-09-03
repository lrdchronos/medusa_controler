import unittest
import sys
import json
import tempfile
import os
import logging
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.builders.encounter_builder import EncounterBuilder
from src.domain.loaders.encounter_loader import EncounterLoader
from src.domain.models.tile_map import TileMap, TileProperties
from src.domain.models.playablechar import PlayableCharacter
from src.manager.grid_manager import GridManager
from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager
from src.ui.dm.creator.config_form import CreatorConfigForm
from src.ui.dm.tactical_minimap import TacticalMiniMap

logger = logging.getLogger(__name__)


class TestEncounterMapTypes(unittest.TestCase):
    """
    Suíte de testes para validação do Suporte Híbrido a Mapas:
    - Imagem Fixa (.png, .jpg) vs Tilemap Modular Dinâmico (.json)
    - Enquadramento Aspect-Fit Proporcional em diferentes resoluções (16:9, 16:10, 4:3)
    - Serialização, Carregamento no EncounterLoader e Inicialização no CombatManager
    - Validação de Movimentação com blocks_movement e integração na interface DM
    """

    @classmethod
    def setUpClass(cls):
        try:
            cls.window = arcade.get_window()
        except RuntimeError:
            cls.window = arcade.open_window(800, 600, "Test Window", visible=False)

    def test_encounter_builder_schema_serialization_image_and_tilemap(self):
        """Valida que EncounterBuilder serializa map_type, map_source e map_file corretamente."""
        # 1. Modo Imagem
        builder_img = EncounterBuilder()
        builder_img.with_metadata("Batalha na Clareira", "Emboscada em floresta.")
        builder_img.with_map("assets/images/maps/open_field.jpg", map_type="image")
        builder_img.with_grid(columns=25, feet_per_square=5)
        builder_img.add_monster("kobold", instance_name="Kobold 1", col=2, row=3)

        data_img = builder_img.to_dict()
        self.assertEqual(data_img["map_type"], "image")
        self.assertEqual(data_img["map_source"], "assets/images/maps/open_field.jpg")
        self.assertEqual(data_img["map_file"], "assets/images/maps/open_field.jpg")

        # 2. Modo Tilemap com dedução automática por extensão .json
        builder_tm = EncounterBuilder()
        builder_tm.with_metadata("Emboscada na Estrada", "Ataque na estrada de pedra.")
        builder_tm.with_map("creations/maps/road_encounter.json")
        builder_tm.with_grid(columns=25, feet_per_square=5)
        builder_tm.add_monster("goblin", instance_name="Goblin 1", col=4, row=5)

        data_tm = builder_tm.to_dict()
        self.assertEqual(data_tm["map_type"], "tilemap")
        self.assertEqual(data_tm["map_source"], "creations/maps/road_encounter.json")
        self.assertEqual(data_tm["map_file"], "creations/maps/road_encounter.json")

    def test_aspect_fit_scaling_mathematics(self):
        """Valida a precisão matemática da escala Aspect-Fit em 16:9, 16:10 e 4:3."""
        # 1. Viewport 16:9 (1920x1080) com Nativo 16:9 (1920x1080)
        scale, rw, rh, ox, oy = GridManager.calculate_aspect_fit(
            viewport_width=1920.0,
            viewport_height=1080.0,
            native_width=1920.0,
            native_height=1080.0,
        )
        self.assertAlmostEqual(scale, 1.0, places=4)
        self.assertAlmostEqual(rw, 1920.0, places=4)
        self.assertAlmostEqual(rh, 1080.0, places=4)
        self.assertAlmostEqual(ox, 0.0, places=4)
        self.assertAlmostEqual(oy, 0.0, places=4)

        # 2. Viewport 16:10 (1920x1200) com Nativo 16:9 (1920x1080) -> Barras horizontais superior/inferior
        scale, rw, rh, ox, oy = GridManager.calculate_aspect_fit(
            viewport_width=1920.0,
            viewport_height=1200.0,
            native_width=1920.0,
            native_height=1080.0,
        )
        self.assertAlmostEqual(scale, 1.0, places=4)
        self.assertAlmostEqual(rw, 1920.0, places=4)
        self.assertAlmostEqual(rh, 1080.0, places=4)
        self.assertAlmostEqual(ox, 0.0, places=4)
        self.assertAlmostEqual(oy, 60.0, places=4)  # (1200 - 1080) / 2 = 60

        # 3. Viewport 4:3 (1024x768) com Nativo 16:9 (800x450)
        # scale = min(1024/800=1.28, 768/450=1.7067) = 1.28
        scale, rw, rh, ox, oy = GridManager.calculate_aspect_fit(
            viewport_width=1024.0,
            viewport_height=768.0,
            native_width=800.0,
            native_height=450.0,
        )
        self.assertAlmostEqual(scale, 1.28, places=4)
        self.assertAlmostEqual(rw, 1024.0, places=4)
        self.assertAlmostEqual(rh, 576.0, places=4)
        self.assertAlmostEqual(ox, 0.0, places=4)
        self.assertAlmostEqual(oy, 96.0, places=4)  # (768 - 576) / 2 = 96

    def test_grid_manager_offsets_and_coordinate_mapping(self):
        """Valida que GridManager mapeia coordenadas locais levando em conta offsets e scale."""
        grid_mgr = GridManager(
            map_width=800.0,
            map_height=600.0,
            columns=20,
            feet_per_square=5,
            offset_x=100.0,
            offset_y=50.0,
        )
        self.assertEqual(grid_mgr.offset_x, 100.0)
        self.assertEqual(grid_mgr.offset_y, 50.0)

        # cell_size = 800 / 20 = 40.0
        # Célula (0, 0): centro = (100 + 20, 50 + 20) = (120, 70)
        cx, cy = grid_mgr.grid_to_world_center(0, 0)
        self.assertEqual(cx, 120.0)
        self.assertEqual(cy, 70.0)

        # Coordenada mundo (125, 75) deve mapear para (0, 0)
        col, row = grid_mgr.world_to_grid(125.0, 75.0)
        self.assertEqual(col, 0)
        self.assertEqual(row, 0)

    def test_encounter_loader_and_combat_manager_tilemap_integration(self):
        """Valida o carregamento de encontro com tilemap e instanciação no CombatManager."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Cria um arquivo de tilemap sintético
            tilemap_path = Path(tmp_dir) / "test_tilemap.json"
            tilemap_data = {
                "tileset": "dungeon_basic",
                "width": 10,
                "height": 8,
                "tiles": [
                    {
                        "x": 0,
                        "y": 0,
                        "tile_id": 1,
                        "properties": {
                            "blocks_movement": False,
                            "blocks_vision": False,
                            "cover_type": "none",
                            "difficult_terrain": False,
                            "height": 0,
                        },
                    },
                    {
                        "x": 1,
                        "y": 1,
                        "tile_id": 2,
                        "properties": {
                            "blocks_movement": True,
                            "blocks_vision": True,
                            "cover_type": "total",
                            "difficult_terrain": False,
                            "height": 1,
                        },
                    },
                ],
            }
            with open(tilemap_path, "w", encoding="utf-8") as f:
                json.dump(tilemap_data, f)

            # 2. Cria arquivo de encontro apontando para o tilemap
            encounter_path = Path(tmp_dir) / "test_encounter.json"
            encounter_data = {
                "uid": "enc_tilemap_test",
                "title": "Encontro em Caverna",
                "map_type": "tilemap",
                "map_source": str(tilemap_path),
                "grid": {"columns": 10, "feet_per_square": 5},
                "combatants": [
                    {
                        "entity_type": "monster",
                        "monster_id": "kobold",
                        "instance_name": "Kobold 1",
                        "position": {"col": 0, "row": 0},
                        "is_hidden": False,
                    }
                ],
            }
            with open(encounter_path, "w", encoding="utf-8") as f:
                json.dump(encounter_data, f)

            # 3. Testa EncounterLoader
            loader = EncounterLoader()
            loaded_enc = loader.load_encounter(encounter_path)
            self.assertEqual(loaded_enc["map_type"], "tilemap")
            self.assertEqual(loaded_enc["map_source"], str(tilemap_path))

            # 4. Testa CombatManager.load_encounter
            combat_mgr = CombatManager()
            combat_mgr.load_encounter(str(encounter_path))
            self.assertEqual(combat_mgr.map_type, "tilemap")
            self.assertIsNotNone(combat_mgr.tile_map)
            self.assertEqual(combat_mgr.tile_map.width, 10)
            self.assertEqual(combat_mgr.tile_map.height, 8)
            self.assertEqual(combat_mgr.grid_manager.columns, 10)
            self.assertEqual(combat_mgr.grid_manager.rows, 8)

    def test_matrix_coordinate_projection_top_left_and_bottom_right(self):
        """
        Valida que (x=0, y=0) no schema JSON é o canto superior esquerdo (Top-Left)
        e (x=width-1, y=height-1) é o canto inferior direito (Bottom-Right).
        """
        tile_map = TileMap(
            width=4,
            height=4,
            tileset_name="test_map_1",
            tactical_grid={
                (0, 0): TileProperties(blocks_movement=True),   # Top-Left no JSON
                (3, 3): TileProperties(blocks_movement=True),   # Bottom-Right no JSON
                (3, 0): TileProperties(blocks_movement=False),  # Top-Right no JSON
                (0, 3): TileProperties(blocks_movement=False),  # Bottom-Left no JSON
                (1, 2): TileProperties(blocks_movement=True),   # 2ª col da esquerda, 3ª linha do topo
            },
        )

        # 1. Grid 4x4 idêntico
        # Canto Superior Esquerdo (col=0, row=3 no grid / tela) -> deve mapear para tile (0, 0)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=0, grid_row=3, grid_cols=4, grid_rows=4)
        self.assertEqual((tx, ty), (0, 0))
        self.assertFalse(tile_map.is_walkable_at_grid(0, 3, 4, 4))

        # Canto Inferior Direito (col=3, row=0 no grid / tela) -> deve mapear para tile (3, 3)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=3, grid_row=0, grid_cols=4, grid_rows=4)
        self.assertEqual((tx, ty), (3, 3))
        self.assertFalse(tile_map.is_walkable_at_grid(3, 0, 4, 4))

        # Canto Superior Direito (col=3, row=3 no grid / tela) -> deve mapear para tile (3, 0)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=3, grid_row=3, grid_cols=4, grid_rows=4)
        self.assertEqual((tx, ty), (3, 0))
        self.assertTrue(tile_map.is_walkable_at_grid(3, 3, 4, 4))

        # Canto Inferior Esquerdo (col=0, row=0 no grid / tela) -> deve mapear para tile (0, 3)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=0, grid_row=0, grid_cols=4, grid_rows=4)
        self.assertEqual((tx, ty), (0, 3))
        self.assertTrue(tile_map.is_walkable_at_grid(0, 0, 4, 4))

        # Tile (x=1, y=2): 2ª coluna da esquerda (col=1) e 3ª linha de cima para baixo (row=1 no grid Arcade de baixo para cima)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=1, grid_row=1, grid_cols=4, grid_rows=4)
        self.assertEqual((tx, ty), (1, 2))
        self.assertFalse(tile_map.is_walkable_at_grid(1, 1, 4, 4))

        # 2. Grid 10x10 independente sobre tilemap 4x4
        # Célula (0, 9) [Top-Left] deve mapear para tile (0, 0)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=0, grid_row=9, grid_cols=10, grid_rows=10)
        self.assertEqual((tx, ty), (0, 0))
        self.assertFalse(tile_map.is_walkable_at_grid(0, 9, 10, 10))

        # Célula (9, 0) [Bottom-Right] deve mapear para tile (3, 3)
        tx, ty = tile_map.grid_to_tile_coords(grid_col=9, grid_row=0, grid_cols=10, grid_rows=10)
        self.assertEqual((tx, ty), (3, 3))
        self.assertFalse(tile_map.is_walkable_at_grid(9, 0, 10, 10))

    def test_tactical_minimap_blocks_movement_validation(self):
        """Valida que TacticalMiniMap impede movimento em tiles com blocks_movement=True respeitando a projeção."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tilemap_path = Path(tmp_dir) / "wall_map.json"
            # 5x5 tilemap com parede em (x=1, y=0) no JSON [Top-Left área: col=1, row=4 no grid]
            tilemap_data = {
                "tileset": "dungeon_basic",
                "width": 5,
                "height": 5,
                "tiles": [
                    {
                        "x": 1,
                        "y": 0,
                        "tile_id": 2,
                        "properties": {"blocks_movement": True},  # Parede / Bloqueado
                    },
                ],
            }
            with open(tilemap_path, "w", encoding="utf-8") as f:
                json.dump(tilemap_data, f)

            tile_map = TileMap.from_file(tilemap_path)
            session_mgr = SessionManager()
            combat_mgr = session_mgr.combat_manager
            combat_mgr.reset_combat()

            pj = PlayableCharacter(
                name="Elfo",
                max_hp=8,
                armor_class=12,
                uid="elf_1",
            )
            combat_mgr.add_combatant(pj)
            combat_mgr.set_combatant_position("elf_1", 0, 0)
            combat_mgr._CombatManager__tile_map = tile_map
            combat_mgr._CombatManager__grid_manager = GridManager(
                map_width=5 * 32.0,
                map_height=5 * 32.0,
                columns=5,
                feet_per_square=5,
            )

            minimap = TacticalMiniMap(window=self.window, session_manager=session_mgr)
            minimap._last_draw_rect = (0.0, 0.0, 500.0, 500.0)
            # cell_w = 100.0, cell_h = 100.0

            # 1. Tenta mover para célula correspondente a (x=1, y=0) -> tela col=1, row=4
            # Clique em x=150, y=450 (col=1, row=4)
            minimap._dragged_combatant_uid = "elf_1"
            minimap.handle_mouse_release(150.0, 450.0, split_x=400.0)

            # Posição deve permanecer (0, 0) pois o movimento foi bloqueado
            pos = pj.position
            self.assertEqual(pos["x"], 0)
            self.assertEqual(pos["y"], 0)

            # 2. Tenta mover para célula livre (col=1, row=1) -> Livre!
            minimap._dragged_combatant_uid = "elf_1"
            minimap.handle_mouse_release(150.0, 150.0, split_x=400.0)

            # Posição atualizada para (1, 1)
            pos = pj.position
            self.assertEqual(pos["x"], 1)
            self.assertEqual(pos["y"], 1)

    def test_creator_config_form_tab_switching_and_independent_grid(self):
        """Valida que CreatorConfigForm mantém o grid tático independente do tilemap."""
        available_maps = [{"name": "Campo", "filename": "field.png", "path": "assets/maps/field.png"}]
        available_tilemaps = [
            {"name": "Caverna", "filename": "cave.json", "path": "creations/maps/cave.json", "width": 4, "height": 4}
        ]
        available_chars = [{"uid": "c1", "name": "Guerreiro"}]
        available_monsters = [{"uid": "m1", "name": "Kobold"}]

        form = CreatorConfigForm(
            available_maps=available_maps,
            available_characters=available_chars,
            available_monsters=available_monsters,
            available_tilemaps=available_tilemaps,
        )

        # 1. Modo Padrão: image com 10 colunas
        self.assertEqual(form.map_type, "image")
        form.columns = 10
        self.assertEqual(form.columns, 10)

        # 2. Alterna para tilemap (4x4)
        form.map_type = "tilemap"
        self.assertEqual(form.map_type, "tilemap")
        # Colunas devem permanecer 10 (grid independente do tilemap 4x4)
        self.assertEqual(form.columns, 10)

        # 3. Altera colunas via steppers
        form.handle_mouse_press(x=65+48, y=form._CreatorConfigForm__last_list_bounds[1] if form._CreatorConfigForm__last_list_bounds else 500, panel_w=640, top_y=670)
        # Config data reflete as colunas independentes configuradas
        config_data = form.get_config_data()
        self.assertEqual(config_data["map_type"], "tilemap")
        self.assertEqual(config_data["map_source"], "creations/maps/cave.json")
        self.assertEqual(config_data["columns"], form.columns)

    def test_texture_cache_defensive_behavior_with_json_and_tilemaps(self):
        """Valida que _get_texture ignora arquivos .json e não tenta carregá-los como textura."""
        session_mgr = SessionManager()
        minimap = TacticalMiniMap(window=self.window, session_manager=session_mgr)

        # 1. Arquivo JSON não deve ser carregado como textura
        json_path = "creations/maps/test_map_1.json"
        tex = minimap._get_texture(json_path)
        self.assertIsNone(tex)

        # 2. Arquivo inexistente retorna None sem lançar exceções
        tex_none = minimap._get_texture("assets/images/battlemaps/non_existent_map_123.png")
        self.assertIsNone(tex_none)

        # 3. Arquivo existente inválido/corrompido é cacheado como None para não retentar
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as f:
            f.write(b"not an image data")
            corrupt_file = f.name
        try:
            tex_corrupt = minimap._get_texture(corrupt_file)
            self.assertIsNone(tex_corrupt)
            resolved = str(os.path.abspath(corrupt_file))
            self.assertIn(resolved, minimap._texture_cache)
            self.assertIsNone(minimap._texture_cache[resolved])
        finally:
            if os.path.exists(corrupt_file):
                os.remove(corrupt_file)

    def test_tilemap_encounter_draw_does_not_request_json_texture(self):
        """Valida que ao desenhar encontro com TileMap, o renderizador modular é usado sem carregar JSON como textura."""
        session_mgr = SessionManager()
        combat_mgr = session_mgr.combat_manager

        builder = EncounterBuilder()
        builder.with_metadata("Encontro Tilemap", "Teste")
        builder.with_map("creations/maps/test_map_1.json")
        builder.with_grid(columns=10, feet_per_square=5)
        builder.add_monster("kobold", "Kobold 1", 1, 1)

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump(builder.to_dict(), f)
            enc_path = f.name

        try:
            combat_mgr.load_encounter(enc_path)
            self.assertEqual(combat_mgr.map_type, "tilemap")
            self.assertIsNotNone(combat_mgr.tile_map)

            minimap = TacticalMiniMap(window=self.window, session_manager=session_mgr)
            minimap._draw_tactical_map(0, 0, 800, 600, None)

            self.assertIsNotNone(minimap._tilemap_renderer)
            json_resolved = str(os.path.abspath("creations/maps/test_map_1.json"))
            self.assertNotIn(json_resolved, minimap._texture_cache)
        finally:
            if os.path.exists(enc_path):
                os.remove(enc_path)


if __name__ == "__main__":
    unittest.main()

