import logging
import math
import time
from typing import Optional, Tuple, Callable, Any, Dict
import arcade
from ....domain.models.entity import DynamicToken, EntityType, Entity
from ....domain.rules.movement_calculator import MovementCalculator
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
        w = float(mini_map.window.width) if mini_map.window else 1280.0
        split_x = w * 0.50

        if x >= split_x:
            mx, my = MiniMapInputHandler.screen_to_minimap_coords(x, y, mini_map.window, mini_map.dm_camera)
        else:
            mx, my = x, y

        is_inside = (draw_x <= mx <= draw_x + draw_w and draw_y <= my <= draw_y + draw_h)
        if not is_inside and (draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h):
            return x, y, True

        return mx, my, is_inside

    @staticmethod
    def on_mouse_press(
        x: float,
        y: float,
        button: int,
        modifiers: int,
        mini_map: Any,
    ) -> bool:
        try:
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
            if mini_map.fog_panel is not None and getattr(mini_map.fog_panel, "is_tool_active", False) and is_inside_map:
                if button in (arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT):
                    is_clear = (mini_map.fog_panel.active_tool == FogTool.REVEAL)
                    if button == arcade.MOUSE_BUTTON_RIGHT:
                        is_clear = not is_clear
                    MiniMapInputHandler._apply_fog_brush(mx, my, is_clear, mini_map)
                    if mini_map.fog_panel.brush_mode == BrushMode.CONTINUOUS:
                        mini_map._is_brushing = True
                    return True

            # 3. Interação com Projeção Tática de Magias
            if mini_map.combat_manager.active_spell_template and mini_map.combat_manager.active_spell_template.is_active and is_inside_map:
                grid_mgr = mini_map.combat_manager.grid_manager
                if grid_mgr is not None:
                    cell_size = draw_w / float(grid_mgr.columns)
                    col_frac = (mx - draw_x) / cell_size
                    row_frac = (my - draw_y) / cell_size
                    world_x = col_frac * grid_mgr.cell_size
                    world_y = row_frac * grid_mgr.cell_size

                    if button == arcade.MOUSE_BUTTON_LEFT:
                        mini_map.combat_manager.update_spell_origin(world_x, world_y)
                        mini_map._is_dragging_spell = True
                        mini_map._is_aiming_spell = False
                        logger.info("TacticalMiniMap: Origem da magia posicionada em world=(%.1f, %.1f).", world_x, world_y)
                        return True
                    elif button == arcade.MOUSE_BUTTON_RIGHT:
                        tpl = mini_map.combat_manager.active_spell_template
                        ox, oy = tpl.origin_world
                        dx = world_x - ox
                        dy = world_y - oy
                        if math.hypot(dx, dy) > (grid_mgr.cell_size * 0.1):
                            target_deg = (math.degrees(math.atan2(dy, dx))) % 360.0
                            delta = (target_deg - tpl.rotation_degrees) % 360.0
                            mini_map.combat_manager.rotate_spell(delta)
                        else:
                            mini_map.combat_manager.rotate_spell(15.0)
                        mini_map._is_aiming_spell = True
                        mini_map._is_dragging_spell = False
                        return True

            # 4. Drag & Drop, Seleção de Tokens e Movimentação Ortogonal no Grid
            if is_inside_map:
                grid_mgr = mini_map.combat_manager.grid_manager
                if grid_mgr is not None:
                    cell_size = draw_w / float(grid_mgr.columns)
                    col = int(math.floor((mx - draw_x) / cell_size))
                    row = int(math.floor((my - draw_y) / cell_size))
                    col = max(0, min(grid_mgr.columns - 1, col))
                    row = max(0, min(grid_mgr.rows - 1, row))

                    clicked_token = None
                    from ....manager.grid_manager import GridManager
                    for c in mini_map.combat_manager.combatants:
                        size_str = getattr(c, "size", "Medium")
                        num_sq = GridManager.get_size_in_squares(size_str)
                        cx_min = c.position.get("x", 0)
                        cy_min = c.position.get("y", 0)
                        if cx_min <= col < cx_min + num_sq and cy_min <= row < cy_min + num_sq:
                            clicked_token = c
                            break

                    if clicked_token is not None:
                        if button == arcade.MOUSE_BUTTON_LEFT:
                            dm_win = getattr(mini_map.session_manager, "dm_window", None) if mini_map.session_manager else None
                            if dm_win is not None:
                                dm_win.selected_combatant_uid = clicked_token.uid
                            mini_map._dragged_combatant_uid = clicked_token.uid
                            mini_map._drag_world_pos = (mx, my)
                            mini_map._drag_start_pos = (mx, my)
                            mini_map._has_dragged = False
                            mini_map.selected_target_cell = None
                            logger.info(
                                "TacticalMiniMap: Token '%s' (%s) selecionado em (%d, %d). Pronto para arrasto livre ou clique ortogonal.",
                                clicked_token.name, clicked_token.uid, clicked_token.position.get("x", 0), clicked_token.position.get("y", 0)
                            )
                            return True
                        elif button == arcade.MOUSE_BUTTON_RIGHT:
                            mini_map.combat_manager.toggle_combatant_visibility(clicked_token.uid)
                            logger.info("TacticalMiniMap: Visibilidade alternada para token '%s' (oculto=%s).", clicked_token.name, clicked_token.is_hidden)
                            return True
                    else:
                        # Clique em célula vazia/sem token
                        if button == arcade.MOUSE_BUTTON_LEFT and mini_map.combat_manager.has_combat_started:
                            active_char = mini_map.combat_manager.active_character
                            dm_win = getattr(mini_map.session_manager, "dm_window", None) if mini_map.session_manager else None
                            sel_uid = getattr(dm_win, "selected_combatant_uid", None) if dm_win is not None else None

                            moving_entity = None
                            if sel_uid:
                                moving_entity = mini_map.combat_manager.get_combatant(sel_uid)
                            if moving_entity is None or not moving_entity.is_alive:
                                moving_entity = active_char

                            if moving_entity is not None and moving_entity.is_alive:
                                res = MovementCalculator.calculate_for_entity(moving_entity, mini_map.combat_manager)
                                target_cell = (col, row)

                                if res.is_reachable(target_cell):
                                    now = time.perf_counter()
                                    last_cell = getattr(mini_map, "_last_click_cell", None)
                                    last_time = getattr(mini_map, "_last_click_time", 0.0)
                                    is_double_click = (last_cell == target_cell and (now - last_time) < 0.4)

                                    if is_double_click:
                                        # Execução de movimento por clique duplo
                                        cost = res.get_cost(target_cell) or 0.0
                                        moving_entity.spend_movement(cost)
                                        mini_map.combat_manager.set_combatant_position(moving_entity.uid, col, row)
                                        mini_map.selected_target_cell = None
                                        mini_map._last_click_cell = None
                                        mini_map._last_click_time = 0.0
                                        logger.info(
                                            "Movimento ortogonal executado para '%s' em (%d, %d) [Custo: %.1f ft, Restante: %.1f ft].",
                                            moving_entity.name, col, row, cost, moving_entity.available_movement
                                        )
                                        return True
                                    else:
                                        # Seleção / Pré-visualização de destino por clique simples
                                        mini_map.selected_target_cell = target_cell
                                        mini_map._last_click_cell = target_cell
                                        mini_map._last_click_time = now
                                        cost = res.get_cost(target_cell) or 0.0
                                        logger.info(
                                            "Destino ortogonal selecionado para '%s': (%d, %d) [Custo: %.1f ft, Restante: %.1f ft].",
                                            moving_entity.name, col, row, cost, moving_entity.available_movement - cost
                                        )
                                        return True
                                else:
                                    # Clique fora da zona azul alcançável
                                    mini_map.selected_target_cell = None
                                    mini_map._last_click_cell = None
                                    mini_map._last_click_time = 0.0

            return False
        except Exception as e:
            logger.error("Erro inesperado em MiniMapInputHandler.on_mouse_press: %s", e, exc_info=True)
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
        try:
            mx, my, is_inside_map = MiniMapInputHandler.resolve_coords(x, y, mini_map)

            # 1. Pincel contínuo de Névoa de Guerra
            if mini_map._is_brushing and is_inside_map:
                is_clear = (mini_map.fog_panel.active_tool == FogTool.REVEAL) if mini_map.fog_panel else False
                if buttons & arcade.MOUSE_BUTTON_RIGHT:
                    is_clear = not is_clear
                MiniMapInputHandler._apply_fog_brush(mx, my, is_clear, mini_map)
                return True

            # 2. Arraste / Mira em tempo real de Projeção de Magias
            if mini_map.combat_manager.active_spell_template and mini_map.combat_manager.active_spell_template.is_active and is_inside_map:
                grid_mgr = mini_map.combat_manager.grid_manager
                if grid_mgr is not None:
                    draw_x, draw_y, draw_w, draw_h = mini_map._last_draw_rect
                    cell_size = draw_w / float(grid_mgr.columns)
                    col_frac = (mx - draw_x) / cell_size
                    row_frac = (my - draw_y) / cell_size
                    world_x = col_frac * grid_mgr.cell_size
                    world_y = row_frac * grid_mgr.cell_size

                    if (buttons & arcade.MOUSE_BUTTON_LEFT) or getattr(mini_map, "_is_dragging_spell", False):
                        mini_map.combat_manager.update_spell_origin(world_x, world_y)
                        return True
                    elif (buttons & arcade.MOUSE_BUTTON_RIGHT) or getattr(mini_map, "_is_aiming_spell", False):
                        tpl = mini_map.combat_manager.active_spell_template
                        ox, oy = tpl.origin_world
                        dwx = world_x - ox
                        dwy = world_y - oy
                        if math.hypot(dwx, dwy) > 0.01:
                            target_deg = (math.degrees(math.atan2(dwy, dwx))) % 360.0
                            delta = (target_deg - tpl.rotation_degrees) % 360.0
                            mini_map.combat_manager.rotate_spell(delta)
                        return True

            # 3. Arraste Livre (Drag & Drop) de Token
            if mini_map._dragged_combatant_uid is not None:
                mini_map._drag_world_pos = (mx, my)
                sx, sy = getattr(mini_map, "_drag_start_pos", (mx, my))
                if math.hypot(mx - sx, my - sy) > 5.0:
                    mini_map._has_dragged = True
                return True

            return False
        except Exception as e:
            logger.error("Erro inesperado em MiniMapInputHandler.on_mouse_drag: %s", e, exc_info=True)
            return False

    @staticmethod
    def process_token_release(mx: float, my: float, mini_map: Any) -> None:
        """Processa a soltura de um token arrastado (drag-and-drop / teleporte / ajuste livre)."""
        try:
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

                # Destino não compartilhável: verificar se já há outro combatente vivo no local
                is_occupied = any(
                    c.is_alive and c.uid != mini_map._dragged_combatant_uid and
                    c.position.get("x") == target_col and c.position.get("y") == target_row
                    for c in mini_map.combat_manager.combatants
                )

                if not is_occupied and mini_map.combat_manager.is_walkable_for_size(target_col, target_row, size_str):
                    # Deslocamento livre / Teleporte: NÃO debita movimento do turno (livre para qualquer token selecionado)
                    mini_map.combat_manager.set_combatant_position(mini_map._dragged_combatant_uid, target_col, target_row)
                    mini_map.selected_target_cell = None
                    mini_map._last_click_cell = None
                    logger.info(
                        "TacticalMiniMap: Drag & Drop livre concluído para '%s' (%s) para (%d, %d).",
                        combatant.name if combatant else mini_map._dragged_combatant_uid,
                        mini_map._dragged_combatant_uid,
                        target_col,
                        target_row,
                    )
                else:
                    logger.warning(
                        f"TacticalMiniMap: Movimento bloqueado para '{combatant.name if combatant else 'Token'}' "
                        f"na célula ({target_col}, {target_row}) [porte: {size_str}, ocupado={is_occupied}]."
                    )
        except Exception as e:
            logger.error("Erro inesperado em process_token_release: %s", e, exc_info=True)
        finally:
            mini_map._dragged_combatant_uid = None
            mini_map._has_dragged = False

    @staticmethod
    def on_mouse_release(
        x: float,
        y: float,
        button: int,
        modifiers: int,
        mini_map: Any,
    ) -> None:
        try:
            if mini_map._is_brushing:
                mini_map._is_brushing = False
                mini_map._last_fog_cell = None

            mini_map._is_dragging_spell = False
            mini_map._is_aiming_spell = False

            if mini_map._dragged_combatant_uid is not None:
                mx, my, is_inside = MiniMapInputHandler.resolve_coords(x, y, mini_map)
                MiniMapInputHandler.process_token_release(mx, my, mini_map)
        except Exception as e:
            logger.error("Erro inesperado em MiniMapInputHandler.on_mouse_release: %s", e, exc_info=True)

    @staticmethod
    def on_mouse_motion(
        x: float,
        y: float,
        dx: float,
        dy: float,
        mini_map: Any,
    ) -> None:
        try:
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
        except Exception as e:
            logger.error("Erro inesperado em MiniMapInputHandler.on_mouse_motion: %s", e, exc_info=True)

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
        try:
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
        except Exception as e:
            logger.error("Erro inesperado em MiniMapInputHandler.on_mouse_scroll: %s", e, exc_info=True)
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
        brush_size = getattr(mini_map.fog_panel, "brush_size", 1) if mini_map.fog_panel else 1
        radius = max(0, (brush_size - 1) // 2)

        for dc in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                tc, tr = col + dc, row + dr
                if 0 <= tc < grid_mgr.columns and 0 <= tr < grid_mgr.rows:
                    if is_clear:
                        mini_map.combat_manager.fog_manager.clear_cell(tc, tr)
                    else:
                        mini_map.combat_manager.fog_manager.set_cell(tc, tr)
