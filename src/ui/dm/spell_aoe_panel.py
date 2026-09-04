import logging
from typing import Optional, Dict, Any, Tuple
import arcade
from ...manager.session_manager import SessionManager
from ...domain.models.spell_template import SpellTemplate, SpellShape
from ..utils.text_input import SmartTextInput

logger = logging.getLogger(__name__)


class SpellAoEPanel:
    """
    Painel de Controle de Magias e Áreas de Efeito (Spell AoE Overlay) na DMWindow.
    Permite selecionar formato geométrico (Círculo, Quadrado, Cone, Linha),
    ativar/desativar projeção tática, configurar raio/comprimento e largura em pés (feet)
    via SmartTextInput e acompanhar a rotação angular.
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager

        self.is_collapsed: bool = False
        self.current_shape: SpellShape = SpellShape.CIRCLE
        self.current_size_feet: float = 20.0
        self.current_width_feet: float = 5.0
        self.is_active: bool = False

        self._text_cache: Dict[str, arcade.Text] = {}

        # Entradas de Texto Inteligentes (SmartTextInput) para Dimensões
        self.size_input = SmartTextInput(
            widget_id="spell_size_in",
            placeholder="20",
            initial_text="20",
            max_length=5,
            font_size=9,
            width=58.0,
            height=24.0,
            padding_left=6.0,
        )

        self.width_input = SmartTextInput(
            widget_id="spell_width_in",
            placeholder="5",
            initial_text="5",
            max_length=5,
            font_size=9,
            width=58.0,
            height=24.0,
            padding_left=6.0,
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
            self.is_active = tpl.is_active

            # Atualiza texto dos inputs se não estiverem com foco ativo
            if not self.size_input.is_focused:
                size_str = str(int(tpl.size_feet)) if tpl.size_feet.is_integer() else f"{tpl.size_feet:.1f}"
                self.size_input.text = size_str
            if not self.width_input.is_focused:
                width_str = str(int(tpl.width_feet)) if tpl.width_feet.is_integer() else f"{tpl.width_feet:.1f}"
                self.width_input.text = width_str

    def sync_to_combat_manager(self) -> None:
        """Propaga as configurações da UI para o CombatManager."""
        # Parsing defensivo das entradas de texto
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

        tpl = self.combat_manager.active_spell_template
        rot = tpl.rotation_degrees if tpl is not None else 0.0
        origin = tpl.origin_world if tpl is not None else (0.0, 0.0)

        new_tpl = SpellTemplate(
            shape=self.current_shape,
            size_feet=self.current_size_feet,
            width_feet=self.current_width_feet,
            rotation_degrees=rot,
            origin_world=origin,
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
        body_h = 82 if not self.is_collapsed else 0
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
        self._get_text("sp_badge", active_badge, 250, head_y, badge_col, 8, bold=True).draw()

        # Botão Colapsar / Expandir [ - ] / [ + ]
        col_icon = "[ - ]" if not self.is_collapsed else "[ + ]"
        col_btn_x = panel_w - 32
        self._get_text("sp_col_btn", col_icon, col_btn_x, head_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

        if self.is_collapsed:
            return top_y - total_h - 8

        # 2. Linha 1 do Corpo: 4 Botões de Formatos Geométricos e Botão Ativar/Desativar
        row1_y = top_y - header_h - 20
        shapes = [
            (SpellShape.CIRCLE, "⚪ Círculo"),
            (SpellShape.SQUARE, "⬜ Quadrado"),
            (SpellShape.CONE, "📐 Cone"),
            (SpellShape.LINE, "📏 Linha"),
        ]

        btn_w = (panel_w - 160) / 4
        btn_h = 24

        for i, (shape_enum, label) in enumerate(shapes):
            bx = 20 + i * (btn_w + 4) + btn_w / 2
            is_sel = (self.current_shape == shape_enum)

            if is_sel:
                btn_bg = (192, 57, 43, 255) if self.is_active else (41, 128, 185, 255)
                btn_border = (241, 196, 15, 255)
            else:
                btn_bg = (30, 40, 56, 255)
                btn_border = (55, 75, 105, 200)

            arcade.draw_rect_filled(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_bg)
            arcade.draw_rect_outline(arcade.XYWH(bx, row1_y, btn_w, btn_h), btn_border, 1.2)
            self._get_text(f"sp_b_{shape_enum.value}", label, bx, row1_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # Botão Ativar / Desativar Projeção
        act_btn_w = 115
        act_btn_x = panel_w - 20 - act_btn_w / 2
        act_bg = (192, 57, 43, 255) if self.is_active else (39, 174, 96, 255)
        act_border = (241, 196, 15, 255) if self.is_active else (46, 204, 113, 255)
        act_label = "⚡ Desativar" if self.is_active else "⚡ Ativar AoE"

        arcade.draw_rect_filled(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_bg)
        arcade.draw_rect_outline(arcade.XYWH(act_btn_x, row1_y, act_btn_w, btn_h), act_border, 1.5)
        self._get_text("sp_b_toggle", act_label, act_btn_x, row1_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 3. Linha 2 do Corpo: Inputs de Tamanho/Largura e Rotação
        row2_y = top_y - header_h - 54

        # Rótulo e Input de Tamanho / Raio
        size_lbl = "Raio:" if self.current_shape == SpellShape.CIRCLE else "Comprimento:"
        self._get_text("sp_lbl_size", size_lbl, 20, row2_y, (180, 195, 215, 255), 8, bold=False).draw()

        size_in_x = 120
        self.size_input.draw(cx=size_in_x, cy=row2_y, width=54, height=22, text_cache=self._text_cache)
        self._get_text("sp_unit_size", "ft", size_in_x + 34, row2_y, (150, 165, 185, 255), 8, bold=False).draw()

        # Rótulo e Input de Largura (se Linha)
        if self.current_shape == SpellShape.LINE:
            self._get_text("sp_lbl_w", "Largura:", 185, row2_y, (180, 195, 215, 255), 8, bold=False).draw()
            w_in_x = 260
            self.width_input.draw(cx=w_in_x, cy=row2_y, width=54, height=22, text_cache=self._text_cache)
            self._get_text("sp_unit_w", "ft", w_in_x + 34, row2_y, (150, 165, 185, 255), 8, bold=False).draw()

        # Rótulo de Rotação
        tpl = self.combat_manager.active_spell_template
        rot_deg = tpl.rotation_degrees if tpl is not None else 0.0
        rot_str = f"🔄 Rotação: {int(rot_deg)}° (Scroll ±2° | Ctrl ±15°)"
        rot_x = panel_w - 20
        self._get_text("sp_rot_lbl", rot_str, rot_x, row2_y, (241, 196, 15, 255), 8, bold=True, anchor_x="right").draw()

        return top_y - total_h - 8

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """Trata cliques nos controles do painel de feitiços."""
        header_h = 28
        body_h = 82 if not self.is_collapsed else 0
        total_h = header_h + body_h

        # 1. Clique no Cabeçalho (Colapsar / Expandir)
        head_y = top_y - header_h / 2
        if abs(y - head_y) <= header_h / 2 and 12 <= x <= panel_w - 12:
            if abs(x - (panel_w - 32)) <= 20:
                self.is_collapsed = not self.is_collapsed
                return True
            # Clique em qualquer lugar do cabeçalho pode alternar colapso se fora dos textos principais
            if x >= panel_w - 60:
                self.is_collapsed = not self.is_collapsed
                return True

        if self.is_collapsed:
            return False

        # 2. Linha 1: Formatos e Botão Ativar
        row1_y = top_y - header_h - 20
        btn_w = (panel_w - 160) / 4
        btn_h = 24

        if abs(y - row1_y) <= btn_h / 2:
            # 4 Botões de Formatos
            shapes = [SpellShape.CIRCLE, SpellShape.SQUARE, SpellShape.CONE, SpellShape.LINE]
            for i, shape_enum in enumerate(shapes):
                bx = 20 + i * (btn_w + 4) + btn_w / 2
                if abs(x - bx) <= btn_w / 2:
                    self.current_shape = shape_enum
                    self.sync_to_combat_manager()
                    return True

            # Botão Ativar / Desativar
            act_btn_w = 115
            act_btn_x = panel_w - 20 - act_btn_w / 2
            if abs(x - act_btn_x) <= act_btn_w / 2:
                self.is_active = not self.is_active
                self.sync_to_combat_manager()
                return True

        # 3. Linha 2: Inputs de Texto
        row2_y = top_y - header_h - 54

        # Input de Tamanho
        size_in_x = 120
        if self.size_input.handle_mouse_press(x, y):
            self.width_input.blur()
            return True

        # Input de Largura
        if self.current_shape == SpellShape.LINE:
            if self.width_input.handle_mouse_press(x, y):
                self.size_input.blur()
                return True

        # Se clicou fora dos inputs mas dentro do painel, desfoque
        if abs(y - (top_y - total_h / 2)) <= total_h / 2 and 12 <= x <= panel_w - 12:
            self.size_input.blur()
            self.width_input.blur()
            return True

        return False

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        """Repassa arrasto do mouse para os SmartTextInputs."""
        if self.size_input.is_focused:
            return self.size_input.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)
        if self.width_input.is_focused:
            return self.width_input.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)
        return False

    def handle_mouse_release(self, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        self.size_input.handle_mouse_release(x, y, button, modifiers)
        self.width_input.handle_mouse_release(x, y, button, modifiers)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Processa digitação e navegação nos SmartTextInputs."""
        if self.size_input.is_focused:
            handled = self.size_input.handle_key_press(symbol, modifiers)
            if handled:
                self.sync_to_combat_manager()
            return handled

        if self.width_input.is_focused:
            handled = self.width_input.handle_key_press(symbol, modifiers)
            if handled:
                self.sync_to_combat_manager()
            return handled

        return False

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        self.size_input.handle_key_release(symbol, modifiers)
        self.width_input.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        """Processa inserção de caracteres nos SmartTextInputs."""
        if self.size_input.is_focused:
            # Aceita apenas dígitos e ponto
            clean = "".join(c for c in text if c.isdigit() or c == ".")
            if clean and self.size_input.handle_text_input(clean):
                self.sync_to_combat_manager()
                return True

        if self.width_input.is_focused:
            clean = "".join(c for c in text if c.isdigit() or c == ".")
            if clean and self.width_input.handle_text_input(clean):
                self.sync_to_combat_manager()
                return True

        return False

    def on_update(self, dt: float) -> None:
        """Atualização de ciclo de blink e key-repeat nos inputs."""
        self.size_input.update(dt)
        self.width_input.update(dt)
