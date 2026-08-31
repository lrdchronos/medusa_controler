import logging
import math
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GridManager:
    """
    Gerenciador e Utilitário de Matriz para o Grid Tático do Medusa VTT.
    Converte coordenadas contínuas de mundo/tela para índices matriciais (coluna, linha)
    e vice-versa, permitindo alinhamento e Snap-to-Grid de tokens sobre o mapa de batalha.
    """

    def __init__(
        self,
        map_width: float,
        map_height: float,
        columns: int = 25,
        feet_per_square: int = 5,
    ) -> None:
        self._map_width: float = max(1.0, float(map_width))
        self._map_height: float = max(1.0, float(map_height))
        self._columns: int = max(1, int(columns))
        self._feet_per_square: int = max(1, int(feet_per_square))

        # Tamanho do quadrado da grade em pixels
        self._cell_size: float = self._map_width / float(self._columns)
        # Número de linhas calculado proporcionalmente à altura
        self._rows: int = max(1, math.ceil(self._map_height / self._cell_size))

    # --- Properties ---

    @property
    def map_width(self) -> float:
        return self._map_width

    @property
    def map_height(self) -> float:
        return self._map_height

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cell_size(self) -> float:
        return self._cell_size

    @property
    def feet_per_square(self) -> int:
        return self._feet_per_square

    # --- Métodos de Conversão e Snap ---

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """
        Converte coordenadas contínuas de mundo (x, y) para índices matriciais (col, row).
        Garante que o retorno permaneça dentro dos limites válidos da grade.
        """
        col = int(math.floor(x / self._cell_size))
        row = int(math.floor(y / self._cell_size))

        # Clamping aos limites válidos
        clamped_col = max(0, min(self._columns - 1, col))
        clamped_row = max(0, min(self._rows - 1, row))
        return clamped_col, clamped_row

    def grid_to_world_center(self, col: int, row: int) -> Tuple[float, float]:
        """
        Devolve o ponto central (center_x, center_y) em pixels da célula especificada
        para alinhamento preciso (Snap-to-Grid) de tokens.
        """
        clamped_col = max(0, min(self._columns - 1, int(col)))
        clamped_row = max(0, min(self._rows - 1, int(row)))

        center_x = (clamped_col + 0.5) * self._cell_size
        center_y = (clamped_row + 0.5) * self._cell_size
        return float(center_x), float(center_y)

    def snap_to_grid(self, x: float, y: float) -> Tuple[float, float]:
        """
        Converte diretamente uma coordenada de mundo contínua (x, y)
        para o centro do quadrado correspondente mais próximo.
        """
        col, row = self.world_to_grid(x, y)
        return self.grid_to_world_center(col, row)

    def is_valid_cell(self, col: int, row: int) -> bool:
        """Verifica se a célula especificada pertence à matriz do mapa."""
        return 0 <= col < self._columns and 0 <= row < self._rows

    def calculate_distance_feet(self, col1: int, row1: int, col2: int, row2: int) -> float:
        """
        Calcula a distância em pés (feet) entre duas células da grade usando
        a métrica euclidiana multiplicada por feet_per_square.
        """
        dx = col2 - col1
        dy = row2 - row1
        squares = math.sqrt(dx * dx + dy * dy)
        return squares * self._feet_per_square

    def to_dict(self) -> Dict[str, Any]:
        """Retorna metadados estruturados da grade."""
        return {
            "map_width": self._map_width,
            "map_height": self._map_height,
            "columns": self._columns,
            "rows": self._rows,
            "cell_size": self._cell_size,
            "feet_per_square": self._feet_per_square,
        }

    def __repr__(self) -> str:
        return (
            f"<GridManager cols={self._columns} rows={self._rows} "
            f"cell_size={self._cell_size:.2f}px feet/sq={self._feet_per_square}>"
        )
