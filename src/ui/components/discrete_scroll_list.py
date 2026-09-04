import logging
from typing import List, Any, Optional, Tuple, Callable, Dict
import arcade

logger = logging.getLogger(__name__)


class DiscreteScrollList:
    """
    Componente OOD reutilizável para exibição e paginação discreta de coleções em interfaces Arcade.

    Premissas e Regras de Negócio (PREMISES.md):
      - Paginação baseada em índice inteiro (start_index) em vez de deslocamento fracionado em pixels.
      - O dimensionamento calcula estritamente quantos itens cabem inteiramente na altura disponível,
        eliminando cortes e truncamentos parciais de elementos nas bordas.
      - Encapsulamento estrito com atributos privados (__) e validação Poka-Yoke.
      - Suporte à renderização Dark Fantasy e indicadores visuais de rolagem (trilha, polegar e setas indicadoras).
    """

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        width: float = 200.0,
        height: float = 200.0,
        item_height: int = 32,
        spacing: int = 4,
        visible_item_count: Optional[int] = None,
        items: Optional[List[Any]] = None,
    ) -> None:
        self.__x: float = float(x)
        self.__y: float = float(y)  # Top-left Y por padrão na convenção visual da UI
        self.__width: float = max(10.0, float(width))
        self.__height: float = max(10.0, float(height))
        self.__item_height: int = max(10, int(item_height))
        self.__spacing: int = max(0, int(spacing))
        self.__visible_item_count_override: Optional[int] = (
            max(1, int(visible_item_count)) if visible_item_count is not None else None
        )

        self.__items: List[Any] = list(items) if items is not None else []
        self.__start_index: int = 0
        self.__selected_index: Optional[int] = None

        # Estilo visual Dark Fantasy padrão
        self.__bg_color: Tuple[int, int, int, int] = (15, 20, 28, 255)
        self.__border_color: Tuple[int, int, int, int] = (45, 60, 85, 200)
        self.__draw_frame: bool = True

    # --- Propriedades e Encapsulamento Estrito (Poka-Yoke) ---

    @property
    def x(self) -> float:
        """Coordenada X (borda esquerda) do contêiner."""
        return self.__x

    @x.setter
    def x(self, val: float) -> None:
        self.__x = float(val)

    @property
    def y(self) -> float:
        """Coordenada Y (topo superior) do contêiner."""
        return self.__y

    @y.setter
    def y(self, val: float) -> None:
        self.__y = float(val)

    @property
    def width(self) -> float:
        """Largura do contêiner."""
        return self.__width

    @width.setter
    def width(self, val: float) -> None:
        self.__width = max(10.0, float(val))

    @property
    def height(self) -> float:
        """Altura total do contêiner."""
        return self.__height

    @height.setter
    def height(self, val: float) -> None:
        self.__height = max(10.0, float(val))
        self._clamp_start_index()

    @property
    def item_height(self) -> int:
        """Altura em pixels de cada item individual."""
        return self.__item_height

    @item_height.setter
    def item_height(self, val: int) -> None:
        self.__item_height = max(10, int(val))
        self._clamp_start_index()

    @property
    def spacing(self) -> int:
        """Espaçamento vertical entre itens vizinhos."""
        return self.__spacing

    @spacing.setter
    def spacing(self, val: int) -> None:
        self.__spacing = max(0, int(val))
        self._clamp_start_index()

    @property
    def items(self) -> List[Any]:
        """Retorna uma cópia defensiva da lista de itens gerenciados."""
        return list(self.__items)

    @items.setter
    def items(self, new_items: List[Any]) -> None:
        if not isinstance(new_items, (list, tuple)):
            raise TypeError("items deve ser uma lista ou tupla.")
        self.__items = list(new_items)
        self._clamp_start_index()

    @property
    def start_index(self) -> int:
        """Índice do primeiro elemento visível na listagem."""
        return self.__start_index

    @start_index.setter
    def start_index(self, val: int) -> None:
        try:
            parsed = int(val)
        except (ValueError, TypeError):
            parsed = 0
        self.__start_index = max(0, min(self.max_start_index, parsed))

    @property
    def selected_index(self) -> Optional[int]:
        return self.__selected_index

    @selected_index.setter
    def selected_index(self, val: Optional[int]) -> None:
        if val is None:
            self.__selected_index = None
        else:
            self.__selected_index = max(0, min(len(self.__items) - 1, int(val)))

    @property
    def visible_item_count(self) -> int:
        """
        Calcula dinamicamente a quantidade de itens que cabem inteiramente na altura do contêiner:
        height // (item_height + spacing).
        Garante que nenhum elemento seja renderizado cortado ao meio.
        """
        if self.__visible_item_count_override is not None:
            return self.__visible_item_count_override

        slot_total_h = self.__item_height + self.__spacing
        if slot_total_h <= 0:
            return 1
        calculated = int(self.__height // slot_total_h)
        return max(1, calculated)

    @visible_item_count.setter
    def visible_item_count(self, count: Optional[int]) -> None:
        if count is None:
            self.__visible_item_count_override = None
        else:
            self.__visible_item_count_override = max(1, int(count))
        self._clamp_start_index()

    @property
    def max_start_index(self) -> int:
        """Calcula o índice máximo de início para que o final da lista alinhe com o final do contêiner."""
        return max(0, len(self.__items) - self.visible_item_count)

    @property
    def can_scroll_up(self) -> bool:
        """Indica se há elementos ocultos antes do primeiro visível."""
        return self.__start_index > 0

    @property
    def can_scroll_down(self) -> bool:
        """Indica se há elementos ocultos após o último visível."""
        return self.__start_index < self.max_start_index

    @property
    def visible_items(self) -> List[Tuple[int, Any]]:
        """
        Retorna a lista de tuplas (índice_original, item) correspondentes aos slots atualmente visíveis.
        """
        end_idx = min(len(self.__items), self.__start_index + self.visible_item_count)
        return [(i, self.__items[i]) for i in range(self.__start_index, end_idx)]

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Retorna a tupla (x, y, width, height) delimitadora do componente."""
        return (self.__x, self.__y, self.__width, self.__height)

    # --- Configuração Geométrica e Auxiliares ---

    def set_bounds(self, x: float, y: float, width: float, height: float) -> None:
        """Atualiza a posição (x=left, y=top) e dimensões do contêiner."""
        self.__x = float(x)
        self.__y = float(y)
        self.__width = max(10.0, float(width))
        self.__height = max(10.0, float(height))
        self._clamp_start_index()

    def set_style(
        self,
        bg_color: Optional[Tuple[int, int, int, int]] = None,
        border_color: Optional[Tuple[int, int, int, int]] = None,
        draw_frame: Optional[bool] = None,
    ) -> None:
        """Configura as cores de fundo e borda do contêiner."""
        if bg_color is not None:
            self.__bg_color = bg_color
        if border_color is not None:
            self.__border_color = border_color
        if draw_frame is not None:
            self.__draw_frame = draw_frame

    def _clamp_start_index(self) -> None:
        """Mantém o start_index restrito aos limites válidos [0, max_start_index]."""
        self.__start_index = max(0, min(self.max_start_index, self.__start_index))

    # --- Métodos de Rolagem ---

    def scroll_up(self, steps: int = 1) -> bool:
        """Retrocede a paginação discreta em N passos. Retorna True se o índice mudou."""
        old = self.__start_index
        self.start_index = self.__start_index - steps
        return self.__start_index != old

    def scroll_down(self, steps: int = 1) -> bool:
        """Avança a paginação discreta em N passos. Retorna True se o índice mudou."""
        old = self.__start_index
        self.start_index = self.__start_index + steps
        return self.__start_index != old

    def scroll_to(self, index: int) -> None:
        """Rola diretamente para o item de índice informado."""
        self.start_index = index

    def reset_scroll(self) -> None:
        """Reinicia a rolagem para o topo (índice 0)."""
        self.start_index = 0

    # --- Tratamento de Interatividade e Eventos do Mouse ---

    def is_point_inside(self, x: float, y: float) -> bool:
        """Verifica se o ponto (x, y) está situado dentro da área do contêiner."""
        left = self.__x
        right = self.__x + self.__width
        top = self.__y
        bottom = self.__y - self.__height
        return (left <= x <= right) and (bottom <= y <= top)

    def on_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """
        Trata o evento de rolagem da roda do mouse.
        Se o ponteiro estiver dentro dos limites do componente:
          - scroll_y > 0 (cima): start_index -= 1
          - scroll_y < 0 (baixo): start_index += 1
          - Reclama o evento (retorna True) para evitar vazamento para outros componentes.
        Caso contrário, retorna False.
        """
        if not self.is_point_inside(x, y):
            return False

        if scroll_y > 0:
            self.scroll_up(1)
        elif scroll_y < 0:
            self.scroll_down(1)

        return True

    def get_slot_rect(self, slot_idx: int) -> Tuple[float, float, float, float]:
        """
        Calcula as coordenadas de centro (cx, cy, slot_w, slot_h) para o slot visível slot_idx (0 a visible_item_count - 1).
        """
        slot_h = float(self.__item_height)
        step = slot_h + float(self.__spacing)
        has_scrollbar = len(self.__items) > self.visible_item_count
        slot_w = self.__width - (14.0 if has_scrollbar else 8.0)
        cx = self.__x + 4.0 + slot_w / 2.0
        cy = self.__y - 4.0 - slot_idx * step - slot_h / 2.0
        return (cx, cy, slot_w, slot_h)

    def get_item_at_position(self, x: float, y: float) -> Optional[Tuple[int, Any]]:
        """
        Retorna a tupla (índice_original, item) correspondente à posição (x, y) clicada dentro de um slot visível.
        Retorna None se o clique não acertou nenhum slot visível.
        """
        if not self.is_point_inside(x, y):
            return None

        slot_h = float(self.__item_height)
        step = slot_h + float(self.__spacing)
        visible_list = self.visible_items

        for slot_idx, (actual_idx, item) in enumerate(visible_list):
            cx, cy, slot_w, slot_h = self.get_slot_rect(slot_idx)
            left = cx - slot_w / 2.0
            right = cx + slot_w / 2.0
            top = cy + slot_h / 2.0
            bottom = cy - slot_h / 2.0

            if left <= x <= right and bottom <= y <= top:
                return (actual_idx, item)

        return None

    # --- Renderização do Contêiner e Indicadores de Rolagem ---

    def draw(
        self,
        draw_item_callback: Optional[Callable[[int, Any, float, float, float, float], None]] = None,
        text_cache: Optional[Dict[str, arcade.Text]] = None,
    ) -> None:
        """
        Desenha o contêiner rolável:
          1. Fundo e contorno estético Dark Fantasy.
          2. Itens visíveis via draw_item_callback(actual_idx, item, cx, cy, w, h).
          3. Barra de rolagem discreta e/ou setas indicadoras de paginação caso haja itens extras.
        """
        cx = self.__x + self.__width / 2.0
        cy = self.__y - self.__height / 2.0

        if self.__draw_frame:
            arcade.draw_rect_filled(arcade.XYWH(cx, cy, self.__width, self.__height), self.__bg_color)
            arcade.draw_rect_outline(arcade.XYWH(cx, cy, self.__width, self.__height), self.__border_color, 1.0)

        visible_list = self.visible_items
        for slot_idx, (actual_idx, item) in enumerate(visible_list):
            slot_cx, slot_cy, slot_w, slot_h = self.get_slot_rect(slot_idx)
            if draw_item_callback is not None:
                draw_item_callback(actual_idx, item, slot_cx, slot_cy, slot_w, slot_h)

        # Indicador visual de rolagem (quando len(items) > visible_item_count)
        if len(self.__items) > self.visible_item_count:
            self._draw_scroll_indicator(text_cache)

    def _draw_scroll_indicator(self, text_cache: Optional[Dict[str, arcade.Text]] = None) -> None:
        """Renderiza uma barra lateral discreta proporcional à paginação."""
        track_w = 6.0
        track_x = self.__x + self.__width - 4.0 - track_w / 2.0
        track_h = max(10.0, self.__height - 8.0)
        track_cy = self.__y - self.__height / 2.0

        # Trilha
        arcade.draw_rect_filled(arcade.XYWH(track_x, track_cy, track_w, track_h), (25, 32, 45, 180))

        # Polegar (Thumb)
        total_items = max(1, len(self.__items))
        visible_count = self.visible_item_count
        thumb_h = max(16.0, track_h * (visible_count / total_items))
        track_travel = max(1.0, track_h - thumb_h)

        max_start = self.max_start_index
        scroll_ratio = (self.__start_index / max_start) if max_start > 0 else 0.0
        thumb_top_y = (self.__y - 4.0) - scroll_ratio * track_travel
        thumb_cy = thumb_top_y - thumb_h / 2.0

        thumb_color = (241, 196, 15, 220) if (self.can_scroll_up or self.can_scroll_down) else (70, 95, 130, 200)
        arcade.draw_rect_filled(arcade.XYWH(track_x, thumb_cy, track_w, thumb_h), thumb_color)
