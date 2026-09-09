import logging
from typing import Dict, Any, Optional

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
        if norm_cover == "full":
            norm_cover = "total"

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
        """Indica se a célula obstrui movimentação de entidades."""
        return self.__blocks_movement

    @property
    def blocks_vision(self) -> bool:
        """Indica se a célula bloqueia linha de visão (LoS) e Fog of War."""
        return self.__blocks_vision

    @property
    def cover_type(self) -> str:
        """Tipo de cobertura D&D 5E ('none', 'half', 'three_quarters', 'total')."""
        return self.__cover_type

    @property
    def difficult_terrain(self) -> bool:
        """Indica se a célula é terreno difícil (dobra custo de movimento)."""
        return self.__difficult_terrain

    @property
    def height(self) -> int:
        """Altura física em células/elevação."""
        return self.__height

    def to_dict(self) -> Dict[str, Any]:
        """Serializa as propriedades para dicionário compatível com JSON."""
        return {
            "blocks_movement": self.__blocks_movement,
            "blocks_vision": self.__blocks_vision,
            "cover_type": self.__cover_type,
            "difficult_terrain": self.__difficult_terrain,
            "height": self.__height,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TileProperties":
        """Instancia TileProperties a partir de dicionário com validações defensivas."""
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
            f"blocks_vision={self.__blocks_vision}, cover='{self.__cover_type}', "
            f"difficult={self.__difficult_terrain}, height={self.__height})"
        )
