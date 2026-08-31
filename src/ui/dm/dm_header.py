from pathlib import Path
from typing import Dict, Any, Callable
import arcade
from ...manager.session_manager import SessionManager, DisplayState


class DMHeader:
    """
    Componente responsável pelo cabeçalho superior e pela barra de abas da tela do Mestre.
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.text_cache: Dict[str, arcade.Text] = {}

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
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            self.text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
        return cached

    def draw(self, panel_w: float, panel_h: float, active_tab: int) -> float:
        """
        Desenha o cabeçalho superior e as abas.
        Retorna a coordenada Y inferior onde o conteúdo da aba deve iniciar.
        """
        header_h = 56
        header_cy = panel_h - header_h / 2

        # 1. Barra de Cabeçalho Global
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, header_cy, panel_w, header_h), (20, 26, 36, 255))
        arcade.draw_line(0, panel_h - header_h, panel_w, panel_h - header_h, (50, 65, 90, 200), 1)

        # Título
        title_txt = self._get_text("dm_title", "🐉 MEDUSA VTT • MESTRE", 16, header_cy, (241, 196, 15, 255), 14, bold=True)
        title_txt.draw()

        # Badge de Estado Atual da Player Window
        state = self.session_manager.display_state
        if state == DisplayState.IDLE:
            state_str = "[ 🟢 ESPERA (IDLE) ]"
            badge_bg = (27, 77, 62, 255)
            badge_fg = (163, 228, 215, 255)
        elif state == DisplayState.PROJECTION:
            proj_name = Path(self.session_manager.projected_image_path or "").stem[:10]
            state_str = f"[ 🖼️ PROJ: {proj_name} ]"
            badge_bg = (74, 35, 90, 255)
            badge_fg = (232, 218, 239, 255)
        else:
            enc_name = self.session_manager.combat_manager.title[:12]
            state_str = f"[ ⚔️ COMBATE: {enc_name} ]"
            badge_bg = (120, 40, 31, 255)
            badge_fg = (245, 183, 177, 255)

        badge_x = panel_w - 210
        arcade.draw_rect_filled(arcade.XYWH(badge_x, header_cy, 140, 28), badge_bg)
        arcade.draw_rect_outline(arcade.XYWH(badge_x, header_cy, 140, 28), (80, 100, 130, 200), 1)
        st_txt = self._get_text("dm_st_badge", state_str, badge_x, header_cy, badge_fg, 9, bold=True, anchor_x="center")
        st_txt.draw()

        # Botão Rápido de Retorno para IDLE
        idle_btn_x = panel_w - 60
        arcade.draw_rect_filled(arcade.XYWH(idle_btn_x, header_cy, 52, 28), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(idle_btn_x, header_cy, 52, 28), (70, 90, 120, 200), 1)
        idle_t = self._get_text("dm_btn_idle", "IDLE", idle_btn_x, header_cy, (236, 240, 241, 255), 9, bold=True, anchor_x="center")
        idle_t.draw()

        # 2. Barra de Abas
        tab_bar_top = panel_h - header_h
        tab_bar_h = 42
        tab_bar_cy = tab_bar_top - tab_bar_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, tab_bar_cy, panel_w, tab_bar_h), (14, 18, 25, 255))
        arcade.draw_line(0, tab_bar_top - tab_bar_h, panel_w, tab_bar_top - tab_bar_h, (40, 50, 70, 200), 1)

        tab_w = (panel_w - 20) / 3
        tabs_meta = [
            (0, "📋 Encontros"),
            (1, "🖼️ Showcase"),
            (2, "⚔️ Combate Ativo"),
        ]

        for idx, label in tabs_meta:
            tx = 10 + idx * tab_w + tab_w / 2
            is_active = (active_tab == idx)

            bg_col = (30, 42, 58, 255) if is_active else (20, 26, 36, 255)
            border_col = (241, 196, 15, 255) if is_active else (45, 58, 78, 200)
            txt_col = (241, 196, 15, 255) if is_active else (160, 175, 195, 255)

            arcade.draw_rect_filled(arcade.XYWH(tx, tab_bar_cy, tab_w - 6, tab_bar_h - 8), bg_col)
            arcade.draw_rect_outline(arcade.XYWH(tx, tab_bar_cy, tab_w - 6, tab_bar_h - 8), border_col, 2 if is_active else 1)

            tab_t = self._get_text(f"tab_btn_{idx}", label, tx, tab_bar_cy, txt_col, 10, bold=is_active, anchor_x="center")
            tab_t.draw()

        return tab_bar_top - tab_bar_h

    def handle_click(self, x: float, y: float, panel_w: float, panel_h: float, set_tab_callback: Callable[[int], None]) -> bool:
        """Processa cliques no cabeçalho e na barra de abas."""
        header_h = 56
        header_cy = panel_h - header_h / 2

        # Clique no Botão IDLE
        idle_btn_x = panel_w - 60
        if abs(y - header_cy) <= 14 and abs(x - idle_btn_x) <= 26:
            self.session_manager.return_to_idle()
            return True

        # Clique nas Abas
        tab_bar_top = panel_h - header_h
        tab_bar_h = 42
        tab_bar_cy = tab_bar_top - tab_bar_h / 2

        if abs(y - tab_bar_cy) <= tab_bar_h / 2:
            tab_w = (panel_w - 20) / 3
            for idx in range(3):
                tx = 10 + idx * tab_w + tab_w / 2
                if abs(x - tx) <= (tab_w - 6) / 2:
                    set_tab_callback(idx)
                    return True

        return False
