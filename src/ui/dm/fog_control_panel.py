import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Tuple, Callable
import arcade
from ...domain.models.fog_manager import FogManager
from ..utils.ui_constants import Colors, Typography, Dimensions, Spacing
from ..utils.ui_layout import FlowRow, calculate_button_bounds

logger = logging.getLogger(__name__)


class FogTool(Enum):
    """Ferramentas manuais de manipulação da Névoa de Guerra."""
    NONE = "none"
    ADD = "add"        # ✏️ Adicionar Névoa
    REVEAL = "reveal"  # 🧹 Revelar Área


class BrushMode(Enum):
    """Modo de aplicação do cursor do mouse."""
    SINGLE = "single"          # Clique unitário (Célula Única)
    CONTINUOUS = "continuous"  # Pincel contínuo (Click-and-Drag)


@dataclass(frozen=True)
class FogPanelLayout:
    """Estrutura imutável de coordenadas e dimensões calculadas para o layout do painel de névoa."""
    panel_cx: float
    panel_cy: float
    panel_w: float
    panel_h: float
    hdr_cy: float
    hdr_h: float
    row1_y: float
    row2_y: float
    btn_h: float
    btn_fill_rect: Tuple[float, float, float, float]    # (cx, cy, w, h)
    btn_clear_rect: Tuple[float, float, float, float]   # (cx, cy, w, h)
    btn_add_rect: Tuple[float, float, float, float]     # (cx, cy, w, h)
    btn_reveal_rect: Tuple[float, float, float, float]  # (cx, cy, w, h)
    btn_mode_rect: Tuple[float, float, float, float]    # (cx, cy, w, h)
    btn_save_rect: Tuple[float, float, float, float]    # (cx, cy, w, h)
    next_y: float


class FogControlPanel:
    """
    Painel de Controle de Névoa de Guerra (Fog of War) na DMWindow.
    Componente modular e reutilizável presente no Preparo do Encontro (Etapa 2 do Wizard)
    e na Aba de Combate Ativo.
    
    Oferece:
      - 4 Ferramentas na Linha 1: [Cobrir Tudo], [Revelar Tudo], [Adicionar Névoa], [Revelar Área]
      - Alternador de Modo e Persistência na Linha 2: [Célula Única / Contínuo] e [Salvar Névoa]
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

    @property
    def header_height(self) -> float:
        """Altura do cabeçalho do acordeão."""
        return float(Dimensions.HEADER_HEIGHT_SUB)

    @property
    def body_height(self) -> float:
        """Altura do corpo expandido comportando 2 linhas independentes e respiros."""
        return 80.0 if not self.__is_collapsed else 0.0

    @property
    def total_height(self) -> float:
        """Altura total do painel (cabeçalho + corpo)."""
        return self.header_height + self.body_height

    def get_next_y(self, top_y: float) -> float:
        """Retorna a coordenada Y inferior para o próximo elemento de UI sequencial."""
        return float(top_y) - self.total_height - float(Spacing.SM)

    def set_save_callback(self, callback: Callable[[], bool]) -> None:
        """Define o callback invocado ao pressionar o botão de Salvar Névoa."""
        self.__save_callback = callback

    def set_dimensions_provider(self, provider: Callable[[], Tuple[int, int]]) -> None:
        """Define o provedor de dimensões (colunas, linhas) para cobrir o grid inteiro."""
        self.__dimensions_provider = provider

    # --- Cálculo de Layout Unificado ---

    def _compute_layout(self, panel_w: float, top_y: float) -> FogPanelLayout:
        """
        Calcula as bounding boxes métricas de todos os botões e divisões do painel,
        garantindo sincronização 100% fiel entre renderização e tratamento de clique.
        """
        hdr_h = float(Dimensions.HEADER_HEIGHT_SUB)
        body_h = float(self.body_height)
        total_h = hdr_h + body_h
        panel_cx = panel_w / 2.0
        panel_cy = top_y - total_h / 2.0
        panel_rect_w = panel_w - 24.0
        hdr_cy = top_y - hdr_h / 2.0
        next_y = self.get_next_y(top_y)

        if self.__is_collapsed:
            dummy_rect = (0.0, 0.0, 0.0, 0.0)
            return FogPanelLayout(
                panel_cx=panel_cx,
                panel_cy=panel_cy,
                panel_w=panel_rect_w,
                panel_h=total_h,
                hdr_cy=hdr_cy,
                hdr_h=hdr_h,
                row1_y=0.0,
                row2_y=0.0,
                btn_h=0.0,
                btn_fill_rect=dummy_rect,
                btn_clear_rect=dummy_rect,
                btn_add_rect=dummy_rect,
                btn_reveal_rect=dummy_rect,
                btn_mode_rect=dummy_rect,
                btn_save_rect=dummy_rect,
                next_y=next_y,
            )

        btn_h = float(Dimensions.BTN_HEIGHT_COMPACT)
        gap = float(Spacing.SM)
        pad_y = float(Spacing.SM)
        content_w = panel_w - 36.0
        start_x = 18.0

        # Linha 1 (row1_y): Ações em Massa e Ferramentas Globais
        row1_y = top_y - hdr_h - pad_y - btn_h / 2.0
        btn_w4 = (content_w - 3.0 * gap) / 4.0
        row1_flow = FlowRow(start_x=start_x, center_y=row1_y, gap=gap, align_center=True)
        fill_cx, _ = row1_flow.add(btn_w4)
        clear_cx, _ = row1_flow.add(btn_w4)
        add_cx, _ = row1_flow.add(btn_w4)
        rev_cx, _ = row1_flow.add(btn_w4)

        # Linha 2 (row2_y = row1_y - btn_h - GAP_SMALL): Ferramenta Ativa e Persistência
        row2_y = row1_y - btn_h - gap
        btn_w2 = (content_w - gap) / 2.0
        row2_flow = FlowRow(start_x=start_x, center_y=row2_y, gap=gap, align_center=True)
        mode_cx, _ = row2_flow.add(btn_w2)
        save_cx, _ = row2_flow.add(btn_w2)

        return FogPanelLayout(
            panel_cx=panel_cx,
            panel_cy=panel_cy,
            panel_w=panel_rect_w,
            panel_h=total_h,
            hdr_cy=hdr_cy,
            hdr_h=hdr_h,
            row1_y=row1_y,
            row2_y=row2_y,
            btn_h=btn_h,
            btn_fill_rect=(fill_cx, row1_y, btn_w4, btn_h),
            btn_clear_rect=(clear_cx, row1_y, btn_w4, btn_h),
            btn_add_rect=(add_cx, row1_y, btn_w4, btn_h),
            btn_reveal_rect=(rev_cx, row1_y, btn_w4, btn_h),
            btn_mode_rect=(mode_cx, row2_y, btn_w2, btn_h),
            btn_save_rect=(save_cx, row2_y, btn_w2, btn_h),
            next_y=next_y,
        )

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
                font_name=Typography.FONT_FAMILY_UI,
            )
            self._text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        return cached

    # --- Renderização ---

    def draw(self, panel_w: float, top_y: float) -> float:
        """
        Renderiza a barra de ferramentas de névoa de guerra em grade de duas linhas independentes.
        Retorna a coordenada vertical inferior (next_y) para o próximo elemento da interface.
        """
        layout = self._compute_layout(panel_w, top_y)
        self._last_bounds = (12.0, top_y - layout.panel_h, layout.panel_w, layout.panel_h)

        # Fundo e contorno do Painel
        panel_rect = arcade.XYWH(layout.panel_cx, layout.panel_cy, layout.panel_w, layout.panel_h)
        arcade.draw_rect_filled(panel_rect, Colors.BG_PANEL)
        arcade.draw_rect_outline(panel_rect, Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        # Cabeçalho
        hdr_rect = arcade.XYWH(layout.panel_cx, layout.hdr_cy, layout.panel_w, layout.hdr_h)
        arcade.draw_rect_filled(hdr_rect, Colors.BG_CARD)
        arcade.draw_line(12.0, top_y - layout.hdr_h, panel_w - 12.0, top_y - layout.hdr_h, Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        # Título do Cabeçalho e Contador
        cell_count = self.__fog_manager.count
        hdr_title = f"🌫️ NÉVOA DE GUERRA ({cell_count} cel)"
        self._get_text("fog_hdr_t", hdr_title, 22.0, layout.hdr_cy, Colors.TEXT_GOLD, Typography.SIZE_MICRO, bold=True).draw()

        # Feedback temporário ou Indicador de Ferramenta Ativa
        if self.__feedback_message:
            self._get_text("fog_fb", self.__feedback_message, panel_w - 55.0, layout.hdr_cy, Colors.SUCCESS, Typography.SIZE_MICRO - 1, bold=True, anchor_x="right").draw()
        elif self.is_tool_active:
            status_txt = "✏️ Adicionando" if self.__active_tool == FogTool.ADD else "🧹 Revelando"
            self._get_text("fog_act_st", status_txt, panel_w - 55.0, layout.hdr_cy, Colors.TEXT_GOLD, Typography.SIZE_MICRO - 1, bold=True, anchor_x="right").draw()

        # Botão Recolher/Expandir
        col_icon = "▲" if not self.__is_collapsed else "▼"
        self._get_text("fog_col_btn", col_icon, panel_w - 28.0, layout.hdr_cy, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        if self.__is_collapsed:
            return layout.next_y

        # --- Linha 1: Ações em Massa e Ferramentas Globais ---
        # 1. Cobrir Tudo
        fill_cx, fill_cy, fill_w, fill_h = layout.btn_fill_rect
        fill_rect = arcade.XYWH(fill_cx, fill_cy, fill_w, fill_h)
        arcade.draw_rect_filled(fill_rect, Colors.BTN_DEFAULT_BG)
        arcade.draw_rect_outline(fill_rect, Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        self._get_text("fog_b_fill", "⬛ Cobrir Tudo", fill_cx, fill_cy, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

        # 2. Revelar Tudo
        clr_cx, clr_cy, clr_w, clr_h = layout.btn_clear_rect
        clr_rect = arcade.XYWH(clr_cx, clr_cy, clr_w, clr_h)
        arcade.draw_rect_filled(clr_rect, Colors.BTN_DEFAULT_BG)
        arcade.draw_rect_outline(clr_rect, Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        self._get_text("fog_b_clr", "⬜ Revelar Tudo", clr_cx, clr_cy, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

        # 3. Adicionar Névoa (Toggle)
        add_cx, add_cy, add_w, add_h = layout.btn_add_rect
        add_rect = arcade.XYWH(add_cx, add_cy, add_w, add_h)
        is_add = (self.__active_tool == FogTool.ADD)
        add_bg = Colors.PURPLE_BG if is_add else Colors.BTN_DEFAULT_BG
        add_bd = Colors.ACCENT_GOLD if is_add else Colors.BTN_DEFAULT_BORDER
        arcade.draw_rect_filled(add_rect, add_bg)
        arcade.draw_rect_outline(add_rect, add_bd, Dimensions.BORDER_WIDTH_ACTIVE if is_add else Dimensions.BORDER_WIDTH_DEFAULT)
        self._get_text("fog_b_add", "✏️ Adicionar", add_cx, add_cy, Colors.TEXT_GOLD if is_add else Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

        # 4. Revelar Área (Toggle)
        rev_cx, rev_cy, rev_w, rev_h = layout.btn_reveal_rect
        rev_rect = arcade.XYWH(rev_cx, rev_cy, rev_w, rev_h)
        is_rev = (self.__active_tool == FogTool.REVEAL)
        rev_bg = Colors.PURPLE_BG if is_rev else Colors.BTN_DEFAULT_BG
        rev_bd = Colors.ACCENT_GOLD if is_rev else Colors.BTN_DEFAULT_BORDER
        arcade.draw_rect_filled(rev_rect, rev_bg)
        arcade.draw_rect_outline(rev_rect, rev_bd, Dimensions.BORDER_WIDTH_ACTIVE if is_rev else Dimensions.BORDER_WIDTH_DEFAULT)
        self._get_text("fog_b_rev", "🧹 Revelar", rev_cx, rev_cy, Colors.TEXT_GOLD if is_rev else Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

        # --- Linha 2: Alternador de Modo de Pincel e Botão Salvar Névoa ---
        # 1. Alternador Modo (Célula Única vs Pincel Contínuo)
        mode_cx, mode_cy, mode_w, mode_h = layout.btn_mode_rect
        mode_rect = arcade.XYWH(mode_cx, mode_cy, mode_w, mode_h)
        is_cont = (self.__brush_mode == BrushMode.CONTINUOUS)
        mode_txt = "🖌️ Pincel: Contínuo (Drag)" if is_cont else "🎯 Pincel: Célula Única"
        mode_bg = Colors.BTN_PRIMARY_BG if is_cont else Colors.BTN_DEFAULT_BG
        mode_bd = Colors.INFO_BORDER if is_cont else Colors.BTN_DEFAULT_BORDER
        arcade.draw_rect_filled(mode_rect, mode_bg)
        arcade.draw_rect_outline(mode_rect, mode_bd, Dimensions.BORDER_WIDTH_DEFAULT)
        self._get_text("fog_b_mode", mode_txt, mode_cx, mode_cy, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

        # 2. Botão Salvar Névoa no Disco (Totalmente desacoplado da Linha 1)
        save_cx, save_cy, save_w, save_h = layout.btn_save_rect
        save_rect = arcade.XYWH(save_cx, save_cy, save_w, save_h)
        arcade.draw_rect_filled(save_rect, Colors.SUCCESS)
        arcade.draw_rect_outline(save_rect, Colors.SUCCESS_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        self._get_text("fog_b_save", "💾 Salvar Névoa", save_cx, save_cy, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO - 1, bold=True, anchor_x="center").draw()

        return layout.next_y

    # --- Tratamento de Cliques ---

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """
        Processa cliques nos botões do painel de névoa baseado na geometria do layout calculado.
        Retorna True se o clique foi consumido por este componente.
        """
        layout = self._compute_layout(panel_w, top_y)

        # 1. Clique no Cabeçalho (Recolher/Expandir)
        if abs(y - layout.hdr_cy) <= layout.hdr_h / 2.0:
            if 12.0 <= x <= panel_w - 12.0:
                self.__is_collapsed = not self.__is_collapsed
                return True

        if self.__is_collapsed:
            return False

        # 2. Linha 1: Ferramentas e Ações Globais
        if abs(y - layout.row1_y) <= layout.btn_h / 2.0:
            # [ ⬛ Cobrir Tudo ]
            fill_cx, _, fill_w, _ = layout.btn_fill_rect
            if abs(x - fill_cx) <= fill_w / 2.0:
                cols, rows = self.__dimensions_provider()
                self.__fog_manager.fill_all(cols, rows)
                self.__set_feedback(f"Grade Coberta ({cols}x{rows})")
                return True

            # [ ⬜ Revelar Tudo ]
            clr_cx, _, clr_w, _ = layout.btn_clear_rect
            if abs(x - clr_cx) <= clr_w / 2.0:
                self.__fog_manager.clear_all()
                self.__set_feedback("Mapa Revelado")
                return True

            # [ ✏️ Adicionar Névoa ]
            add_cx, _, add_w, _ = layout.btn_add_rect
            if abs(x - add_cx) <= add_w / 2.0:
                self.__active_tool = FogTool.NONE if self.__active_tool == FogTool.ADD else FogTool.ADD
                return True

            # [ 🧹 Revelar Área ]
            rev_cx, _, rev_w, _ = layout.btn_reveal_rect
            if abs(x - rev_cx) <= rev_w / 2.0:
                self.__active_tool = FogTool.NONE if self.__active_tool == FogTool.REVEAL else FogTool.REVEAL
                return True

        # 3. Linha 2: Modo e Salvar
        if abs(y - layout.row2_y) <= layout.btn_h / 2.0:
            # Alternar Modo de Pincel
            mode_cx, _, mode_w, _ = layout.btn_mode_rect
            if abs(x - mode_cx) <= mode_w / 2.0:
                if self.__brush_mode == BrushMode.SINGLE:
                    self.__brush_mode = BrushMode.CONTINUOUS
                    self.__set_feedback("Pincel Contínuo")
                else:
                    self.__brush_mode = BrushMode.SINGLE
                    self.__set_feedback("Célula Única")
                return True

            # Salvar Névoa
            save_cx, _, save_w, _ = layout.btn_save_rect
            if abs(x - save_cx) <= save_w / 2.0:
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
