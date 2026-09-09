import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

VALID_ASSET_TYPES = ("sprite", "spritesheet")


class MapAsset:
    """
    Objeto de valor (Value Object) que encapsula as definições de um Objeto/Prop sobre o mapa.
    Suporta props estáticos ('sprite', 32x32px) e props animados ('spritesheet', loop contínuo de 6 frames 32x32px).
    """

    def __init__(
        self,
        sprite: str,
        asset_type: str = "sprite",
        x: int = 0,
        y: int = 0,
        scale: float = 1.0,
    ) -> None:
        self.__sprite: str = str(sprite).strip() if sprite else ""
        norm_type = str(asset_type).strip().lower() if asset_type else "sprite"
        if norm_type not in VALID_ASSET_TYPES:
            logger.warning(
                f"Tipo de asset '{asset_type}' inválido. Ajustando para 'sprite'. Válidos: {VALID_ASSET_TYPES}"
            )
            norm_type = "sprite"
        self.__type: str = norm_type
        self.__x: int = int(x)
        self.__y: int = int(y)
        self.__scale: float = max(0.001, float(scale))

    @property
    def sprite(self) -> str:
        """Caminho do arquivo de imagem ou spritesheet."""
        return self.__sprite

    @property
    def sprite_path(self) -> str:
        """Alias para sprite."""
        return self.__sprite

    @property
    def type(self) -> str:
        """Tipo de prop ('sprite' ou 'spritesheet')."""
        return self.__type

    @property
    def asset_type(self) -> str:
        """Alias para type."""
        return self.__type

    @property
    def x(self) -> int:
        """Coordenada X lógica da célula de grid."""
        return self.__x

    @property
    def y(self) -> int:
        """Coordenada Y lógica da célula de grid."""
        return self.__y

    @property
    def position(self) -> Dict[str, int]:
        """Posição {'x': x, 'y': y} do prop."""
        return {"x": self.__x, "y": self.__y}

    @property
    def scale(self) -> float:
        """Fator de escala local do prop."""
        return self.__scale

    def to_dict(self) -> Dict[str, Any]:
        """Serializa o MapAsset para dicionário compatível com JSON."""
        return {
            "sprite": self.__sprite,
            "type": self.__type,
            "position": {"x": self.__x, "y": self.__y},
            "scale": self.__scale,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["MapAsset"]:
        """Instancia MapAsset a partir de dicionário com validações defensivas."""
        if not data or not isinstance(data, dict):
            return None

        sprite = data.get("sprite", "")
        asset_type = data.get("type", "sprite")
        pos = data.get("position", {})
        if isinstance(pos, dict):
            x = pos.get("x", 0)
            y = pos.get("y", 0)
        else:
            x = data.get("x", 0)
            y = data.get("y", 0)
        scale = data.get("scale", 1.0)

        return cls(
            sprite=sprite,
            asset_type=asset_type,
            x=x,
            y=y,
            scale=scale,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MapAsset):
            return False
        return (
            self.__sprite == other.__sprite
            and self.__type == other.__type
            and self.__x == other.__x
            and self.__y == other.__y
            and abs(self.__scale - other.__scale) < 1e-5
        )

    def __repr__(self) -> str:
        return (
            f"MapAsset(sprite='{self.__sprite}', type='{self.__type}', "
            f"pos=({self.__x}, {self.__y}), scale={self.__scale})"
        )
