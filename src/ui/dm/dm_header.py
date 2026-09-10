from pathlib import Path
from typing import Dict, Any, Callable, Optional
import arcade
from ...manager.session_manager import SessionManager, DisplayState
from ..utils.ui_constants import Colors, Typography, Dimensions, Spacing, with_alpha
from ..utils.ui_layout import FlowRow, calculate_button_bounds


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
                font_name=Typography.FONT_FAMILY_UI,
            )
            self.text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.anchor_x = anchor_x
            cached.anchor_y = anchor_y
        return cached

    def _calculate_header_layout(
        self,
        panel_w: float,
        panel_h: float,
        is_open: bool,
        is_fs: bool,
    ) -> Dict[str, Any]:
        """
        Calcula dinamicamente a geometria, larguras dos botões e coordenadas centrais
        da barra superior utilizando calculate_button_bounds e FlowRow.
        """
        header_h = Dimensions.HEADER_HEIGHT
        header_cy = panel_h - header_h / 2.0
        btn_h = Dimensions.BTN_HEIGHT_COMPACT
        padding_x = Dimensions.BTN_PADDING_X_MIN  # 12.0px
        gap = float(Spacing.SM)                    # 8.0px
        margin_right = 10.0

        # 1. Rótulos e estilização de estado
        if is_open:
            pw_label = "📺 Fechar Tela Jogador"
            pw_bg = Colors.SUCCESS_BG
            pw_border = Colors.SUCCESS_BORDER
            pw_fg = (235, 255, 240, 255)
            pw_bw = Dimensions.BORDER_WIDTH_ACTIVE
        else:
            pw_label = "📺 Abrir Tela Jogador"
            pw_bg = (44, 62, 80, 255)
            pw_border = Colors.BTN_DEFAULT_BORDER
            pw_fg = Colors.TEXT_SECONDARY
            pw_bw = Dimensions.BORDER_WIDTH_DEFAULT

        if not is_open:
            fs_label = "⛶ Tela Cheia"
            fs_bg = (22, 28, 38, 160)
            fs_border = Colors.BORDER_SUBTLE
            fs_fg = with_alpha(Colors.TEXT_MUTED, 160)
            fs_bw = Dimensions.BORDER_WIDTH_DEFAULT
        elif is_fs:
            fs_label = "🗗 Modo Janela"
            fs_bg = Colors.INFO_BG
            fs_border = Colors.INFO_BORDER
            fs_fg = Colors.TEXT_WHITE
            fs_bw = Dimensions.BORDER_WIDTH_ACTIVE
        else:
            fs_label = "⛶ Tela Cheia"
            fs_bg = (36, 52, 74, 255)
            fs_border = (52, 152, 219, 200)
            fs_fg = (236, 240, 241, 255)
            fs_bw = Dimensions.BORDER_WIDTH_DEFAULT

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

        idle_label = "IDLE"

        # 2. Cálculo dinâmico das larguras com padding seguro >= 12px
        pw_w = calculate_button_bounds(pw_label, font_size=Typography.SIZE_MICRO, padding_x=padding_x, min_width=144.0)
        fs_w = calculate_button_bounds(fs_label, font_size=Typography.SIZE_MICRO, padding_x=padding_x, min_width=106.0)
        badge_w = calculate_button_bounds(state_str, font_size=Typography.SIZE_MICRO, padding_x=Spacing.SM, min_width=116.0)
        idle_w = calculate_button_bounds(idle_label, font_size=Typography.SIZE_MICRO, padding_x=Spacing.SM, min_width=44.0)

        # 3. Distribuição em linha alinhada à direita via FlowRow
        total_span = pw_w + gap + fs_w + gap + badge_w + gap + idle_w
        start_x = panel_w - margin_right - total_span
        row = FlowRow(start_x=start_x, center_y=header_cy, gap=gap, align_center=True)

        pw_cx, _ = row.add(pw_w)
        fs_cx, _ = row.add(fs_w)
        badge_cx, _ = row.add(badge_w)
        idle_cx, _ = row.add(idle_w)

        return {
            "header_h": header_h,
            "header_cy": header_cy,
            "btn_h": btn_h,
            "pw": {
                "cx": pw_cx,
                "w": pw_w,
                "label": pw_label,
                "bg": pw_bg,
                "border": pw_border,
                "fg": pw_fg,
                "bw": pw_bw,
            },
            "fs": {
                "cx": fs_cx,
                "w": fs_w,
                "label": fs_label,
                "bg": fs_bg,
                "border": fs_border,
                "fg": fs_fg,
                "bw": fs_bw,
            },
            "badge": {
                "cx": badge_cx,
                "w": badge_w,
                "label": state_str,
                "bg": badge_bg,
                "border": (80, 100, 130, 200),
                "fg": badge_fg,
                "bw": Dimensions.BORDER_WIDTH_DEFAULT,
            },
            "idle": {
                "cx": idle_cx,
                "w": idle_w,
                "label": idle_label,
                "bg": (44, 62, 80, 255),
                "border": Colors.BTN_DEFAULT_BORDER,
                "fg": (236, 240, 241, 255),
                "bw": Dimensions.BORDER_WIDTH_DEFAULT,
            },
        }

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
        # Determina estado da PlayerWindow
        is_open = self._is_player_window_open() if player_window_open is None else bool(player_window_open)
        is_fs = self._is_player_fullscreen() if is_fullscreen is None else bool(is_fullscreen)

        layout = self._calculate_header_layout(panel_w, panel_h, is_open, is_fs)
        header_h = layout["header_h"]
        header_cy = layout["header_cy"]
        btn_h = layout["btn_h"]

        # 1. Barra de Cabeçalho Global
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2.0, header_cy, panel_w, header_h), Colors.BG_PANEL)
        arcade.draw_line(0, panel_h - header_h, panel_w, panel_h - header_h, Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        # Título do Painel do Mestre (alinhado verticalmente com anchor_y="center")
        title_txt = self._get_text(
            "dm_title",
            "🐉 MEDUSA VTT • MESTRE",
            float(Spacing.MD),
            header_cy,
            Colors.ACCENT_GOLD,
            Typography.SIZE_SUBHEADER,
            bold=True,
            anchor_x="left",
            anchor_y="center",
        )
        title_txt.draw()

        # Botão 1: Exibição da Tela dos Jogadores (Abrir / Fechar)
        pw = layout["pw"]
        arcade.draw_rect_filled(arcade.XYWH(pw["cx"], header_cy, pw["w"], btn_h), pw["bg"])
        arcade.draw_rect_outline(arcade.XYWH(pw["cx"], header_cy, pw["w"], btn_h), pw["border"], pw["bw"])
        btn_pw_t = self._get_text("dm_btn_pw", pw["label"], pw["cx"], header_cy, pw["fg"], Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center")
        btn_pw_t.draw()

        # Botão 2: Alternância de Tela Cheia (Fullscreen Toggle)
        fs = layout["fs"]
        arcade.draw_rect_filled(arcade.XYWH(fs["cx"], header_cy, fs["w"], btn_h), fs["bg"])
        arcade.draw_rect_outline(arcade.XYWH(fs["cx"], header_cy, fs["w"], btn_h), fs["border"], fs["bw"])
        btn_fs_t = self._get_text("dm_btn_fs", fs["label"], fs["cx"], header_cy, fs["fg"], Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center")
        btn_fs_t.draw()

        # Badge de Estado Atual da Player Window
        badge = layout["badge"]
        arcade.draw_rect_filled(arcade.XYWH(badge["cx"], header_cy, badge["w"], btn_h), badge["bg"])
        arcade.draw_rect_outline(arcade.XYWH(badge["cx"], header_cy, badge["w"], btn_h), badge["border"], badge["bw"])
        st_txt = self._get_text("dm_st_badge", badge["label"], badge["cx"], header_cy, badge["fg"], Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center")
        st_txt.draw()

        # Botão Rápido de Retorno para IDLE
        idle = layout["idle"]
        arcade.draw_rect_filled(arcade.XYWH(idle["cx"], header_cy, idle["w"], btn_h), idle["bg"])
        arcade.draw_rect_outline(arcade.XYWH(idle["cx"], header_cy, idle["w"], btn_h), idle["border"], idle["bw"])
        idle_t = self._get_text("dm_btn_idle", idle["label"], idle["cx"], header_cy, idle["fg"], Typography.SIZE_MICRO, bold=True, anchor_x="center", anchor_y="center")
        idle_t.draw()

        # 2. Barra de Abas
        tab_bar_top = panel_h - header_h
        tab_bar_h = 42.0
        tab_bar_cy = tab_bar_top - tab_bar_h / 2.0

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2.0, tab_bar_cy, panel_w, tab_bar_h), Colors.BG_DARK)
        arcade.draw_line(0, tab_bar_top - tab_bar_h, panel_w, tab_bar_top - tab_bar_h, Colors.BORDER_SUBTLE, Dimensions.BORDER_WIDTH_DEFAULT)

        tab_w = (panel_w - 20.0) / 4.0
        tabs_meta = [
            (0, "📋 Encontros"),
            (1, "🖼️ Showcase"),
            (2, "⚔️ Combate"),
            (3, "🛠️ Criador"),
        ]

        for idx, label in tabs_meta:
            tx = 10.0 + idx * tab_w + tab_w / 2.0
            is_active = (active_tab == idx)

            bg_col = (30, 42, 58, 255) if is_active else Colors.BG_PANEL
            border_col = Colors.ACCENT_GOLD if is_active else Colors.BORDER_SUBTLE
            txt_col = Colors.ACCENT_GOLD if is_active else Colors.TEXT_MUTED

            arcade.draw_rect_filled(arcade.XYWH(tx, tab_bar_cy, tab_w - 6.0, tab_bar_h - 8.0), bg_col)
            arcade.draw_rect_outline(arcade.XYWH(tx, tab_bar_cy, tab_w - 6.0, tab_bar_h - 8.0), border_col, Dimensions.BORDER_WIDTH_THICK if is_active else Dimensions.BORDER_WIDTH_DEFAULT)

            tab_t = self._get_text(f"tab_btn_{idx}", label, tx, tab_bar_cy, txt_col, Typography.SIZE_BADGE, bold=is_active, anchor_x="center", anchor_y="center")
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
        header_h = Dimensions.HEADER_HEIGHT
        header_cy = panel_h - header_h / 2.0
        btn_h = Dimensions.BTN_HEIGHT_COMPACT

        is_open = self._is_player_window_open()
        is_fs = self._is_player_fullscreen()
        layout = self._calculate_header_layout(panel_w, panel_h, is_open, is_fs)

        # 1. Cliques nos Botões do Cabeçalho Superior
        if abs(y - header_cy) <= btn_h / 2.0 + 2.0:
            # Clique no Botão IDLE
            idle = layout["idle"]
            if abs(x - idle["cx"]) <= idle["w"] / 2.0:
                self.session_manager.clear_display_to_idle()
                return True

            # Clique no Botão de Fullscreen
            fs = layout["fs"]
            if abs(x - fs["cx"]) <= fs["w"] / 2.0:
                if is_open:
                    if on_toggle_fullscreen:
                        on_toggle_fullscreen()
                    elif self.dm_window and hasattr(self.dm_window, "toggle_player_fullscreen"):
                        self.dm_window.toggle_player_fullscreen()
                return True

            # Clique no Botão de Exibição da Tela dos Jogadores (Abrir/Fechar)
            pw = layout["pw"]
            if abs(x - pw["cx"]) <= pw["w"] / 2.0:
                if on_toggle_player_window:
                    on_toggle_player_window()
                elif self.dm_window and hasattr(self.dm_window, "toggle_player_window"):
                    self.dm_window.toggle_player_window()
                return True

        # 2. Cliques nas Abas
        tab_bar_top = panel_h - header_h
        tab_bar_h = 42.0
        tab_bar_cy = tab_bar_top - tab_bar_h / 2.0

        if abs(y - tab_bar_cy) <= tab_bar_h / 2.0:
            tab_w = (panel_w - 20.0) / 4.0
            for idx in range(4):
                tx = 10.0 + idx * tab_w + tab_w / 2.0
                if abs(x - tx) <= (tab_w - 6.0) / 2.0:
                    set_tab_callback(idx)
                    return True

        return False
