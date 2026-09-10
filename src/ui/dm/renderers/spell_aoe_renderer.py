import logging
from typing import Any
import arcade
from ....domain.models.spell_template import AoEShape
from ...utils.ui_constants import Colors, Typography, Dimensions, Spacing
from ...utils.ui_layout import FlowRow

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

        header_h = Dimensions.HEADER_HEIGHT_SUB
        body_h = 96.0 if not panel.is_collapsed else 0.0
        total_h = header_h + body_h
        center_y = top_y - total_h / 2.0

        panel._last_bounds = (panel_w / 2.0, center_y, panel_w - 24.0, total_h)

        # Fundo do Painel
        bg_col = Colors.BG_PANEL
        border_col = Colors.DANGER_BORDER if panel.is_active else Colors.BORDER_DEFAULT
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2.0, center_y, panel_w - 24.0, total_h), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2.0, center_y, panel_w - 24.0, total_h), border_col, 1.5)

        # 1. Barra de Cabeçalho / Título e Toggle de Colapso
        head_y = top_y - header_h / 2.0
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2.0, head_y, panel_w - 24.0, header_h), Colors.BG_CARD)
        arcade.draw_line(12.0, top_y - header_h, panel_w - 12.0, top_y - header_h, Colors.BORDER_DEFAULT, 1.0)

        # Título e Tag de Estado posicionados dinamicamente via FlowRow com 12px de gap
        active_badge = "[ATIVADO]" if panel.is_active else "[DESATIVADO]"
        badge_col = Colors.DANGER if panel.is_active else Colors.TEXT_MUTED
        title_str = "✨ PROJEÇÃO TÁTICA DE MAGIAS (AOE)"

        title_txt = panel._get_text(
            "sp_title",
            title_str,
            24.0,
            head_y,
            Colors.TEXT_GOLD,
            Typography.SIZE_MICRO,
            bold=True,
            anchor_x="left",
            anchor_y="center",
        )
        try:
            title_w = float(title_txt.content_width)
        except Exception:
            title_w = float(len(title_str) * Typography.SIZE_MICRO * 0.60)

        badge_txt = panel._get_text(
            "sp_badge",
            active_badge,
            0.0,
            head_y,
            badge_col,
            Typography.SIZE_MICRO - 1,
            bold=True,
            anchor_x="left",
            anchor_y="center",
        )
        try:
            badge_w = float(badge_txt.content_width)
        except Exception:
            badge_w = float(len(active_badge) * (Typography.SIZE_MICRO - 1) * 0.60)

        # FlowRow com start_x=24.0, center_y=head_y e gap=12.0
        head_row = FlowRow(start_x=24.0, center_y=head_y, gap=12.0, align_center=False)
        title_x, _ = head_row.add(title_w)
        title_txt.x = title_x
        title_txt.y = head_y
        title_txt.draw()

        badge_x, _ = head_row.add(badge_w)
        badge_txt.x = badge_x
        badge_txt.y = head_y
        badge_txt.draw()

        # Botão Colapsar / Expandir [ - ] / [ + ]
        col_icon = "[ - ]" if not panel.is_collapsed else "[ + ]"
        col_btn_x = panel_w - 32.0
        panel._get_text("sp_col_btn", col_icon, col_btn_x, head_y, Colors.TEXT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

        if panel.is_collapsed:
            return top_y - total_h - 8.0

        # 2. Linha 1: 6 Botões de Formatos Canônicos D&D 5E + Botão Ativar/Desativar
        row1_y = top_y - header_h - 18.0
        shapes = [
            (AoEShape.CIRCLE, "⚪ Círculo"),
            (AoEShape.SQUARE, "⬜ Quadrado"),
            (AoEShape.SPHERE, "🌐 Esfera"),
            (AoEShape.CUBE, "📦 Cubo"),
            (AoEShape.CONE, "📐 Cone"),
            (AoEShape.LINE, "📏 Linha"),
        ]

        act_btn_w = 100.0
        btn_margin = 4.0
        avail_shapes_w = panel_w - 36.0 - act_btn_w - 12.0
        btn_w = (avail_shapes_w - (len(shapes) - 1) * btn_margin) / len(shapes)
        btn_h = 22.0

        for i, (shape_enum, label) in enumerate(shapes):
            bx = 18.0 + i * (btn_w + btn_margin) + btn_w / 2.0
            is_sel = (panel.current_shape == shape_enum)

            if is_sel:
                btn_bg = Colors.DANGER if panel.is_active else Colors.BTN_PRIMARY_BG
                btn_border = Colors.ACCENT_GOLD
            else:
                btn_bg = Colors.BTN_DEFAULT_BG
                btn_border = Colors.BTN_DEFAULT_BORDER

            arcade.draw_rect_filled(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_bg)
            arcade.draw_rect_outline(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_border, 1.2)
            panel._get_text(f"sp_b_{shape_enum.value}", label, bx, row1_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center", anchor_y="center").draw()

        # Botão Ativar / Desativar Projeção
        act_btn_x = panel_w - 18.0 - act_btn_w / 2.0
        act_bg = Colors.DANGER if panel.is_active else Colors.SUCCESS
        act_border = Colors.DANGER_BORDER if panel.is_active else Colors.SUCCESS_BORDER
        act_label = "⚡ Desativar" if panel.is_active else "⚡ Ativar AoE"

        arcade.draw_rect_filled(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_bg)
        arcade.draw_rect_outline(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_border, 1.5)
        panel._get_text("sp_b_toggle", act_label, act_btn_x, row1_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center").draw()

        # 3. Linha 2: Inputs Numéricos (Tamanho, Largura se Linha, Altura Z, Pitch)
        # Padronização de uma linha de centro comum row2_y
        row2_y = top_y - header_h - 48.0
        inp_h = 20.0

        # Rótulo dinâmico do Tamanho (Raio / Lado / Comprimento)
        if panel.current_shape in (AoEShape.CIRCLE, AoEShape.SPHERE):
            size_lbl = "Raio:"
        elif panel.current_shape in (AoEShape.SQUARE, AoEShape.CUBE):
            size_lbl = "Lado:"
        else:
            size_lbl = "Comprimento:"

        # Criação do FlowRow para Linha 2 com gap canônico de 8px (Spacing.SM)
        row2 = FlowRow(start_x=18.0, center_y=row2_y, gap=float(Spacing.SM), align_center=False)

        # 3.1. Grupo 1: Tamanho (Raio / Lado / Comprimento)
        lbl_size_txt = panel._get_text("sp_lbl_size", size_lbl, 0.0, row2_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
        try:
            lbl_size_w = float(lbl_size_txt.content_width)
        except Exception:
            lbl_size_w = float(len(size_lbl) * Typography.SIZE_MICRO * 0.60)
        lbl_size_x, _ = row2.add(lbl_size_w)
        lbl_size_txt.x = lbl_size_x
        lbl_size_txt.y = row2_y
        lbl_size_txt.draw()

        size_inp_w = 44.0
        size_inp_x, _ = row2.add(size_inp_w)
        panel.size_input.draw(cx=size_inp_x + size_inp_w / 2.0, cy=row2_y, width=size_inp_w, height=inp_h, text_cache=panel._text_cache)

        unit_size_txt = panel._get_text("sp_unit_size", "ft", 0.0, row2_y, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
        try:
            unit_size_w = float(unit_size_txt.content_width)
        except Exception:
            unit_size_w = float(len("ft") * Typography.SIZE_MICRO * 0.60)
        unit_size_x, _ = row2.add(unit_size_w)
        unit_size_txt.x = unit_size_x
        unit_size_txt.y = row2_y
        unit_size_txt.draw()

        # 3.2. Grupo 2: Largura (apenas se AoEShape.LINE)
        if panel.current_shape == AoEShape.LINE:
            lbl_w_txt = panel._get_text("sp_lbl_w", "Largura:", 0.0, row2_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
            try:
                lbl_w_w = float(lbl_w_txt.content_width)
            except Exception:
                lbl_w_w = float(len("Largura:") * Typography.SIZE_MICRO * 0.60)
            lbl_w_x, _ = row2.add(lbl_w_w)
            lbl_w_txt.x = lbl_w_x
            lbl_w_txt.y = row2_y
            lbl_w_txt.draw()

            w_inp_w = 40.0
            w_inp_x, _ = row2.add(w_inp_w)
            panel.width_input.draw(cx=w_inp_x + w_inp_w / 2.0, cy=row2_y, width=w_inp_w, height=inp_h, text_cache=panel._text_cache)

            unit_w_txt = panel._get_text("sp_unit_w", "ft", 0.0, row2_y, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
            try:
                unit_w_w = float(unit_w_txt.content_width)
            except Exception:
                unit_w_w = float(len("ft") * Typography.SIZE_MICRO * 0.60)
            unit_w_x, _ = row2.add(unit_w_w)
            unit_w_txt.x = unit_w_x
            unit_w_txt.y = row2_y
            unit_w_txt.draw()

        # 3.3. Grupo 3: Altura Origem Z (pés)
        lbl_z_txt = panel._get_text("sp_lbl_z", "Alt Z:", 0.0, row2_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
        try:
            lbl_z_w = float(lbl_z_txt.content_width)
        except Exception:
            lbl_z_w = float(len("Alt Z:") * Typography.SIZE_MICRO * 0.60)
        lbl_z_x, _ = row2.add(lbl_z_w)
        lbl_z_txt.x = lbl_z_x
        lbl_z_txt.y = row2_y
        lbl_z_txt.draw()

        z_inp_w = 40.0
        z_inp_x, _ = row2.add(z_inp_w)
        panel.z_input.draw(cx=z_inp_x + z_inp_w / 2.0, cy=row2_y, width=z_inp_w, height=inp_h, text_cache=panel._text_cache)

        unit_z_txt = panel._get_text("sp_unit_z", "ft", 0.0, row2_y, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
        try:
            unit_z_w = float(unit_z_txt.content_width)
        except Exception:
            unit_z_w = float(len("ft") * Typography.SIZE_MICRO * 0.60)
        unit_z_x, _ = row2.add(unit_z_w)
        unit_z_txt.x = unit_z_x
        unit_z_txt.y = row2_y
        unit_z_txt.draw()

        # 3.4. Grupo 4: Inclinação Vertical (Pitch em graus)
        is_pitch_avail = panel.current_shape in (AoEShape.SPHERE, AoEShape.CUBE, AoEShape.CONE, AoEShape.LINE)
        pitch_col = Colors.TEXT_SECONDARY if is_pitch_avail else Colors.TEXT_DISABLED

        lbl_pitch_txt = panel._get_text("sp_lbl_pitch", "Pitch:", 0.0, row2_y, pitch_col, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
        try:
            lbl_pitch_w = float(lbl_pitch_txt.content_width)
        except Exception:
            lbl_pitch_w = float(len("Pitch:") * Typography.SIZE_MICRO * 0.60)
        lbl_pitch_x, _ = row2.add(lbl_pitch_w)
        lbl_pitch_txt.x = lbl_pitch_x
        lbl_pitch_txt.y = row2_y
        lbl_pitch_txt.draw()

        pitch_inp_w = 40.0
        pitch_inp_x, _ = row2.add(pitch_inp_w)
        panel.pitch_input.draw(cx=pitch_inp_x + pitch_inp_w / 2.0, cy=row2_y, width=pitch_inp_w, height=inp_h, text_cache=panel._text_cache)

        unit_pitch_txt = panel._get_text("sp_unit_pitch", "°", 0.0, row2_y, pitch_col, Typography.SIZE_MICRO, bold=False, anchor_x="left", anchor_y="center")
        try:
            unit_pitch_w = float(unit_pitch_txt.content_width)
        except Exception:
            unit_pitch_w = float(len("°") * Typography.SIZE_MICRO * 0.60)
        unit_pitch_x, _ = row2.add(unit_pitch_w)
        unit_pitch_txt.x = unit_pitch_x
        unit_pitch_txt.y = row2_y
        unit_pitch_txt.draw()

        # 4. Linha 3: Informações de Rotação e Controles Rápidos do Mouse
        row3_y = top_y - header_h - 78.0
        tpl = panel.combat_manager.active_spell_template
        rot_deg = tpl.rotation_degrees if tpl is not None else 0.0
        pitch_deg = tpl.pitch_degrees if tpl is not None else 0.0
        z_ft = tpl.origin_z_feet if tpl is not None else 0.0

        info_str = f"🔄 Yaw: {int(rot_deg)}° (Scroll ±2° | Ctrl ±15°)  •  Pitch: {int(pitch_deg)}° (Alt+Scroll ±15°)  •  Z: {int(z_ft)}ft"
        panel._get_text("sp_rot_info", info_str, 18.0, row3_y, Colors.TEXT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="left", anchor_y="center").draw()

        return top_y - total_h - 8.0
