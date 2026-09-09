import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, Union, List, Set
from .map_asset import MapAsset, VALID_ASSET_TYPES
from .tile_properties import TileProperties, VALID_COVER_TYPES

logger = logging.getLogger(__name__)


class TileMap:
    """
    Motor e Modelo de Mapa Modular baseado em Tilesets e Grade Tática D&D 5E.
    Processa arquivos JSON de layout, armazena propriedades matriciais por (x, y)
    e fornece consultas em O(1) com validações defensivas.
    """

    def __init__(
        self,
        width: int,
        height: int,
        tileset_name: str,
        tactical_grid: Optional[Dict[Tuple[int, int], TileProperties]] = None,
        tile_ids: Optional[Dict[Tuple[int, int], int]] = None,
        assets: Optional[List[MapAsset]] = None,
    ) -> None:
        self.__width: int = max(1, int(width))
        self.__height: int = max(1, int(height))
        self.__tileset_name: str = str(tileset_name).strip() if tileset_name else "default"

        self.__tactical_grid: Dict[Tuple[int, int], TileProperties] = (
            dict(tactical_grid) if tactical_grid else {}
        )
        self.__tile_ids: Dict[Tuple[int, int], int] = (
            dict(tile_ids) if tile_ids else {}
        )
        self.__assets: List[MapAsset] = list(assets) if assets else []

    # --- Properties Públicas (Imutabilidade Externa) ---

    @property
    def width(self) -> int:
        """Largura do mapa em quantidade de colunas/células."""
        return self.__width

    @property
    def height(self) -> int:
        """Altura do mapa em quantidade de linhas/células."""
        return self.__height

    @property
    def tileset_name(self) -> str:
        """Nome base do tileset associado ao mapa."""
        return self.__tileset_name

    @property
    def tactical_grid(self) -> Dict[Tuple[int, int], TileProperties]:
        """Cópia defensiva do mapa de propriedades táticas."""
        return self.__tactical_grid.copy()

    @property
    def tile_ids(self) -> Dict[Tuple[int, int], int]:
        """Cópia defensiva do mapa de IDs visuais dos tiles."""
        return self.__tile_ids.copy()

    @property
    def assets(self) -> List[MapAsset]:
        """Cópia defensiva da lista de props e objetos do mapa."""
        return self.__assets.copy()

    # --- Métodos Utilitários em O(1) com Validações Defensivas ---

    def is_valid_cell(self, x: int, y: int) -> bool:
        """Verifica se as coordenadas (x, y) estão dentro dos limites do grid."""
        return 0 <= int(x) < self.__width and 0 <= int(y) < self.__height

    def is_walkable(self, x: int, y: int) -> bool:
        """
        Retorna True se a célula permite movimentação física de entidades.
        Coordenadas fora do grid retornam False defensivamente.
        """
        if not self.is_valid_cell(x, y):
            return False
        props = self.__tactical_grid.get((int(x), int(y)))
        if props is not None:
            return not props.blocks_movement
        return True

    def blocks_vision(self, x: int, y: int) -> bool:
        """
        Retorna True se a célula bloqueia linha de visão (LoS) e Fog of War.
        Coordenadas fora do grid retornam True defensivamente.
        """
        if not self.is_valid_cell(x, y):
            return True
        props = self.__tactical_grid.get((int(x), int(y)))
        if props is not None:
            return props.blocks_vision
        return False

    def get_cover(self, x: int, y: int) -> str:
        """
        Retorna o tipo de cobertura D&D 5E da célula ('none', 'half', 'three_quarters', 'total').
        Coordenadas fora do grid retornam 'none'.
        """
        if not self.is_valid_cell(x, y):
            return "none"
        props = self.__tactical_grid.get((int(x), int(y)))
        if props is not None:
            return props.cover_type
        return "none"

    def is_difficult(self, x: int, y: int) -> bool:
        """
        Retorna True se a célula é terreno difícil (custo dobrado de movimento).
        Coordenadas fora do grid retornam False.
        """
        if not self.is_valid_cell(x, y):
            return False
        props = self.__tactical_grid.get((int(x), int(y)))
        if props is not None:
            return props.difficult_terrain
        return False

    def get_height(self, x: int, y: int) -> int:
        """
        Retorna a elevação da célula em quadrados (padrão 0).
        Coordenadas fora do grid retornam 0.
        """
        if not self.is_valid_cell(x, y):
            return 0
        props = self.__tactical_grid.get((int(x), int(y)))
        if props is not None:
            return props.height
        return 0

    def get_tile_id(self, x: int, y: int) -> Optional[int]:
        """Retorna o ID do tile na célula especificada, ou None se não definido / fora do grid."""
        if not self.is_valid_cell(x, y):
            return None
        return self.__tile_ids.get((int(x), int(y)))

    def get_properties(self, x: int, y: int) -> TileProperties:
        """Retorna o objeto TileProperties da célula especificada, ou um padrão neutro."""
        if not self.is_valid_cell(x, y):
            return TileProperties(blocks_movement=True, blocks_vision=True)
        return self.__tactical_grid.get((int(x), int(y)), TileProperties())

    def grid_to_tile_coords(self, grid_col: int, grid_row: int, grid_cols: int, grid_rows: int) -> Tuple[int, int]:
        """
        Mapeia uma célula de um grid tático independente (grid_col, grid_row) para as coordenadas
        matriciais do TileMap (x, y), onde x=0, y=0 é o canto superior esquerdo (Top-Left) e
        x=width-1, y=height-1 é o canto inferior direito (Bottom-Right).
        """
        if grid_cols <= 0 or grid_rows <= 0:
            return 0, 0
        u = (float(grid_col) + 0.5) / float(grid_cols)
        v = (float(grid_row) + 0.5) / float(grid_rows)

        tx = min(self.__width - 1, max(0, int(u * self.__width)))
        tile_screen_row = min(self.__height - 1, max(0, int(v * self.__height)))
        ty = (self.__height - 1) - tile_screen_row
        return tx, ty

    def is_walkable_at_grid(self, grid_col: int, grid_row: int, grid_cols: int, grid_rows: int) -> bool:
        """Verifica se a célula do grid tático independente é transitável com base no tile subjacente."""
        tx, ty = self.grid_to_tile_coords(grid_col, grid_row, grid_cols, grid_rows)
        return self.is_walkable(tx, ty)

    def blocks_vision_at_grid(self, grid_col: int, grid_row: int, grid_cols: int, grid_rows: int) -> bool:
        """Verifica se a célula do grid tático independente bloqueia visão com base no tile subjacente."""
        tx, ty = self.grid_to_tile_coords(grid_col, grid_row, grid_cols, grid_rows)
        return self.blocks_vision(tx, ty)

    def is_difficult_at_grid(self, grid_col: int, grid_row: int, grid_cols: int, grid_rows: int) -> bool:
        """Verifica se a célula do grid tático independente é terreno difícil com base no tile subjacente."""
        tx, ty = self.grid_to_tile_coords(grid_col, grid_row, grid_cols, grid_rows)
        return self.is_difficult(tx, ty)

    # --- Métodos de Fábrica e Serialização ---

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TileMap":
        """
        Constrói uma instância de TileMap a partir de um dicionário de layout e dados táticos.
        Delega ao TileMapLoader especializado.
        """
        from ..loaders.tile_map_loader import TileMapLoader
        return TileMapLoader.load_from_dict(data)

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "TileMap":
        """
        Carrega e processa o arquivo JSON de layout do mapa com tratamento de erros.
        Delega ao TileMapLoader especializado.
        """
        from ..loaders.tile_map_loader import TileMapLoader
        return TileMapLoader.load_from_file(file_path)

    def to_dict(self, compact: bool = False) -> Dict[str, Any]:
        """
        Serializa a estrutura do mapa para formato JSON padrão (legado ou compacto).
        """
        if compact:
            # Serialização compacta normalizada por Tile ID
            data_matrix: List[List[int]] = []
            block_movement_set: Set[int] = set()
            block_vision_set: Set[int] = set()
            difficult_terrain_set: Set[int] = set()
            half_cover_set: Set[int] = set()
            three_quarters_cover_set: Set[int] = set()
            full_cover_set: Set[int] = set()
            heights_list: List[Dict[str, Any]] = []

            for y in range(self.__height):
                row: List[int] = []
                for x in range(self.__width):
                    tid = self.__tile_ids.get((x, y), 0)
                    row.append(tid)
                    props = self.__tactical_grid.get((x, y))
                    if props:
                        if props.blocks_movement:
                            block_movement_set.add(tid)
                        if props.blocks_vision:
                            block_vision_set.add(tid)
                        if props.difficult_terrain:
                            difficult_terrain_set.add(tid)
                        if props.cover_type == "half":
                            half_cover_set.add(tid)
                        elif props.cover_type == "three_quarters":
                            three_quarters_cover_set.add(tid)
                        elif props.cover_type in ("total", "full"):
                            full_cover_set.add(tid)
                        if props.height > 0:
                            heights_list.append({"pos": {"x": x, "y": y}, "height": props.height})
                data_matrix.append(row)

            result: Dict[str, Any] = {
                "tileset": self.__tileset_name,
                "width": self.__width,
                "height": self.__height,
                "data": data_matrix,
                "block_movement": sorted(list(block_movement_set)),
                "block_vision": sorted(list(block_vision_set)),
                "cover": {
                    "half": sorted(list(half_cover_set)),
                    "three_quarters": sorted(list(three_quarters_cover_set)),
                    "full": sorted(list(full_cover_set)),
                },
                "difficult_terrain": sorted(list(difficult_terrain_set)),
                "heights": heights_list if len(heights_list) > 1 else (heights_list[0] if heights_list else None),
            }
            if self.__assets:
                result["assets"] = [a.to_dict() for a in self.__assets]
            return result

        # Serialização legada
        tiles_data: List[Dict[str, Any]] = []
        all_coords = set(self.__tile_ids.keys()) | set(self.__tactical_grid.keys())
        for x, y in sorted(all_coords, key=lambda c: (c[1], c[0])):
            entry: Dict[str, Any] = {"x": x, "y": y}
            if (x, y) in self.__tile_ids:
                entry["tile_id"] = self.__tile_ids[(x, y)]
            if (x, y) in self.__tactical_grid:
                entry["properties"] = self.__tactical_grid[(x, y)].to_dict()
            tiles_data.append(entry)

        legacy_result: Dict[str, Any] = {
            "tileset": self.__tileset_name,
            "width": self.__width,
            "height": self.__height,
            "tiles": tiles_data,
        }
        if self.__assets:
            legacy_result["assets"] = [a.to_dict() for a in self.__assets]
        return legacy_result

    def __repr__(self) -> str:
        return (
            f"<TileMap '{self.__tileset_name}' {self.__width}x{self.__height} "
            f"tiles={len(self.__tile_ids)} tactical_cells={len(self.__tactical_grid)}>"
        )


# Alias de conveniência e conformidade arquitetural
TileMapEngine = TileMap
