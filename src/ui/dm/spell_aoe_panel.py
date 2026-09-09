import logging
from typing import Optional, Dict, Any, Tuple
import arcade
from ...manager.session_manager import SessionManager
from ...domain.models.spell_template import SpellTemplate, AoEShape, SpellShape
from ..utils.text_input import SmartTextInput
from .renderers.spell_aoe_renderer import SpellAoERenderer
from .handlers.spell_aoe_input_handler import SpellAoEInputHandler

logger = logging.getLogger(__name__)


class SpellAoEPanel:
    """
    Painel de Controle de Magias e Áreas de Efeito (Spell AoE Overlay) na DMWindow.
    Permite selecionar os 6 formatos canônicos de D&D 5E (Círculo, Quadrado, Esfera, Cubo, Cone, Linha),
    ativar/desativar projeção tática, configurar dimensões (raio/lado/comprimento, largura, altitude Z, pitch)
    via SmartTextInput e acompanhar rotação e inclinação vertical em tempo real.
    Orquestra a renderização e eventos delegando para SpellAoERenderer e SpellAoEInputHandler.
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
            cached.text = text
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
        """Desenha o painel de feitiços delegando para SpellAoERenderer."""
        return SpellAoERenderer.draw(self, panel_w, top_y)

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """Trata cliques nos controles do painel de feitiços."""
        return SpellAoEInputHandler.handle_click(self, x, y, panel_w, top_y)

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        """Repassa arrasto do mouse para os SmartTextInputs."""
        return SpellAoEInputHandler.handle_mouse_drag(self, x, y, dx, dy, buttons, modifiers)

    def handle_mouse_release(self, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        SpellAoEInputHandler.handle_mouse_release(self, x, y, button, modifiers)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Processa digitação e navegação nos SmartTextInputs."""
        return SpellAoEInputHandler.handle_key_press(self, symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        SpellAoEInputHandler.handle_key_release(self, symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        """Processa inserção de caracteres nos SmartTextInputs."""
        return SpellAoEInputHandler.handle_text_input(self, text)

    def on_update(self, dt: float) -> None:
        """Atualização de ciclo de blink e key-repeat nos inputs."""
        SpellAoEInputHandler.on_update(self, dt)
