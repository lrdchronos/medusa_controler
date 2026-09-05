from pathlib import Path
from typing import Dict, Any, Callable, Optional
import arcade
from ...manager.session_manager import SessionManager, DisplayState


class DMHeader:
    """
    Componente responsável pelo cabeçalho superior e pela barra de abas da tela do Mestre.
    Contém status da sessão, atalhos rápidos e controle de ciclo de vida e tela cheia da PlayerWindow.
    """

    def __init__(self, session_manager: SessionManager, dm_window: Optional[Any] = None) -> None:
        self.session_manager = session_manager
        self.dm_window = dm_window
        self.text_cache: Dict[str, arcade.Text] = {}

    def _is_player_window_open(self) -> bool:
        if self.dm_window is not None:
            return bool(getattr(self.dm_window, "is_player_window_open", False))
        return False

    def _is_player_fullscreen(self) -> bool:
        if self.dm_window is not None:
            return bool(getattr(self.dm_window, "is_player_fullscreen", False))
        return False

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

    def draw(
        self,
        panel_w: float,
        panel_h: float,
        active_tab: int,
        player_window_open: Optional[bool] = None,
        is_fullscreen: Optional[bool] = None,
    ) -> float:
        """
        Desenha o cabeçalho superior e as abas.
        Retorna a coordenada Y inferior onde o conteúdo da aba deve iniciar.
        """
        header_h = 56
        header_cy = panel_h - header_h / 2

        # Determina estado da PlayerWindow
        is_open = self._is_player_window_open() if player_window_open is None else bool(player_window_open)
        is_fs = self._is_player_fullscreen() if is_fullscreen is None else bool(is_fullscreen)

        # 1. Barra de Cabeçalho Global
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, header_cy, panel_w, header_h), (20, 26, 36, 255))
        arcade.draw_line(0, panel_h - header_h, panel_w, panel_h - header_h, (50, 65, 90, 200), 1)

        # Título do Painel do Mestre
        title_txt = self._get_text("dm_title", "🐉 MEDUSA VTT • MESTRE", 16, header_cy, (241, 196, 15, 255), 13, bold=True)
        title_txt.draw()

        # Botão 1: Exibição da Tela dos Jogadores (Abrir / Fechar)
        player_btn_x = panel_w - 366
        player_btn_w = 144
        player_btn_h = 28

        if is_open:
            btn_pw_label = "📺 Fechar Tela Jogador"
            btn_pw_bg = (27, 94, 52, 255)
            btn_pw_border = (46, 204, 113, 255)
            btn_pw_fg = (235, 255, 240, 255)
            btn_pw_bw = 1.5
        else:
            btn_pw_label = "📺 Abrir Tela Jogador"
            btn_pw_bg = (44, 62, 80, 255)
            btn_pw_border = (70, 90, 120, 200)
            btn_pw_fg = (189, 195, 199, 255)
            btn_pw_bw = 1.0

        arcade.draw_rect_filled(arcade.XYWH(player_btn_x, header_cy, player_btn_w, player_btn_h), btn_pw_bg)
        arcade.draw_rect_outline(arcade.XYWH(player_btn_x, header_cy, player_btn_w, player_btn_h), btn_pw_border, btn_pw_bw)
        btn_pw_t = self._get_text("dm_btn_pw", btn_pw_label, player_btn_x, header_cy, btn_pw_fg, 8, bold=True, anchor_x="center")
        btn_pw_t.draw()

        # Botão 2: Alternância de Tela Cheia (Fullscreen Toggle)
        fs_btn_x = panel_w - 235
        fs_btn_w = 106
        fs_btn_h = 28

        if not is_open:
            btn_fs_label = "⛶ Tela Cheia"
            btn_fs_bg = (22, 28, 38, 160)
            btn_fs_border = (40, 50, 65, 120)
            btn_fs_fg = (90, 105, 120, 160)
            btn_fs_bw = 1.0
        elif is_fs:
            btn_fs_label = "🗗 Modo Janela"
            btn_fs_bg = (31, 78, 121, 255)
            btn_fs_border = (93, 173, 226, 255)
            btn_fs_fg = (255, 255, 255, 255)
            btn_fs_bw = 1.5
        else:
            btn_fs_label = "⛶ Tela Cheia"
            btn_fs_bg = (36, 52, 74, 255)
            btn_fs_border = (52, 152, 219, 200)
            btn_fs_fg = (236, 240, 241, 255)
            btn_fs_bw = 1.0

        arcade.draw_rect_filled(arcade.XYWH(fs_btn_x, header_cy, fs_btn_w, fs_btn_h), btn_fs_bg)
        arcade.draw_rect_outline(arcade.XYWH(fs_btn_x, header_cy, fs_btn_w, fs_btn_h), btn_fs_border, btn_fs_bw)
        btn_fs_t = self._get_text("dm_btn_fs", btn_fs_label, fs_btn_x, header_cy, btn_fs_fg, 8, bold=True, anchor_x="center")
        btn_fs_t.draw()

        # Badge de Estado Atual da Player Window
        state = self.session_manager.display_state
        if state == DisplayState.IDLE:
            state_str = "[ 🟢 IDLE ]"
            badge_bg = (27, 77, 62, 255)
            badge_fg = (163, 228, 215, 255)
        elif state == DisplayState.PROJECTION:
            proj_name = Path(self.session_manager.projected_image_path or "").stem[:8]
            state_str = f"[ 🖼️ {proj_name} ]"
            badge_bg = (74, 35, 90, 255)
            badge_fg = (232, 218, 239, 255)
        else:
            enc_name = self.session_manager.combat_manager.title[:10]
            state_str = f"[ ⚔️ {enc_name} ]"
            badge_bg = (120, 40, 31, 255)
            badge_fg = (245, 183, 177, 255)

        badge_x = panel_w - 118
        badge_w = 116
        arcade.draw_rect_filled(arcade.XYWH(badge_x, header_cy, badge_w, 28), badge_bg)
        arcade.draw_rect_outline(arcade.XYWH(badge_x, header_cy, badge_w, 28), (80, 100, 130, 200), 1)
        st_txt = self._get_text("dm_st_badge", state_str, badge_x, header_cy, badge_fg, 8, bold=True, anchor_x="center")
        st_txt.draw()

        # Botão Rápido de Retorno para IDLE
        idle_btn_x = panel_w - 32
        arcade.draw_rect_filled(arcade.XYWH(idle_btn_x, header_cy, 44, 28), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(idle_btn_x, header_cy, 44, 28), (70, 90, 120, 200), 1)
        idle_t = self._get_text("dm_btn_idle", "IDLE", idle_btn_x, header_cy, (236, 240, 241, 255), 8, bold=True, anchor_x="center")
        idle_t.draw()

        # 2. Barra de Abas
        tab_bar_top = panel_h - header_h
        tab_bar_h = 42
        tab_bar_cy = tab_bar_top - tab_bar_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, tab_bar_cy, panel_w, tab_bar_h), (14, 18, 25, 255))
        arcade.draw_line(0, tab_bar_top - tab_bar_h, panel_w, tab_bar_top - tab_bar_h, (40, 50, 70, 200), 1)

        tab_w = (panel_w - 20) / 4
        tabs_meta = [
            (0, "📋 Encontros"),
            (1, "🖼️ Showcase"),
            (2, "⚔️ Combate"),
            (3, "🛠️ Criador"),
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

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        panel_h: float,
        set_tab_callback: Callable[[int], None],
        on_toggle_player_window: Optional[Callable[[], None]] = None,
        on_toggle_fullscreen: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Processa cliques no cabeçalho e na barra de abas."""
        header_h = 56
        header_cy = panel_h - header_h / 2

        # 1. Cliques nos Botões do Cabeçalho Superior
        if abs(y - header_cy) <= 15:
            # Clique no Botão IDLE
            idle_btn_x = panel_w - 32
            if abs(x - idle_btn_x) <= 22:
                self.session_manager.clear_display_to_idle()
                return True

            # Clique no Botão de Fullscreen
            fs_btn_x = panel_w - 235
            if abs(x - fs_btn_x) <= 53:
                is_open = self._is_player_window_open()
                if is_open:
                    if on_toggle_fullscreen:
                        on_toggle_fullscreen()
                    elif self.dm_window and hasattr(self.dm_window, "toggle_player_fullscreen"):
                        self.dm_window.toggle_player_fullscreen()
                return True

            # Clique no Botão de Exibição da Tela dos Jogadores (Abrir/Fechar)
            player_btn_x = panel_w - 366
            if abs(x - player_btn_x) <= 72:
                if on_toggle_player_window:
                    on_toggle_player_window()
                elif self.dm_window and hasattr(self.dm_window, "toggle_player_window"):
                    self.dm_window.toggle_player_window()
                return True

        # 2. Cliques nas Abas
        tab_bar_top = panel_h - header_h
        tab_bar_h = 42
        tab_bar_cy = tab_bar_top - tab_bar_h / 2

        if abs(y - tab_bar_cy) <= tab_bar_h / 2:
            tab_w = (panel_w - 20) / 4
            for idx in range(4):
                tx = 10 + idx * tab_w + tab_w / 2
                if abs(x - tx) <= (tab_w - 6) / 2:
                    set_tab_callback(idx)
                    return True

        return False

