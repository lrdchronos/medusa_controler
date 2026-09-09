import logging
import math
from typing import Optional, Tuple, Callable, Any, Dict
import arcade
from ....domain.models.entity import DynamicToken, EntityType, Entity
from ..fog_control_panel import FogControlPanel, FogTool, BrushMode

logger = logging.getLogger("src.ui.dm.tactical_minimap")


class MiniMapInputHandler:
    """
    Controlador especializado de eventos de entrada (mouse / scroll / drag-and-drop)
    para o Mini-Mapa Tático da DMWindow.
    """

    @staticmethod
    def screen_to_minimap_coords(
        screen_x: float,
        screen_y: float,
        window: arcade.Window,
        dm_camera: Any,
    ) -> Tuple[float, float]:
        """Converte coordenadas globais da tela para o espaço de coordenadas da DMCamera."""
        try:
            world_pos = dm_camera.unproject((screen_x, screen_y))
            return (float(world_pos[0]), float(world_pos[1]))
        except Exception:
            viewport = getattr(dm_camera, "viewport", None)
            left = getattr(viewport, "left", float(window.width) * 0.50 if window else 0.0)
            bottom = getattr(viewport, "bottom", 0.0)
            return (screen_x - left, screen_y - bottom)

    @staticmethod
    def resolve_coords(x: float, y: float, mini_map: Any) -> Tuple[float, float, bool]:
        """
        Resolve coordenadas para o espaço de desenho do minimapa.
        Suporta tanto coordenadas diretas locais (testes/legado) quanto coordenadas globais de tela.
        """
        draw_x, draw_y, draw_w, draw_h = mini_map._last_draw_rect
        if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
            return x, y, True

        mx, my = MiniMapInputHandler.screen_to_minimap_coords(x, y, mini_map.window, mini_map.dm_camera)
        is_inside = (draw_x <= mx <= draw_x + draw_w and draw_y <= my <= draw_y + draw_h)
        return mx, my, is_inside

    @staticmethod
    def on_mouse_press(
        x: float,
        y: float,
        button: int,
        modifiers: int,
        mini_map: Any,
    ) -> bool:
        mx, my, is_inside_map = MiniMapInputHandler.resolve_coords(x, y, mini_map)
        draw_x, draw_y, draw_w, draw_h = mini_map._last_draw_rect

        # 1. Modo PLACING_TOKEN
        if mini_map._is_placing_token and is_inside_map:
            if button == arcade.MOUSE_BUTTON_LEFT:
                grid_mgr = mini_map.combat_manager.grid_manager
                if grid_mgr is not None and mini_map._placing_token_data is not None:
                    cell_size = draw_w / float(grid_mgr.columns)
                    col = int(math.floor((mx - draw_x) / cell_size))
                    row = int(math.floor((my - draw_y) / cell_size))
                    size_str = mini_map._placing_token_data.get("size", "Medium")

                    if not mini_map.combat_manager.is_walkable_for_size(col, row, size_str):
                        logger.warning(f"TacticalMiniMap: célula ({col}, {row}) bloqueada para tamanho '{size_str}'. Posicionamento cancelado.")
                        return True

                    etype = mini_map._placing_token_data.get("entity_type", EntityType.NEUTRAL)
                    token_entity = DynamicToken(
                        name=mini_map._placing_token_data.get("name", "Token"),
                        max_hp=int(mini_map._placing_token_data.get("max_hp", 1)),
                        armor_class=int(mini_map._placing_token_data.get("armor_class", 10)),
                        entity_type=etype,
                        token_sprite=mini_map._placing_token_data.get("token_sprite"),
                        size=size_str,
                    )
                    slot = mini_map._placing_token_data.get("initiative_slot", "next")
                    mini_map.combat_manager.spawn_combatant(token_entity, (col, row), initiative_slot=slot)

                    if mini_map._on_token_spawn_callback is not None:
                        mini_map._on_token_spawn_callback(token_entity, (col, row), slot)

                    mini_map.cancel_placing_token()
                    return True

            elif button == arcade.MOUSE_BUTTON_RIGHT:
                mini_map.cancel_placing_token()
                return True

        # 2. Interação com Névoa de Guerra
        if mini_map.fog_panel is not None and mini_map.fog_panel.active_tool == FogTool.BRUSH and is_inside_map:
            if button in (arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT):
                mini_map._is_brushing = True
                is_clear = (button == arcade.MOUSE_BUTTON_RIGHT or mini_map.fog_panel.brush_mode == BrushMode.CLEAR)
                MiniMapInputHandler._apply_fog_brush(mx, my, is_clear, mini_map)
                return True

        # 3. Interação com Projeção Tática de Magias
        if mini_map.combat_manager.active_spell_template and mini_map.combat_manager.active_spell_template.is_active and is_inside_map:
            grid_mgr = mini_map.combat_manager.grid_manager
            feet_per_sq = float(mini_map.combat_manager.grid_data.get("feet_per_square", 5.0))
            cell_size = draw_w / float(grid_mgr.columns) if grid_mgr else 32.0
            world_x = ((mx - draw_x) / cell_size) * feet_per_sq
            world_y = ((my - draw_y) / cell_size) * feet_per_sq

            if button == arcade.MOUSE_BUTTON_LEFT:
                mini_map.combat_manager.update_spell_origin(world_x, world_y)
                return True
            elif button == arcade.MOUSE_BUTTON_RIGHT:
                mini_map.combat_manager.rotate_spell(15.0)
                return True

        # 4. Drag & Drop e Seleção de Tokens de Combate
        if is_inside_map:
            grid_mgr = mini_map.combat_manager.grid_manager
            if grid_mgr is not None:
                cell_size = draw_w / float(grid_mgr.columns)
                col = int(math.floor((mx - draw_x) / cell_size))
                row = int(math.floor((my - draw_y) / cell_size))

                clicked_token = None
                for c in mini_map.combat_manager.combatants:
                    size_str = getattr(c, "size", "Medium")
                    if hasattr(grid_mgr, "is_point_inside_creature"):
                        if grid_mgr.is_point_inside_creature(mx, my, c.position.get("x", 0), c.position.get("y", 0), size_str, cell_size, draw_x, draw_y):
                            clicked_token = c
                            break
                    else:
                        if c.position.get("x") == col and c.position.get("y") == row:
                            clicked_token = c
                            break

                if clicked_token is not None:
                    if button == arcade.MOUSE_BUTTON_LEFT:
                        if mini_map.session_manager.dm_window is not None:
                            mini_map.session_manager.dm_window.selected_combatant_uid = clicked_token.uid
                        mini_map._dragged_combatant_uid = clicked_token.uid
                        mini_map._drag_world_pos = (mx, my)
                        return True
                    elif button == arcade.MOUSE_BUTTON_RIGHT:
                        mini_map.combat_manager.toggle_combatant_visibility(clicked_token.uid)
                        return True

        return False

    @staticmethod
    def on_mouse_drag(
        x: float,
        y: float,
        dx: float,
        dy: float,
        buttons: int,
        modifiers: int,
        mini_map: Any,
    ) -> bool:
        mx, my, is_inside_map = MiniMapInputHandler.resolve_coords(x, y, mini_map)

        if mini_map._is_brushing and is_inside_map:
            is_clear = (buttons & arcade.MOUSE_BUTTON_RIGHT) or (mini_map.fog_panel and mini_map.fog_panel.brush_mode == BrushMode.CLEAR)
            MiniMapInputHandler._apply_fog_brush(mx, my, is_clear, mini_map)
            return True

        if mini_map._dragged_combatant_uid is not None:
            mini_map._drag_world_pos = (mx, my)
            return True

        return False

    @staticmethod
    def process_token_release(mx: float, my: float, mini_map: Any) -> None:
        """Processa a soltura de um token arrastado nas coordenadas mx, my."""
        draw_x, draw_y, draw_w, draw_h = mini_map._last_draw_rect
        grid_mgr = mini_map.combat_manager.grid_manager

        if grid_mgr is not None and (draw_x <= mx <= draw_x + draw_w and draw_y <= my <= draw_y + draw_h):
            cell_size = draw_w / float(grid_mgr.columns)
            target_col = int(math.floor((mx - draw_x) / cell_size))
            target_row = int(math.floor((my - draw_y) / cell_size))

            target_col = max(0, min(grid_mgr.columns - 1, target_col))
            target_row = max(0, min(grid_mgr.rows - 1, target_row))

            combatant = mini_map.combat_manager.get_combatant(mini_map._dragged_combatant_uid)
            size_str = getattr(combatant, "size", "Medium") if combatant else "Medium"

            if mini_map.combat_manager.is_walkable_for_size(target_col, target_row, size_str):
                mini_map.combat_manager.set_combatant_position(mini_map._dragged_combatant_uid, target_col, target_row)
            else:
                logger.warning(
                    f"TacticalMiniMap: Movimento bloqueado para '{combatant.name if combatant else 'Token'}' "
                    f"na célula ({target_col}, {target_row}) [porte: {size_str}]."
                )
        mini_map._dragged_combatant_uid = None

    @staticmethod
    def on_mouse_release(
        x: float,
        y: float,
        button: int,
        modifiers: int,
        mini_map: Any,
    ) -> None:
        if mini_map._is_brushing:
            mini_map._is_brushing = False
            mini_map._last_fog_cell = None

        if mini_map._dragged_combatant_uid is not None:
            mx, my, is_inside = MiniMapInputHandler.resolve_coords(x, y, mini_map)
            MiniMapInputHandler.process_token_release(mx, my, mini_map)

    @staticmethod
    def on_mouse_motion(
        x: float,
        y: float,
        dx: float,
        dy: float,
        mini_map: Any,
    ) -> None:
        mx, my, is_inside_map = MiniMapInputHandler.resolve_coords(x, y, mini_map)
        draw_x, draw_y, draw_w, draw_h = mini_map._last_draw_rect

        if mini_map._is_placing_token and is_inside_map:
            grid_mgr = mini_map.combat_manager.grid_manager
            if grid_mgr is not None:
                cell_size = draw_w / float(grid_mgr.columns)
                col = max(0, min(grid_mgr.columns - 1, int(math.floor((mx - draw_x) / cell_size))))
                row = max(0, min(grid_mgr.rows - 1, int(math.floor((my - draw_y) / cell_size))))
                mini_map._hover_grid_cell = (col, row)
        else:
            mini_map._hover_grid_cell = None

    @staticmethod
    def on_mouse_scroll(
        x: float,
        y: float,
        scroll_x: float,
        scroll_y: float,
        mini_map: Any,
        is_ctrl: bool = False,
        is_alt: bool = False,
    ) -> bool:
        mx, my, is_inside_map = MiniMapInputHandler.resolve_coords(x, y, mini_map)

        if mini_map.combat_manager.active_spell_template and mini_map.combat_manager.active_spell_template.is_active and is_inside_map:
            if is_alt:
                delta = 15.0 if scroll_y > 0 else -15.0
                mini_map.combat_manager.adjust_spell_pitch(delta)
                return True
            elif is_ctrl:
                delta = 15.0 if scroll_y > 0 else -15.0
                mini_map.combat_manager.rotate_spell(delta)
                return True
            else:
                delta = 2.0 if scroll_y > 0 else -2.0
                mini_map.combat_manager.rotate_spell(delta)
                return True

        return False

    @staticmethod
    def _apply_fog_brush(mx: float, my: float, is_clear: bool, mini_map: Any) -> None:
        draw_x, draw_y, draw_w, draw_h = mini_map._last_draw_rect
        grid_mgr = mini_map.combat_manager.grid_manager
        if grid_mgr is None:
            return

        cell_size = draw_w / float(grid_mgr.columns)
        col = int(math.floor((mx - draw_x) / cell_size))
        row = int(math.floor((my - draw_y) / cell_size))

        if not (0 <= col < grid_mgr.columns and 0 <= row < grid_mgr.rows):
            return

        if mini_map._last_fog_cell == (col, row):
            return

        mini_map._last_fog_cell = (col, row)
        brush_size = mini_map.fog_panel.brush_size if mini_map.fog_panel else 1
        radius = (brush_size - 1) // 2

        for dc in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                tc, tr = col + dc, row + dr
                if 0 <= tc < grid_mgr.columns and 0 <= tr < grid_mgr.rows:
                    if is_clear:
                        mini_map.combat_manager.fog_manager.clear_cell(tc, tr)
                    else:
                        mini_map.combat_manager.fog_manager.set_cell(tc, tr)
