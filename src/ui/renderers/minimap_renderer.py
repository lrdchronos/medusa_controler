import os
import math
import logging
from typing import Optional, Dict, Any, Tuple
import arcade
from ...manager.session_manager import DisplayState
from ...domain.models.entity import Entity, EntityType
from ...domain.models.playablechar import PlayableCharacter
from ...domain.rules.movement_calculator import MovementCalculator
from ..sprites.sprite_factory import SpriteFactory
from ..utils.tilemap_renderer import TileMapRenderer
from ..utils.aoe_renderer import AoERenderer
from ..components.grid_cell_highlighter import GridCellHighlighter
from ..utils.ui_constants import Colors, Typography, Dimensions
from .token_status_renderer import TokenStatusRenderer

logger = logging.getLogger(__name__)


class MiniMapRenderer:
    """
    Renderizador dedicado para o Mini-Mapa Tático do Mestre (DM Tactical MiniMap).
    Separa a lógica gráfica pura e desenho OpenGL/Arcade da visualização do MiniMap.
    """

    @staticmethod
    def draw_content(
        window_width: float,
        window_height: float,
        draw_rect: Tuple[float, float, float, float],
        session_manager: Any,
        texture_cache: Dict[str, arcade.Texture],
        text_cache: Dict[str, arcade.Text],
        tilemap_renderer: Optional[TileMapRenderer],
        aoe_highlighter: Optional[GridCellHighlighter],
        movement_highlighter: Optional[GridCellHighlighter] = None,
        selected_target_cell: Optional[Tuple[int, int]] = None,
        selected_combatant_uid: Optional[str] = None,
        is_placing_token: bool = False,
        placing_token_data: Optional[Dict[str, Any]] = None,
        hover_grid_cell: Optional[Tuple[int, int]] = None,
        dragged_combatant_uid: Optional[str] = None,
        drag_world_pos: Tuple[float, float] = (0.0, 0.0),
    ) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        display_state = session_manager.display_state
        combat_manager = session_manager.combat_manager

        # 1. Fundo Geral
        arcade.draw_rect_filled(
            arcade.XYWH(window_width * 0.25, window_height * 0.50, window_width * 0.50, window_height),
            Colors.BG_DARK,
        )

        if display_state == DisplayState.IDLE:
            MiniMapRenderer._draw_idle_mirror(window_width, window_height, text_cache)
        elif display_state == DisplayState.PROJECTION:
            MiniMapRenderer._draw_projection_mirror(draw_rect, session_manager.projected_image_path, texture_cache, text_cache)
        elif display_state == DisplayState.COMBAT:
            MiniMapRenderer._draw_combat_map(
                draw_rect=draw_rect,
                combat_manager=combat_manager,
                texture_cache=texture_cache,
                text_cache=text_cache,
                tilemap_renderer=tilemap_renderer,
                aoe_highlighter=aoe_highlighter,
                movement_highlighter=movement_highlighter,
                selected_target_cell=selected_target_cell,
                selected_combatant_uid=selected_combatant_uid,
                is_placing_token=is_placing_token,
                placing_token_data=placing_token_data,
                hover_grid_cell=hover_grid_cell,
                dragged_combatant_uid=dragged_combatant_uid,
                drag_world_pos=drag_world_pos,
                session_manager=session_manager,
            )

    @staticmethod
    def _draw_idle_mirror(window_width: float, window_height: float, text_cache: Dict[str, arcade.Text]) -> None:
        cx = window_width * 0.25
        cy = window_height * 0.50
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, 320, 100), Colors.BG_CARD)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, 320, 100), Colors.BORDER_DEFAULT, 1.5)
        MiniMapRenderer._render_text(
            "mm_idle_title",
            "🛡️ TELA DOS JOGADORES: IDLE",
            cx, cy + 18,
            Colors.TEXT_GOLD, Typography.SIZE_SUBHEADER - 1, True, text_cache, anchor_x="center"
        )
        MiniMapRenderer._render_text(
            "mm_idle_sub",
            "(Sigil Místico e Descanso Ativos)",
            cx, cy - 14,
            Colors.TEXT_MUTED, Typography.SIZE_MICRO, False, text_cache, anchor_x="center"
        )

    @staticmethod
    def _draw_projection_mirror(
        draw_rect: Tuple[float, float, float, float],
        projected_image_path: Optional[str],
        texture_cache: Dict[str, arcade.Texture],
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        cx = draw_x + draw_w / 2
        cy = draw_y + draw_h / 2

        tex = None
        if projected_image_path and os.path.isfile(projected_image_path):
            resolved = str(os.path.abspath(projected_image_path))
            if resolved not in texture_cache:
                try:
                    texture_cache[resolved] = arcade.load_texture(resolved)
                except Exception:
                    texture_cache[resolved] = None
            tex = texture_cache.get(resolved)

        if tex is not None:
            tex_w = float(tex.width)
            tex_h = float(tex.height)
            tex_aspect = tex_w / max(1.0, tex_h)
            avail_w = max(10.0, draw_w)
            avail_h = max(10.0, draw_h)
            avail_aspect = avail_w / max(1.0, avail_h)

            if avail_aspect > tex_aspect:
                img_h = avail_h
                img_w = img_h * tex_aspect
            else:
                img_w = avail_w
                img_h = img_w / tex_aspect

            arcade.draw_texture_rect(tex, arcade.XYWH(cx, cy, img_w, img_h))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy, img_w, img_h), Colors.BORDER_DEFAULT, 2)
        else:
            arcade.draw_rect_filled(arcade.XYWH(cx, cy, draw_w, draw_h), Colors.BG_PANEL)
            MiniMapRenderer._render_text(
                "mm_proj_no_tex",
                "🖼️ Imagem Projetada",
                cx, cy,
                Colors.TEXT_PRIMARY, Typography.SIZE_LABEL, True, text_cache, anchor_x="center"
            )

    @staticmethod
    def _draw_combat_map(
        draw_rect: Tuple[float, float, float, float],
        combat_manager: Any,
        texture_cache: Dict[str, arcade.Texture],
        text_cache: Dict[str, arcade.Text],
        tilemap_renderer: Optional[TileMapRenderer],
        aoe_highlighter: Optional[GridCellHighlighter],
        movement_highlighter: Optional[GridCellHighlighter] = None,
        selected_target_cell: Optional[Tuple[int, int]] = None,
        selected_combatant_uid: Optional[str] = None,
        is_placing_token: bool = False,
        placing_token_data: Optional[Dict[str, Any]] = None,
        hover_grid_cell: Optional[Tuple[int, int]] = None,
        dragged_combatant_uid: Optional[str] = None,
        drag_world_pos: Tuple[float, float] = (0.0, 0.0),
        session_manager: Any = None,
    ) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        grid_mgr = combat_manager.grid_manager

        # 1. Mapa Base (TileMap ou Imagem)
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
                arcade.draw_rect_filled(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), Colors.BG_PANEL)

        # Borda externa do mapa
        arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), Colors.BORDER_DEFAULT, 2)

        if grid_mgr is None:
            return

        cell_size = draw_w / float(grid_mgr.columns)

        # 2. Grade Tática
        MiniMapRenderer._draw_grid_overlay(draw_rect, grid_mgr, cell_size)

        # 2.5 Hierarquia de Modos e Zona de Alcance de Movimento Ortogonal (4-Vizinhança)
        is_fog_tool_active = False
        dm_win = getattr(session_manager, "dm_window", None) if session_manager else None
        if dm_win is not None and hasattr(dm_win, "combat_tab") and getattr(dm_win.combat_tab, "fog_panel", None):
            is_fog_tool_active = dm_win.combat_tab.fog_panel.is_tool_active

        is_spell_active = bool(combat_manager.active_spell_template and combat_manager.active_spell_template.is_active)

        if not is_fog_tool_active and not is_spell_active:
            MiniMapRenderer._draw_movement_overlay(
                draw_rect=draw_rect,
                combat_manager=combat_manager,
                grid_mgr=grid_mgr,
                cell_size=cell_size,
                movement_highlighter=movement_highlighter,
                selected_target_cell=selected_target_cell,
                selected_combatant_uid=selected_combatant_uid,
                text_cache=text_cache,
            )
        elif movement_highlighter is not None:
            movement_highlighter.clear()

        # 3. Projeção de Magias (AoE)
        if is_spell_active:
            if aoe_highlighter is not None:
                aoe_cells = combat_manager.get_spell_aoe_cells()
                aoe_highlighter.highlighted_cells = aoe_cells
                aoe_highlighter.draw(draw_x=draw_x, draw_y=draw_y, cell_w=cell_size, cell_h=cell_size)
            AoERenderer.draw_spell_overlay(
                template=combat_manager.active_spell_template,
                grid_origin_x=draw_x,
                grid_origin_y=draw_y,
                cell_size_px=cell_size,
                grid_manager=grid_mgr,
                feet_per_square=float(combat_manager.grid_data.get("feet_per_square", 5.0)),
                is_dm=True,
            )
        elif aoe_highlighter is not None:
            aoe_highlighter.clear()

        # 4. Névoa de Guerra (Visão do Mestre: Translúcida)
        MiniMapRenderer._draw_fog_overlay(draw_rect, combat_manager.fog_manager, grid_mgr, cell_size)

        # 5. Combatentes e Tokens
        MiniMapRenderer._draw_tokens(
            draw_rect=draw_rect,
            combat_manager=combat_manager,
            grid_mgr=grid_mgr,
            cell_size=cell_size,
            text_cache=text_cache,
            dragged_combatant_uid=dragged_combatant_uid,
            drag_world_pos=drag_world_pos,
            session_manager=session_manager,
        )

        # 6. Preview de Posicionamento de Token
        if is_placing_token and placing_token_data is not None and hover_grid_cell is not None:
            MiniMapRenderer._draw_placing_token_preview(
                draw_rect=draw_rect,
                token_data=placing_token_data,
                grid_cell=hover_grid_cell,
                grid_mgr=grid_mgr,
                cell_size=cell_size,
                combat_manager=combat_manager,
                text_cache=text_cache,
            )

    @staticmethod
    def _draw_movement_overlay(
        draw_rect: Tuple[float, float, float, float],
        combat_manager: Any,
        grid_mgr: Any,
        cell_size: float,
        movement_highlighter: Optional[GridCellHighlighter],
        selected_target_cell: Optional[Tuple[int, int]],
        selected_combatant_uid: Optional[str],
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        """Renderiza a zona azul de alcance ortogonal (4-vizinhança) e a pré-visualização de custo."""
        if movement_highlighter is None or not combat_manager.has_combat_started:
            if movement_highlighter is not None:
                movement_highlighter.clear()
            return

        active_char = combat_manager.active_character
        entity_to_move = None
        if selected_combatant_uid:
            entity_to_move = combat_manager.get_combatant(selected_combatant_uid)
        if entity_to_move is None or not entity_to_move.is_alive:
            entity_to_move = active_char

        if entity_to_move is None or not entity_to_move.is_alive:
            movement_highlighter.clear()
            return

        available_mov = getattr(entity_to_move, "available_movement", float(entity_to_move.speed))
        if available_mov <= 0.0:
            movement_highlighter.clear()
            return

        draw_x, draw_y, draw_w, draw_h = draw_rect
        res = MovementCalculator.calculate_for_entity(entity_to_move, combat_manager)

        if not res.reachable_cells:
            movement_highlighter.clear()
            return

        # Cores Canônicas: Azul translúcido e Azul vivo
        cell_colors: Dict[Tuple[int, int], Tuple[int, int, int, int]] = {}
        for cell in res.reachable_cells:
            if selected_target_cell is not None and cell == selected_target_cell:
                cell_colors[cell] = (52, 152, 219, 210)
            else:
                cell_colors[cell] = (41, 128, 185, 90)

        movement_highlighter.set_cells(cell_colors)
        movement_highlighter.draw(draw_x=draw_x, draw_y=draw_y, cell_w=cell_size, cell_h=cell_size)

        # Destino Selecionado: Borda contrastante e Badge Flutuante de Custo
        if selected_target_cell is not None and selected_target_cell in res.reachable_cells:
            sc_x = draw_x + (selected_target_cell[0] + 0.5) * cell_size
            sc_y = draw_y + (selected_target_cell[1] + 0.5) * cell_size

            arcade.draw_rect_outline(arcade.XYWH(sc_x, sc_y, cell_size, cell_size), Colors.TEXT_PRIMARY, 2.0)

            cost = res.get_cost(selected_target_cell) or 0.0
            remaining = available_mov - cost
            badge_w = 175.0
            badge_h = 22.0
            badge_y = min(draw_y + draw_h - 14, sc_y + cell_size * 0.75 + 10)

            arcade.draw_rect_filled(arcade.XYWH(sc_x, badge_y, badge_w, badge_h), Colors.BG_DARK)
            arcade.draw_rect_outline(arcade.XYWH(sc_x, badge_y, badge_w, badge_h), Colors.INFO_BORDER, 1.2)
            MiniMapRenderer._render_text(
                "mm_cost_badge",
                f"Custo: {cost:.0f} ft / Restante: {remaining:.0f} ft",
                sc_x,
                badge_y,
                Colors.TEXT_GOLD,
                Typography.SIZE_MICRO - 1,
                True,
                text_cache,
                anchor_x="center",
            )

    @staticmethod
    def _draw_grid_overlay(draw_rect: Tuple[float, float, float, float], grid_mgr: Any, cell_size: float) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        grid_color = Colors.GRID_LINE
        for c in range(grid_mgr.columns + 1):
            lx = draw_x + float(c) * cell_size
            arcade.draw_line(lx, draw_y, lx, draw_y + draw_h, grid_color, 1.0)
        for r in range(grid_mgr.rows + 1):
            ly = draw_y + float(r) * cell_size
            arcade.draw_line(draw_x, ly, draw_x + draw_w, ly, grid_color, 1.0)

    @staticmethod
    def _draw_fog_overlay(draw_rect: Tuple[float, float, float, float], fog_mgr: Any, grid_mgr: Any, cell_size: float) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        if fog_mgr is None:
            return
        fog_cells = fog_mgr.get_fogged_cells() if hasattr(fog_mgr, "get_fogged_cells") else fog_mgr.get_fog_cells()
        fog_color = Colors.FOG_OVERLAY
        fog_border = Colors.FOG_BORDER

        for col, row in fog_cells:
            if 0 <= col < grid_mgr.columns and 0 <= row < grid_mgr.rows:
                cx = draw_x + (col + 0.5) * cell_size
                cy = draw_y + (row + 0.5) * cell_size
                arcade.draw_rect_filled(arcade.XYWH(cx, cy, cell_size, cell_size), fog_color)
                arcade.draw_rect_outline(arcade.XYWH(cx, cy, cell_size, cell_size), fog_border, 1.0)

    @staticmethod
    def _draw_tokens(
        draw_rect: Tuple[float, float, float, float],
        combat_manager: Any,
        grid_mgr: Any,
        cell_size: float,
        text_cache: Dict[str, arcade.Text],
        dragged_combatant_uid: Optional[str],
        drag_world_pos: Tuple[float, float],
        session_manager: Any,
    ) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        active_char = combat_manager.active_character
        dm_win = getattr(session_manager, "dm_window", None) if session_manager else None

        for combatant in combat_manager.combatants:
            c_uid = combatant.uid
            pos = combatant.position
            col = pos.get("x", 0)
            row = pos.get("y", 0)

            size_str = getattr(combatant, "size", "Medium")
            footprint = grid_mgr.get_creature_pixel_size(size_str, cell_size) if hasattr(grid_mgr, "get_creature_pixel_size") else cell_size
            token_radius = max(8.0, (footprint / 2.0) - 2.0)

            if dragged_combatant_uid == c_uid:
                tx, ty = drag_world_pos
            else:
                if hasattr(grid_mgr, "grid_to_world_center_for_size"):
                    tx, ty = grid_mgr.grid_to_world_center_for_size(col, row, size_str, cell_size, draw_x, draw_y)
                else:
                    tx = draw_x + (col + 0.5) * cell_size
                    ty = draw_y + (row + 0.5) * cell_size

            is_player = combatant.is_player or getattr(combatant, "entity_type", None) == EntityType.PLAYER
            is_active = (active_char is not None and active_char.uid == c_uid)
            is_selected = (dm_win is not None and getattr(dm_win, "selected_combatant_uid", None) == c_uid)

            etype = getattr(combatant, "entity_type", EntityType.PLAYER if is_player else EntityType.MONSTER)

            SpriteFactory.draw_tactical_token(
                name=combatant.name,
                is_player=is_player,
                x=tx,
                y=ty,
                radius=token_radius,
                is_alive=combatant.is_alive,
                is_hidden=combatant.is_hidden,
                is_selected=is_selected,
                is_active=is_active,
                text_cache=text_cache,
                token_key=f"mm_{c_uid}",
                entity_type=etype,
            )

            # Órbita de Condições e Badges de Status
            TokenStatusRenderer.draw_status_badges(
                entity=combatant,
                center_x=tx,
                center_y=ty,
                radius=token_radius,
                is_dm=True,
            )

    @staticmethod
    def _draw_placing_token_preview(
        draw_rect: Tuple[float, float, float, float],
        token_data: Dict[str, Any],
        grid_cell: Tuple[int, int],
        grid_mgr: Any,
        cell_size: float,
        combat_manager: Any,
        text_cache: Dict[str, arcade.Text],
    ) -> None:
        draw_x, draw_y, draw_w, draw_h = draw_rect
        col, row = grid_cell
        size_str = token_data.get("size", "Medium")

        is_walkable = combat_manager.is_walkable_for_size(col, row, size_str)
        t_name = token_data.get("name", "Token")
        etype = token_data.get("entity_type", EntityType.NEUTRAL)

        if hasattr(grid_mgr, "grid_to_world_center_for_size"):
            cx, cy = grid_mgr.grid_to_world_center_for_size(col, row, size_str, cell_size, draw_x, draw_y)
        else:
            cx = draw_x + (col + 0.5) * cell_size
            cy = draw_y + (row + 0.5) * cell_size

        footprint = grid_mgr.get_creature_pixel_size(size_str, cell_size) if hasattr(grid_mgr, "get_creature_pixel_size") else cell_size
        token_radius = max(8.0, (footprint / 2.0) - 2.0)

        box_bg = (46, 204, 113, 80) if is_walkable else (231, 76, 60, 100)
        box_bd = Colors.SUCCESS_BORDER if is_walkable else Colors.DANGER_BORDER
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, footprint, footprint), box_bg)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, footprint, footprint), box_bd, 2.0)

        SpriteFactory.draw_tactical_token(
            name=t_name,
            x=cx,
            y=cy,
            radius=token_radius,
            is_alive=True,
            is_hidden=False,
            is_selected=True,
            is_active=False,
            text_cache=text_cache,
            token_key="preview_placing_tkn",
            entity_type=etype,
        )

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
                font_name=Typography.FONT_FAMILY_UI,
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
