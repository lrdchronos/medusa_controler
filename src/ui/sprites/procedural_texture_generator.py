from typing import Optional, Dict, Any
import arcade
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from .token_badge_renderer import extract_badge_text

_TOKEN_TEXTURE_CACHE: Dict[str, arcade.Texture] = {}


def get_procedural_token_texture(
    name: str,
    is_player: bool = False,
    entity_type: Optional[Any] = None,
    base_size: int = 64,
) -> arcade.Texture:
    """Gera ou recupera do cache uma textura procedural de token tático circular Dark Fantasy."""
    short_name = extract_badge_text(name)
    if entity_type is not None:
        etype_str = str(entity_type.value if hasattr(entity_type, "value") else entity_type).lower()
    else:
        etype_str = "player" if is_player else "monster"

    cache_key = f"{short_name}_{etype_str.upper()}_{base_size}"

    if cache_key in _TOKEN_TEXTURE_CACHE:
        return _TOKEN_TEXTURE_CACHE[cache_key]

    img = PIL.Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)

    # Paleta: Jogador (Azul), Neutro/Magia (Dourado/Âmbar) vs Monstro (Carmim)
    if etype_str == "neutral":
        fill_color = (75, 55, 15, 255)
        border_color = (241, 196, 15, 255)
        inner_border = (255, 235, 59, 200)
        text_color = (255, 255, 255, 255)
    elif etype_str == "player" or is_player:
        fill_color = (25, 42, 86, 255)
        border_color = (74, 189, 255, 255)
        inner_border = (241, 196, 15, 200)
        text_color = (255, 255, 255, 255)
    else:
        fill_color = (120, 20, 20, 255)
        border_color = (235, 77, 75, 255)
        inner_border = (180, 50, 50, 200)
        text_color = (255, 240, 240, 255)

    margin = 3
    draw.ellipse(
        (margin, margin, base_size - margin, base_size - margin),
        fill=fill_color,
        outline=border_color,
        width=3,
    )
    draw.ellipse(
        (margin + 4, margin + 4, base_size - margin - 4, base_size - margin - 4),
        fill=None,
        outline=inner_border,
        width=1,
    )

    try:
        font = PIL.ImageFont.load_default()
    except Exception:
        font = None

    bbox = draw.textbbox((0, 0), short_name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (base_size - text_w) / 2
    text_y = (base_size - text_h) / 2 - 1

    draw.text((text_x, text_y), short_name, fill=text_color, font=font)

    tex = arcade.Texture(img)
    _TOKEN_TEXTURE_CACHE[cache_key] = tex
    return tex
