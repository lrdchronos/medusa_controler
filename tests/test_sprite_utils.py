import unittest
import sys
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.utils.sprite_utils import (
    SpriteFactory,
    UIUtils,
    create_sprite,
    create_static_prop,
    create_animated_prop,
    AnimatedPropSprite,
    AnimatedTimeBasedSprite,
)


class TestSpriteUtils(unittest.TestCase):
    """Testes unitários para o helper de sprites e props (SpriteFactory/UIUtils)."""

    def setUp(self):
        self.medusa_asset = "assets/sprites/medusa_idle_1.png"
        self.firepit_asset = "assets/sprites/firepit.png"

    def test_default_parameters_32px(self):
        """Verifica que chamadas sem especificar tamanho assumem padrão de 32x32px."""
        sprite = SpriteFactory.create_sprite(sheet_path=self.firepit_asset)
        self.assertIsInstance(sprite, arcade.Sprite)
        self.assertEqual(len(sprite.textures), 1)
        self.assertEqual(sprite.texture.width, 32)
        self.assertEqual(sprite.texture.height, 32)

    def test_create_static_prop(self):
        """Testa criação de prop estático de 32x32px com escala personalizada."""
        prop = SpriteFactory.create_static_prop(
            image_path=self.firepit_asset,
            scale=2.0,
        )
        self.assertIsInstance(prop, arcade.Sprite)
        self.assertEqual(len(prop.textures), 1)
        self.assertEqual(prop.texture.width, 32)
        self.assertEqual(prop.texture.height, 32)
        self.assertAlmostEqual(prop.scale_x, 2.0)
        self.assertAlmostEqual(prop.scale_y, 2.0)

    def test_create_animated_prop_and_loop_animation(self):
        """Testa criação de prop animado (6 frames, 8.0 FPS) e ciclo de avanço de frames."""
        prop = SpriteFactory.create_animated_prop(
            spritesheet_path=self.firepit_asset,
            scale=1.5,
            frame_count=6,
            fps=8.0,
        )
        self.assertIsInstance(prop, AnimatedPropSprite)
        self.assertIsInstance(prop, AnimatedTimeBasedSprite)
        self.assertEqual(len(prop.textures), 6)
        self.assertAlmostEqual(prop.scale_x, 1.5)
        self.assertAlmostEqual(prop.fps, 8.0)
        self.assertAlmostEqual(prop.frame_duration, 0.125)
        self.assertEqual(prop.cur_frame_idx, 0)
        self.assertEqual(prop.texture, prop.textures[0])

        # Avança 0.125s -> deve mudar para o frame 1
        prop.update_animation(0.125)
        self.assertEqual(prop.cur_frame_idx, 1)
        self.assertEqual(prop.texture, prop.textures[1])

        # Avança mais 5 frames (0.625s) -> deve completar o ciclo e voltar para 0
        prop.update_animation(0.625)
        self.assertEqual(prop.cur_frame_idx, 0)
        self.assertEqual(prop.texture, prop.textures[0])

    def test_create_static_sprite(self):
        sprite = SpriteFactory.create_sprite(
            sheet_path=self.medusa_asset,
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
            sheet_path=self.medusa_asset,
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

    def test_idle_screen_legacy_exception_preservation(self):
        """Garante que a chamada da tela de IDLE (Medusa sigil) preserva 48x48px e 5 frames."""
        target_size = 92.0
        width = 48
        expected_scale = target_size / width

        sprite = SpriteFactory.create_sprite(
            sheet_path=self.medusa_asset,
            x=512.0,
            y=414.0,
            width=width,
            height=48,
            target_size=target_size,
            frame_count=5,
        )
        self.assertEqual(len(sprite.textures), 5)
        self.assertAlmostEqual(sprite.scale_x, expected_scale, places=4)
        self.assertAlmostEqual(sprite.scale_y, expected_scale, places=4)
        self.assertAlmostEqual(sprite.width, target_size, places=1)
        self.assertAlmostEqual(sprite.height, target_size, places=1)

    def test_automatic_scale_with_target_size(self):
        # Escala automática: 92px na tela a partir de 48px originais
        target_size = 92.0
        width = 48
        expected_scale = target_size / width

        sprite = SpriteFactory.create_sprite(
            sheet_path=self.medusa_asset,
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
            sheet_path=self.medusa_asset,
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
        # Verifica que UIUtils, create_static_prop e create_animated_prop funcionam de forma idêntica
        sp1 = UIUtils.create_sprite(
            sheet_path=self.medusa_asset,
            x=10.0,
            y=20.0,
            width=48,
            height=48,
            target_size=92,
            frame_count=5,
        )
        sp2 = create_sprite(
            sheet_path=self.medusa_asset,
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

        p_static = create_static_prop(self.firepit_asset, scale=1.0)
        p_anim = create_animated_prop(self.firepit_asset, scale=1.0)
        self.assertEqual(len(p_static.textures), 1)
        self.assertEqual(len(p_anim.textures), 6)

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

        # Prop com arquivo inexistente também não quebra
        prop_err = SpriteFactory.create_animated_prop("assets/sprites/non_existent_prop.png")
        self.assertIsInstance(prop_err, AnimatedPropSprite)
        self.assertEqual(len(prop_err.textures), 0)


if __name__ == "__main__":
    unittest.main()
