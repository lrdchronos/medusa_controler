from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Set, Tuple, Optional, List, Any

from ..models.spell_template import SpellTemplate, AoEShape

if TYPE_CHECKING:
    from ...manager.grid_manager import GridManager

logger = logging.getLogger(__name__)


class AoECalculator:
    """
    Motor analítico desacoplado de avaliação de células atingidas por Áreas de Efeito (Spell AoE) de D&D 5E.
    Suporta as 6 formas canônicas (Círculo, Quadrado, Esfera, Cubo, Cone e Linha),
    interseções volumétricas 3D com elevação de terreno do TileMap e rotação yaw/pitch.
    """

    # Tolerância angular para semi-abertura do Cone D&D 5E: arctan(0.5) ~ 26.565° -> cos(alpha) = 2/sqrt(5) ~ 0.89442719
    CONE_COS_HALF_ANGLE: float = 2.0 / math.sqrt(5.0)

    @classmethod
    def calculate_aoe_cells(
        cls,
        template: Optional[SpellTemplate],
        grid_manager: Optional[GridManager],
        tilemap_engine: Optional[Any] = None,
    ) -> Set[Tuple[int, int]]:
        """
        Calcula o conjunto de coordenadas matriciais (col, row) atingidas pela Área de Efeito ativa.
        
        :param template: Instância de SpellTemplate ativa. Se None ou inativo, retorna conjunto vazio.
        :param grid_manager: Instância de GridManager para leitura de métricas métricas/espaciais.
        :param tilemap_engine: Instância opcional de TileMap/TileMapEngine para consulta de elevações z_solo.
        :return: Conjunto de tuplas (col, row) das células atingidas.
        """
        if template is None or not template.is_active or not template.is_visible:
            return set()

        if grid_manager is None or grid_manager.columns <= 0 or grid_manager.rows <= 0:
            return set()

        ppf = grid_manager.pixels_per_foot
        if ppf <= 0.0:
            return set()

        feet_per_pixel = 1.0 / ppf
        cell_size = grid_manager.cell_size
        feet_per_sq = grid_manager.feet_per_square

        ox_world, oy_world = template.origin_world
        oz_feet = template.origin_z_feet
        size_feet = template.size_feet
        width_feet = template.width_feet
        shape = template.shape

        if size_feet <= 0.0:
            return set()

        # 1. Bounding Box 2D para filtrar células candidatas
        max_reach_feet = size_feet
        if shape == AoEShape.LINE:
            max_reach_feet = math.sqrt(size_feet * size_feet + (width_feet / 2.0) ** 2)
        elif shape in (AoEShape.SQUARE, AoEShape.CUBE):
            max_reach_feet = size_feet * math.sqrt(2.0)

        max_reach_px = max_reach_feet * ppf + cell_size
        min_wx = ox_world - max_reach_px
        max_wx = ox_world + max_reach_px
        min_wy = oy_world - max_reach_px
        max_wy = oy_world + max_reach_px

        col_min, row_min = grid_manager.world_to_grid(min_wx, min_wy)
        col_max, row_max = grid_manager.world_to_grid(max_wx, max_wy)

        col_start = max(0, min(col_min, col_max))
        col_end = min(grid_manager.columns - 1, max(col_min, col_max))
        row_start = max(0, min(row_min, row_max))
        row_end = min(grid_manager.rows - 1, max(row_min, row_max))

        # Pré-computação trigonométrica para rotações
        yaw_rad = math.radians(template.rotation_degrees)
        pitch_rad = math.radians(template.pitch_degrees)

        cos_yaw = math.cos(yaw_rad)
        sin_yaw = math.sin(yaw_rad)
        cos_pitch = math.cos(pitch_rad)
        sin_pitch = math.sin(pitch_rad)

        # Vetor de direção unitário 3D: D = (cos(pitch)*cos(yaw), cos(pitch)*sin(yaw), sin(pitch))
        dir_x = cos_pitch * cos_yaw
        dir_y = cos_pitch * sin_yaw
        dir_z = sin_pitch

        affected_cells: Set[Tuple[int, int]] = set()

        # 2. Avaliação analítica de cada célula candidata
        for col in range(col_start, col_end + 1):
            for row in range(row_start, row_end + 1):
                min_x, min_y, max_x, max_y = grid_manager.grid_to_world_bounds(col, row)
                center_x = (min_x + max_x) / 2.0
                center_y = (min_y + max_y) / 2.0

                # Coordenadas do centro da célula relativas à origem em pés
                rel_cx_feet = (center_x - ox_world) * feet_per_pixel
                rel_cy_feet = (center_y - oy_world) * feet_per_pixel

                # Elevação do solo e intervalo vertical da célula em pés
                ground_h = 0
                if tilemap_engine is not None and hasattr(tilemap_engine, "get_height"):
                    ground_h = int(tilemap_engine.get_height(col, row))

                z_ground_feet = ground_h * feet_per_sq
                z_bottom = z_ground_feet
                z_top = z_ground_feet + feet_per_sq
                z_mid = (z_bottom + z_top) / 2.0

                is_hit = False

                # --- Forma 1: Círculo (2D) ---
                if shape == AoEShape.CIRCLE:
                    d_2d = math.hypot(rel_cx_feet, rel_cy_feet)
                    # Atinge se o centro da célula estiver dentro do raio ou cobrir amostras
                    if d_2d <= size_feet:
                        is_hit = True
                    else:
                        # Teste defensivo de amostras de 50% de área
                        half_s = feet_per_sq * 0.4
                        samples = [
                            (rel_cx_feet - half_s, rel_cy_feet - half_s),
                            (rel_cx_feet + half_s, rel_cy_feet - half_s),
                            (rel_cx_feet + half_s, rel_cy_feet + half_s),
                            (rel_cx_feet - half_s, rel_cy_feet + half_s),
                        ]
                        inside_count = sum(1 for sx, sy in samples if math.hypot(sx, sy) <= size_feet)
                        if inside_count >= 2:
                            is_hit = True

                # --- Forma 2: Quadrado (2D) ---
                elif shape == AoEShape.SQUARE:
                    # Rotação inversa do centro da célula no plano XY
                    local_x = rel_cx_feet * cos_yaw + rel_cy_feet * sin_yaw
                    local_y = -rel_cx_feet * sin_yaw + rel_cy_feet * cos_yaw
                    half_side = size_feet / 2.0

                    if abs(local_x) <= half_side and abs(local_y) <= half_side:
                        is_hit = True
                    else:
                        half_s = feet_per_sq * 0.4
                        samples = [
                            (rel_cx_feet - half_s, rel_cy_feet - half_s),
                            (rel_cx_feet + half_s, rel_cy_feet - half_s),
                            (rel_cx_feet + half_s, rel_cy_feet + half_s),
                            (rel_cx_feet - half_s, rel_cy_feet + half_s),
                        ]
                        inside_count = 0
                        for sx, sy in samples:
                            lx = sx * cos_yaw + sy * sin_yaw
                            ly = -sx * sin_yaw + sy * cos_yaw
                            if abs(lx) <= half_side and abs(ly) <= half_side:
                                inside_count += 1
                        if inside_count >= 2:
                            is_hit = True

                # --- Forma 3: Esfera (3D) ---
                elif shape == AoEShape.SPHERE:
                    d_2d = math.hypot(rel_cx_feet, rel_cy_feet)
                    if d_2d <= size_feet:
                        # Raio vertical disponível na coordenada horizontal (x, y)
                        vert_radius = math.sqrt(max(0.0, size_feet * size_feet - d_2d * d_2d))
                        sphere_z_min = oz_feet - vert_radius
                        sphere_z_max = oz_feet + vert_radius

                        # Interseção entre o intervalo da esfera e o intervalo vertical da célula
                        overlap_min = max(sphere_z_min, z_bottom)
                        overlap_max = min(sphere_z_max, z_top)
                        if overlap_min <= overlap_max:
                            is_hit = True

                # --- Forma 4: Cubo (3D) ---
                elif shape == AoEShape.CUBE:
                    # Base ortonormal 3D rotacionada por (yaw, pitch)
                    # ux = (dir_x, dir_y, dir_z)
                    # uy = (-sin_yaw, cos_yaw, 0)
                    # uz = (-sin_pitch*cos_yaw, -sin_pitch*sin_yaw, cos_pitch)
                    ux = (dir_x, dir_y, dir_z)
                    uy = (-sin_yaw, cos_yaw, 0.0)
                    uz = (-sin_pitch * cos_yaw, -sin_pitch * sin_yaw, cos_pitch)

                    # Amostras 3D da coluna da célula
                    z_samples = [z_bottom - oz_feet, z_mid - oz_feet, z_top - oz_feet]
                    half_side = size_feet / 2.0

                    for rel_z in z_samples:
                        # Projeção no referencial local do cubo
                        lx = rel_cx_feet * ux[0] + rel_cy_feet * ux[1] + rel_z * ux[2]
                        ly = rel_cx_feet * uy[0] + rel_cy_feet * uy[1] + rel_z * uy[2]
                        lz = rel_cx_feet * uz[0] + rel_cy_feet * uz[1] + rel_z * uz[2]

                        # Cubo centrado na origem ou projetado a partir da face de origem
                        if (abs(lx) <= half_side or (0.0 <= lx <= size_feet)) and abs(ly) <= half_side and abs(lz) <= half_side:
                            is_hit = True
                            break

                # --- Forma 5: Cone (3D) ---
                elif shape == AoEShape.CONE:
                    # Amostras da coluna vertical da célula (topo, meio, base)
                    z_samples = [z_bottom - oz_feet, z_mid - oz_feet, z_top - oz_feet]
                    # Inclui amostras nas bordas da célula para capturar tangências
                    half_s = feet_per_sq * 0.35
                    xy_samples = [
                        (rel_cx_feet, rel_cy_feet),
                        (rel_cx_feet - half_s, rel_cy_feet - half_s),
                        (rel_cx_feet + half_s, rel_cy_feet - half_s),
                        (rel_cx_feet + half_s, rel_cy_feet + half_s),
                        (rel_cx_feet - half_s, rel_cy_feet + half_s),
                    ]

                    for sx, sy in xy_samples:
                        for sz in z_samples:
                            dist = math.sqrt(sx * sx + sy * sy + sz * sz)
                            if dist == 0.0:
                                is_hit = True
                                break
                            if dist <= size_feet:
                                # Projeção escalar sobre o eixo do cone
                                proj = sx * dir_x + sy * dir_y + sz * dir_z
                                if proj >= 0.0 and proj <= size_feet:
                                    # Verificação angular: cos(theta) >= cos(26.565°)
                                    cos_theta = proj / dist
                                    if cos_theta >= cls.CONE_COS_HALF_ANGLE - 1e-4:
                                        is_hit = True
                                        break
                        if is_hit:
                            break

                # --- Forma 6: Linha (3D) ---
                elif shape == AoEShape.LINE:
                    half_w = width_feet / 2.0
                    z_samples = [z_bottom - oz_feet, z_mid - oz_feet, z_top - oz_feet]
                    half_s = feet_per_sq * 0.35
                    xy_samples = [
                        (rel_cx_feet, rel_cy_feet),
                        (rel_cx_feet - half_s, rel_cy_feet - half_s),
                        (rel_cx_feet + half_s, rel_cy_feet - half_s),
                        (rel_cx_feet + half_s, rel_cy_feet + half_s),
                        (rel_cx_feet - half_s, rel_cy_feet + half_s),
                    ]

                    for sx, sy in xy_samples:
                        for sz in z_samples:
                            # Projeção escalar ao longo da linha
                            t = sx * dir_x + sy * dir_y + sz * dir_z
                            if 0.0 <= t <= size_feet:
                                # Vetor perpendicular à linha
                                perp_x = sx - t * dir_x
                                perp_y = sy - t * dir_y
                                perp_z = sz - t * dir_z
                                perp_dist = math.sqrt(perp_x * perp_x + perp_y * perp_y + perp_z * perp_z)
                                if perp_dist <= half_w:
                                    is_hit = True
                                    break
                        if is_hit:
                            break

                if is_hit:
                    affected_cells.add((col, row))

        return affected_cells


# Função canônica de conveniência
def calculate_aoe_cells(
    template: Optional[SpellTemplate],
    grid_manager: Optional[GridManager],
    tilemap_engine: Optional[Any] = None,
) -> Set[Tuple[int, int]]:
    """Função canônica de conveniência que encapsula AoECalculator.calculate_aoe_cells."""
    return AoECalculator.calculate_aoe_cells(template, grid_manager, tilemap_engine)
