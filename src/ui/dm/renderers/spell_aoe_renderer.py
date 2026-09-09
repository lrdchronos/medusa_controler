import logging
from typing import Any
import arcade
from ....domain.models.spell_template import AoEShape

logger = logging.getLogger(__name__)


class SpellAoERenderer:
    """
    Renderizador do painel de feitiços e projeção de áreas de efeito (Spell AoE Overlay).
    """

    @staticmethod
    def draw(panel: Any, panel_w: float, top_y: float) -> float:
        """
        Desenha o painel de feitiços e retorna a coordenada bottom_y para layout sequencial.
        """
        panel.sync_from_combat_manager()

        header_h = 28
        body_h = 96 if not panel.is_collapsed else 0
        total_h = header_h + body_h
        center_y = top_y - total_h / 2

        panel._last_bounds = (panel_w / 2, center_y, panel_w - 24, total_h)

        # Fundo do Painel
        bg_col = (18, 24, 34, 255)
        border_col = (231, 76, 60, 200) if panel.is_active else (50, 68, 95, 200)
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, center_y, panel_w - 24, total_h), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, center_y, panel_w - 24, total_h), border_col, 1.5)

        # 1. Barra de Cabeçalho / Título e Toggle de Colapso
        head_y = top_y - header_h / 2
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, head_y, panel_w - 24, header_h), (24, 32, 46, 255))
        arcade.draw_line(12, top_y - header_h, panel_w - 12, top_y - header_h, (50, 68, 95, 180), 1)

        # Título
        active_badge = " [ATIVADO]" if panel.is_active else " [DESATIVADO]"
        badge_col = (231, 76, 60, 255) if panel.is_active else (140, 155, 175, 255)
        title_str = "✨ PROJEÇÃO TÁTICA DE MAGIAS (AOE)"
        panel._get_text("sp_title", title_str, 24, head_y, (241, 196, 15, 255), 9, bold=True).draw()
        panel._get_text("sp_badge", active_badge, 245, head_y, badge_col, 8, bold=True).draw()

        # Botão Colapsar / Expandir [ - ] / [ + ]
        col_icon = "[ - ]" if not panel.is_collapsed else "[ + ]"
        col_btn_x = panel_w - 32
        panel._get_text("sp_col_btn", col_icon, col_btn_x, head_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

        if panel.is_collapsed:
            return top_y - total_h - 8

        # 2. Linha 1: 6 Botões de Formatos Canônicos D&D 5E + Botão Ativar/Desativar
        row1_y = top_y - header_h - 18
        shapes = [
            (AoEShape.CIRCLE, "⚪ Círculo"),
            (AoEShape.SQUARE, "⬜ Quadrado"),
            (AoEShape.SPHERE, "🌐 Esfera"),
            (AoEShape.CUBE, "📦 Cubo"),
            (AoEShape.CONE, "📐 Cone"),
            (AoEShape.LINE, "📏 Linha"),
        ]

        act_btn_w = 100
        btn_margin = 4
        avail_shapes_w = panel_w - 36 - act_btn_w - 12
        btn_w = (avail_shapes_w - (len(shapes) - 1) * btn_margin) / len(shapes)
        btn_h = 22

        for i, (shape_enum, label) in enumerate(shapes):
            bx = 18 + i * (btn_w + btn_margin) + btn_w / 2
            is_sel = (panel.current_shape == shape_enum)

            if is_sel:
                btn_bg = (192, 57, 43, 255) if panel.is_active else (41, 128, 185, 255)
                btn_border = (241, 196, 15, 255)
            else:
                btn_bg = (30, 40, 56, 255)
                btn_border = (55, 75, 105, 200)

            arcade.draw_rect_filled(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_bg)
            arcade.draw_rect_outline(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_border, 1.2)
            panel._get_text(f"sp_b_{shape_enum.value}", label, bx, row1_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão Ativar / Desativar Projeção
        act_btn_x = panel_w - 18 - act_btn_w / 2
        act_bg = (192, 57, 43, 255) if panel.is_active else (39, 174, 96, 255)
        act_border = (241, 196, 15, 255) if panel.is_active else (46, 204, 113, 255)
        act_label = "⚡ Desativar" if panel.is_active else "⚡ Ativar AoE"

        arcade.draw_rect_filled(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_bg)
        arcade.draw_rect_outline(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_border, 1.5)
        panel._get_text("sp_b_toggle", act_label, act_btn_x, row1_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 3. Linha 2: Inputs Numéricos (Tamanho, Largura se Linha, Altura Z, Pitch)
        row2_y = top_y - header_h - 48

        # Rótulo dinâmico do Tamanho (Raio / Lado / Comprimento)
        if panel.current_shape in (AoEShape.CIRCLE, AoEShape.SPHERE):
            size_lbl = "Raio:"
        elif panel.current_shape in (AoEShape.SQUARE, AoEShape.CUBE):
            size_lbl = "Lado:"
        else:
            size_lbl = "Comprimento:"

        cur_x = 18
        panel._get_text("sp_lbl_size", size_lbl, cur_x, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
        cur_x += 65
        panel.size_input.draw(cx=cur_x + 22, cy=row2_y, width=44, height=20, text_cache=panel._text_cache)
        cur_x += 48
        panel._get_text("sp_unit_size", "ft", cur_x, row2_y, (150, 165, 185, 255), 8, bold=False).draw()
        cur_x += 22

        # Rótulo e Input de Largura (se Linha)
        if panel.current_shape == AoEShape.LINE:
            panel._get_text("sp_lbl_w", "Largura:", cur_x, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
            cur_x += 46
            panel.width_input.draw(cx=cur_x + 20, cy=row2_y, width=40, height=20, text_cache=panel._text_cache)
            cur_x += 44
            panel._get_text("sp_unit_w", "ft", cur_x, row2_y, (150, 165, 185, 255), 8, bold=False).draw()
            cur_x += 22

        # Input de Altura Origem Z (pés)
        panel._get_text("sp_lbl_z", "Alt Z:", cur_x, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
        cur_x += 38
        panel.z_input.draw(cx=cur_x + 20, cy=row2_y, width=40, height=20, text_cache=panel._text_cache)
        cur_x += 44
        panel._get_text("sp_unit_z", "ft", cur_x, row2_y, (150, 165, 185, 255), 8, bold=False).draw()
        cur_x += 22

        # Input de Inclinação Vertical (Pitch)
        is_pitch_avail = panel.current_shape in (AoEShape.SPHERE, AoEShape.CUBE, AoEShape.CONE, AoEShape.LINE)
        pitch_col = (180, 195, 215, 255) if is_pitch_avail else (90, 105, 125, 160)
        panel._get_text("sp_lbl_pitch", "Pitch:", cur_x, row2_y, pitch_col, 8, bold=False).draw()
        cur_x += 38
        panel.pitch_input.draw(cx=cur_x + 20, cy=row2_y, width=40, height=20, text_cache=panel._text_cache)
        cur_x += 44
        panel._get_text("sp_unit_pitch", "°", cur_x, row2_y, pitch_col, 8, bold=False).draw()

        # 4. Linha 3: Informações de Rotação e Controles Rápidos do Mouse
        row3_y = top_y - header_h - 78
        tpl = panel.combat_manager.active_spell_template
        rot_deg = tpl.rotation_degrees if tpl is not None else 0.0
        pitch_deg = tpl.pitch_degrees if tpl is not None else 0.0
        z_ft = tpl.origin_z_feet if tpl is not None else 0.0

        info_str = f"🔄 Yaw: {int(rot_deg)}° (Scroll ±2° | Ctrl ±15°)  •  Pitch: {int(pitch_deg)}° (Alt+Scroll ±15°)  •  Z: {int(z_ft)}ft"
        panel._get_text("sp_rot_info", info_str, 18, row3_y, (241, 196, 15, 240), 8, bold=True).draw()

        return top_y - total_h - 8
