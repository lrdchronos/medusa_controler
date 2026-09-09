import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import arcade
from .animated_prop_sprite import AnimatedPropSprite
from .combat_token import CombatToken
from .token_badge_renderer import extract_badge_text, draw_tactical_token
from .procedural_texture_generator import get_procedural_token_texture

logger = logging.getLogger(__name__)


def resolve_asset_path(file_path: str) -> str:
    """
    Resolve o caminho do arquivo de asset de maneira resiliente,
    tentando caminhos relativos ao diretório de trabalho ou à raiz do projeto.
    """
    if not file_path:
        return file_path

    if os.path.isabs(file_path) and os.path.isfile(file_path):
        return file_path

    if os.path.isfile(file_path):
        return os.path.abspath(file_path)

    project_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = project_root / file_path
    if candidate.is_file():
        return str(candidate)

    return file_path


class SpriteFactory:
    """
    Fábrica utilitária declarativa para criação, escalonamento e posicionamento
    de Sprites, Props de cenário e Tokens Táticos para o Medusa VTT.
    """

    _token_texture_cache: Dict[str, arcade.Texture] = {}
    _text_cache: Dict[str, arcade.Text] = {}

    @staticmethod
    def resolve_asset_path(file_path: str) -> str:
        return resolve_asset_path(file_path)

    @staticmethod
    def create_sprite(
        sheet_path: str,
        x: float = 0.0,
        y: float = 0.0,
        width: int = 32,
        height: int = 32,
        target_size: Optional[float] = None,
        frame_count: int = 1,
        scale: float = 1.0,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        fps: float = 8.0,
    ) -> arcade.Sprite:
        eff_width = frame_width if frame_width is not None else width
        eff_height = frame_height if frame_height is not None else height
        resolved_path = resolve_asset_path(sheet_path)

        if frame_count <= 1:
            sprite = arcade.Sprite()
            try:
                base_tex = arcade.load_texture(resolved_path)
                if eff_width > 0 and eff_height > 0 and (base_tex.width > eff_width or base_tex.height > eff_height):
                    tex = base_tex.crop(0, 0, eff_width, eff_height)
                else:
                    tex = base_tex
                sprite.texture = tex
                sprite.textures = [tex]
            except Exception as e:
                logger.error(f"Erro ao carregar textura do Sprite '{sheet_path}' (resolvido: '{resolved_path}'): {e}")
                sprite.textures = []
        else:
            textures: List[arcade.Texture] = []
            try:
                base_tex = arcade.load_texture(resolved_path)
                textures = [
                    base_tex.crop(i * eff_width, 0, eff_width, eff_height)
                    for i in range(frame_count)
                ]
            except Exception as e:
                logger.error(f"Erro ao carregar spritesheet animado '{sheet_path}' (resolvido: '{resolved_path}'): {e}")

            sprite = AnimatedPropSprite(
                textures=textures,
                fps=fps,
            )

        if target_size is not None and eff_width > 0:
            effective_scale = float(target_size) / float(eff_width)
        else:
            effective_scale = float(scale)

        sprite.scale = effective_scale
        sprite.position = (float(x), float(y))
        return sprite

    @classmethod
    def create_static_prop(
        cls,
        image_path: str,
        scale: float = 1.0,
    ) -> arcade.Sprite:
        """
        Carrega e instancia um objeto/prop estático de quadro único (padrão 32x32px).
        """
        return cls.create_sprite(
            sheet_path=image_path,
            width=32,
            height=32,
            frame_count=1,
            scale=scale,
        )

    @classmethod
    def create_animated_prop(
        cls,
        spritesheet_path: str,
        scale: float = 1.0,
        frame_count: int = 6,
        fps: float = 8.0,
        frame_width: int = 32,
        frame_height: int = 32,
    ) -> AnimatedPropSprite:
        """
        Carrega e instancia um objeto/prop animado composto por quadros sequenciais de 32x32px em loop contínuo.
        """
        resolved_path = resolve_asset_path(spritesheet_path)
        textures: List[arcade.Texture] = []
        try:
            base_tex = arcade.load_texture(resolved_path)
            textures = [
                base_tex.crop(i * frame_width, 0, frame_width, frame_height)
                for i in range(frame_count)
            ]
        except Exception as e:
            logger.error(f"Erro ao carregar prop animado '{spritesheet_path}' (resolvido: '{resolved_path}'): {e}")

        prop_sprite = AnimatedPropSprite(
            textures=textures,
            fps=fps,
            scale=scale,
        )
        return prop_sprite

    @staticmethod
    def extract_badge_text(name: str) -> str:
        return extract_badge_text(name)

    @staticmethod
    def get_procedural_token_texture(
        name: str,
        is_player: bool = False,
        entity_type: Optional[Any] = None,
        base_size: int = 64,
    ) -> arcade.Texture:
        return get_procedural_token_texture(name, is_player, entity_type, base_size)

    @classmethod
    def create_entity_token_sprite(
        cls,
        name: str,
        is_player: bool = False,
        x: float = 0.0,
        y: float = 0.0,
        target_size: float = 64.0,
        is_hidden: bool = False,
        asset_path: Optional[str] = None,
        entity_type: Optional[Any] = None,
    ) -> arcade.Sprite:
        if asset_path and os.path.isfile(resolve_asset_path(asset_path)):
            sprite = cls.create_sprite(
                sheet_path=asset_path,
                x=x,
                y=y,
                target_size=target_size,
            )
        else:
            base_size = 64
            tex = cls.get_procedural_token_texture(
                name=name,
                is_player=is_player,
                entity_type=entity_type,
                base_size=base_size,
            )
            sprite = arcade.Sprite()
            sprite.texture = tex
            sprite.textures = [tex]
            sprite.scale = float(target_size) / float(base_size)
            sprite.position = (float(x), float(y))

        if is_hidden:
            sprite.alpha = 128
        else:
            sprite.alpha = 255

        return sprite

    @staticmethod
    def draw_tactical_token(
        name: str,
        is_player: bool = False,
        x: float = 0.0,
        y: float = 0.0,
        radius: float = 16.0,
        is_alive: bool = True,
        is_hidden: bool = False,
        is_selected: bool = False,
        is_active: bool = False,
        text_cache: Optional[Dict[str, arcade.Text]] = None,
        token_key: Optional[str] = None,
        entity_type: Optional[Any] = None,
    ) -> None:
        draw_tactical_token(
            name=name,
            is_player=is_player,
            x=x,
            y=y,
            radius=radius,
            is_alive=is_alive,
            is_hidden=is_hidden,
            is_selected=is_selected,
            is_active=is_active,
            text_cache=text_cache,
            token_key=token_key,
            entity_type=entity_type,
        )
