import logging
import math
import time
from typing import Optional, Any
import arcade
from ...fog_control_panel import FogTool, BrushMode

logger = logging.getLogger(__name__)


class TacticalStageInputHandler:
    """
    Controlador especializado de eventos de entrada (mouse, scroll, drag & drop)
    para o Palco Tático (Etapa 2 do Criador de Encontros).
    """

    @staticmethod
    def handle_mouse_press(stage: Any, x: float, y: float, split_x: float, h: float, button: int) -> Optional[str]:
        """Processa cliques na sidebar ou no canvas tático."""
        if x < split_x:
            header_h = 56
            tab_bar_h = 42
            top_y = h - header_h - tab_bar_h
            return TacticalStageInputHandler.handle_sidebar_press(stage, x, y, split_x, top_y)

        return TacticalStageInputHandler.handle_canvas_press(stage, x, y, button)

    @staticmethod
    def handle_sidebar_press(stage: Any, x: float, y: float, panel_w: float, top_y: float) -> Optional[str]:
        # Cliques no Painel de Névoa de Guerra
        tip_y = (top_y - 18) - 20
        if stage.fog_panel.handle_click(x, y, panel_w, tip_y - 14):
            return None

        # Interação com itens visíveis da DiscreteScrollList
        visible_items = stage.scroll_list.visible_items
        for slot_idx, (idx, item) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = stage.scroll_list.get_slot_rect(slot_idx)
            left = slot_cx - slot_w / 2.0
            right = slot_cx + slot_w / 2.0
            top = slot_cy + slot_h / 2.0
            bottom = slot_cy - slot_h / 2.0

            if left <= x <= right and bottom <= y <= top:
                eye_x = slot_cx + slot_w / 2.0 - 14.0
                if abs(x - eye_x) <= 15:
                    item["is_hidden"] = not item["is_hidden"]
                    logger.info(f"Combatente '{item['name']}' visibilidade alternada para is_hidden={item['is_hidden']}")
                    return None
                else:
                    stage.dragged_combatant_idx = idx
                    stage.drag_pos = (float(x), float(y))
                    logger.info(f"Combatente '{item['name']}' selecionado na sidebar para posicionamento.")
                    return None

        # Botões Inferiores
        if stage.is_editing:
            btn_row1_y = 54
            btn_row2_y = 20
            btn_w = (panel_w - 36) / 2

            # ⬅️ Voltar
            b_back_x = 12 + btn_w / 2
            if abs(y - btn_row1_y) <= 14 and abs(x - b_back_x) <= (btn_w - 4) / 2:
                return "RETURN_TO_STAGE_1"

            # ❌ Cancelar Edição
            b_cancel_x = 12 + btn_w + btn_w / 2
            if abs(y - btn_row1_y) <= 14 and abs(x - b_cancel_x) <= (btn_w - 4) / 2:
                return "CANCEL_EDITING"

            # 💾 Salvar Alterações
            b_save_w = panel_w - 24
            b_save_x = panel_w / 2
            if abs(y - btn_row2_y) <= 16 and abs(x - b_save_x) <= b_save_w / 2:
                return "SAVE_ENCOUNTER"

        else:
            btn_y = 36
            btn_w = (panel_w - 36) / 2

            # ⬅️ Voltar
            b_back_x = 12 + btn_w / 2
            if abs(y - btn_y) <= 18 and abs(x - b_back_x) <= (btn_w - 4) / 2:
                return "RETURN_TO_STAGE_1"

            # 💾 Salvar Encontro
            b_save_x = 12 + btn_w + btn_w / 2
            if abs(y - btn_y) <= 18 and abs(x - b_save_x) <= (btn_w - 4) / 2:
                return "SAVE_ENCOUNTER"

        return None

    @staticmethod
    def handle_canvas_press(stage: Any, x: float, y: float, button: int) -> Optional[str]:
        now = time.time()
        is_double_click = False

        draw_x, draw_y, draw_w, draw_h = stage._last_map_rect
        res_x, res_y, res_w, res_h = stage._last_reserve_rect

        columns = stage.config_data.get("columns", 25)
        rows = stage.grid_manager.rows if stage.grid_manager else 14
        cell_w = draw_w / columns
        cell_h = draw_h / rows
        radius = (min(cell_w, cell_h) * 0.88) / 2.0
        reserve_slot_w = 46.0

        # Prioridade 1: Ferramenta de Névoa de Guerra ativa
        if stage.fog_panel.is_tool_active:
            if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                col = int(math.floor((x - draw_x) / cell_w))
                row = int(math.floor((y - draw_y) / cell_h))
                if 0 <= col < columns and 0 <= row < rows:
                    if stage.fog_panel.active_tool == FogTool.ADD:
                        stage.fog_manager.add_fog(col, row)
                    elif stage.fog_panel.active_tool == FogTool.REVEAL:
                        stage.fog_manager.remove_fog(col, row)
                    stage._is_brushing = True
                    stage._last_fog_cell = (col, row)
                    return None

        # Prioridade 2: Seleção e posicionamento de Tokens
        for idx, item in enumerate(reversed(stage.staging_combatants)):
            real_idx = len(stage.staging_combatants) - 1 - idx

            if item["placed"]:
                cx = draw_x + (item["col"] + 0.5) * cell_w
                cy = draw_y + (item["row"] + 0.5) * cell_h
            else:
                cx = res_x + 28 + real_idx * reserve_slot_w
                cy = res_y + res_h / 2 - 4

            dist_sq = (x - cx) ** 2 + (y - cy) ** 2
            if dist_sq <= (radius + 6) ** 2:
                if stage._last_clicked_idx == real_idx and (now - stage._last_click_time) <= 0.35:
                    is_double_click = True

                stage._last_click_time = now
                stage._last_clicked_idx = real_idx

                # Alternar Visibilidade
                if button == arcade.MOUSE_BUTTON_RIGHT or is_double_click:
                    item["is_hidden"] = not item["is_hidden"]
                    logger.info(f"Combatente '{item['name']}' visibilidade alternada para is_hidden={item['is_hidden']}")
                    return None

                # Inicia Drag & Drop
                if button == arcade.MOUSE_BUTTON_LEFT:
                    stage.dragged_combatant_idx = real_idx
                    stage.drag_pos = (float(x), float(y))
                    return None

        return None

    @staticmethod
    def handle_mouse_drag(stage: Any, x: float, y: float) -> None:
        if (
            stage._is_brushing
            and stage.fog_panel.is_tool_active
            and stage.fog_panel.brush_mode == BrushMode.CONTINUOUS
        ):
            draw_x, draw_y, draw_w, draw_h = stage._last_map_rect
            if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                columns = stage.config_data.get("columns", 25)
                rows = stage.grid_manager.rows if stage.grid_manager else 14
                cell_w = draw_w / columns
                cell_h = draw_h / rows
                col = int(math.floor((float(x) - draw_x) / cell_w))
                row = int(math.floor((float(y) - draw_y) / cell_h))
                if 0 <= col < columns and 0 <= row < rows:
                    if (col, row) != stage._last_fog_cell:
                        if stage.fog_panel.active_tool == FogTool.ADD:
                            stage.fog_manager.add_fog(col, row)
                        elif stage.fog_panel.active_tool == FogTool.REVEAL:
                            stage.fog_manager.remove_fog(col, row)
                        stage._last_fog_cell = (col, row)
            return

        if stage.dragged_combatant_idx is not None:
            stage.drag_pos = (float(x), float(y))

    @staticmethod
    def handle_mouse_release(stage: Any, x: float, y: float, split_x: float) -> None:
        if stage._is_brushing:
            stage._is_brushing = False
            stage._last_fog_cell = None
            return

        if stage.dragged_combatant_idx is not None:
            item = stage.staging_combatants[stage.dragged_combatant_idx]
            draw_x, draw_y, draw_w, draw_h = stage._last_map_rect

            # Snap-to-Grid sobre o mapa
            if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                columns = stage.config_data.get("columns", 25)
                rows = stage.grid_manager.rows if stage.grid_manager else 14
                cell_w = draw_w / columns
                cell_h = draw_h / rows

                col = int(math.floor((x - draw_x) / cell_w))
                row = int(math.floor((y - draw_y) / cell_h))

                clamped_col = max(0, min(columns - 1, col))
                clamped_row = max(0, min(rows - 1, row))

                item["placed"] = True
                item["col"] = clamped_col
                item["row"] = clamped_row
                logger.info(f"Token '{item['name']}' posicionado no grid: [{clamped_col}, {clamped_row}].")
            else:
                item["placed"] = False
                logger.info(f"Token '{item['name']}' retornado para a reserva.")

            stage.dragged_combatant_idx = None

    @staticmethod
    def handle_mouse_scroll(stage: Any, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        return stage.scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)
