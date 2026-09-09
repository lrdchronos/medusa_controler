import logging
from typing import Optional, Dict, Any, Tuple
import arcade
from ...manager.session_manager import SessionManager
from ...domain.models.spell_template import SpellTemplate, AoEShape, SpellShape
from ..utils.text_input import SmartTextInput

logger = logging.getLogger(__name__)


class SpellAoEPanel:
    """
    Painel de Controle de Magias e Áreas de Efeito (Spell AoE Overlay) na DMWindow.
    Permite selecionar os 6 formatos canônicos de D&D 5E (Círculo, Quadrado, Esfera, Cubo, Cone, Linha),
    ativar/desativar projeção tática, configurar dimensões (raio/lado/comprimento, largura, altitude Z, pitch)
    via SmartTextInput e acompanhar rotação e inclinação vertical em tempo real.
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager

        self.is_collapsed: bool = False
        self.current_shape: AoEShape = AoEShape.CIRCLE
        self.current_size_feet: float = 20.0
        self.current_width_feet: float = 5.0
        self.current_origin_z_feet: float = 0.0
        self.current_pitch_degrees: float = 0.0
        self.is_active: bool = False

        self._text_cache: Dict[str, arcade.Text] = {}

        # 1. Input: Tamanho / Raio / Lado / Comprimento
        self.size_input = SmartTextInput(
            widget_id="spell_size_in",
            placeholder="20",
            initial_text="20",
            max_length=5,
            font_size=9,
            width=50.0,
            height=22.0,
            padding_left=5.0,
        )

        # 2. Input: Largura (para Linha)
        self.width_input = SmartTextInput(
            widget_id="spell_width_in",
            placeholder="5",
            initial_text="5",
            max_length=5,
            font_size=9,
            width=46.0,
            height=22.0,
            padding_left=5.0,
        )

        # 3. Input: Altura Origem Z
        self.z_input = SmartTextInput(
            widget_id="spell_z_in",
            placeholder="0",
            initial_text="0",
            max_length=5,
            font_size=9,
            width=46.0,
            height=22.0,
            padding_left=5.0,
        )

        # 4. Input: Inclinação Vertical Pitch
        self.pitch_input = SmartTextInput(
            widget_id="spell_pitch_in",
            placeholder="0",
            initial_text="0",
            max_length=5,
            font_size=9,
            width=46.0,
            height=22.0,
            padding_left=5.0,
        )

        self._last_bounds: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

        # Sincroniza estado inicial se já houver template ativo
        self.sync_from_combat_manager()

    def _get_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool = True,
        anchor_x: str = "left",
        anchor_y: str = "center",
    ) -> arcade.Text:
        cached = self._text_cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            self._text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
        return cached

    def sync_from_combat_manager(self) -> None:
        """Sincroniza os controles visuais a partir do template ativo no CombatManager."""
        tpl = self.combat_manager.active_spell_template
        if tpl is not None:
            self.current_shape = tpl.shape
            self.current_size_feet = tpl.size_feet
            self.current_width_feet = tpl.width_feet
            self.current_origin_z_feet = tpl.origin_z_feet
            self.current_pitch_degrees = tpl.pitch_degrees
            self.is_active = tpl.is_active

            # Atualiza texto dos inputs se não estiverem focados
            if not self.size_input.is_focused:
                size_str = str(int(tpl.size_feet)) if tpl.size_feet.is_integer() else f"{tpl.size_feet:.1f}"
                self.size_input.text = size_str
            if not self.width_input.is_focused:
                width_str = str(int(tpl.width_feet)) if tpl.width_feet.is_integer() else f"{tpl.width_feet:.1f}"
                self.width_input.text = width_str
            if not self.z_input.is_focused:
                z_str = str(int(tpl.origin_z_feet)) if tpl.origin_z_feet.is_integer() else f"{tpl.origin_z_feet:.1f}"
                self.z_input.text = z_str
            if not self.pitch_input.is_focused:
                pitch_str = str(int(tpl.pitch_degrees)) if tpl.pitch_degrees.is_integer() else f"{tpl.pitch_degrees:.1f}"
                self.pitch_input.text = pitch_str

    def sync_to_combat_manager(self) -> None:
        """Propaga as configurações da UI para o CombatManager."""
        try:
            val_size = float(self.size_input.text.strip())
            if val_size > 0:
                self.current_size_feet = val_size
        except Exception:
            pass

        try:
            val_width = float(self.width_input.text.strip())
            if val_width > 0:
                self.current_width_feet = val_width
        except Exception:
            pass

        try:
            val_z = float(self.z_input.text.strip())
            self.current_origin_z_feet = val_z
        except Exception:
            pass

        try:
            val_pitch = float(self.pitch_input.text.strip())
            self.current_pitch_degrees = val_pitch % 360.0
        except Exception:
            pass

        tpl = self.combat_manager.active_spell_template
        rot = tpl.rotation_degrees if tpl is not None else 0.0
        origin = tpl.origin_world if tpl is not None else (0.0, 0.0)

        new_tpl = SpellTemplate(
            shape=self.current_shape,
            size_feet=self.current_size_feet,
            width_feet=self.current_width_feet,
            rotation_degrees=rot,
            origin_world=origin,
            origin_z_feet=self.current_origin_z_feet,
            pitch_degrees=self.current_pitch_degrees,
            is_active=self.is_active,
            is_visible=True,
        )
        self.combat_manager.set_spell_template(new_tpl)

    def draw(self, panel_w: float, top_y: float) -> float:
        """
        Desenha o painel de feitiços e retorna a coordenada bottom_y para layout sequencial.
        """
        self.sync_from_combat_manager()

        header_h = 28
        body_h = 96 if not self.is_collapsed else 0
        total_h = header_h + body_h
        center_y = top_y - total_h / 2

        self._last_bounds = (panel_w / 2, center_y, panel_w - 24, total_h)

        # Fundo do Painel
        bg_col = (18, 24, 34, 255)
        border_col = (231, 76, 60, 200) if self.is_active else (50, 68, 95, 200)
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, center_y, panel_w - 24, total_h), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, center_y, panel_w - 24, total_h), border_col, 1.5)

        # 1. Barra de Cabeçalho / Título e Toggle de Colapso
        head_y = top_y - header_h / 2
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, head_y, panel_w - 24, header_h), (24, 32, 46, 255))
        arcade.draw_line(12, top_y - header_h, panel_w - 12, top_y - header_h, (50, 68, 95, 180), 1)

        # Título
        active_badge = " [ATIVADO]" if self.is_active else " [DESATIVADO]"
        badge_col = (231, 76, 60, 255) if self.is_active else (140, 155, 175, 255)
        title_str = "✨ PROJEÇÃO TÁTICA DE MAGIAS (AOE)"
        self._get_text("sp_title", title_str, 24, head_y, (241, 196, 15, 255), 9, bold=True).draw()
        self._get_text("sp_badge", active_badge, 245, head_y, badge_col, 8, bold=True).draw()

        # Botão Colapsar / Expandir [ - ] / [ + ]
        col_icon = "[ - ]" if not self.is_collapsed else "[ + ]"
        col_btn_x = panel_w - 32
        self._get_text("sp_col_btn", col_icon, col_btn_x, head_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

        if self.is_collapsed:
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
            is_sel = (self.current_shape == shape_enum)

            if is_sel:
                btn_bg = (192, 57, 43, 255) if self.is_active else (41, 128, 185, 255)
                btn_border = (241, 196, 15, 255)
            else:
                btn_bg = (30, 40, 56, 255)
                btn_border = (55, 75, 105, 200)

            arcade.draw_rect_filled(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_bg)
            arcade.draw_rect_outline(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_border, 1.2)
            self._get_text(f"sp_b_{shape_enum.value}", label, bx, row1_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão Ativar / Desativar Projeção
        act_btn_x = panel_w - 18 - act_btn_w / 2
        act_bg = (192, 57, 43, 255) if self.is_active else (39, 174, 96, 255)
        act_border = (241, 196, 15, 255) if self.is_active else (46, 204, 113, 255)
        act_label = "⚡ Desativar" if self.is_active else "⚡ Ativar AoE"

        arcade.draw_rect_filled(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_bg)
        arcade.draw_rect_outline(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_border, 1.5)
        self._get_text("sp_b_toggle", act_label, act_btn_x, row1_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 3. Linha 2: Inputs Numéricos (Tamanho, Largura se Linha, Altura Z, Pitch)
        row2_y = top_y - header_h - 48

        # Rótulo dinâmico do Tamanho (Raio / Lado / Comprimento)
        if self.current_shape in (AoEShape.CIRCLE, AoEShape.SPHERE):
            size_lbl = "Raio:"
        elif self.current_shape in (AoEShape.SQUARE, AoEShape.CUBE):
            size_lbl = "Lado:"
        else:
            size_lbl = "Comprimento:"

        cur_x = 18
        self._get_text("sp_lbl_size", size_lbl, cur_x, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
        cur_x += 65
        self.size_input.draw(cx=cur_x + 22, cy=row2_y, width=44, height=20, text_cache=self._text_cache)
        cur_x += 48
        self._get_text("sp_unit_size", "ft", cur_x, row2_y, (150, 165, 185, 255), 8, bold=False).draw()
        cur_x += 22

        # Rótulo e Input de Largura (se Linha)
        if self.current_shape == AoEShape.LINE:
            self._get_text("sp_lbl_w", "Largura:", cur_x, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
            cur_x += 46
            self.width_input.draw(cx=cur_x + 20, cy=row2_y, width=40, height=20, text_cache=self._text_cache)
            cur_x += 44
            self._get_text("sp_unit_w", "ft", cur_x, row2_y, (150, 165, 185, 255), 8, bold=False).draw()
            cur_x += 22

        # Input de Altura Origem Z (pés)
        self._get_text("sp_lbl_z", "Alt Z:", cur_x, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
        cur_x += 38
        self.z_input.draw(cx=cur_x + 20, cy=row2_y, width=40, height=20, text_cache=self._text_cache)
        cur_x += 44
        self._get_text("sp_unit_z", "ft", cur_x, row2_y, (150, 165, 185, 255), 8, bold=False).draw()
        cur_x += 22

        # Input de Inclinação Vertical (Pitch)
        is_pitch_avail = self.current_shape in (AoEShape.SPHERE, AoEShape.CUBE, AoEShape.CONE, AoEShape.LINE)
        pitch_col = (180, 195, 215, 255) if is_pitch_avail else (90, 105, 125, 160)
        self._get_text("sp_lbl_pitch", "Pitch:", cur_x, row2_y, pitch_col, 8, bold=False).draw()
        cur_x += 38
        self.pitch_input.draw(cx=cur_x + 20, cy=row2_y, width=40, height=20, text_cache=self._text_cache)
        cur_x += 44
        self._get_text("sp_unit_pitch", "°", cur_x, row2_y, pitch_col, 8, bold=False).draw()

        # 4. Linha 3: Informações de Rotação e Controles Rápidos do Mouse
        row3_y = top_y - header_h - 78
        tpl = self.combat_manager.active_spell_template
        rot_deg = tpl.rotation_degrees if tpl is not None else 0.0
        pitch_deg = tpl.pitch_degrees if tpl is not None else 0.0
        z_ft = tpl.origin_z_feet if tpl is not None else 0.0

        info_str = f"🔄 Yaw: {int(rot_deg)}° (Scroll ±2° | Ctrl ±15°)  •  Pitch: {int(pitch_deg)}° (Alt+Scroll ±15°)  •  Z: {int(z_ft)}ft"
        self._get_text("sp_rot_info", info_str, 18, row3_y, (241, 196, 15, 240), 8, bold=True).draw()

        return top_y - total_h - 8

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """Trata cliques nos controles do painel de feitiços."""
        header_h = 28
        body_h = 96 if not self.is_collapsed else 0
        total_h = header_h + body_h

        # 1. Clique no Cabeçalho (Colapsar / Expandir)
        head_y = top_y - header_h / 2
        if abs(y - head_y) <= header_h / 2 and 12 <= x <= panel_w - 12:
            if abs(x - (panel_w - 32)) <= 20 or x >= panel_w - 60:
                self.is_collapsed = not self.is_collapsed
                return True

        if self.is_collapsed:
            return False

        # 2. Linha 1: Formatos e Botão Ativar
        row1_y = top_y - header_h - 18
        shapes = [
            AoEShape.CIRCLE,
            AoEShape.SQUARE,
            AoEShape.SPHERE,
            AoEShape.CUBE,
            AoEShape.CONE,
            AoEShape.LINE,
        ]

        act_btn_w = 100
        btn_margin = 4
        avail_shapes_w = panel_w - 36 - act_btn_w - 12
        btn_w = (avail_shapes_w - (len(shapes) - 1) * btn_margin) / len(shapes)
        btn_h = 22

        if abs(y - row1_y) <= btn_h / 2:
            # 6 Botões de Formatos
            for i, shape_enum in enumerate(shapes):
                bx = 18 + i * (btn_w + btn_margin) + btn_w / 2
                if abs(x - bx) <= btn_w / 2:
                    self.current_shape = shape_enum
                    self.sync_to_combat_manager()
                    return True

            # Botão Ativar / Desativar
            act_btn_x = panel_w - 18 - act_btn_w / 2
            if abs(x - act_btn_x) <= act_btn_w / 2:
                self.is_active = not self.is_active
                self.sync_to_combat_manager()
                return True

        # 3. Linha 2: Inputs de Texto
        row2_y = top_y - header_h - 48
        if abs(y - row2_y) <= 16:
            if self.size_input.handle_mouse_press(x, y):
                self.width_input.blur()
                self.z_input.blur()
                self.pitch_input.blur()
                return True

            if self.current_shape == AoEShape.LINE and self.width_input.handle_mouse_press(x, y):
                self.size_input.blur()
                self.z_input.blur()
                self.pitch_input.blur()
                return True

            if self.z_input.handle_mouse_press(x, y):
                self.size_input.blur()
                self.width_input.blur()
                self.pitch_input.blur()
                return True

            if self.pitch_input.handle_mouse_press(x, y):
                self.size_input.blur()
                self.width_input.blur()
                self.z_input.blur()
                return True

        # Clique fora dos inputs mas dentro do painel
        if abs(y - (top_y - total_h / 2)) <= total_h / 2 and 12 <= x <= panel_w - 12:
            self.size_input.blur()
            self.width_input.blur()
            self.z_input.blur()
            self.pitch_input.blur()
            return True

        return False

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        """Repassa arrasto do mouse para os SmartTextInputs."""
        for inp in (self.size_input, self.width_input, self.z_input, self.pitch_input):
            if inp.is_focused:
                return inp.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)
        return False

    def handle_mouse_release(self, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        self.size_input.handle_mouse_release(x, y, button, modifiers)
        self.width_input.handle_mouse_release(x, y, button, modifiers)
        self.z_input.handle_mouse_release(x, y, button, modifiers)
        self.pitch_input.handle_mouse_release(x, y, button, modifiers)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Processa digitação e navegação nos SmartTextInputs."""
        for inp in (self.size_input, self.width_input, self.z_input, self.pitch_input):
            if inp.is_focused:
                handled = inp.handle_key_press(symbol, modifiers)
                if handled:
                    self.sync_to_combat_manager()
                return handled
        return False

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        self.size_input.handle_key_release(symbol, modifiers)
        self.width_input.handle_key_release(symbol, modifiers)
        self.z_input.handle_key_release(symbol, modifiers)
        self.pitch_input.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        """Processa inserção de caracteres nos SmartTextInputs."""
        for inp in (self.size_input, self.width_input, self.z_input, self.pitch_input):
            if inp.is_focused:
                clean = "".join(c for c in text if c.isdigit() or c in (".", "-"))
                if clean and inp.handle_text_input(clean):
                    self.sync_to_combat_manager()
                    return True
        return False

    def on_update(self, dt: float) -> None:
        """Atualização de ciclo de blink e key-repeat nos inputs."""
        self.size_input.update(dt)
        self.width_input.update(dt)
        self.z_input.update(dt)
        self.pitch_input.update(dt)
