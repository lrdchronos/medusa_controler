"""
Módulo de Utilitários de Layout e Dimensionamento de Interface (UI) para o Medusa VTT.

Este módulo encapsula helpers puros de posicionamento horizontal fluido (FlowRow),
cálculo de bounding boxes para botões responsivos (SmartButton / calculate_button_bounds)
e renderização proporcional nítida de ícones em pixel art (PixelIconDrawer / draw_pixel_icon).

NÃO CONTÉM PRINTS (utiliza logging padrão).
Respeita o Grid de 8pt e os design tokens de src/ui/utils/ui_constants.py.
"""

import logging
from typing import List, Optional, Tuple, Any
import arcade

from .ui_constants import Spacing, Dimensions, Typography

logger = logging.getLogger(__name__)


class FlowRow:
    """
    Gerenciador de posicionamento horizontal relativo para múltiplos controles (botões, badges, inputs).
    Controla o avanço incremental de um cursor X com base na largura dos itens e no gap horizontal configurado.
    """

    def __init__(
        self,
        start_x: float,
        center_y: float,
        gap: float = float(Spacing.SM),
        align_center: bool = True,
    ) -> None:
        """
        Inicializa o gerenciador de linha com a posição inicial e o espaçamento entre itens.

        :param start_x: Coordenada X inicial da linha de itens.
        :param center_y: Coordenada Y vertical central onde todos os itens são alinhados.
        :param gap: Espaçamento horizontal entre itens consecutivos (padrão 8.0px / Spacing.SM).
        :param align_center: Se True, `add()` retorna o ponto central (X) do item para Arcade XYWH.
                             Se False, retorna o ponto de início (X) esquerdo do item.
        """
        self.__start_x: float = float(start_x)
        self.__center_y: float = float(center_y)
        self.__gap: float = float(gap)
        self.__align_center: bool = bool(align_center)

        self.__cursor_x: float = float(start_x)
        self.__item_widths: List[float] = []
        self.__item_positions: List[Tuple[float, float]] = []

    @property
    def start_x(self) -> float:
        """Retorna a coordenada X inicial da linha."""
        return self.__start_x

    @property
    def center_y(self) -> float:
        """Retorna a coordenada Y central da linha."""
        return self.__center_y

    @property
    def gap(self) -> float:
        """Retorna o gap horizontal entre itens."""
        return self.__gap

    @property
    def cursor_x(self) -> float:
        """Retorna a posição X atual do cursor."""
        return self.__cursor_x

    @property
    def total_width(self) -> float:
        """
        Retorna a largura acumulada de todos os itens adicionados (soma direta de widths).
        """
        return sum(self.__item_widths)

    @property
    def total_span(self) -> float:
        """
        Retorna a extensão horizontal total ocupada do início do primeiro item ao fim do último item,
        incluindo os gaps intermediários.
        """
        if not self.__item_widths:
            return 0.0
        return sum(self.__item_widths) + (len(self.__item_widths) - 1) * self.__gap

    @property
    def item_count(self) -> int:
        """Retorna a quantidade de itens adicionados nesta linha."""
        return len(self.__item_widths)

    @property
    def item_widths(self) -> List[float]:
        """Retorna uma cópia defensiva da lista de larguras dos itens adicionados."""
        return self.__item_widths.copy()

    @property
    def item_positions(self) -> List[Tuple[float, float]]:
        """Retorna uma cópia defensiva das coordenadas (x, y) de desenho calculadas."""
        return self.__item_positions.copy()

    def add(self, width: float, align_center: Optional[bool] = None) -> Tuple[float, float]:
        """
        Calcula as coordenadas de desenho para o próximo elemento de largura informada,
        registra o elemento e avança o cursor interno: `cursor_x += width + gap`.

        :param width: Largura horizontal do item a ser inserido.
        :param align_center: Sobrescrita opcional do alinhamento central (padrão usa o definido no construtor).
        :return: Tupla (item_x, center_y) indicando onde o elemento deve ser desenhado.
        """
        safe_width = max(0.0, float(width))
        use_center = self.__align_center if align_center is None else bool(align_center)

        item_x = self.__cursor_x + (safe_width / 2.0 if use_center else 0.0)
        position = (float(item_x), float(self.__center_y))

        self.__cursor_x += safe_width + self.__gap
        self.__item_widths.append(safe_width)
        self.__item_positions.append(position)

        return position

    def reset(
        self,
        start_x: Optional[float] = None,
        center_y: Optional[float] = None,
        gap: Optional[float] = None,
    ) -> None:
        """
        Reinicializa o cursor e o histórico de itens, permitindo reutilizar a instância.
        """
        if start_x is not None:
            self.__start_x = float(start_x)
        if center_y is not None:
            self.__center_y = float(center_y)
        if gap is not None:
            self.__gap = float(gap)

        self.__cursor_x = self.__start_x
        self.__item_widths.clear()
        self.__item_positions.clear()


def calculate_button_bounds(
    text: str,
    font_size: int = Typography.SIZE_BODY,
    padding_x: float = Dimensions.BTN_PADDING_X_MIN,
    min_width: float = 80.0,
    font_name: Optional[Any] = None,
) -> float:
    """
    Calcula dinamicamente a largura total de um botão para acomodar o texto com padding horizontal seguro.
    Utiliza `arcade.Text.content_width` com fallback defensivo para ambientes sem janela ativa.

    :param text: Rótulo de texto do botão.
    :param font_size: Tamanho da fonte em pontos/pixels (padrão Typography.SIZE_BODY).
    :param padding_x: Padding horizontal aplicado em ambos os lados do texto (padrão 12.0px).
    :param min_width: Largura mínima garantida para o botão (padrão 80.0px).
    :param font_name: Família de fontes opcional (padrão Typography.FONT_FAMILY_UI).
    :return: Largura calculada max(min_width, text_width + 2 * padding_x).
    """
    if not text:
        return max(float(min_width), 2.0 * float(padding_x))

    text_width: float
    has_window = False
    try:
        if arcade.get_window() is not None:
            has_window = True
    except Exception:
        has_window = False

    if has_window:
        try:
            t = arcade.Text(
                text=str(text),
                x=0,
                y=0,
                font_size=font_size,
                font_name=font_name or Typography.FONT_FAMILY_UI,
            )
            text_width = float(t.content_width)
        except Exception:
            # Fallback proporcional métrico
            text_width = float(len(str(text)) * font_size * 0.60)
    else:
        # Fallback métrico proporcional para execução headless / testes unitários
        text_width = float(len(str(text)) * font_size * 0.60)

    calculated_width = text_width + 2.0 * float(padding_x)
    return max(float(min_width), calculated_width)


class SmartButton:
    """
    Helper de Bounding Box e cálculo métrico para botões responsivos no Medusa VTT.
    """

    @staticmethod
    def calculate_button_bounds(
        text: str,
        font_size: int = Typography.SIZE_BODY,
        padding_x: float = Dimensions.BTN_PADDING_X_MIN,
        min_width: float = 80.0,
        font_name: Optional[Any] = None,
    ) -> float:
        """
        Calcula a largura necessária para o botão contendo o texto especificado.
        """
        return calculate_button_bounds(
            text=text,
            font_size=font_size,
            padding_x=padding_x,
            min_width=min_width,
            font_name=font_name,
        )


def draw_pixel_icon(
    texture: Optional[arcade.Texture],
    center_x: float,
    center_y: float,
    target_size: float = 24.0,
) -> None:
    """
    Desenha uma sub-textura ou sprite de ícone centralizada na coordenada informada,
    aplicando fator de escala proporcional (scale = target_size / texture.width)
    e preservando a nitidez de pixel art (pixelated=True).

    :param texture: Textura ou sub-textura do Arcade a ser desenhada.
    :param center_x: Posição central X na tela.
    :param center_y: Posição central Y na tela.
    :param target_size: Tamanho de destino em pixels (largura final desejada, padrão 24.0px).
    """
    if texture is None:
        logger.warning("draw_pixel_icon chamado com textura nula (None). Renderização ignorada.")
        return

    try:
        tex_w = float(texture.width)
        tex_h = float(texture.height)
        if tex_w <= 0.0 or tex_h <= 0.0:
            return

        scale = float(target_size) / tex_w
        draw_w = tex_w * scale
        draw_h = tex_h * scale

        arcade.draw_texture_rect(
            texture,
            arcade.XYWH(float(center_x), float(center_y), draw_w, draw_h),
            pixelated=True,
        )
    except Exception as e:
        logger.debug(f"draw_pixel_icon suprimido em ambiente sem contexto gráfico ativo: {e}")


class PixelIconDrawer:
    """
    Utilitário canônico para renderização de ícones de Pixel Art em Python Arcade.
    """

    @staticmethod
    def draw_pixel_icon(
        texture: Optional[arcade.Texture],
        center_x: float,
        center_y: float,
        target_size: float = 24.0,
    ) -> None:
        """
        Desenha a textura centralizada com pixelated=True e escala proporcional.
        """
        draw_pixel_icon(
            texture=texture,
            center_x=center_x,
            center_y=center_y,
            target_size=target_size,
        )
