# Fallback clipboard compartilhado em memória
_INTERNAL_CLIPBOARD: str = ""


def copy_to_system_clipboard(text: str) -> bool:
    """Copia o texto para a área de transferência do sistema operacional com fallback seguro."""
    global _INTERNAL_CLIPBOARD
    _INTERNAL_CLIPBOARD = text
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return True


def paste_from_system_clipboard() -> str:
    """Obtém o texto da área de transferência do sistema operacional ou fallback de memória."""
    global _INTERNAL_CLIPBOARD
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        if text is not None:
            return str(text)
    except Exception:
        pass
    return _INTERNAL_CLIPBOARD
