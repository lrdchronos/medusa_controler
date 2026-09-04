import unittest
import sys
import json
import logging
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.domain.models.tile_map import (
    TileProperties,
    TileMap,
    TileMapEngine,
    VALID_COVER_TYPES,
    MapAsset,
    VALID_ASSET_TYPES,
)
from src.domain.loaders.tile_map_loader import TileMapLoader
from src.domain.loaders.tileset_manager import TilesetManager
from src.manager.grid_manager import GridManager
from src.ui.utils.tilemap_renderer import TileMapRenderer
from src.ui.utils.sprite_utils import AnimatedPropSprite
from src.manager.combat_manager import CombatManager
from src.domain.models.playablechar import PlayableCharacter
from src.manager.session_manager import SessionManager
from src.ui.dm.tactical_minimap import TacticalMiniMap


class TestTileMapEngine(unittest.TestCase):
    """Suíte de testes unitários para o TileMapEngine, TileMapLoader, TilesetManager e TileMapRenderer."""

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

        # Cover type "full" deve ser normalizado para "total"
        props_full = TileProperties(cover_type="full")
        self.assertEqual(props_full.cover_type, "total")

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

    def test_synthetic_legacy_tilemap_creation_and_o1_queries(self):
        """Testa parsing de mapa sintético legado (tiles) e consultas táticas em O(1)."""
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

    def test_load_real_map_file_legacy(self):
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

    def test_compact_schema_sprite_0007_map_loading_and_blocked_walkability(self):
        """
        Testa o carregamento do mapa no novo formato compacto (Sprite-0007_map.json),
        validando catálogo de tile_ids bloqueados, elevações customizadas e consultas O(1).
        """
        map_path = "creations/maps/Sprite-0007_map.json"
        tile_map = TileMap.from_file(map_path)

        # 1. Dimensões e Tileset
        self.assertEqual(tile_map.width, 21)
        self.assertEqual(tile_map.height, 12)
        self.assertEqual(tile_map.tileset_name, "Sprite-007")

        # 2. Validação de Células com Tile IDs Bloqueados (1, 5, 23, 32)
        # Linha 1 (y=1): todos os tiles são tile_id 1 -> is_walkable deve ser False
        for x in range(21):
            self.assertEqual(tile_map.get_tile_id(x, 1), 1)
            self.assertFalse(tile_map.is_walkable(x, 1), f"Célula ({x}, 1) com tile 1 deveria estar bloqueada.")

        # Linha 2 (y=2): todos os tiles são tile_id 5 -> is_walkable deve ser False
        for x in range(21):
            self.assertEqual(tile_map.get_tile_id(x, 2), 5)
            self.assertFalse(tile_map.is_walkable(x, 2), f"Célula ({x}, 2) com tile 5 deveria estar bloqueada.")

        # Linha 5 (y=5): Célula (3, 5) possui tile_id 23 -> is_walkable deve ser False
        self.assertEqual(tile_map.get_tile_id(3, 5), 23)
        self.assertFalse(tile_map.is_walkable(3, 5))

        # Linha 6 (y=6): Célula (3, 6) possui tile_id 32 -> is_walkable deve ser False
        self.assertEqual(tile_map.get_tile_id(3, 6), 32)
        self.assertFalse(tile_map.is_walkable(3, 6))

        # 3. Validação de Células Livres (Walkable)
        # Linha 0 (y=0): tiles 16 -> is_walkable deve ser True
        for x in range(21):
            self.assertEqual(tile_map.get_tile_id(x, 0), 16)
            self.assertTrue(tile_map.is_walkable(x, 0), f"Célula ({x}, 0) com tile 16 deveria ser walkable.")

        # Linha 3 (y=3): tiles 55 -> is_walkable deve ser True
        self.assertTrue(tile_map.is_walkable(0, 3))
        self.assertEqual(tile_map.get_tile_id(0, 3), 55)

        # Linha 6 (y=6): Célula (6, 6) possui tile_id 28 -> is_walkable deve ser True
        self.assertEqual(tile_map.get_tile_id(6, 6), 28)
        self.assertTrue(tile_map.is_walkable(6, 6))

        # 4. Validação de Elevação Customizada ("heights")
        # No JSON: "heights": { "pos": { "x": 6, "y": 6 }, "height": 1 }
        self.assertEqual(tile_map.get_height(6, 6), 1)
        self.assertEqual(tile_map.get_height(0, 0), 0)
        self.assertEqual(tile_map.get_height(3, 5), 0)

        # 5. Validação Defensiva Out-of-Bounds
        self.assertFalse(tile_map.is_walkable(-1, 0))
        self.assertFalse(tile_map.is_walkable(21, 0))
        self.assertFalse(tile_map.is_walkable(0, 12))
        self.assertTrue(tile_map.blocks_vision(50, 50))
        self.assertEqual(tile_map.get_cover(-5, -5), "none")
        self.assertFalse(tile_map.is_difficult(100, 100))
        self.assertEqual(tile_map.get_height(100, 100), 0)
        self.assertIsNone(tile_map.get_tile_id(100, 100))

    def test_tile_map_loader_compact_features_and_heights_list(self):
        """Testa parsing avançado do TileMapLoader com heights em lista e catálogo completo de coberturas."""
        compact_data = {
            "tileset": "dungeon_compact",
            "width": 3,
            "height": 3,
            "data": [
                [10, 20, 30],
                [40, 50, 60],
                [70, 80, 90],
            ],
            "block_movement": [20],
            "block_vision": [30],
            "cover": {
                "half": [40],
                "three_quarters": [50],
                "full": [60],
            },
            "difficult_terrain": [70],
            "heights": [
                {"pos": {"x": 0, "y": 0}, "height": 2},
                {"x": 2, "y": 2, "height": 5},
            ],
        }

        tile_map = TileMapLoader.load_from_dict(compact_data)
        self.assertEqual(tile_map.width, 3)
        self.assertEqual(tile_map.height, 3)

        # (0, 0): tile 10, height 2
        self.assertTrue(tile_map.is_walkable(0, 0))
        self.assertFalse(tile_map.blocks_vision(0, 0))
        self.assertEqual(tile_map.get_cover(0, 0), "none")
        self.assertFalse(tile_map.is_difficult(0, 0))
        self.assertEqual(tile_map.get_height(0, 0), 2)

        # (1, 0): tile 20 -> block_movement
        self.assertFalse(tile_map.is_walkable(1, 0))

        # (2, 0): tile 30 -> block_vision
        self.assertTrue(tile_map.blocks_vision(2, 0))

        # (0, 1): tile 40 -> half cover
        self.assertEqual(tile_map.get_cover(0, 1), "half")

        # (1, 1): tile 50 -> three_quarters cover
        self.assertEqual(tile_map.get_cover(1, 1), "three_quarters")

        # (2, 1): tile 60 -> full/total cover
        self.assertEqual(tile_map.get_cover(2, 1), "total")

        # (0, 2): tile 70 -> difficult_terrain
        self.assertTrue(tile_map.is_difficult(0, 2))

        # (2, 2): tile 90, height 5
        self.assertEqual(tile_map.get_height(2, 2), 5)

    def test_tile_map_engine_alias_and_serialization(self):
        """Testa o alias TileMapEngine e serialização compacta/legada."""
        self.assertIs(TileMapEngine, TileMap)

        tile_map = TileMap(
            width=2,
            height=2,
            tileset_name="test_alias",
            tile_ids={(0, 0): 1, (1, 0): 2, (0, 1): 3, (1, 1): 4},
            tactical_grid={
                (0, 0): TileProperties(blocks_movement=True),
                (1, 0): TileProperties(cover_type="half"),
                (0, 1): TileProperties(difficult_terrain=True),
                (1, 1): TileProperties(height=3),
            },
        )

        # Serialização compacta
        compact_dict = tile_map.to_dict(compact=True)
        self.assertIn("data", compact_dict)
        self.assertIn("block_movement", compact_dict)
        self.assertIn(1, compact_dict["block_movement"])
        self.assertEqual(compact_dict["cover"]["half"], [2])
        self.assertEqual(compact_dict["difficult_terrain"], [3])

        # Reconstrução a partir do compact dict
        reconstructed = TileMap.from_dict(compact_dict)
        self.assertEqual(reconstructed.width, 2)
        self.assertEqual(reconstructed.height, 2)
        self.assertFalse(reconstructed.is_walkable(0, 0))
        self.assertEqual(reconstructed.get_cover(1, 0), "half")
        self.assertTrue(reconstructed.is_difficult(0, 1))
        self.assertEqual(reconstructed.get_height(1, 1), 3)

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

    def test_tileset_manager_resolves_sprite_007_variants(self):
        """Testa se TilesetManager resolve o tileset 'Sprite-007' para 'Sprite-0007.json'."""
        manager = TilesetManager.get_tileset("Sprite-007")
        self.assertEqual(manager.tileset_name, "Sprite-007")
        self.assertGreater(manager.tile_count, 0)
        self.assertEqual(manager.tile_count, 70)

        tex_1 = manager.get_tile_texture(1)
        self.assertIsNotNone(tex_1)
        self.assertEqual(tex_1.width, 32)
        self.assertEqual(tex_1.height, 32)

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
        first_sprite = renderer.sprite_list[0]
        self.assertAlmostEqual(first_sprite.scale_x, 2.0)
        self.assertAlmostEqual(first_sprite.scale_y, 2.0)

        # Executa draw sem lançar exceções
        renderer.draw(pixelated=True)

    def test_tilemap_renderer_with_sprite_0007_map(self):
        """Testa TileMapRenderer com o novo mapa Sprite-0007_map.json (21x12 = 252 tiles)."""
        tile_map = TileMap.from_file("creations/maps/Sprite-0007_map.json")
        renderer = TileMapRenderer(tile_map=tile_map, tile_size=32.0)

        self.assertEqual(renderer.tile_count, 21 * 12)
        self.assertIsInstance(renderer.sprite_list, arcade.SpriteList)
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

    def test_map_asset_model_and_poka_yoke(self):
        """Testa encapsulamento e validações defensivas do MapAsset."""
        asset = MapAsset(
            sprite="assets/sprites/firepit.png",
            asset_type="SPRITESHEET",
            x=6,
            y=4,
            scale=1.5,
        )
        self.assertEqual(asset.sprite, "assets/sprites/firepit.png")
        self.assertEqual(asset.type, "spritesheet")
        self.assertEqual(asset.x, 6)
        self.assertEqual(asset.y, 4)
        self.assertEqual(asset.position, {"x": 6, "y": 4})
        self.assertAlmostEqual(asset.scale, 1.5)

        # Normalização Poka-Yoke de tipo inválido para 'sprite'
        invalid_type_asset = MapAsset(sprite="test.png", asset_type="unknown_type")
        self.assertEqual(invalid_type_asset.type, "sprite")

        # Serialização e reconstrução
        data = asset.to_dict()
        reconstructed = MapAsset.from_dict(data)
        self.assertIsNotNone(reconstructed)
        self.assertEqual(asset, reconstructed)

    def test_tilemap_parsing_assets_compact_and_legacy(self):
        """Testa parsing de lista 'assets' em mapas de formato compacto e legado."""
        raw_compact = {
            "tileset": "test_map_1",
            "width": 4,
            "height": 4,
            "data": [
                [0, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
            "assets": [
                {
                    "sprite": "assets/sprites/firepit.png",
                    "type": "spritesheet",
                    "position": {"x": 2, "y": 2},
                    "scale": 1.0,
                },
                {
                    "sprite": "assets/sprites/medusa_idle_1.png",
                    "type": "sprite",
                    "position": {"x": 1, "y": 3},
                    "scale": 0.5,
                },
            ],
        }

        tile_map = TileMap.from_dict(raw_compact)
        self.assertEqual(len(tile_map.assets), 2)
        self.assertEqual(tile_map.assets[0].type, "spritesheet")
        self.assertEqual(tile_map.assets[0].x, 2)
        self.assertEqual(tile_map.assets[0].y, 2)
        self.assertEqual(tile_map.assets[1].type, "sprite")
        self.assertEqual(tile_map.assets[1].x, 1)
        self.assertEqual(tile_map.assets[1].y, 3)

        # Serialização preserva assets
        compact_dict = tile_map.to_dict(compact=True)
        self.assertIn("assets", compact_dict)
        self.assertEqual(len(compact_dict["assets"]), 2)

    def test_tilemap_parsing_absent_or_empty_assets(self):
        """Garante que ausência ou lista vazia de assets é tratada sem erros."""
        map_no_assets = TileMap.from_dict({
            "tileset": "test_map_1",
            "width": 2,
            "height": 2,
            "data": [[0, 0], [0, 0]],
        })
        self.assertEqual(len(map_no_assets.assets), 0)

        map_empty_assets = TileMap.from_dict({
            "tileset": "test_map_1",
            "width": 2,
            "height": 2,
            "data": [[0, 0], [0, 0]],
            "assets": [],
        })
        self.assertEqual(len(map_empty_assets.assets), 0)

    def test_tilemap_renderer_props_instantiation_and_world_centering(self):
        """Testa instanciação de camadas ground/props e posicionamento centralizado no grid."""
        raw_map = {
            "tileset": "test_map_1",
            "width": 4,
            "height": 4,
            "data": [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
            "assets": [
                {
                    "sprite": "assets/sprites/firepit.png",
                    "type": "spritesheet",
                    "position": {"x": 1, "y": 1},
                    "scale": 1.0,
                },
                {
                    "sprite": "assets/sprites/medusa_idle_1.png",
                    "type": "sprite",
                    "position": {"x": 2, "y": 0},
                    "scale": 2.0,
                },
            ],
        }
        tile_map = TileMap.from_dict(raw_map)
        grid_mgr = GridManager(map_width=128.0, map_height=128.0, columns=4, feet_per_square=5)
        renderer = TileMapRenderer(tile_map=tile_map, grid_manager=grid_mgr, tile_size=32.0)

        self.assertEqual(renderer.tile_count, 16)
        self.assertEqual(renderer.prop_count, 2)
        self.assertIsInstance(renderer.ground_sprites, arcade.SpriteList)
        self.assertIsInstance(renderer.prop_sprites, arcade.SpriteList)

        # Prop 0: (x=1, y=1) no mapa 4x4 -> col=1, row=(4-1)-1 = 2
        # grid_to_world_center(1, 2) -> (16 + 1*32, 16 + 2*32) = (48.0, 80.0)
        prop_0 = renderer.prop_sprites[0]
        expected_cx, expected_cy = grid_mgr.grid_to_world_center(1, 2)
        self.assertAlmostEqual(prop_0.center_x, expected_cx)
        self.assertAlmostEqual(prop_0.center_y, expected_cy)
        self.assertAlmostEqual(prop_0.scale_x, 1.0)

        # Prop 1: (x=2, y=0) no mapa 4x4 -> col=2, row=3
        # grid_to_world_center(2, 3) -> (16 + 2*32, 16 + 3*32) = (80.0, 112.0)
        prop_1 = renderer.prop_sprites[1]
        expected_cx1, expected_cy1 = grid_mgr.grid_to_world_center(2, 3)
        self.assertAlmostEqual(prop_1.center_x, expected_cx1)
        self.assertAlmostEqual(prop_1.center_y, expected_cy1)
        self.assertAlmostEqual(prop_1.scale_x, 2.0)

    def test_tilemap_renderer_props_animation_cycle(self):
        """Testa que invocar update() no TileMapRenderer atualiza animações de props."""
        raw_map = {
            "tileset": "test_map_1",
            "width": 2,
            "height": 2,
            "data": [[0, 0], [0, 0]],
            "assets": [
                {
                    "sprite": "assets/sprites/firepit.png",
                    "type": "spritesheet",
                    "position": {"x": 0, "y": 0},
                    "scale": 1.0,
                }
            ],
        }
        tile_map = TileMap.from_dict(raw_map)
        renderer = TileMapRenderer(tile_map=tile_map)

        anim_prop = renderer.prop_sprites[0]
        self.assertIsInstance(anim_prop, AnimatedPropSprite)
        self.assertEqual(anim_prop.cur_frame_idx, 0)

        # Avança 0.125s através do método update do renderer
        renderer.update(0.125)
        self.assertEqual(anim_prop.cur_frame_idx, 1)

    def test_tilemap_renderer_with_sprite_0007_props(self):
        """Testa carregamento do mapa oficial Sprite-0007_map.json com props e desenho de camadas."""
        tile_map = TileMap.from_file("creations/maps/Sprite-0007_map.json")
        renderer = TileMapRenderer(tile_map=tile_map, tile_size=32.0)

        self.assertEqual(renderer.tile_count, 21 * 12)
        self.assertGreaterEqual(renderer.prop_count, 1)

        # Executa ciclo de update e draw ordenado
        renderer.update(1 / 60)
        renderer.draw(pixelated=True)


if __name__ == "__main__":
    unittest.main()
