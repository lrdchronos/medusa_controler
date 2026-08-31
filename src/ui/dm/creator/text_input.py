from typing import Optional, Dict, Any, Tuple
import arcade
from ...utils.text_input import SmartTextInput


class TextInputWidget(SmartTextInput):
    """
    Subclasse especializada / Alias de compatibilidade para o Criador de Encontros,
    herdando de SmartTextInput e mantendo total compatibilidade retroativa.
    """

    def __init__(
        self,
        widget_id: str,
        placeholder: str = "",
        initial_text: str = "",
        max_length: int = 150,
        font_size: int = 9,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            widget_id=widget_id,
            placeholder=placeholder,
            initial_text=initial_text,
            max_length=max_length,
            font_size=font_size,
            **kwargs,
        )

    @property
    def cursor_blink_time(self) -> float:
        return self._blink_timer

    @cursor_blink_time.setter
    def cursor_blink_time(self, val: float) -> None:
        self._blink_timer = val


__all__ = ["TextInputWidget", "SmartTextInput"]
