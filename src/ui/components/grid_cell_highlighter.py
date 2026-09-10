import logging
from typing import Optional, Dict, Tuple, Set, Union, List, Any
import arcade
try:
    from arcade.shape_list import (
        ShapeElementList,
        create_rectangle_filled,
        create_rectangle_outline,
    )
except ImportError:
    ShapeElementList = None  # type: ignore
    create_rectangle_filled = None  # type: ignore
    create_rectangle_outline = None  # type: ignore

from ...manager.grid_manager import GridManager

logger = logging.getLogger(__name__)


class GridCellHighlighter:
    """
    Componente genérico, desacoplado e reutilizável de Destaque Matricial de Células (Grid Cell Highlight Overlay).
    Gerencia coleções de células marcadas indexadas por (col, row) com suporte a cores RGBA personalizadas.
    
    Aplicações canônicas:
      - Áreas de Efeito (Spell AoE Overlay): Células atingidas pintadas em carmim translúcido.
      - Alcance de Movimento (Movement Range): Células acessíveis com custo de deslocamento válido em azul luminoso.
    
    Renderização otimizada:
      - Utiliza arcade.shape_list.ShapeElementList para preenchimento em lote em um único draw call na GPU.
      - Inclui contorno sutil de 1px na borda do quadrado.
      - Fallback defensivo compatível com execução headless em testes unitários.
    """

    # Cores Canônicas do Medusa VTT
    COLOR_SPELL_AOE: Tuple[int, int, int, int] = (231, 76, 60, 110)           # Carmim translúcido mágico
    COLOR_OUTLINE_SPELL_AOE: Tuple[int, int, int, int] = (192, 57, 43, 220)   # Contorno carmim vivo
    COLOR_MOVEMENT_RANGE: Tuple[int, int, int, int] = (41, 128, 185, 110)      # Azul luminoso translúcido
    COLOR_OUTLINE_MOVEMENT: Tuple[int, int, int, int] = (52, 152, 219, 220)    # Contorno azul vivo

    def __init__(
        self,
        grid_manager: Optional[GridManager] = None,
        fill_color: Optional[Tuple[int, int, int, int]] = None,
        outline_color: Optional[Tuple[int, int, int, int]] = None,
        outline_width: float = 1.0,
    ) -> None:
        self.__grid_manager: Optional[GridManager] = grid_manager
        self.default_fill_color: Tuple[int, int, int, int] = fill_color or self.COLOR_SPELL_AOE
        self.default_outline_color: Optional[Tuple[int, int, int, int]] = outline_color
        self.outline_width: float = outline_width
        self.__highlighted_cells: Dict[Tuple[int, int], Tuple[int, int, int, int]] = {}
        self.__shape_list: Optional[Any] = None
        self.__dirty: bool = True
        self.__last_layout: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    # --- Properties ---

    @property
    def grid_manager(self) -> Optional[GridManager]:
        return self.__grid_manager

    @grid_manager.setter
    def grid_manager(self, value: Optional[GridManager]) -> None:
        if self.__grid_manager != value:
            self.__grid_manager = value
            self.__dirty = True

    @property
    def highlighted_cells(self) -> Dict[Tuple[int, int], Tuple[int, int, int, int]]:
        """Retorna cópia defensiva do dicionário de células destacadas."""
        return self.__highlighted_cells.copy()

    @highlighted_cells.setter
    def highlighted_cells(
        self,
        value: Union[Set[Tuple[int, int]], List[Tuple[int, int]], Dict[Tuple[int, int], Tuple[int, int, int, int]]],
    ) -> None:
        """Define o conjunto de células destacadas."""
        self.set_cells(value, color=self.default_fill_color)

    @property
    def cell_count(self) -> int:
        """Quantidade de células destacadas."""
        return len(self.__highlighted_cells)

    def __len__(self) -> int:
        return len(self.__highlighted_cells)

    # --- Métodos Canônicos de Manipulação de Células ---

    def set_cells(
        self,
        cells: Union[Set[Tuple[int, int]], List[Tuple[int, int]], Dict[Tuple[int, int], Tuple[int, int, int, int]]],
        color: Tuple[int, int, int, int] = COLOR_SPELL_AOE,
    ) -> None:
        """
        Substitui integralmente o conjunto de células destacadas.
        Aceita um dicionário mapeando (col, row) -> cor RGBA, ou um conjunto/lista de tuplas (col, row).
        """
        self.__highlighted_cells.clear()
        if isinstance(cells, dict):
            for (col, row), c in cells.items():
                self.__highlighted_cells[(int(col), int(row))] = tuple(c)  # type: ignore
        else:
            for (col, row) in cells:
                self.__highlighted_cells[(int(col), int(row))] = tuple(color)
        self.__dirty = True

    def add_cell(
        self,
        col: int,
        row: int,
        color: Tuple[int, int, int, int] = COLOR_SPELL_AOE,
    ) -> None:
        """Adiciona ou atualiza a cor de uma célula específica."""
        self.__highlighted_cells[(int(col), int(row))] = tuple(color)
        self.__dirty = True

    def remove_cell(self, col: int, row: int) -> bool:
        """Remove a célula especificada. Retorna True se foi removida, False se não existia."""
        key = (int(col), int(row))
        if key in self.__highlighted_cells:
            del self.__highlighted_cells[key]
            self.__dirty = True
            return True
        return False

    def clear(self) -> None:
        """Limpa todas as células destacadas."""
        if self.__highlighted_cells:
            self.__highlighted_cells.clear()
            self.__dirty = True

    def is_highlighted(self, col: int, row: int) -> bool:
        """Verifica se a célula especificada está destacada."""
        return (int(col), int(row)) in self.__highlighted_cells

    def get_color(self, col: int, row: int) -> Optional[Tuple[int, int, int, int]]:
        """Retorna a cor RGBA da célula especificada, ou None se não destacada."""
        return self.__highlighted_cells.get((int(col), int(row)))

    # --- Renderização Otimizada em GPU (Batch Draw) ---

    def _rebuild_shape_list(
        self,
        draw_x: float,
        draw_y: float,
        cell_w: float,
        cell_h: float,
    ) -> bool:
        """
        Reconstrói a ShapeElementList para renderização acelerada por GPU.
        Retorna True se a construção foi bem-sucedida, ou False se não há contexto/janela.
        """
        if ShapeElementList is None:
            self.__shape_list = None
            return False

        try:
            shape_list = ShapeElementList()
            for (col, row), color in self.__highlighted_cells.items():
                cx = draw_x + (col + 0.5) * cell_w
                cy = draw_y + (row + 0.5) * cell_h

                # Preenchimento translúcido da célula
                fill_shape = create_rectangle_filled(
                    center_x=cx,
                    center_y=cy,
                    width=cell_w,
                    height=cell_h,
                    color=color,
                )
                shape_list.append(fill_shape)

                # Borda sutil de 1px
                r, g, b, a = color
                outline_color = (r, g, b, min(255, int(a * 1.8)))
                outline_shape = create_rectangle_outline(
                    center_x=cx,
                    center_y=cy,
                    width=cell_w,
                    height=cell_h,
                    color=outline_color,
                    border_width=1.0,
                )
                shape_list.append(outline_shape)

            self.__shape_list = shape_list
            self.__last_layout = (draw_x, draw_y, cell_w, cell_h)
            self.__dirty = False
            return True
        except Exception as e:
            # Em ambientes sem janela gráfica ou contexto headless, fallback defensivo
            logger.debug(f"ShapeElementList indisponível para GridCellHighlighter: {e}")
            self.__shape_list = None
            return False

    def draw(
        self,
        draw_x: float,
        draw_y: float,
        scale: float = 1.0,
        cell_w: Optional[float] = None,
        cell_h: Optional[float] = None,
    ) -> None:
        """
        Desenha as células destacadas sobre a grade tática.
        
        :param draw_x: Offset X de início do grid na tela.
        :param draw_y: Offset Y de início do grid na tela.
        :param scale: Escala uniforme entre coordenadas de mundo e tela (ou tamanho da célula se > 5.0 e cell_w is None).
        :param cell_w: Largura em pixels da célula na tela.
        :param cell_h: Altura em pixels da célula na tela.
        """
        if not self.__highlighted_cells:
            return

        # Determinação das dimensões da célula
        if cell_w is not None and cell_h is not None:
            cw = float(cell_w)
            ch = float(cell_h)
        elif scale > 5.0 and cell_w is None:
            # Compatibilidade com chamadas draw(draw_x, draw_y, cell_size)
            cw = float(scale)
            ch = float(scale)
        elif self.__grid_manager is not None:
            cw = self.__grid_manager.cell_size * scale
            ch = self.__grid_manager.cell_size * scale
        else:
            return

        if cw <= 0.0 or ch <= 0.0:
            return

        current_layout = (draw_x, draw_y, cw, ch)
        if self.__dirty or current_layout != self.__last_layout or self.__shape_list is None:
            self._rebuild_shape_list(draw_x, draw_y, cw, ch)

        # Se ShapeElementList estiver construída, executa em GPU
        if self.__shape_list is not None:
            try:
                self.__shape_list.draw()
                return
            except Exception:
                pass

        # Fallback de desenho direto (compatível com testes e contextos imediatos)
        try:
            for (col, row), color in self.__highlighted_cells.items():
                cx = draw_x + (col + 0.5) * cw
                cy = draw_y + (row + 0.5) * ch
                r, g, b, a = color
                outline_color = (r, g, b, min(255, int(a * 1.8)))

                arcade.draw_rect_filled(arcade.XYWH(cx, cy, cw, ch), color)
                arcade.draw_rect_outline(arcade.XYWH(cx, cy, cw, ch), outline_color, 1.0)
        except Exception as e:
            logger.debug(f"GridCellHighlighter.draw ignorado em ambiente sem janela gráfica: {e}")
