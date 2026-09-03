import unittest
import sys
import json
import logging
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.tile_map import TileProperties, TileMap, VALID_COVER_TYPES
from src.domain.loaders.tileset_manager import TilesetManager
from src.manager.grid_manager import GridManager
from src.ui.utils.tilemap_renderer import TileMapRenderer
from src.manager.combat_manager import CombatManager
from src.domain.models.playablechar import PlayableCharacter
from src.manager.session_manager import SessionManager
from src.ui.dm.tactical_minimap import TacticalMiniMap


class TestTileMapEngine(unittest.TestCase):
    """Suíte de testes unitários para o TileMapEngine, TilesetManager e TileMapRenderer."""

    def setUp(self):
        # Janela headless/oculta para contexto do Arcade
        try:
            self.window = arcade.get_window()
        except RuntimeError:
            self.window = arcade.open_window(800, 600, "Test Window", visible=False)

    def test_tile_properties_defaults_and_immutability(self):
        """Testa valores padrão e validações defensivas do TileProperties."""
        props = TileProperties()
        self.assertFalse(props.blocks_movement)
        self.assertFalse(props.blocks_vision)
        self.assertEqual(props.cover_type, "none")
        self.assertFalse(props.difficult_terrain)
        self.assertEqual(props.height, 0)

        # Imutabilidade: tentativa de atribuição deve falhar
        with self.assertRaises(AttributeError):
            props.blocks_movement = True  # type: ignore

    def test_tile_properties_custom_and_poka_yoke(self):
        """Testa Poka-Yoke de cover_type e altura negativa."""
        props = TileProperties(
            blocks_movement=True,
            blocks_vision=True,
            cover_type="HALF",
            difficult_terrain=True,
            height=-5,
        )
        self.assertTrue(props.blocks_movement)
        self.assertTrue(props.blocks_vision)
        self.assertEqual(props.cover_type, "half")
        self.assertTrue(props.difficult_terrain)
        self.assertEqual(props.height, 0)  # Negativo ajustado para 0

        # Cover type inválido deve cair para "none"
        invalid_props = TileProperties(cover_type="invulnerable")
        self.assertEqual(invalid_props.cover_type, "none")

    def test_tile_properties_serialization(self):
        """Testa to_dict e from_dict de TileProperties."""
        original = TileProperties(
            blocks_movement=True,
            blocks_vision=False,
            cover_type="three_quarters",
            difficult_terrain=True,
            height=2,
        )
        data = original.to_dict()
        reconstructed = TileProperties.from_dict(data)

        self.assertEqual(original, reconstructed)
        self.assertEqual(reconstructed.blocks_movement, True)
        self.assertEqual(reconstructed.cover_type, "three_quarters")
        self.assertEqual(reconstructed.height, 2)

    def test_synthetic_tilemap_creation_and_o1_queries(self):
        """Testa parsing de mapa sintético e consultas táticas em O(1)."""
        raw_map_data = {
            "tileset": "dungeon_basic",
            "width": 3,
            "height": 3,
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
                    "y": 0,
                    "tile_id": 5,
                    "properties": {
                        "blocks_movement": True,
                        "blocks_vision": True,
                        "cover_type": "total",
                        "difficult_terrain": False,
                        "height": 3,
                    },
                },
                {
                    "x": 2,
                    "y": 0,
                    "tile_id": 8,
                    "properties": {
                        "blocks_movement": False,
                        "blocks_vision": False,
                        "cover_type": "half",
                        "difficult_terrain": True,
                        "height": 1,
                    },
                },
            ],
        }

        tile_map = TileMap.from_dict(raw_map_data)
        self.assertEqual(tile_map.width, 3)
        self.assertEqual(tile_map.height, 3)
        self.assertEqual(tile_map.tileset_name, "dungeon_basic")

        # Consultas na célula (0, 0)
        self.assertTrue(tile_map.is_walkable(0, 0))
        self.assertFalse(tile_map.blocks_vision(0, 0))
        self.assertEqual(tile_map.get_cover(0, 0), "none")
        self.assertFalse(tile_map.is_difficult(0, 0))
        self.assertEqual(tile_map.get_height(0, 0), 0)
        self.assertEqual(tile_map.get_tile_id(0, 0), 1)

        # Consultas na célula (1, 0) - Parede / Bloqueado
        self.assertFalse(tile_map.is_walkable(1, 0))
        self.assertTrue(tile_map.blocks_vision(1, 0))
        self.assertEqual(tile_map.get_cover(1, 0), "total")
        self.assertFalse(tile_map.is_difficult(1, 0))
        self.assertEqual(tile_map.get_height(1, 0), 3)
        self.assertEqual(tile_map.get_tile_id(1, 0), 5)

        # Consultas na célula (2, 0) - Terreno Difícil com Meia Cobertura
        self.assertTrue(tile_map.is_walkable(2, 0))
        self.assertFalse(tile_map.blocks_vision(2, 0))
        self.assertEqual(tile_map.get_cover(2, 0), "half")
        self.assertTrue(tile_map.is_difficult(2, 0))
        self.assertEqual(tile_map.get_height(2, 0), 1)
        self.assertEqual(tile_map.get_tile_id(2, 0), 8)

        # Consultas em célula sem definição explícita no grid (ex: (1, 1))
        self.assertTrue(tile_map.is_walkable(1, 1))
        self.assertFalse(tile_map.blocks_vision(1, 1))
        self.assertEqual(tile_map.get_cover(1, 1), "none")
        self.assertFalse(tile_map.is_difficult(1, 1))
        self.assertEqual(tile_map.get_height(1, 1), 0)
        self.assertIsNone(tile_map.get_tile_id(1, 1))

    def test_tilemap_out_of_bounds_queries(self):
        """Testa consultas defensivas fora dos limites do mapa."""
        tile_map = TileMap(width=4, height=4, tileset_name="test")

        # Coordenadas fora da grade
        out_of_bounds = [(-1, 0), (0, -1), (4, 0), (0, 4), (10, 10), (-5, -5)]
        for x, y in out_of_bounds:
            self.assertFalse(tile_map.is_valid_cell(x, y))
            self.assertFalse(tile_map.is_walkable(x, y), f"is_walkable({x}, {y}) deveria ser False")
            self.assertTrue(tile_map.blocks_vision(x, y), f"blocks_vision({x}, {y}) deveria ser True")
            self.assertEqual(tile_map.get_cover(x, y), "none")
            self.assertFalse(tile_map.is_difficult(x, y))
            self.assertEqual(tile_map.get_height(x, y), 0)
            self.assertIsNone(tile_map.get_tile_id(x, y))

    def test_load_real_map_file(self):
        """Testa o carregamento do arquivo creations/maps/test_map_1.json."""
        map_path = "creations/maps/test_map_1.json"
        tile_map = TileMap.from_file(map_path)

        self.assertEqual(tile_map.width, 4)
        self.assertEqual(tile_map.height, 4)
        self.assertEqual(tile_map.tileset_name, "test_map_1")

        # No test_map_1.json, célula (2, 0) possui difficult_terrain=True
        self.assertTrue(tile_map.is_difficult(2, 0))
        # Célula (0, 0) possui tile_id=2
        self.assertEqual(tile_map.get_tile_id(0, 0), 2)
        # Célula (0, 3) possui tile_id=15
        self.assertEqual(tile_map.get_tile_id(0, 3), 15)

    def test_tileset_manager_loads_and_crops_textures(self):
        """Testa o TilesetManager fatiando texturas do atlas real em O(1)."""
        manager = TilesetManager.get_tileset("test_map_1")
        self.assertEqual(manager.tileset_name, "test_map_1")
        self.assertGreater(manager.tile_count, 0)

        # O atlas do test_map_1 possui 63 frames
        self.assertEqual(manager.tile_count, 63)

        # Teste de consulta em O(1)
        tex_0 = manager.get_tile_texture(0)
        self.assertIsNotNone(tex_0)
        self.assertIsInstance(tex_0, arcade.Texture)
        self.assertEqual(tex_0.width, 32)
        self.assertEqual(tex_0.height, 32)

        tex_15 = manager.get_tile_texture(15)
        self.assertIsNotNone(tex_15)
        self.assertEqual(tex_15.width, 32)
        self.assertEqual(tex_15.height, 32)

        # Consulta fora dos limites
        self.assertIsNone(manager.get_tile_texture(999))
        self.assertIsNone(manager.get_tile_texture(-1))

    def test_tilemap_renderer_batch_and_grid_math(self):
        """Testa TileMapRenderer montando SpriteList com posicionamento centralizado de 32px."""
        tile_map = TileMap.from_file("creations/maps/test_map_1.json")
        grid_mgr = GridManager(map_width=128.0, map_height=128.0, columns=4, feet_per_square=5)
        tileset_mgr = TilesetManager.get_tileset("test_map_1")

        renderer = TileMapRenderer(
            tile_map=tile_map,
            tileset_manager=tileset_mgr,
            grid_manager=grid_mgr,
            tile_size=32.0,
        )

        # Total de tiles com sprite no layout
        self.assertEqual(renderer.tile_count, len(tile_map.tile_ids))
        self.assertIsInstance(renderer.sprite_list, arcade.SpriteList)

        # Verifica posicionamento centralizado de (0, 0): deve estar em (16.0, 16.0)
        # correspondendo ao half-tile offset (16px) do grid de 32px
        cx, cy = grid_mgr.grid_to_world_center(0, 0)
        self.assertEqual(cx, 16.0)
        self.assertEqual(cy, 16.0)

        # Testa ajuste dinâmico de layout para um viewport
        renderer.update_layout(draw_x=100.0, draw_y=50.0, cell_w=64.0, cell_h=64.0)
        # Primeiro sprite deve estar em (100 + 32 = 132, 50 + 32 = 82)
        first_sprite = renderer.sprite_list[0]
        self.assertAlmostEqual(first_sprite.scale_x, 2.0)
        self.assertAlmostEqual(first_sprite.scale_y, 2.0)

        # Executa draw sem lançar exceções
        renderer.draw(pixelated=True)

    def test_combat_manager_tilemap_integration_and_walkability(self):
        """Testa integração de TileMap com CombatManager."""
        cm = CombatManager()
        tile_map = TileMap.from_dict({
            "tileset": "test_map_1",
            "width": 4,
            "height": 4,
            "tiles": [
                {
                    "x": 1,
                    "y": 1,
                    "tile_id": 0,
                    "properties": {"blocks_movement": True},
                },
                {
                    "x": 2,
                    "y": 2,
                    "tile_id": 1,
                    "properties": {"blocks_movement": False},
                },
            ],
        })

        cm.set_tile_map(tile_map)
        self.assertEqual(cm.tile_map, tile_map)
        self.assertIsNotNone(cm.grid_manager)
        self.assertEqual(cm.grid_manager.columns, 4)

        # Walkability test: tile (1, 1) bloqueado no JSON corresponde a célula de grid (1, 2)
        self.assertFalse(cm.is_walkable(1, 2))
        self.assertTrue(cm.is_walkable(2, 1))
        self.assertTrue(cm.is_walkable(0, 0))  # Célula padrão
        self.assertFalse(cm.is_walkable(-1, 0))  # Fora do grid

        # Reset limpa o tile_map
        cm.reset_combat()
        self.assertIsNone(cm.tile_map)

    def test_drag_and_drop_reverts_on_blocked_movement(self):
        """Testa que arrastar token para célula com blocks_movement reverte a posição."""
        sm = SessionManager()
        cm = sm.combat_manager

        # Cria mapa com (1, 1) bloqueado no JSON -> corresponde a célula (1, 2) na tela
        tile_map = TileMap.from_dict({
            "tileset": "test_map_1",
            "width": 4,
            "height": 4,
            "tiles": [
                {"x": 0, "y": 0, "tile_id": 0, "properties": {"blocks_movement": False}},
                {"x": 1, "y": 1, "tile_id": 1, "properties": {"blocks_movement": True}},
            ],
        })
        cm.set_tile_map(tile_map)

        # Adiciona combatente na posição (0, 0)
        pc = PlayableCharacter(
            uid="hero_1",
            name="Geralt",
            classes=[{"name": "Guerreiro", "level": 5}],
            max_hp=40,
            armor_class=16,
            position={"x": 0, "y": 0},
        )
        cm.add_combatant(pc)
        self.assertEqual(pc.position, {"x": 0, "y": 0})

        mini_map = TacticalMiniMap(window=self.window, session_manager=sm)
        # Configura viewport artificial: draw_rect (0, 0, 400, 400), cell_size=100px
        mini_map._last_draw_rect = (0.0, 0.0, 400.0, 400.0)

        # 1. Movimento Válido: Arrasta para célula (0, 1) -> world_pos (50, 150)
        mini_map._dragged_combatant_uid = "hero_1"
        mini_map.handle_mouse_release(50.0, 150.0, split_x=400.0)
        self.assertEqual(pc.position, {"x": 0, "y": 1})

        # 2. Movimento Inválido: Tenta arrastar para célula bloqueada (1, 2) -> world_pos (150, 250)
        mini_map._dragged_combatant_uid = "hero_1"
        with self.assertLogs("src.ui.dm.tactical_minimap", level="WARNING") as log_cm:
            mini_map.handle_mouse_release(150.0, 250.0, split_x=400.0)

        # Posição deve ter sido revertida / mantida em (0, 1)
        self.assertEqual(pc.position, {"x": 0, "y": 1})
        self.assertTrue(any("Movimento bloqueado para 'Geralt'" in msg for msg in log_cm.output))


if __name__ == "__main__":
    unittest.main()
