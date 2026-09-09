import logging
import math
from enum import Enum
from typing import Tuple, List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class AoEShape(Enum):
    """
    Formatos geométricos canônicos de Áreas de Efeito (AoE) de D&D 5E.
    Suporta projeções 2D (Círculo, Quadrado) e 3D (Esfera, Cubo, Cone, Linha).
    """
    CIRCLE = "circle"
    SQUARE = "square"
    SPHERE = "sphere"
    CUBE = "cube"
    CONE = "cone"
    LINE = "line"

    @property
    def is_3d(self) -> bool:
        """Indica se a forma possui dimensão vertical e requer avaliação 3D."""
        return self in (AoEShape.SPHERE, AoEShape.CUBE, AoEShape.CONE, AoEShape.LINE)

    @property
    def display_name(self) -> str:
        """Nome formatado para exibição na interface."""
        names = {
            AoEShape.CIRCLE: "Círculo",
            AoEShape.SQUARE: "Quadrado",
            AoEShape.SPHERE: "Esfera",
            AoEShape.CUBE: "Cubo",
            AoEShape.CONE: "Cone",
            AoEShape.LINE: "Linha",
        }
        return names.get(self, self.value.capitalize())


# Alias para retrocompatibilidade com código existente
SpellShape = AoEShape


class SpellTemplate:
    """
    Estrutura de dados imutável para projeção tática de áreas de efeito de feitiços (Spell AoE Overlay).
    Desacoplada de escalas fixas: a conversão métrica de pés (feet) para pixels no mundo
    é realizada dinamicamente com base nas propriedades do GridManager (cell_size / feet_per_square).
    Suporta as 6 formas canônicas de D&D 5E, altura de origem Z e inclinação vertical (pitch).
    """

    def __init__(
        self,
        shape: Union[AoEShape, str] = AoEShape.CIRCLE,
        size_feet: float = 20.0,
        width_feet: float = 5.0,
        rotation_degrees: float = 0.0,
        origin_world: Tuple[float, float] = (0.0, 0.0),
        origin_z_feet: float = 0.0,
        pitch_degrees: float = 0.0,
        is_active: bool = False,
        is_visible: bool = True,
    ) -> None:
        if isinstance(shape, str):
            shape = AoEShape(shape.lower())

        self.__shape: AoEShape = shape
        self.__size_feet: float = max(0.0, float(size_feet))
        self.__width_feet: float = max(0.0, float(width_feet))
        self.__rotation_degrees: float = float(rotation_degrees) % 360.0
        self.__origin_world: Tuple[float, float] = (float(origin_world[0]), float(origin_world[1]))
        self.__origin_z_feet: float = float(origin_z_feet)
        self.__pitch_degrees: float = float(pitch_degrees) % 360.0
        self.__is_active: bool = bool(is_active)
        self.__is_visible: bool = bool(is_visible)

    # --- Properties (Encapsulamento Estrito e Imutabilidade) ---

    @property
    def shape(self) -> AoEShape:
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
    def origin_z_feet(self) -> float:
        return self.__origin_z_feet

    @property
    def pitch_degrees(self) -> float:
        return self.__pitch_degrees

    @property
    def is_active(self) -> bool:
        return self.__is_active

    @property
    def is_visible(self) -> bool:
        return self.__is_visible

    # --- Métodos de Criação de Cópia com Novos Valores (Padrão Imutável) ---

    def with_origin(
        self,
        origin_world: Tuple[float, float],
        origin_z_feet: Optional[float] = None,
    ) -> "SpellTemplate":
        """Retorna nova instância com nova coordenada de mundo da origem."""
        z = self.__origin_z_feet if origin_z_feet is None else float(origin_z_feet)
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=origin_world,
            origin_z_feet=z,
            pitch_degrees=self.__pitch_degrees,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_origin_z(self, origin_z_feet: float) -> "SpellTemplate":
        """Retorna nova instância com altitude da origem alterada em pés."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            origin_z_feet=float(origin_z_feet),
            pitch_degrees=self.__pitch_degrees,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_rotation(self, rotation_degrees: float) -> "SpellTemplate":
        """Retorna nova instância com rotação horizontal (yaw) atualizada (envelopada em 0..360)."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=rotation_degrees,
            origin_world=self.__origin_world,
            origin_z_feet=self.__origin_z_feet,
            pitch_degrees=self.__pitch_degrees,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_pitch(self, pitch_degrees: float) -> "SpellTemplate":
        """Retorna nova instância com inclinação vertical (pitch) atualizada."""
        return SpellTemplate(
            shape=self.__shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            origin_z_feet=self.__origin_z_feet,
            pitch_degrees=pitch_degrees,
            is_active=self.__is_active,
            is_visible=self.__is_visible,
        )

    def with_shape(self, shape: Union[AoEShape, str]) -> "SpellTemplate":
        """Retorna nova instância com novo formato geométrico."""
        return SpellTemplate(
            shape=shape,
            size_feet=self.__size_feet,
            width_feet=self.__width_feet,
            rotation_degrees=self.__rotation_degrees,
            origin_world=self.__origin_world,
            origin_z_feet=self.__origin_z_feet,
            pitch_degrees=self.__pitch_degrees,
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
            origin_z_feet=self.__origin_z_feet,
            pitch_degrees=self.__pitch_degrees,
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
            origin_z_feet=self.__origin_z_feet,
            pitch_degrees=self.__pitch_degrees,
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
            origin_z_feet=self.__origin_z_feet,
            pitch_degrees=self.__pitch_degrees,
            is_active=self.__is_active,
            is_visible=is_visible,
        )

    # --- Conversão Geométrica e Projeção 2D de Vértices ---

    def get_vertices_world(self, pixels_per_foot: float) -> List[Tuple[float, float]]:
        """
        Calcula os vértices geométricos no espaço contínuo de coordenadas de mundo
        aplicando a rotação e a escala dinâmica de pixels por pé (pixels_per_foot).

        Retorno por formato:
        - CIRCLE / SPHERE: [] (geometria circular definida por centro e raio)
        - SQUARE / CUBE: 4 vértices do quadrado rotacionado em torno de origin_world
        - CONE: 3 vértices [origem, ponta_esquerda, ponta_direita] com abertura de 53.13°
        - LINE: 4 vértices do retângulo projetado a partir da base em origin_world
        """
        ppf = max(0.0001, float(pixels_per_foot))
        ox, oy = self.__origin_world
        theta = math.radians(self.__rotation_degrees)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        if self.__shape in (AoEShape.CIRCLE, AoEShape.SPHERE):
            return []

        elif self.__shape in (AoEShape.SQUARE, AoEShape.CUBE):
            # Quadrado / Cubo projetado no plano 2D com centro em origin_world
            side_px = self.__size_feet * ppf
            half_side = side_px / 2.0

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

        elif self.__shape == AoEShape.CONE:
            # Cone D&D 5E: vértice na base em origin_world, alcance L = size_feet * ppf
            # Largura na extremidade = comprimento projetado (L).
            # Semi-ângulo alpha = atan(0.5) ~ 26.565° (abertura total = 53.13°)
            # Para projeção 2D consideramos o componente horizontal do comprimento se houver pitch
            pitch_rad = math.radians(self.__pitch_degrees)
            horiz_length_px = self.__size_feet * ppf * math.cos(pitch_rad)
            horiz_length_px = max(1.0, abs(horiz_length_px))
            alpha = math.atan(0.5)

            v0 = (ox, oy)
            v1 = (
                ox + horiz_length_px * math.cos(theta - alpha),
                oy + horiz_length_px * math.sin(theta - alpha),
            )
            v2 = (
                ox + horiz_length_px * math.cos(theta + alpha),
                oy + horiz_length_px * math.sin(theta + alpha),
            )
            return [v0, v1, v2]

        elif self.__shape == AoEShape.LINE:
            # Linha D&D 5E: base centrada em origin_world, retângulo de comprimento L e largura W
            pitch_rad = math.radians(self.__pitch_degrees)
            horiz_length_px = self.__size_feet * ppf * math.cos(pitch_rad)
            horiz_length_px = max(1.0, abs(horiz_length_px))
            width_px = self.__width_feet * ppf
            half_w = width_px / 2.0

            b_left = (ox + half_w * sin_t, oy - half_w * cos_t)
            b_right = (ox - half_w * sin_t, oy + half_w * cos_t)
            t_right = (ox + horiz_length_px * cos_t - half_w * sin_t, oy + horiz_length_px * sin_t + half_w * cos_t)
            t_left = (ox + horiz_length_px * cos_t + half_w * sin_t, oy + horiz_length_px * sin_t - half_w * cos_t)

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
            "origin_z_feet": self.__origin_z_feet,
            "pitch_degrees": self.__pitch_degrees,
            "is_active": self.__is_active,
            "is_visible": self.__is_visible,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["SpellTemplate"]:
        """Desserialização defensiva a partir de dicionário."""
        if not data or not isinstance(data, dict):
            return None

        shape = data.get("shape", AoEShape.CIRCLE.value)
        size_feet = data.get("size_feet", 20.0)
        width_feet = data.get("width_feet", 5.0)
        rotation_degrees = data.get("rotation_degrees", 0.0)
        origin_world = data.get("origin_world", (0.0, 0.0))
        if isinstance(origin_world, list):
            origin_world = (float(origin_world[0]), float(origin_world[1]))
        origin_z_feet = data.get("origin_z_feet", 0.0)
        pitch_degrees = data.get("pitch_degrees", 0.0)
        is_active = data.get("is_active", False)
        is_visible = data.get("is_visible", True)

        return cls(
            shape=shape,
            size_feet=size_feet,
            width_feet=width_feet,
            rotation_degrees=rotation_degrees,
            origin_world=origin_world,
            origin_z_feet=origin_z_feet,
            pitch_degrees=pitch_degrees,
            is_active=is_active,
            is_visible=is_visible,
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SpellTemplate):
            return False
        return (
            self.__shape == other.__shape
            and abs(self.__size_feet - other.__size_feet) < 1e-4
            and abs(self.__width_feet - other.__width_feet) < 1e-4
            and abs(self.__rotation_degrees - other.__rotation_degrees) < 1e-4
            and abs(self.__origin_world[0] - other.__origin_world[0]) < 1e-4
            and abs(self.__origin_world[1] - other.__origin_world[1]) < 1e-4
            and abs(self.__origin_z_feet - other.__origin_z_feet) < 1e-4
            and abs(self.__pitch_degrees - other.__pitch_degrees) < 1e-4
            and self.__is_active == other.__is_active
            and self.__is_visible == other.__is_visible
        )

    def __repr__(self) -> str:
        return (
            f"<SpellTemplate shape={self.__shape.value} size={self.__size_feet}ft "
            f"width={self.__width_feet}ft rot={self.__rotation_degrees:.1f}° "
            f"origin=({self.__origin_world[0]:.1f}, {self.__origin_world[1]:.1f}, {self.__origin_z_feet:.1f}ft) "
            f"pitch={self.__pitch_degrees:.1f}° active={self.__is_active} visible={self.__is_visible}>"
        )
