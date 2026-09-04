import logging
from typing import Optional, Dict, Tuple, List, Any
import arcade
from ...domain.models.tile_map import TileMap, MapAsset
from ...domain.loaders.tileset_manager import TilesetManager
from ...manager.grid_manager import GridManager
from .sprite_utils import SpriteFactory

logger = logging.getLogger(__name__)


class TileMapRenderer:
    """
    Renderizador em Lote (Batch GPU) de Mapas Modulares baseados em Tilesets e Props para o Medusa VTT.
    Integra a arte fatiada pelo TilesetManager com as dimensões do TileMap e GridManager,
    montando camadas separadas para Chão (ground_sprites) e Objetos/Props (prop_sprites)
    com suporte a atualização de animações contínuas e renderização com pixelated=True.
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

        self.__ground_sprites: arcade.SpriteList = arcade.SpriteList(use_spatial_hash=False)
        self.__prop_sprites: arcade.SpriteList = arcade.SpriteList(use_spatial_hash=False)
        self.__sprites_by_coord: Dict[Tuple[int, int], arcade.Sprite] = {}
        self.__prop_entries: List[Tuple[arcade.Sprite, MapAsset]] = []

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
    def ground_sprites(self) -> arcade.SpriteList:
        """Acesso à lista de sprites da camada de chão."""
        return self.__ground_sprites

    @property
    def prop_sprites(self) -> arcade.SpriteList:
        """Acesso à lista de sprites da camada de props/objetos."""
        return self.__prop_sprites

    @property
    def sprite_list(self) -> arcade.SpriteList:
        """Alias para ground_sprites para conformidade e compatibilidade legada."""
        return self.__ground_sprites

    @property
    def tile_count(self) -> int:
        """Quantidade de sprites de chão instanciados."""
        return len(self.__ground_sprites)

    @property
    def prop_count(self) -> int:
        """Quantidade de sprites de props instanciados."""
        return len(self.__prop_sprites)

    @property
    def tile_size(self) -> float:
        """Dimensão base em pixels de cada tile (padrão: 32px)."""
        return self.__tile_size

    # --- Construção dos Sprites ---

    def _build_sprites(self) -> None:
        """
        Itera sobre todos os tiles e assets do TileMap, obtém as texturas fatiadas
        e instancia cada sprite na posição correspondente do grid.
        """
        self.__ground_sprites.clear()
        self.__prop_sprites.clear()
        self.__sprites_by_coord.clear()
        self.__prop_entries.clear()

        # 1. Camada de Chão (Ground Tiles)
        tile_ids = self.__tile_map.tile_ids
        for (tx, ty), tile_id in sorted(tile_ids.items(), key=lambda item: (item[0][1], item[0][0])):
            tex = self.__tileset_manager.get_tile_texture(tile_id)
            if tex is None:
                logger.warning(
                    f"Textura para tile_id {tile_id} na célula ({tx}, {ty}) não encontrada."
                )
                continue

            sprite = arcade.Sprite(tex)

            # Mapeamento matricial: (0, 0) é Top-Left, (width-1, height-1) é Bottom-Right
            col = tx
            row = (self.__tile_map.height - 1) - ty

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

            self.__ground_sprites.append(sprite)
            self.__sprites_by_coord[(tx, ty)] = sprite

        # 2. Camada de Objetos e Props de Cenário (Props Layer)
        for asset in self.__tile_map.assets:
            if not asset.sprite:
                continue

            if asset.type == "spritesheet":
                prop_sprite = SpriteFactory.create_animated_prop(
                    spritesheet_path=asset.sprite,
                    scale=1.0,
                    frame_count=6,
                    fps=8.0,
                    frame_width=32,
                    frame_height=32,
                )
            else:
                prop_sprite = SpriteFactory.create_static_prop(
                    image_path=asset.sprite,
                    scale=1.0,
                )

            col = asset.x
            row = (self.__tile_map.height - 1) - asset.y

            if self.__grid_manager is not None:
                cx, cy = self.__grid_manager.grid_to_world_center(col, row)
                global_scale_factor = self.__grid_manager.scale_factor
            else:
                cx = (float(col) + 0.5) * self.__tile_size
                cy = (float(row) + 0.5) * self.__tile_size
                global_scale_factor = 1.0

            prop_sprite.center_x = cx
            prop_sprite.center_y = cy
            prop_sprite.scale = float(asset.scale) * float(global_scale_factor)

            self.__prop_sprites.append(prop_sprite)
            self.__prop_entries.append((prop_sprite, asset))

        logger.info(
            f"TileMapRenderer montado: {len(self.__ground_sprites)} ground sprites e "
            f"{len(self.__prop_sprites)} prop sprites para mapa '{self.__tile_map.tileset_name}' "
            f"({self.__tile_map.width}x{self.__tile_map.height})."
        )

    # --- Ajuste Dinâmico de Viewport / Layout ---

    def update_layout(
        self,
        draw_x: float,
        draw_y: float,
        tile_w: Optional[float] = None,
        tile_h: Optional[float] = None,
        cell_w: Optional[float] = None,
        cell_h: Optional[float] = None,
    ) -> None:
        """
        Reposiciona e redimensiona todos os sprites (chão e props) para se ajustarem
        a um retângulo de viewport específico (ex: TacticalMiniMap ou PlayerWindow).
        """
        tw = float(tile_w if tile_w is not None else (cell_w if cell_w is not None else self.__tile_size))
        th = float(tile_h if tile_h is not None else (cell_h if cell_h is not None else self.__tile_size))
        scale_x = tw / self.__tile_size
        scale_y = th / self.__tile_size

        for (tx, ty), sprite in self.__sprites_by_coord.items():
            col = tx
            row = (self.__tile_map.height - 1) - ty

            cx = draw_x + (float(col) + 0.5) * tw
            cy = draw_y + (float(row) + 0.5) * th
            sprite.center_x = cx
            sprite.center_y = cy
            sprite.scale_x = scale_x
            sprite.scale_y = scale_y

        for prop_sprite, asset in self.__prop_entries:
            col = asset.x
            row = (self.__tile_map.height - 1) - asset.y

            cx = draw_x + (float(col) + 0.5) * tw
            cy = draw_y + (float(row) + 0.5) * th
            prop_sprite.center_x = cx
            prop_sprite.center_y = cy
            prop_sprite.scale_x = float(asset.scale) * scale_x
            prop_sprite.scale_y = float(asset.scale) * scale_y

    def reset_to_world_coordinates(self) -> None:
        """Restaura as posições e escalas de todos os sprites para as coordenadas mundiais padrão."""
        for (tx, ty), sprite in self.__sprites_by_coord.items():
            col = tx
            row = (self.__tile_map.height - 1) - ty

            if self.__grid_manager is not None:
                cx, cy = self.__grid_manager.grid_to_world_center(col, row)
            else:
                cx = (float(col) + 0.5) * self.__tile_size
                cy = (float(row) + 0.5) * self.__tile_size

            sprite.center_x = cx
            sprite.center_y = cy
            sprite.scale_x = 1.0
            sprite.scale_y = 1.0

        for prop_sprite, asset in self.__prop_entries:
            col = asset.x
            row = (self.__tile_map.height - 1) - asset.y

            if self.__grid_manager is not None:
                cx, cy = self.__grid_manager.grid_to_world_center(col, row)
                gs = self.__grid_manager.scale_factor
            else:
                cx = (float(col) + 0.5) * self.__tile_size
                cy = (float(row) + 0.5) * self.__tile_size
                gs = 1.0

            prop_sprite.center_x = cx
            prop_sprite.center_y = cy
            prop_sprite.scale = float(asset.scale) * float(gs)

    # --- Ciclo de Atualização e Desenho ---

    def update(self, delta_time: float = 1 / 60) -> None:
        """
        Atualiza as animações de props contínuos (fogo, tochas, etc.) da camada de objetos.
        """
        if len(self.__prop_sprites) > 0:
            self.__prop_sprites.update_animation(delta_time)

    def draw(self, pixelated: bool = True) -> None:
        """
        Desenha as camadas do mapa em ordem estrita:
        1. Chão (ground_sprites)
        2. Props / Objetos (prop_sprites)
        """
        if len(self.__ground_sprites) > 0:
            self.__ground_sprites.draw(pixelated=pixelated)
        if len(self.__prop_sprites) > 0:
            self.__prop_sprites.draw(pixelated=pixelated)

    def __repr__(self) -> str:
        return (
            f"<TileMapRenderer map='{self.__tile_map.tileset_name}' "
            f"tiles={len(self.__ground_sprites)} props={len(self.__prop_sprites)} "
            f"tile_size={self.__tile_size}px>"
        )
