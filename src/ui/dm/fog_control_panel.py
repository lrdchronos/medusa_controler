import logging
import time
from enum import Enum
from typing import Optional, Dict, Tuple, Callable
import arcade
from ...domain.models.fog_manager import FogManager

logger = logging.getLogger(__name__)


class FogTool(Enum):
    """Ferramentas manuais de manipulação da Névoa de Guerra."""
    NONE = "none"
    ADD = "add"        # 🖌️ Adicionar Névoa
    REVEAL = "reveal"  # 🧹 Revelar Área


class BrushMode(Enum):
    """Modo de aplicação do cursor do mouse."""
    SINGLE = "single"          # Clique unitário (Célula Única)
    CONTINUOUS = "continuous"  # Pincel contínuo (Click-and-Drag)


class FogControlPanel:
    """
    Painel de Controle de Névoa de Guerra (Fog of War) na DMWindow.
    Componente modular e reutilizável presente no Preparo do Encontro (Etapa 2 do Wizard)
    e na Aba de Combate Ativo.
    
    Oferece:
      - 4 Ferramentas: [Cobrir Tudo], [Revelar Tudo], [Adicionar Névoa], [Revelar Área]
      - Alternador de Modo: [Célula Única] vs [Pincel Contínuo]
      - Botão de Persistência: [Salvar Névoa]
    """

    def __init__(
        self,
        fog_manager: FogManager,
        dimensions_provider: Optional[Callable[[], Tuple[int, int]]] = None,
        save_callback: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.__fog_manager: FogManager = fog_manager
        self.__dimensions_provider: Callable[[], Tuple[int, int]] = dimensions_provider or (lambda: (25, 14))
        self.__save_callback: Optional[Callable[[], bool]] = save_callback

        self.__active_tool: FogTool = FogTool.NONE
        self.__brush_mode: BrushMode = BrushMode.SINGLE

        self.__is_collapsed: bool = False
        self.__feedback_message: Optional[str] = None
        self.__feedback_timer: float = 0.0

        self._text_cache: Dict[str, arcade.Text] = {}
        self._last_bounds: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

    # --- Properties ---

    @property
    def fog_manager(self) -> FogManager:
        return self.__fog_manager

    @fog_manager.setter
    def fog_manager(self, manager: FogManager) -> None:
        self.__fog_manager = manager

    @property
    def active_tool(self) -> FogTool:
        return self.__active_tool

    @active_tool.setter
    def active_tool(self, tool: FogTool) -> None:
        self.__active_tool = tool

    @property
    def brush_mode(self) -> BrushMode:
        return self.__brush_mode

    @brush_mode.setter
    def brush_mode(self, mode: BrushMode) -> None:
        self.__brush_mode = mode

    @property
    def is_tool_active(self) -> bool:
        """Indica se alguma ferramenta manual de adição ou remoção está selecionada."""
        return self.__active_tool != FogTool.NONE

    @property
    def is_collapsed(self) -> bool:
        return self.__is_collapsed

    @is_collapsed.setter
    def is_collapsed(self, value: bool) -> None:
        self.__is_collapsed = value

    def set_save_callback(self, callback: Callable[[], bool]) -> None:
        """Define o callback invocado ao pressionar o botão de Salvar Névoa."""
        self.__save_callback = callback

    def set_dimensions_provider(self, provider: Callable[[], Tuple[int, int]]) -> None:
        """Define o provedor de dimensões (colunas, linhas) para cobrir o grid inteiro."""
        self.__dimensions_provider = provider

    # --- Helper de Texto ---

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

    # --- Renderização ---

    def draw(self, panel_w: float, top_y: float) -> float:
        """
        Renderiza a barra de ferramentas de névoa de guerra.
        Retorna a coordenada vertical inferior (next_y) para o próximo elemento da interface.
        """
        hdr_h = 26
        body_h = 68 if not self.__is_collapsed else 0
        total_h = hdr_h + body_h
        center_y = top_y - total_h / 2
        hdr_cy = top_y - hdr_h / 2

        self._last_bounds = (12.0, top_y - total_h, panel_w - 24.0, total_h)

        # Fundo do Painel
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, center_y, panel_w - 24, total_h), (18, 24, 34, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, center_y, panel_w - 24, total_h), (50, 65, 90, 200), 1)

        # Cabeçalho
        hdr_bg = (28, 36, 48, 255)
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, hdr_cy, panel_w - 24, hdr_h), hdr_bg)
        arcade.draw_line(12, top_y - hdr_h, panel_w - 12, top_y - hdr_h, (50, 65, 90, 200), 1)

        # Título do Cabeçalho e Contador
        cell_count = self.__fog_manager.count
        hdr_title = f"🌫️ NÉVOA DE GUERRA ({cell_count} cel)"
        self._get_text("fog_hdr_t", hdr_title, 22, hdr_cy, (241, 196, 15, 255), 8, bold=True).draw()

        # Feedback temporário ou Indicador de Ferramenta Ativa
        if self.__feedback_message:
            self._get_text("fog_fb", self.__feedback_message, panel_w - 55, hdr_cy, (46, 204, 113, 255), 7, bold=True, anchor_x="right").draw()
        elif self.is_tool_active:
            status_txt = "🖌️ Adicionando" if self.__active_tool == FogTool.ADD else "🧹 Revelando"
            self._get_text("fog_act_st", status_txt, panel_w - 55, hdr_cy, (241, 196, 15, 255), 7, bold=True, anchor_x="right").draw()

        # Botão Recolher/Expandir
        col_icon = "▲" if not self.__is_collapsed else "▼"
        self._get_text("fog_col_btn", col_icon, panel_w - 28, hdr_cy, (180, 190, 205, 255), 9, bold=True, anchor_x="center").draw()

        if self.__is_collapsed:
            return top_y - total_h - 8

        # --- Corpo da Barra de Ferramentas ---
        content_w = panel_w - 36

        # Linha 1: 4 Ferramentas Globais e de Pincel
        row1_y = hdr_cy - 22
        btn_w4 = (content_w - 12) / 4
        btn_h = 22

        # 1. Cobrir Tudo
        b_fill_x = 18 + btn_w4 / 2
        arcade.draw_rect_filled(arcade.XYWH(b_fill_x, row1_y, btn_w4, btn_h), (35, 45, 60, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_fill_x, row1_y, btn_w4, btn_h), (70, 90, 120, 200), 1)
        self._get_text("fog_b_fill", "⬛ Cobrir Tudo", b_fill_x, row1_y, (220, 225, 235, 255), 7, bold=True, anchor_x="center").draw()

        # 2. Revelar Tudo
        b_clr_x = 18 + btn_w4 + 4 + btn_w4 / 2
        arcade.draw_rect_filled(arcade.XYWH(b_clr_x, row1_y, btn_w4, btn_h), (35, 45, 60, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_clr_x, row1_y, btn_w4, btn_h), (70, 90, 120, 200), 1)
        self._get_text("fog_b_clr", "⬜ Revelar Tudo", b_clr_x, row1_y, (220, 225, 235, 255), 7, bold=True, anchor_x="center").draw()

        # 3. Adicionar Névoa (Toggle)
        b_add_x = 18 + 2 * (btn_w4 + 4) + btn_w4 / 2
        is_add = (self.__active_tool == FogTool.ADD)
        add_bg = (40, 60, 90, 255) if is_add else (35, 45, 60, 255)
        add_bd = (241, 196, 15, 255) if is_add else (70, 90, 120, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_add_x, row1_y, btn_w4, btn_h), add_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_add_x, row1_y, btn_w4, btn_h), add_bd, 1.5 if is_add else 1.0)
        self._get_text("fog_b_add", "🖌️ Adicionar", b_add_x, row1_y, (241, 196, 15, 255) if is_add else (220, 225, 235, 255), 7, bold=True, anchor_x="center").draw()

        # 4. Revelar Área (Toggle)
        b_rev_x = 18 + 3 * (btn_w4 + 4) + btn_w4 / 2
        is_rev = (self.__active_tool == FogTool.REVEAL)
        rev_bg = (60, 40, 70, 255) if is_rev else (35, 45, 60, 255)
        rev_bd = (241, 196, 15, 255) if is_rev else (70, 90, 120, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_rev_x, row1_y, btn_w4, btn_h), rev_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_rev_x, row1_y, btn_w4, btn_h), rev_bd, 1.5 if is_rev else 1.0)
        self._get_text("fog_b_rev", "🧹 Revelar", b_rev_x, row1_y, (241, 196, 15, 255) if is_rev else (220, 225, 235, 255), 7, bold=True, anchor_x="center").draw()

        # Linha 2: Alternador de Modo de Pincel e Botão Salvar Névoa
        row2_y = row1_y - 24
        btn_w2 = (content_w - 6) / 2

        # Alternador Modo (Célula Única vs Pincel Contínuo)
        b_mode_x = 18 + btn_w2 / 2
        is_cont = (self.__brush_mode == BrushMode.CONTINUOUS)
        mode_txt = "🖌️ Pincel: Contínuo (Drag)" if is_cont else "🎯 Pincel: Célula Única"
        mode_bg = (45, 55, 75, 255) if is_cont else (30, 40, 55, 255)
        mode_bd = (52, 152, 219, 255) if is_cont else (70, 90, 120, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_mode_x, row2_y, btn_w2, btn_h), mode_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_mode_x, row2_y, btn_w2, btn_h), mode_bd, 1.2)
        self._get_text("fog_b_mode", mode_txt, b_mode_x, row2_y, (230, 240, 255, 255), 7, bold=True, anchor_x="center").draw()

        # Botão Salvar Névoa no Disco
        b_save_x = 18 + btn_w2 + 6 + btn_w2 / 2
        arcade.draw_rect_filled(arcade.XYWH(b_save_x, row2_y, btn_w2, btn_h), (27, 77, 62, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_save_x, row2_y, btn_w2, btn_h), (46, 204, 113, 200), 1.2)
        self._get_text("fog_b_save", "💾 Salvar Névoa", b_save_x, row2_y, (163, 228, 215, 255), 7, bold=True, anchor_x="center").draw()

        return top_y - total_h - 8

    # --- Tratamento de Cliques ---

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """
        Processa cliques nos botões do painel de névoa.
        Retorna True se o clique foi consumido por este componente.
        """
        hdr_h = 26
        body_h = 68 if not self.__is_collapsed else 0
        total_h = hdr_h + body_h
        hdr_cy = top_y - hdr_h / 2

        # 1. Clique no Cabeçalho (Recolher/Expandir)
        if abs(y - hdr_cy) <= hdr_h / 2:
            if 12 <= x <= panel_w - 12:
                self.__is_collapsed = not self.__is_collapsed
                return True

        if self.__is_collapsed:
            return False

        content_w = panel_w - 36
        btn_h = 22

        # 2. Linha 1: Ferramentas
        row1_y = hdr_cy - 22
        if abs(y - row1_y) <= btn_h / 2:
            btn_w4 = (content_w - 12) / 4

            # [ Cobrir Tudo ]
            b_fill_x = 18 + btn_w4 / 2
            if abs(x - b_fill_x) <= btn_w4 / 2:
                cols, rows = self.__dimensions_provider()
                self.__fog_manager.fill_all(cols, rows)
                self.__set_feedback(f"Grade Coberta ({cols}x{rows})")
                return True

            # [ Revelar Tudo ]
            b_clr_x = 18 + btn_w4 + 4 + btn_w4 / 2
            if abs(x - b_clr_x) <= btn_w4 / 2:
                self.__fog_manager.clear_all()
                self.__set_feedback("Mapa Revelado")
                return True

            # [ 🖌️ Adicionar Névoa ]
            b_add_x = 18 + 2 * (btn_w4 + 4) + btn_w4 / 2
            if abs(x - b_add_x) <= btn_w4 / 2:
                self.__active_tool = FogTool.NONE if self.__active_tool == FogTool.ADD else FogTool.ADD
                return True

            # [ 🧹 Revelar Área ]
            b_rev_x = 18 + 3 * (btn_w4 + 4) + btn_w4 / 2
            if abs(x - b_rev_x) <= btn_w4 / 2:
                self.__active_tool = FogTool.NONE if self.__active_tool == FogTool.REVEAL else FogTool.REVEAL
                return True

        # 3. Linha 2: Modo e Salvar
        row2_y = row1_y - 24
        if abs(y - row2_y) <= btn_h / 2:
            btn_w2 = (content_w - 6) / 2

            # Alternar Modo de Pincel
            b_mode_x = 18 + btn_w2 / 2
            if abs(x - b_mode_x) <= btn_w2 / 2:
                if self.__brush_mode == BrushMode.SINGLE:
                    self.__brush_mode = BrushMode.CONTINUOUS
                    self.__set_feedback("Pincel Contínuo")
                else:
                    self.__brush_mode = BrushMode.SINGLE
                    self.__set_feedback("Célula Única")
                return True

            # Salvar Névoa
            b_save_x = 18 + btn_w2 + 6 + btn_w2 / 2
            if abs(x - b_save_x) <= btn_w2 / 2:
                if self.__save_callback:
                    success = self.__save_callback()
                    if success:
                        self.__set_feedback("Salvo no JSON!")
                    else:
                        self.__set_feedback("Erro ao salvar")
                else:
                    self.__set_feedback("Sem save callback")
                return True

        return False

    def __set_feedback(self, msg: str, duration: float = 2.5) -> None:
        """Exibe uma mensagem temporária de feedback no cabeçalho do painel."""
        self.__feedback_message = msg
        self.__feedback_timer = duration

    def on_update(self, delta_time: float) -> None:
        """Atualiza temporizador da mensagem de feedback."""
        if self.__feedback_timer > 0:
            self.__feedback_timer -= delta_time
            if self.__feedback_timer <= 0:
                self.__feedback_message = None
