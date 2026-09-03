import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, Union, List

logger = logging.getLogger(__name__)

VALID_COVER_TYPES = ("none", "half", "three_quarters", "total")


class TileProperties:
    """
    Objeto imutável de valor (Value Object) que encapsula as propriedades táticas D&D 5E de uma célula.
    Encapsulamento estrito com atributos privados e validações defensivas Poka-Yoke.
    """

    def __init__(
        self,
        blocks_movement: bool = False,
        blocks_vision: bool = False,
        cover_type: str = "none",
        difficult_terrain: bool = False,
        height: int = 0,
    ) -> None:
        self.__blocks_movement: bool = bool(blocks_movement)
        self.__blocks_vision: bool = bool(blocks_vision)

        norm_cover = str(cover_type).strip().lower() if cover_type else "none"
        if norm_cover not in VALID_COVER_TYPES:
            logger.warning(
                f"cover_type '{cover_type}' inválido. Ajustando para 'none'. Válidos: {VALID_COVER_TYPES}"
            )
            norm_cover = "none"
        self.__cover_type: str = norm_cover

        self.__difficult_terrain: bool = bool(difficult_terrain)
        self.__height: int = max(0, int(height))

    @property
    def blocks_movement(self) -> bool:
        """Indica se a célula impede passagem física de entidades e trava o Snap-to-Grid."""
        return self.__blocks_movement

    @property
    def blocks_vision(self) -> bool:
        """Indica se a célula oclui cálculos de Linha de Visão (LoS) e Fog of War."""
        return self.__blocks_vision

    @property
    def cover_type(self) -> str:
        """Nível de cobertura D&D 5E ('none', 'half', 'three_quarters', 'total')."""
        return self.__cover_type

    @property
    def difficult_terrain(self) -> bool:
        """Indica se a célula cobra custo dobrado de movimento (10ft por quadrado)."""
        return self.__difficult_terrain

    @property
    def height(self) -> int:
        """Elevação da célula em quadrados (padrão 0)."""
        return self.__height

    def to_dict(self) -> Dict[str, Any]:
        """Serializa propriedades para dicionário JSON-compatível."""
        return {
            "blocks_movement": self.__blocks_movement,
            "blocks_vision": self.__blocks_vision,
            "cover_type": self.__cover_type,
            "difficult_terrain": self.__difficult_terrain,
            "height": self.__height,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TileProperties":
        """Instancia TileProperties a partir de dicionário com validação defensiva."""
        if not data or not isinstance(data, dict):
            return cls()

        return cls(
            blocks_movement=data.get("blocks_movement", False),
            blocks_vision=data.get("blocks_vision", False),
            cover_type=data.get("cover_type", "none"),
            difficult_terrain=data.get("difficult_terrain", False),
            height=data.get("height", 0),
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TileProperties):
            return False
        return (
            self.__blocks_movement == other.__blocks_movement
            and self.__blocks_vision == other.__blocks_vision
            and self.__cover_type == other.__cover_type
            and self.__difficult_terrain == other.__difficult_terrain
            and self.__height == other.__height
        )

    def __repr__(self) -> str:
        return (
            f"TileProperties(blocks_movement={self.__blocks_movement}, "
            f"blocks_vision={self.__blocks_vision}, cover_type='{self.__cover_type}', "
            f"difficult_terrain={self.__difficult_terrain}, height={self.__height})"
        )


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

    # --- Métodos de Fábrica e Serialização ---

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TileMap":
        """
        Constrói uma instância de TileMap a partir de um dicionário de layout e dados táticos.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Dados inválidos para TileMap: esperado dict, recebido {type(data)}")

        width = int(data.get("width", 1))
        height = int(data.get("height", 1))
        tileset_name = str(data.get("tileset", "default")).strip()

        tactical_grid: Dict[Tuple[int, int], TileProperties] = {}
        tile_ids: Dict[Tuple[int, int], int] = {}

        raw_tiles: List[Dict[str, Any]] = data.get("tiles", [])
        for entry in raw_tiles:
            if not isinstance(entry, dict):
                continue
            tx = int(entry.get("x", 0))
            ty = int(entry.get("y", 0))
            tile_id = entry.get("tile_id")
            if tile_id is not None:
                tile_ids[(tx, ty)] = int(tile_id)

            raw_props = entry.get("properties")
            if raw_props is not None:
                tactical_grid[(tx, ty)] = TileProperties.from_dict(raw_props)

        return cls(
            width=width,
            height=height,
            tileset_name=tileset_name,
            tactical_grid=tactical_grid,
            tile_ids=tile_ids,
        )

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "TileMap":
        """
        Carrega e processa o arquivo JSON de layout do mapa com tratamento de erros.
        """
        p = Path(file_path)
        if not p.is_file():
            # Tenta resolver relativo a creations/maps/
            candidate = Path("creations/maps") / p.name
            if candidate.is_file():
                p = candidate
            else:
                logger.error(f"Arquivo de mapa não encontrado: '{file_path}' (resolvido: '{p}')")
                raise FileNotFoundError(f"Arquivo de mapa não encontrado: '{file_path}'")

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"TileMap carregado com sucesso a partir de '{p}'.")
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Erro ao carregar TileMap de '{p}': {e}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a estrutura do mapa para formato JSON padrão."""
        tiles_data: List[Dict[str, Any]] = []

        all_coords = set(self.__tile_ids.keys()) | set(self.__tactical_grid.keys())
        for x, y in sorted(all_coords, key=lambda c: (c[1], c[0])):
            entry: Dict[str, Any] = {"x": x, "y": y}
            if (x, y) in self.__tile_ids:
                entry["tile_id"] = self.__tile_ids[(x, y)]
            if (x, y) in self.__tactical_grid:
                entry["properties"] = self.__tactical_grid[(x, y)].to_dict()
            tiles_data.append(entry)

        return {
            "tileset": self.__tileset_name,
            "width": self.__width,
            "height": self.__height,
            "tiles": tiles_data,
        }

    def __repr__(self) -> str:
        return (
            f"<TileMap '{self.__tileset_name}' {self.__width}x{self.__height} "
            f"tiles={len(self.__tile_ids)} tactical_cells={len(self.__tactical_grid)}>"
        )
