import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
import arcade
from ...domain.models.entity import EntityType
from ..utils.ui_constants import Typography
from ..utils.text_input import SmartTextInput
from .renderers.add_token_modal_renderer import AddTokenModalRenderer
from .handlers.add_token_input_handler import AddTokenInputHandler

logger = logging.getLogger(__name__)


class AddTokenModal:
    """
    Modal flutuante para Criação e Inserção Dinâmica de Tokens durante o Combate (Mid-Combat Token Spawning).
    """

    SIZE_OPTIONS: List[Tuple[str, str, str]] = [
        ("Tiny", "Miúdo (1x1)", "1x1"),
        ("Medium", "Médio (1x1)", "1x1"),
        ("Large", "Grande (2x2)", "2x2"),
        ("Huge", "Enorme (3x3)", "3x3"),
        ("Gargantuan", "Imenso (4x4)", "4x4"),
    ]

    def __init__(self, on_confirm: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.on_confirm: Optional[Callable[[Dict[str, Any]], None]] = on_confirm
        self.is_open: bool = False

        # Configurações do Token
        self.name_input: SmartTextInput = SmartTextInput(
            widget_id="modal_tkn_name",
            placeholder="Nome (ex: Arma Espiritual, Reforço 1...)",
            initial_text="",
            max_length=40,
            font_size=9,
            padding_left=8.0,
        )
        self.selected_type: EntityType = EntityType.NEUTRAL
        self.selected_size: str = "Medium"
        self.hp_value: int = 1
        self.ac_value: int = 10
        self.initiative_slot: str = "next"
        self.selected_sprite_path: Optional[str] = None

        self.available_sprites: List[str] = []
        self.selected_sprite_idx: int = 0
        self.text_cache: Dict[str, arcade.Text] = {}
        self.validation_error: Optional[str] = None

        self._refresh_available_sprites()

    def _refresh_available_sprites(self) -> None:
        tokens_dir = Path("assets/sprites/tokens")
        try:
            tokens_dir.mkdir(parents=True, exist_ok=True)
            files = [str(f) for f in tokens_dir.glob("*.png")] + [str(f) for f in tokens_dir.glob("*.jpg")]
            self.available_sprites = ["procedural"] + sorted(files)
        except Exception as e:
            logger.debug(f"Aviso ao varrer pasta de tokens: {e}")
            self.available_sprites = ["procedural"]
        self.selected_sprite_idx = 0
        self.selected_sprite_path = None

    def open(self) -> None:
        self._refresh_available_sprites()
        self.name_input.clear()
        self.name_input.focus()
        self.selected_type = EntityType.NEUTRAL
        self.selected_size = "Medium"
        self.hp_value = 1
        self.ac_value = 10
        self.initiative_slot = "next"
        self.selected_sprite_idx = 0
        self.selected_sprite_path = None
        self.validation_error = None
        self.is_open = True
        logger.info("Modal AddTokenModal aberto.")

    def close(self) -> None:
        self.is_open = False
        self.name_input.blur()
        self.validation_error = None
        logger.info("Modal AddTokenModal fechado.")

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
        cached = self.text_cache.get(key)
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
                font_name=Typography.FONT_FAMILY_UI,
            )
            self.text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        return cached

    def draw(self, screen_w: float, screen_h: float) -> None:
        AddTokenModalRenderer.draw(self, screen_w, screen_h)

    def handle_click(self, x: float, y: float, screen_w: float, screen_h: float) -> bool:
        return AddTokenInputHandler.handle_click(self, x, y, screen_w, screen_h)

    def _handle_confirm(self) -> None:
        token_name = self.name_input.text.strip()
        if not token_name:
            self.validation_error = "O nome do token é obrigatório!"
            return

        self.validation_error = None
        token_data = {
            "name": token_name,
            "entity_type": self.selected_type,
            "size": self.selected_size,
            "max_hp": self.hp_value,
            "current_hp": self.hp_value,
            "armor_class": self.ac_value,
            "initiative_slot": self.initiative_slot,
            "token_sprite": self.selected_sprite_path,
        }

        logger.info(f"AddTokenModal confirmado: {token_data}")
        self.close()

        if self.on_confirm:
            self.on_confirm(token_data)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        return AddTokenInputHandler.handle_key_press(self, symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        if self.is_open:
            self.name_input.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        if not self.is_open:
            return False
        return self.name_input.handle_text_input(text)

    def on_update(self, dt: float) -> None:
        if self.is_open:
            self.name_input.on_update(dt)
