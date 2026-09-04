import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, Union, List, Set
from ..models.tile_map import TileMap, TileProperties

logger = logging.getLogger(__name__)


def _resolve_project_path(path_str: str) -> Optional[Path]:
    """Resolve caminho de arquivo relativo ao diretório de trabalho ou raiz do projeto."""
    if not path_str:
        return None
    p = Path(path_str)
    if p.is_file():
        return p.resolve()

    root = Path(__file__).resolve().parent.parent.parent.parent
    cand = root / path_str
    if cand.is_file():
        return cand.resolve()
    return None


class TileMapLoader:
    """
    Carregador e Parser de Mapas Modulares (TileMap) para o Medusa VTT.
    Responsável por interpretar arquivos JSON em formato compacto (normalizado por Tile ID)
    ou no formato legado (lista 'tiles'), construindo a grade tática e o mapa de IDs de tiles.
    """

    DEFAULT_SEARCH_DIRS = (
        "creations/maps",
        "presets/maps",
        "assets/tilesets",
        "assets/images/tilemaps",
        "assets/images/maps",
        ".",
    )

    @classmethod
    def resolve_map_path(cls, file_path: Union[str, Path]) -> Optional[Path]:
        """
        Resolve o caminho de um arquivo de mapa JSON em múltiplos diretórios candidatos.
        """
        p_str = str(file_path).strip()
        if not p_str:
            return None

        # 1. Checagem direta
        direct = _resolve_project_path(p_str)
        if direct:
            return direct

        p = Path(p_str)
        file_name = p.name
        candidates = [
            file_name,
            f"{file_name}.json" if not file_name.endswith(".json") else file_name,
            f"{p.stem}_map.json",
        ]

        # 2. Busca nos diretórios padrão
        for base in cls.DEFAULT_SEARCH_DIRS:
            base_p = Path(base)
            if not base_p.exists():
                root = Path(__file__).resolve().parent.parent.parent.parent
                base_p = root / base
                if not base_p.exists():
                    continue

            for cand in candidates:
                cand_path = base_p / cand
                if cand_path.is_file():
                    return cand_path.resolve()

            # Busca por varredura de stem
            for f in base_p.glob("*.json"):
                if p.stem == f.stem or p.stem in f.stem:
                    return f.resolve()

        return None

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> TileMap:
        """
        Carrega e processa um arquivo JSON de layout de mapa com tratamento defensivo de erros.
        """
        resolved_path = cls.resolve_map_path(file_path)
        if resolved_path is None or not resolved_path.is_file():
            logger.error(f"Arquivo de mapa não encontrado: '{file_path}'")
            raise FileNotFoundError(f"Arquivo de mapa não encontrado: '{file_path}'")

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"TileMap carregado com sucesso a partir de '{resolved_path.name}'.")
            return cls.load_from_dict(data)
        except Exception as e:
            logger.error(f"Erro ao carregar TileMap de '{resolved_path}': {e}")
            raise

    @classmethod
    def load_from_dict(cls, data: Dict[str, Any]) -> TileMap:
        """
        Constrói uma instância de TileMap a partir de um dicionário,
        detectando automaticamente entre o formato compacto ('data') e o formato legado ('tiles').
        """
        if not isinstance(data, dict):
            raise ValueError(f"Dados inválidos para TileMap: esperado dict, recebido {type(data)}")

        width = max(1, int(data.get("width", 1)))
        height = max(1, int(data.get("height", 1)))
        tileset_name = str(data.get("tileset", "default")).strip()

        if "data" in data:
            tile_ids, tactical_grid = cls.parse_compact_schema(data, width=width, height=height)
        elif "tiles" in data:
            tile_ids, tactical_grid = cls.parse_legacy_schema(data, width=width, height=height)
        else:
            logger.warning(
                "Dados de mapa não contêm 'data' nem 'tiles'. Inicializando grade tática neutra."
            )
            tile_ids = {}
            tactical_grid = {}

        return TileMap(
            width=width,
            height=height,
            tileset_name=tileset_name,
            tactical_grid=tactical_grid,
            tile_ids=tile_ids,
        )

    @classmethod
    def parse_compact_schema(
        cls, data: Dict[str, Any], width: int, height: int
    ) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], TileProperties]]:
        """
        Faz o parsing do schema compacto normalizado por Tile ID:
          - 'data': matriz 2D [height][width] contendo tile_id.
          - 'block_movement': lista de tile_ids que bloqueiam movimento.
          - 'block_vision': lista de tile_ids que bloqueiam visão.
          - 'cover': dicionário com listas {'half': [...], 'three_quarters': [...], 'full': [...]}
          - 'difficult_terrain': lista de tile_ids com terreno difícil.
          - 'heights': objeto ou lista de objetos definindo elevação {'pos': {'x': int, 'y': int}, 'height': int}.
        """
        raw_data: List[List[Any]] = data.get("data", [])
        tile_ids: Dict[Tuple[int, int], int] = {}
        tactical_grid: Dict[Tuple[int, int], TileProperties] = {}

        # 1. Catálogos de Lookup por Tile ID
        block_movement_ids: Set[int] = set(int(tid) for tid in data.get("block_movement", []) if tid is not None)
        block_vision_ids: Set[int] = set(int(tid) for tid in data.get("block_vision", []) if tid is not None)
        difficult_terrain_ids: Set[int] = set(int(tid) for tid in data.get("difficult_terrain", []) if tid is not None)

        cover_dict: Dict[str, Any] = data.get("cover", {})
        if not isinstance(cover_dict, dict):
            cover_dict = {}

        half_cover_ids: Set[int] = set(int(tid) for tid in cover_dict.get("half", []) if tid is not None)
        three_quarters_cover_ids: Set[int] = set(
            int(tid) for tid in cover_dict.get("three_quarters", []) if tid is not None
        )
        full_cover_ids: Set[int] = set(
            int(tid)
            for tid in (cover_dict.get("full", []) or cover_dict.get("total", []))
            if tid is not None
        )

        # 2. Processamento de Alturas Customizadas (Heights)
        height_overrides: Dict[Tuple[int, int], int] = {}
        raw_heights = data.get("heights")
        if raw_heights:
            heights_list: List[Dict[str, Any]] = (
                raw_heights if isinstance(raw_heights, list) else [raw_heights]
            )
            for entry in heights_list:
                if not isinstance(entry, dict):
                    continue
                h_val = max(0, int(entry.get("height", 0)))
                pos = entry.get("pos")
                if isinstance(pos, dict):
                    hx = pos.get("x")
                    hy = pos.get("y")
                else:
                    hx = entry.get("x")
                    hy = entry.get("y")

                if hx is not None and hy is not None:
                    height_overrides[(int(hx), int(hy))] = h_val

        # 3. Iteração pela Matriz 2D data[y][x]
        # y varia de 0 até height - 1 (linhas), x varia de 0 até width - 1 (colunas)
        for y in range(height):
            row = raw_data[y] if y < len(raw_data) and isinstance(raw_data[y], list) else []
            for x in range(width):
                tile_id: Optional[int] = int(row[x]) if x < len(row) and row[x] is not None else None

                if tile_id is not None:
                    tile_ids[(x, y)] = tile_id
                    blocks_movement = tile_id in block_movement_ids
                    blocks_vision = tile_id in block_vision_ids
                    difficult_terrain = tile_id in difficult_terrain_ids

                    if tile_id in full_cover_ids:
                        cover_type = "total"
                    elif tile_id in three_quarters_cover_ids:
                        cover_type = "three_quarters"
                    elif tile_id in half_cover_ids:
                        cover_type = "half"
                    else:
                        cover_type = "none"
                else:
                    blocks_movement = False
                    blocks_vision = False
                    difficult_terrain = False
                    cover_type = "none"

                # Altura situacional tem precedência ou default 0
                cell_height = height_overrides.get((x, y), 0)

                tactical_grid[(x, y)] = TileProperties(
                    blocks_movement=blocks_movement,
                    blocks_vision=blocks_vision,
                    cover_type=cover_type,
                    difficult_terrain=difficult_terrain,
                    height=cell_height,
                )

        return tile_ids, tactical_grid

    @classmethod
    def parse_legacy_schema(
        cls, data: Dict[str, Any], width: int, height: int
    ) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], TileProperties]]:
        """
        Faz o parsing do schema legado baseado na lista 'tiles':
        [ {'x': int, 'y': int, 'tile_id': int, 'properties': {...}}, ... ]
        """
        raw_tiles: List[Dict[str, Any]] = data.get("tiles", [])
        tile_ids: Dict[Tuple[int, int], int] = {}
        tactical_grid: Dict[Tuple[int, int], TileProperties] = {}

        for entry in raw_tiles:
            if not isinstance(entry, dict):
                continue
            tx = int(entry.get("x", 0))
            ty = int(entry.get("y", 0))
            raw_tid = entry.get("tile_id")
            if raw_tid is not None:
                tile_ids[(tx, ty)] = int(raw_tid)

            raw_props = entry.get("properties")
            if raw_props is not None:
                tactical_grid[(tx, ty)] = TileProperties.from_dict(raw_props)
            else:
                tactical_grid[(tx, ty)] = TileProperties()

        return tile_ids, tactical_grid
