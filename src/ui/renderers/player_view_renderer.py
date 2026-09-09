import os
import logging
from typing import Optional, Dict, Any, Tuple
import arcade
from ...manager.session_manager import DisplayState
from ...domain.models.entity import EntityType
from ..sprites.sprite_factory import SpriteFactory
from ..utils.tilemap_renderer import TileMapRenderer
from ..utils.aoe_renderer import AoERenderer
from ..components.grid_cell_highlighter import GridCellHighlighter
from .token_status_renderer import TokenStatusRenderer

logger = logging.getLogger(__name__)


class PlayerViewRenderer:
    """
    Renderizador dedicado para a Tela dos Jogadores (PlayerWindow).
    Decompõe as rotinas de desenho para os três estados da Máquina de Exibição (DisplayState):
      - IDLE: Sigil místico animado e tipografia dark fantasy.
      - PROJECTION: Imagens de cenário/itens/NPCs em aspect-fit contido.
      - COMBAT: Mapa de combate, grade tática, tokens interpolados, névoa de guerra e HUD de iniciativa.
    """

    @staticmethod
    def draw_idle(
        window_width: float,
        window_height: float,
        idle_sprites: arcade.SpriteList,
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        """Desenha a tela de descanso/espera IDLE."""
        arcade.draw_rect_filled(
            arcade.XYWH(window_width / 2, window_height / 2, window_width, window_height),
            (14, 18, 24, 255),
        )

        idle_sprites.draw(pixelated=True)

        cx = window_width / 2
        cy = window_height / 2
        PlayerViewRenderer._render_text(
            "idle_title",
            "MEDUSA VTT",
            cx, cy - 40,
            (241, 196, 15, 255), 22, True, text_cache, anchor_x="center"
        )
        PlayerViewRenderer._render_text(
            "idle_sub",
            "Aguardando o Mestre...",
            cx, cy - 75,
            (140, 155, 175, 255), 11, False, text_cache, anchor_x="center"
        )

    @staticmethod
    def draw_projection(
        window_width: float,
        window_height: float,
        projected_image_path: Optional[str],
        texture_cache: Dict[str, arcade.Texture],
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        """Desenha a tela de projeção de imagens avulsas (PROJECTION)."""
        arcade.draw_rect_filled(
            arcade.XYWH(window_width / 2, window_height / 2, window_width, window_height),
            (10, 14, 20, 255),
        )

        tex = None
        if projected_image_path and os.path.isfile(projected_image_path):
            resolved = str(os.path.abspath(projected_image_path))
            if resolved not in texture_cache:
                try:
                    texture_cache[resolved] = arcade.load_texture(resolved)
                except Exception as e:
                    logger.error(f"Erro ao carregar textura para projeção: {e}")
                    texture_cache[resolved] = None
            tex = texture_cache.get(resolved)

        if tex is not None:
            tex_w = float(tex.width)
            tex_h = float(tex.height)

            pad_x = 32.0
            pad_y = 32.0
            avail_w = max(10.0, float(window_width) - (pad_x * 2))
            avail_h = max(10.0, float(window_height) - (pad_y * 2))

            tex_aspect = tex_w / max(1.0, tex_h)
            avail_aspect = avail_w / max(1.0, avail_h)

            if avail_aspect > tex_aspect:
                draw_h = avail_h
                draw_w = draw_h * tex_aspect
            else:
                draw_w = avail_w
                draw_h = draw_w / tex_aspect

            cx = float(window_width) / 2.0
            cy = float(window_height) / 2.0

            arcade.draw_texture_rect(tex, arcade.XYWH(cx, cy, draw_w, draw_h))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy, draw_w, draw_h), (70, 95, 130, 200), 2)
        else:
            cx = float(window_width) / 2.0
            cy = float(window_height) / 2.0
            arcade.draw_rect_filled(arcade.XYWH(cx, cy, 400, 200), (20, 26, 36, 220))
            PlayerViewRenderer._render_text(
                "proj_no_tex",
                "🖼️ Imagem em Exibição",
                cx, cy,
                (200, 210, 225, 255), 14, True, text_cache, anchor_x="center"
            )

    @staticmethod
    def draw_combat(
        window_width: float,
        window_height: float,
        combat_manager: Any,
        texture_cache: Dict[str, arcade.Texture],
        text_cache: Dict[str, arcade.Text],
        tilemap_renderer: Optional[TileMapRenderer],
        aoe_highlighter: Optional[GridCellHighlighter],
        token_sprites: Dict[str, Any],
        hud: Any,
    ) -> None:
        """Desenha a tela cheia de combate (COMBAT)."""
        arcade.draw_rect_filled(
            arcade.XYWH(window_width / 2, window_height / 2, window_width, window_height),
            (10, 14, 20, 255),
        )

        grid_mgr = combat_manager.grid_manager
        draw_rect = PlayerViewRenderer._calculate_draw_rect(window_width, window_height, grid_mgr)
        draw_x, draw_y, draw_w, draw_h = draw_rect

        # 1. Desenho do Mapa (TileMap ou Imagem)
        if combat_manager.map_type == "tilemap" and tilemap_renderer is not None and combat_manager.tile_map is not None:
            tile_map = combat_manager.tile_map
            cell_w = draw_w / tile_map.width
            cell_h = draw_h / tile_map.height
            tilemap_renderer.update_layout(draw_x, draw_y, cell_w, cell_h)
            tilemap_renderer.draw(pixelated=True)
        else:
            map_path = combat_manager.map_file
            tex = None
            if map_path and os.path.isfile(map_path) and not str(map_path).lower().endswith((".json", ".xml", ".txt", ".csv")):
                resolved = str(os.path.abspath(map_path))
                if resolved not in texture_cache:
                    try:
                        texture_cache[resolved] = arcade.load_texture(resolved)
                    except Exception:
                        texture_cache[resolved] = None
                tex = texture_cache.get(resolved)

            if tex is not None:
                arcade.draw_texture_rect(tex, arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h))
            else:
                arcade.draw_rect_filled(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (25, 35, 45, 255))

        arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (70, 95, 130, 220), 2)

        if grid_mgr is None:
            hud.draw(window_width, window_height)
            return

        cell_size = draw_w / float(grid_mgr.columns)

        # 2. Linhas da Grade Tática
        grid_color = (130, 205, 255, 40)
        for c in range(grid_mgr.columns + 1):
            lx = draw_x + float(c) * cell_size
            arcade.draw_line(lx, draw_y, lx, draw_y + draw_h, grid_color, 1.0)
        for r in range(grid_mgr.rows + 1):
            ly = draw_y + float(r) * cell_size
            arcade.draw_line(draw_x, ly, draw_x + draw_w, ly, grid_color, 1.0)

        # 3. Projeção Tática de Magias (AoE)
        if combat_manager.active_spell_template and combat_manager.active_spell_template.is_active:
            if aoe_highlighter is not None:
                aoe_cells = combat_manager.get_spell_aoe_cells()
                aoe_highlighter.highlighted_cells = aoe_cells
                aoe_highlighter.draw(draw_x, draw_y, cell_size)
            AoERenderer.draw_spell_overlay(
                template=combat_manager.active_spell_template,
                grid_origin_x=draw_x,
                grid_origin_y=draw_y,
                cell_size_px=cell_size,
                feet_per_square=float(combat_manager.grid_data.get("feet_per_square", 5.0)),
                is_dm=False,
            )

        # 4. Névoa de Guerra (Visão do Jogador: 100% Opaca / Oclusiva)
        fog_cells = combat_manager.fog_manager.get_fog_cells()
        fog_color = (10, 14, 20, 255)
        for col, row in fog_cells:
            if 0 <= col < grid_mgr.columns and 0 <= row < grid_mgr.rows:
                cx = draw_x + (col + 0.5) * cell_size
                cy = draw_y + (row + 0.5) * cell_size
                arcade.draw_rect_filled(arcade.XYWH(cx, cy, cell_size + 0.5, cell_size + 0.5), fog_color)

        # 5. Tokens dos Combatentes (Apenas Visíveis)
        active_char = combat_manager.active_character
        for combatant in combat_manager.combatants:
            if combatant.is_hidden:
                continue

            c_uid = combatant.uid
            size_str = getattr(combatant, "size", "Medium")
            footprint = grid_mgr.get_creature_pixel_size(size_str, cell_size) if hasattr(grid_mgr, "get_creature_pixel_size") else cell_size
            token_radius = max(8.0, (footprint / 2.0) - 2.0)

            token_sprite = token_sprites.get(c_uid)
            if token_sprite is not None:
                tx = token_sprite.center_x
                ty = token_sprite.center_y
            else:
                if hasattr(grid_mgr, "grid_to_world_center_for_size"):
                    tx, ty = grid_mgr.grid_to_world_center_for_size(combatant.position.get("x", 0), combatant.position.get("y", 0), size_str, cell_size, draw_x, draw_y)
                else:
                    tx = draw_x + (combatant.position.get("x", 0) + 0.5) * cell_size
                    ty = draw_y + (combatant.position.get("y", 0) + 0.5) * cell_size

            is_player = combatant.is_player or getattr(combatant, "entity_type", None) == EntityType.PLAYER
            is_active = (active_char is not None and active_char.uid == c_uid)
            etype = getattr(combatant, "entity_type", EntityType.PLAYER if is_player else EntityType.MONSTER)

            SpriteFactory.draw_tactical_token(
                name=combatant.name,
                is_player=is_player,
                x=tx,
                y=ty,
                radius=token_radius,
                is_alive=combatant.is_alive,
                is_hidden=False,
                is_selected=False,
                is_active=is_active,
                text_cache=text_cache,
                token_key=f"pw_{c_uid}",
                entity_type=etype,
            )

            # Órbita de Condições e Faixas de Saúde
            TokenStatusRenderer.draw_status_badges(
                entity=combatant,
                center_x=tx,
                center_y=ty,
                radius=token_radius,
                is_dm=False,
            )

        # 6. Fita de Iniciativa (InitiativeHUD) no Topo
        hud.draw(window_width, window_height)

    @staticmethod
    def _calculate_draw_rect(window_width: float, window_height: float, grid_mgr: Any) -> Tuple[float, float, float, float]:
        pad_x = 24.0
        pad_y = 24.0
        top_offset = 64.0
        avail_w = max(10.0, float(window_width) - (pad_x * 2))
        avail_h = max(10.0, float(window_height) - (pad_y * 2) - top_offset)

        aspect = 16.0 / 9.0
        if grid_mgr is not None and grid_mgr.columns > 0 and grid_mgr.rows > 0:
            aspect = float(grid_mgr.columns) / float(grid_mgr.rows)

        if (avail_w / avail_h) > aspect:
            draw_h = avail_h
            draw_w = draw_h * aspect
        else:
            draw_w = avail_w
            draw_h = draw_w / aspect

        draw_x = (float(window_width) - draw_w) / 2.0
        draw_y = (float(window_height) - top_offset - draw_h) / 2.0
        return (draw_x, draw_y, draw_w, draw_h)

    @staticmethod
    def _render_text(
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool,
        cache: Dict[str, arcade.Text],
        anchor_x: str = "left",
    ) -> None:
        cached = cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y="center",
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        try:
            cached.draw()
        except Exception:
            pass
