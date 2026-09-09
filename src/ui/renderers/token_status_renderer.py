import logging
import math
from typing import Dict, List, Optional, Tuple, Any
import arcade

try:
    from ..utils.status_icon_atlas import StatusIconAtlas
except ImportError:
    from src.ui.utils.status_icon_atlas import StatusIconAtlas

logger = logging.getLogger(__name__)


class TokenStatusRenderer:
    """
    Renderizador Orbital de Badges de Vida e Condições Táticas para Tokens do Medusa VTT.
    Distribui os ícones de estado ao redor da borda circular do token utilizando
    o Algoritmo de Relógio de 12 horas (12h para vida, 1h..11h para condições ativas).
    """

    BASE_ICON_SIZE = 12.8  # Reduzido em 20% (16px * 0.8 = 12.8px)

    @classmethod
    def calculate_angular_step(cls, num_conditions: int) -> float:
        """
        Calcula o passo angular (delta_theta em graus) dinamicamente para N condições ativas (0 <= N <= 11).
        Regra:
          - Se N <= 8: passo fixo de delta_theta = 40.0 graus.
          - Se N > 8 (9 a 11): interpolação linear reduzindo até delta_theta = 30.0 graus em N = 11.
            Fórmula: delta_theta = 40.0 - (N - 8) * ((40.0 - 30.0) / (11 - 8))
        """
        if num_conditions <= 8:
            return 40.0
        n = min(11, max(9, int(num_conditions)))
        return 40.0 - (float(n) - 8.0) * (10.0 / 3.0)

    @classmethod
    def calculate_condition_angle(
        cls,
        index: int,
        total_conditions: int,
        delta_theta: Optional[float] = None,
    ) -> float:
        """
        Calcula o ângulo em graus (0..360) para a i-ésima condição (0-indexed) de um total N,
        com simetria bilateral em torno do eixo vertical (distribuído no semicírculo inferior a partir de 270°).
        Fórmula:
            delta = delta_theta if delta_theta is not None else calculate_angular_step(total_conditions)
            offset_lateral = (index - (total_conditions - 1) / 2.0) * delta
            angle_deg = 270.0 + offset_lateral
        """
        if total_conditions <= 0:
            return 270.0
        step = delta_theta if delta_theta is not None else cls.calculate_angular_step(total_conditions)
        offset_lateral = (float(index) - (float(total_conditions) - 1.0) / 2.0) * step
        return 270.0 + offset_lateral

    @classmethod
    def calculate_position_by_angle(
        cls,
        center_x: float,
        center_y: float,
        token_radius: float,
        angle_deg: float,
        icon_size: float = 12.8,
    ) -> Tuple[float, float]:
        """
        Calcula as coordenadas de tela/mundo (x, y) de um badge com base no ângulo trigonométrico em graus.
        Fórmula:
            radius = token_radius + (icon_size / 2)
            x = center_x + radius * cos(radians(angle_deg))
            y = center_y + radius * sin(radians(angle_deg))
        """
        orbit_radius = float(token_radius) + (float(icon_size) / 2.0)
        angle_rad = math.radians(float(angle_deg))
        x = float(center_x) + orbit_radius * math.cos(angle_rad)
        y = float(center_y) + orbit_radius * math.sin(angle_rad)
        return x, y

    @classmethod
    def calculate_slot_position(
        cls,
        center_x: float,
        center_y: float,
        token_radius: float,
        hour: int,
        icon_size: float = 12.8,
    ) -> Tuple[float, float]:
        """
        Calcula as coordenadas de mundo/tela (x, y) de um slot orbital para a hora H no relógio (1..12).
        Mantido para retrocompatibilidade.
        """
        angle_deg = 90.0 - (int(hour) * 30.0)
        return cls.calculate_position_by_angle(
            center_x=center_x,
            center_y=center_y,
            token_radius=token_radius,
            angle_deg=angle_deg,
            icon_size=icon_size,
        )

    @classmethod
    def get_orbital_slots(
        cls,
        entity: Any,
        center_x: float,
        center_y: float,
        token_radius: float,
        scale_factor: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Calcula os slots ativos (ângulo, nome do ícone, textura, x, y, tamanho) para a entidade informada.
        - Posição Fixa de Vida: Topo em 12h (theta = 90°). Omitido se neutro sem vida gerenciada.
        - Posições de Condições: Distribuição angular adaptativa e simétrica bilateral em torno de 270° (6h).
        """
        slots: List[Dict[str, Any]] = []
        if entity is None:
            return slots

        scale = max(0.1, float(scale_factor))
        icon_draw_size = cls.BASE_ICON_SIZE * scale

        # 1. Posição Fixa 12h (90°): Indicador de Vida (Health Badge)
        is_neutral = getattr(entity, "is_neutral", False)
        entity_type_str = str(getattr(entity, "entity_type", "")).lower()
        if "neutral" in entity_type_str:
            is_neutral = True

        max_hp = getattr(entity, "max_hp", 0)
        current_hp = getattr(entity, "current_hp", 0)

        # Se for neutro sem vida gerenciada (ex: feitiço estático/token leve com max_hp <= 1 ou flag explícita), omite vida
        has_managed_health = not (is_neutral and max_hp <= 1) and max_hp > 0

        if has_managed_health:
            health_icon_name = StatusIconAtlas.get_health_icon_name(current_hp, max_hp)
            tex = StatusIconAtlas.get_health_texture(health_icon_name)
            if tex is not None:
                hx, hy = cls.calculate_position_by_angle(
                    center_x=center_x,
                    center_y=center_y,
                    token_radius=token_radius,
                    angle_deg=90.0,
                    icon_size=icon_draw_size,
                )
                slots.append({
                    "hour": 12,
                    "angle_deg": 90.0,
                    "name": health_icon_name,
                    "texture": tex,
                    "x": hx,
                    "y": hy,
                    "size": icon_draw_size,
                    "type": "health",
                })

        # 2. Condições Ativas da Entidade: Distribuição Angular Progressiva e Simétrica
        raw_conditions = getattr(entity, "conditions", [])
        if isinstance(raw_conditions, (set, list, tuple)):
            active_set = {str(c).strip().lower() for c in raw_conditions if c}
        else:
            active_set = set()

        # Ordena de forma canônica e determinística D&D 5E
        canonical_list = StatusIconAtlas.get_condition_names()
        active_conditions = [c for c in canonical_list if c in active_set]
        for c in active_set:
            if c not in active_conditions:
                active_conditions.append(c)

        # Limita ao máximo de 11 condições
        conditions_to_render = active_conditions[:11]
        num_conds = len(conditions_to_render)

        if num_conds > 0:
            delta_theta = cls.calculate_angular_step(num_conds)
            for idx, cond_name in enumerate(conditions_to_render):
                angle_deg = cls.calculate_condition_angle(idx, num_conds, delta_theta)
                tex = StatusIconAtlas.get_condition_texture(cond_name)
                if tex is not None:
                    cx, cy = cls.calculate_position_by_angle(
                        center_x=center_x,
                        center_y=center_y,
                        token_radius=token_radius,
                        angle_deg=angle_deg,
                        icon_size=icon_draw_size,
                    )
                    slots.append({
                        "hour": idx + 1,
                        "index": idx,
                        "angle_deg": angle_deg,
                        "name": cond_name,
                        "texture": tex,
                        "x": cx,
                        "y": cy,
                        "size": icon_draw_size,
                        "type": "condition",
                    })

        return slots

    @classmethod
    def draw(
        cls,
        entity: Any,
        center_x: float,
        center_y: float,
        token_radius: float,
        scale_factor: float = 1.0,
    ) -> None:
        """
        Renderiza os badges orbitais de vida e condições ativas ao redor da borda do token.
        Garante renderização nítida pixelated e borda sutil sob cada ícone.
        """
        slots = cls.get_orbital_slots(
            entity=entity,
            center_x=center_x,
            center_y=center_y,
            token_radius=token_radius,
            scale_factor=scale_factor,
        )

        for slot in slots:
            x = slot["x"]
            y = slot["y"]
            sz = slot["size"]
            tex: arcade.Texture = slot["texture"]

            # 1. Sombra e fundo circular sob o badge
            bg_radius = sz * 0.52
            arcade.draw_circle_filled(x, y - 1, bg_radius + 1.0, (0, 0, 0, 140))
            arcade.draw_circle_filled(x, y, bg_radius, (18, 24, 34, 230))
            arcade.draw_circle_outline(x, y, bg_radius, (50, 65, 90, 200), 1.0)

            # 2. Ícone de Status pixelated nítido
            arcade.draw_texture_rect(
                tex,
                arcade.XYWH(x, y, sz, sz),
                pixelated=True,
            )
