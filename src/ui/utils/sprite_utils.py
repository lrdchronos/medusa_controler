"""
Módulo de compatibilidade para SpriteFactory, CombatToken e utilitários de sprites.
Reexporta a implementação modularizada de src.ui.sprites.
"""

from ..sprites.animated_prop_sprite import AnimatedPropSprite, AnimatedTimeBasedSprite
from ..sprites.combat_token import CombatToken
from ..sprites.token_badge_renderer import extract_badge_text, draw_tactical_token
from ..sprites.procedural_texture_generator import get_procedural_token_texture
from ..sprites.sprite_factory import SpriteFactory, resolve_asset_path, resolve_asset_path as _resolve_asset_path

UIUtils = SpriteFactory
create_sprite = SpriteFactory.create_sprite
create_static_prop = SpriteFactory.create_static_prop
create_animated_prop = SpriteFactory.create_animated_prop
create_entity_token = SpriteFactory.create_entity_token_sprite

__all__ = [
    "SpriteFactory",
    "CombatToken",
    "AnimatedPropSprite",
    "AnimatedTimeBasedSprite",
    "extract_badge_text",
    "draw_tactical_token",
    "get_procedural_token_texture",
    "resolve_asset_path",
    "_resolve_asset_path",
    "UIUtils",
    "create_sprite",
    "create_static_prop",
    "create_animated_prop",
    "create_entity_token",
]
