import logging
from typing import Optional, Set, Tuple, Any
from ..models.spell_template import SpellTemplate, AoEShape
from ..models.tile_map import TileMap
from .aoe_calculator import calculate_aoe_cells

logger = logging.getLogger(__name__)


class SpellProjectionController:
    """
    Controlador de projeção tática de áreas de efeito de feitiços (SpellTemplate).
    Gerencia rotação (yaw), inclinação vertical (pitch), altitude Z e cálculo de células atingidas.
    """

    @staticmethod
    def update_origin(template: Optional[SpellTemplate], world_x: float, world_y: float) -> Optional[SpellTemplate]:
        if template is not None:
            return template.with_origin((world_x, world_y)).with_visibility(True)
        return None

    @staticmethod
    def rotate_spell(template: Optional[SpellTemplate], delta_degrees: float) -> Optional[SpellTemplate]:
        if template is not None:
            new_rot = (template.rotation_degrees + delta_degrees) % 360.0
            updated = template.with_rotation(new_rot)
            logger.debug("Rotação da magia ajustada: %.1f°", updated.rotation_degrees)
            return updated
        return None

    @staticmethod
    def set_pitch(template: Optional[SpellTemplate], pitch_degrees: float) -> Optional[SpellTemplate]:
        if template is not None:
            updated = template.with_pitch(pitch_degrees)
            logger.debug("Pitch da magia ajustado: %.1f°", updated.pitch_degrees)
            return updated
        return None

    @staticmethod
    def adjust_pitch(template: Optional[SpellTemplate], delta_degrees: float) -> Optional[SpellTemplate]:
        if template is not None:
            new_pitch = (template.pitch_degrees + delta_degrees) % 360.0
            updated = template.with_pitch(new_pitch)
            logger.debug("Pitch da magia ajustado: %.1f°", updated.pitch_degrees)
            return updated
        return None

    @staticmethod
    def set_origin_z(template: Optional[SpellTemplate], z_feet: float) -> Optional[SpellTemplate]:
        if template is not None:
            updated = template.with_origin_z(z_feet)
            logger.debug("Altitude Z da magia ajustada: %.1fft", updated.origin_z_feet)
            return updated
        return None

    @staticmethod
    def adjust_origin_z(template: Optional[SpellTemplate], delta_feet: float) -> Optional[SpellTemplate]:
        if template is not None:
            new_z = max(0.0, template.origin_z_feet + delta_feet)
            updated = template.with_origin_z(new_z)
            logger.debug("Altitude Z da magia ajustada: %.1fft", updated.origin_z_feet)
            return updated
        return None

    @staticmethod
    def get_aoe_cells(template: Optional[SpellTemplate], grid_manager: Any, tile_map: Optional[TileMap]) -> Set[Tuple[int, int]]:
        if template is None or not template.is_active:
            return set()
        return calculate_aoe_cells(template, grid_manager, tile_map)

    @staticmethod
    def toggle_active(
        template: Optional[SpellTemplate],
        is_active: Optional[bool] = None,
        feet_per_square: float = 5.0,
    ) -> Tuple[SpellTemplate, bool]:
        if template is not None:
            new_active = not template.is_active if is_active is None else bool(is_active)
            updated = template.with_active(new_active)
            logger.info("Projeção de magia: is_active=%s", new_active)
            return updated, new_active
        else:
            new_tpl = SpellTemplate(
                shape=AoEShape.CIRCLE,
                size_feet=feet_per_square * 4.0,
                width_feet=feet_per_square,
                rotation_degrees=0.0,
                origin_world=(0.0, 0.0),
                origin_z_feet=0.0,
                pitch_degrees=0.0,
                is_active=True,
                is_visible=True,
            )
            logger.info("Template padrão de magia inicializado e ativado.")
            return new_tpl, True
