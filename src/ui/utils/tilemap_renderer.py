import logging
from typing import Optional, Dict, Tuple, List
import arcade
from ...domain.models.tile_map import TileMap
from ...domain.loaders.tileset_manager import TilesetManager
from ...manager.grid_manager import GridManager

logger = logging.getLogger(__name__)


class TileMapRenderer:
    """
    Renderizador em Lote (Batch GPU) de Mapas Modulares baseados em Tilesets para o Medusa VTT.
    Integra a arte fatiada pelo TilesetManager com as dimensões do TileMap e GridManager,
    montando uma única arcade.SpriteList(use_spatial_hash=False) para renderização com pixelated=True.
    """

    def __init__(
        self,
        tile_map: TileMap,
        tileset_manager: Optional[TilesetManager] = None,
        grid_manager: Optional[GridManager] = None,
        tile_size: float = 32.0,
    ) -> None:
        self.__tile_map: TileMap = tile_map
        self.__tileset_manager: TilesetManager = (
            tileset_manager or TilesetManager.get_tileset(tile_map.tileset_name)
        )
        self.__grid_manager: Optional[GridManager] = grid_manager
        self.__tile_size: float = max(1.0, float(tile_size))

        self.__sprite_list: arcade.SpriteList = arcade.SpriteList(use_spatial_hash=False)
        self.__sprites_by_coord: Dict[Tuple[int, int], arcade.Sprite] = {}

        self._build_sprites()

    # --- Properties ---

    @property
    def tile_map(self) -> TileMap:
        """Referência ao modelo de dados do TileMap."""
        return self.__tile_map

    @property
    def tileset_manager(self) -> TilesetManager:
        """Referência ao TilesetManager associado."""
        return self.__tileset_manager

    @property
    def grid_manager(self) -> Optional[GridManager]:
        """Referência ao GridManager associado (se houver)."""
        return self.__grid_manager

    @property
    def sprite_list(self) -> arcade.SpriteList:
        """Acesso à lista única de sprites montada para desenho em lote."""
        return self.__sprite_list

    @property
    def tile_count(self) -> int:
        """Quantidade de sprites de chão instanciados."""
        return len(self.__sprite_list)

    @property
    def tile_size(self) -> float:
        """Dimensão base em pixels de cada tile (padrão: 32px)."""
        return self.__tile_size

    # --- Construção dos Sprites ---

    def _build_sprites(self) -> None:
        """
        Itera sobre todos os tiles definidos no TileMap, obtém a textura fatiada
        do TilesetManager e posiciona cada sprite no centro da célula correspondente.
        """
        self.__sprite_list.clear()
        self.__sprites_by_coord.clear()

        tile_ids = self.__tile_map.tile_ids
        for (col, row), tile_id in sorted(tile_ids.items(), key=lambda item: (item[0][1], item[0][0])):
            tex = self.__tileset_manager.get_tile_texture(tile_id)
            if tex is None:
                logger.warning(
                    f"Textura para tile_id {tile_id} na célula ({col}, {row}) não encontrada."
                )
                continue

            sprite = arcade.Sprite(tex)

            # Cálculo de centro com half-tile offset (16px para tile_size=32)
            if self.__grid_manager is not None:
                cx, cy = self.__grid_manager.grid_to_world_center(col, row)
            else:
                cx = (float(col) + 0.5) * self.__tile_size
                cy = (float(row) + 0.5) * self.__tile_size

            sprite.center_x = cx
            sprite.center_y = cy
            sprite.scale_x = 1.0
            sprite.scale_y = 1.0

            self.__sprite_list.append(sprite)
            self.__sprites_by_coord[(col, row)] = sprite

        logger.info(
            f"TileMapRenderer montado: {len(self.__sprite_list)} sprites instanciados "
            f"para mapa '{self.__tile_map.tileset_name}' ({self.__tile_map.width}x{self.__tile_map.height})."
        )

    # --- Ajuste Dinâmico de Viewport / Layout ---

    def update_layout(
        self,
        draw_x: float,
        draw_y: float,
        cell_w: float,
        cell_h: float,
    ) -> None:
        """
        Reposiciona e redimensiona todos os sprites da SpriteList para se ajustarem
        a um retângulo de viewport específico (ex: TacticalMiniMap ou PlayerWindow).
        """
        scale_x = cell_w / self.__tile_size
        scale_y = cell_h / self.__tile_size

        for (col, row), sprite in self.__sprites_by_coord.items():
            cx = draw_x + (float(col) + 0.5) * cell_w
            cy = draw_y + (float(row) + 0.5) * cell_h
            sprite.center_x = cx
            sprite.center_y = cy
            sprite.scale_x = scale_x
            sprite.scale_y = scale_y

    def reset_to_world_coordinates(self) -> None:
        """Restaura as posições e escalas dos sprites para as coordenadas mundiais padrão."""
        for (col, row), sprite in self.__sprites_by_coord.items():
            if self.__grid_manager is not None:
                cx, cy = self.__grid_manager.grid_to_world_center(col, row)
            else:
                cx = (float(col) + 0.5) * self.__tile_size
                cy = (float(row) + 0.5) * self.__tile_size

            sprite.center_x = cx
            sprite.center_y = cy
            sprite.scale_x = 1.0
            sprite.scale_y = 1.0

    # --- Renderização em Lote na GPU ---

    def draw(self, pixelated: bool = True) -> None:
        """
        Desenha a lista completa de sprites em uma única chamada de renderização na GPU.
        Por padrão, utiliza pixelated=True para manter a nitidez de pixel art.
        """
        if len(self.__sprite_list) > 0:
            self.__sprite_list.draw(pixelated=pixelated)

    def __repr__(self) -> str:
        return (
            f"<TileMapRenderer map='{self.__tile_map.tileset_name}' "
            f"sprites={len(self.__sprite_list)} tile_size={self.__tile_size}px>"
        )
