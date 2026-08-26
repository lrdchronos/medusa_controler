import unittest
import sys
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.utils.sprite_utils import SpriteFactory, UIUtils, create_sprite


class TestSpriteUtils(unittest.TestCase):
    """Testes unitários para o helper de sprites em 1 linha (SpriteFactory/UIUtils)."""

    def setUp(self):
        self.asset_path = "assets/sprites/medusa_idle_1.png"

    def test_create_static_sprite(self):
        sprite = SpriteFactory.create_sprite(
            sheet_path=self.asset_path,
            x=100.0,
            y=200.0,
            width=48,
            height=48,
            frame_count=1,
        )
        self.assertIsInstance(sprite, arcade.Sprite)
        self.assertEqual(len(sprite.textures), 1)
        self.assertEqual(sprite.center_x, 100.0)
        self.assertEqual(sprite.center_y, 200.0)
        self.assertAlmostEqual(sprite.scale_x, 1.0)
        self.assertAlmostEqual(sprite.scale_y, 1.0)

    def test_create_animated_sprite(self):
        sprite = SpriteFactory.create_sprite(
            sheet_path=self.asset_path,
            x=400.0,
            y=300.0,
            width=48,
            height=48,
            frame_count=5,
        )
        self.assertIsInstance(sprite, arcade.Sprite)
        self.assertEqual(len(sprite.textures), 5)
        self.assertEqual(sprite.center_x, 400.0)
        self.assertEqual(sprite.center_y, 300.0)
        self.assertIsNotNone(sprite.texture)

    def test_automatic_scale_with_target_size(self):
        # Escala automática: 92px na tela a partir de 48px originais
        target_size = 92.0
        width = 48
        expected_scale = target_size / width

        sprite = SpriteFactory.create_sprite(
            sheet_path=self.asset_path,
            x=50.0,
            y=50.0,
            width=width,
            height=48,
            target_size=target_size,
            frame_count=5,
        )
        self.assertAlmostEqual(sprite.scale_x, expected_scale, places=4)
        self.assertAlmostEqual(sprite.scale_y, expected_scale, places=4)
        self.assertAlmostEqual(sprite.width, target_size, places=1)
        self.assertAlmostEqual(sprite.height, target_size, places=1)

    def test_explicit_custom_scale(self):
        custom_scale = 2.5
        sprite = SpriteFactory.create_sprite(
            sheet_path=self.asset_path,
            x=150.0,
            y=250.0,
            width=48,
            height=48,
            scale=custom_scale,
            frame_count=1,
        )
        self.assertAlmostEqual(sprite.scale_x, custom_scale, places=4)
        self.assertAlmostEqual(sprite.scale_y, custom_scale, places=4)

    def test_aliases_uiutils_and_create_sprite(self):
        # Verifica que UIUtils e create_sprite funcionam de forma idêntica
        sp1 = UIUtils.create_sprite(
            sheet_path=self.asset_path,
            x=10.0,
            y=20.0,
            width=48,
            height=48,
            target_size=92,
            frame_count=5,
        )
        sp2 = create_sprite(
            sheet_path=self.asset_path,
            x=10.0,
            y=20.0,
            width=48,
            height=48,
            target_size=92,
            frame_count=5,
        )
        self.assertEqual(len(sp1.textures), 5)
        self.assertEqual(len(sp2.textures), 5)
        self.assertEqual(sp1.position, sp2.position)
        self.assertEqual(sp1.scale_x, sp2.scale_x)

    def test_graceful_error_handling_nonexistent_file(self):
        # Arquivo inexistente não deve quebrar o programa
        sprite = SpriteFactory.create_sprite(
            sheet_path="assets/sprites/non_existent_image.png",
            x=100.0,
            y=100.0,
            width=32,
            height=32,
            frame_count=3,
        )
        self.assertIsInstance(sprite, arcade.Sprite)
        self.assertEqual(len(sprite.textures), 0)
        self.assertEqual(sprite.center_x, 100.0)
        self.assertEqual(sprite.center_y, 100.0)


if __name__ == "__main__":
    unittest.main()
