"""
Módulo de compatibilidade para SmartTextInput e TextInputWidget.
Reexporta a implementação modularizada de src.ui.components.text_input.
"""

from ..components.text_input.clipboard_helper import (
    copy_to_system_clipboard as _copy_to_system_clipboard,
    paste_from_system_clipboard as _paste_from_system_clipboard,
    _INTERNAL_CLIPBOARD,
)
from ..components.text_input.smart_text_input import SmartTextInput
from ..components.text_input.text_input_widget import TextInputWidget

__all__ = [
    "SmartTextInput",
    "TextInputWidget",
    "_copy_to_system_clipboard",
    "_paste_from_system_clipboard",
    "_INTERNAL_CLIPBOARD",
]
