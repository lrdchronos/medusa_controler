import logging
import math
from typing import Optional, Tuple, List
import arcade
from ...domain.models.spell_template import SpellTemplate, SpellShape
from ...manager.grid_manager import GridManager

logger = logging.getLogger(__name__)


class AoERenderer:
    """
    Renderizador utilitário estático e desacoplado para sobreposição visual de
    Áreas de Efeito de Feitiços (Spell AoE Overlay) no Medusa VTT.
    Utilizado de forma idêntica tanto no TacticalMiniMap (DMWindow) quanto na PlayerWindow.
    """

    COLOR_FILL: Tuple[int, int, int, int] = (231, 76, 60, 90)        # Carmim translúcido mágico
    COLOR_OUTLINE: Tuple[int, int, int, int] = (192, 57, 43, 240)    # Borda vermelha viva
    COLOR_ANCHOR: Tuple[int, int, int, int] = (241, 196, 15, 255)    # Ponto de ancoragem dourado místico
    COLOR_ANCHOR_RING: Tuple[int, int, int, int] = (255, 255, 255, 220)

    @classmethod
    def draw(
        cls,
        template: Optional[SpellTemplate],
        grid_manager: Optional[GridManager],
        draw_x: float,
        draw_y: float,
        scale: float,
    ) -> None:
        """
        Desenha a projeção da AoE com base no template e nas dimensões/escala ativas do mapa.

        :param template: Estrutura SpellTemplate ativa. Se None, inativa ou invisível, nada é desenhado.
        :param grid_manager: GridManager ativo para leitura da métrica dinâmica de pixels_per_foot.
        :param draw_x: Offset X de renderização do mapa na viewport.
        :param draw_y: Offset Y de renderização do mapa na viewport.
        :param scale: Escala uniforme de conversão entre coordenadas de mundo e pixels de tela.
        """
        if template is None or not template.is_active or not template.is_visible:
            return

        if grid_manager is None:
            return

        # Métrica de escala em pixels de tela por pé
        screen_ppf = grid_manager.pixels_per_foot * scale
        if screen_ppf <= 0.0:
            return

        # Conversão do ponto de origem de mundo para coordenadas locais da tela
        world_ox, world_oy = template.origin_world
        screen_ox = draw_x + world_ox * scale
        screen_oy = draw_y + world_oy * scale

        theta = math.radians(template.rotation_degrees)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        anchor_point = (screen_ox, screen_oy)

        if template.shape == SpellShape.CIRCLE:
            radius_px = template.size_feet * screen_ppf
            if radius_px > 0:
                arcade.draw_circle_filled(screen_ox, screen_oy, radius_px, cls.COLOR_FILL)
                arcade.draw_circle_outline(screen_ox, screen_oy, radius_px, cls.COLOR_OUTLINE, 2.0)

        elif template.shape == SpellShape.SQUARE:
            side_px = template.size_feet * screen_ppf
            half_side = side_px / 2.0

            local_corners = [
                (-half_side, -half_side),
                (half_side, -half_side),
                (half_side, half_side),
                (-half_side, half_side),
            ]

            screen_vertices: List[Tuple[float, float]] = []
            for dx, dy in local_corners:
                rx = screen_ox + dx * cos_t - dy * sin_t
                ry = screen_oy + dx * sin_t + dy * cos_t
                screen_vertices.append((rx, ry))

            arcade.draw_polygon_filled(screen_vertices, cls.COLOR_FILL)
            arcade.draw_polygon_outline(screen_vertices, cls.COLOR_OUTLINE, 2.0)

        elif template.shape == SpellShape.CONE:
            length_px = template.size_feet * screen_ppf
            alpha = math.atan(0.5)  # Abertura angular D&D 5E (~53.13°)

            v0 = (screen_ox, screen_oy)
            v1 = (
                screen_ox + length_px * math.cos(theta - alpha),
                screen_oy + length_px * math.sin(theta - alpha),
            )
            v2 = (
                screen_ox + length_px * math.cos(theta + alpha),
                screen_oy + length_px * math.sin(theta + alpha),
            )

            screen_vertices = [v0, v1, v2]
            arcade.draw_polygon_filled(screen_vertices, cls.COLOR_FILL)
            arcade.draw_polygon_outline(screen_vertices, cls.COLOR_OUTLINE, 2.0)

        elif template.shape == SpellShape.LINE:
            length_px = template.size_feet * screen_ppf
            width_px = template.width_feet * screen_ppf
            half_w = width_px / 2.0

            b_left = (screen_ox + half_w * sin_t, screen_oy - half_w * cos_t)
            b_right = (screen_ox - half_w * sin_t, screen_oy + half_w * cos_t)
            t_right = (screen_ox + length_px * cos_t - half_w * sin_t, screen_oy + length_px * sin_t + half_w * cos_t)
            t_left = (screen_ox + length_px * cos_t + half_w * sin_t, screen_oy + length_px * sin_t - half_w * cos_t)

            screen_vertices = [b_left, b_right, t_right, t_left]
            arcade.draw_polygon_filled(screen_vertices, cls.COLOR_FILL)
            arcade.draw_polygon_outline(screen_vertices, cls.COLOR_OUTLINE, 2.0)

        # Renderização do Ponto de Ancoragem (círculo dourado de 4px)
        ax, ay = anchor_point
        arcade.draw_circle_filled(ax, ay, 4.0, cls.COLOR_ANCHOR)
        arcade.draw_circle_outline(ax, ay, 4.0, cls.COLOR_ANCHOR_RING, 1.0)
