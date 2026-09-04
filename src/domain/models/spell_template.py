import logging
import math
from enum import Enum
from typing import Tuple, List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class SpellShape(Enum):
    """Formatos geométricos de Áreas de Efeito (AoE) de feitiços suportados."""
    CIRCLE = "circle"
    SQUARE = "square"
    CONE = "cone"
    LINE = "line"


class SpellTemplate:
    """
    Estrutura de dados imutável para projeção tática de áreas de efeito de feitiços (Spell AoE Overlay).
    Desacoplada de escalas fixas: a conversão métrica de pés (feet) para pixels no mundo
    é realizada dinamicamente com base nas propriedades do GridManager (cell_size / feet_per_square).
    """

    def __init__(
        self,
        shape: Union[SpellShape, str] = SpellShape.CIRCLE,
        size_feet: float = 20.0,
        width_feet: float = 5.0,
        rotation_degrees: float = 0.0,
        origin_world: Tuple[float, float] = (0.0, 0.0),
        is_active: bool = False,
        is_visible: bool = True,
    ) -> None:
        if isinstance(shape, str):
            shape = SpellShape(shape.lower())

        self.__shape: SpellShape = shape
        self.__size_feet: float = max(0.0, float(size_feet))
        self.__width_feet: float = max(0.0, float(width_feet))
        self.__rotation_degrees: float = float(rotation_degrees) % 360.0
        self.__origin_world: Tuple[float, float] = (float(origin_world[0]), float(origin_world[1]))
        self.__is_active: bool = bool(is_active)
        self.__is_visible: bool = bool(is_visible)

    # --- Properties (Encapsulamento Estrito e Imutabilidade) ---

    @property
    def shape(self) -> SpellShape:
        return self.__shape

    @property
    def size_feet(self) -> float:
        return self.__size_feet

    @property
    def width_feet(self) -> float:
        return self.__width_feet

    @property
    def rotation_degrees(self) -> float:
        return self.__rotation_degrees

    @property
    def origin_world(self) -> Tuple[float, float]:
        return self.__origin_world

    @property
    def is_active(self) -> bool:
        return self.__is_active

    @property
    def is_visible(self) -> bool:
        return self.__is_visible

    # --- Métodos de Criação de Cópia com Novos Valores (Padrão Imutável) ---

    def with_origin(self, origin_world: Tuple[float, float]) -> "SpellTemplate":
        """Retorna nova instância com nova coordenada de mundo da origem."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=origin_world,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_rotation(self, rotation_degrees: float) -> "SpellTemplate":
        """Retorna nova instância com rotação atualizada (envelopada em 0..360)."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=rotation_degrees,
            origin_world=self.__origin_world,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_shape(self, shape: Union[SpellShape, str]) -> "SpellTemplate":
        """Retorna nova instância com novo formato geométrico."""
        return SpellTemplate(
            shape=shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_size(self, size_feet: float, width_feet: Optional[float] = None) -> "SpellTemplate":
        """Retorna nova instância com novas dimensões em pés."""
        w = self.__width_feet if width_feet is None else width_feet
        return SpellTemplate(
            shape=self.__shape,
            size_feet=size_feet,
            width_feet=w,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_active(self, is_active: bool) -> "SpellTemplate":
        """Retorna nova instância com estado de ativação alterado."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            is_active=is_active,
            is_visible=self.__is_visible,
        )

    def with_visibility(self, is_visible: bool) -> "SpellTemplate":
        """Retorna nova instância com visibilidade temporária alterada."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            is_active=self.__is_active,
            is_visible=is_visible,
        )

    # --- Conversão Geométrica e Cálculo de Vértices ---

    def get_vertices_world(self, pixels_per_foot: float) -> List[Tuple[float, float]]:
        """
        Calcula os vértices geométricos no espaço contínuo de coordenadas de mundo
        aplicando a rotação e a escala dinâmica de pixels por pé (pixels_per_foot).

        Retorno por formato:
        - CIRCLE: [] (geometria circular definida por centro e raio)
        - SQUARE: 4 vértices do retângulo/quadrado rotacionado em torno de origin_world
        - CONE: 3 vértices [origem, ponta_esquerda, ponta_direita] com abertura de 53.13°
        - LINE: 4 vértices do retângulo projetado a partir da base em origin_world
        """
        ppf = max(0.0001, float(pixels_per_foot))
        ox, oy = self.__origin_world
        theta = math.radians(self.__rotation_degrees)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        if self.__shape == SpellShape.CIRCLE:
            return []

        elif self.__shape == SpellShape.SQUARE:
            # Quadrado com centro em origin_world, lado em pixels = size_feet * ppf
            side_px = self.__size_feet * ppf
            half_side = side_px / 2.0

            # 4 cantos antes da rotação
            local_corners = [
                (-half_side, -half_side),
                (half_side, -half_side),
                (half_side, half_side),
                (-half_side, half_side),
            ]

            vertices: List[Tuple[float, float]] = []
            for dx, dy in local_corners:
                rx = ox + dx * cos_t - dy * sin_t
                ry = oy + dx * sin_t + dy * cos_t
                vertices.append((rx, ry))
            return vertices

        elif self.__shape == SpellShape.CONE:
            # Cone D&D 5E: vértice na base em origin_world, alcance L = size_feet * ppf
            # Largura na extremidade = comprimento projetado (L).
            # Semi-ângulo alpha = atan(0.5) ~ 26.565° (abertura total = 53.13°)
            length_px = self.__size_feet * ppf
            alpha = math.atan(0.5)

            v0 = (ox, oy)
            v1 = (
                ox + length_px * math.cos(theta - alpha),
                oy + length_px * math.sin(theta - alpha),
            )
            v2 = (
                ox + length_px * math.cos(theta + alpha),
                oy + length_px * math.sin(theta + alpha),
            )
            return [v0, v1, v2]

        elif self.__shape == SpellShape.LINE:
            # Linha D&D 5E: base centrada em origin_world, retângulo de comprimento L e largura W
            # projetando a partir de origin_world no ângulo rotation_degrees.
            length_px = self.__size_feet * ppf
            width_px = self.__width_feet * ppf
            half_w = width_px / 2.0

            # Vetor direção unitário: u = (cos_t, sin_t)
            # Vetor normal perpendicular: n = (-sin_t, cos_t)
            # Base corners: origin - half_w * n, origin + half_w * n
            # Tip corners: origin + L*u + half_w * n, origin + L*u - half_w * n
            b_left = (ox + half_w * sin_t, oy - half_w * cos_t)
            b_right = (ox - half_w * sin_t, oy + half_w * cos_t)
            t_right = (ox + length_px * cos_t - half_w * sin_t, oy + length_px * sin_t + half_w * cos_t)
            t_left = (ox + length_px * cos_t + half_w * sin_t, oy + length_px * sin_t - half_w * cos_t)

            return [b_left, b_right, t_right, t_left]

        return []

    def to_dict(self) -> Dict[str, Any]:
        """Serialização defensiva do template de feitiço."""
        return {
            "shape": self.__shape.value,
            "size_feet": self.__size_feet,
            "width_feet": self.__width_feet,
            "rotation_degrees": self.__rotation_degrees,
            "origin_world": list(self.__origin_world),
            "is_active": self.__is_active,
            "is_visible": self.__is_visible,
        }

    def __repr__(self) -> str:
        return (
            f"<SpellTemplate shape={self.__shape.value} size={self.__size_feet}ft "
            f"width={self.__width_feet}ft rot={self.__rotation_degrees:.1f}° "
            f"origin=({self.__origin_world[0]:.1f}, {self.__origin_world[1]:.1f}) "
            f"active={self.__is_active} visible={self.__is_visible}>"
        )
