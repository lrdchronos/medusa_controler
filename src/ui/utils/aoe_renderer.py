import logging
import math
from typing import Optional, Tuple, Set, Any
import arcade

from ...domain.models.spell_template import SpellTemplate, AoEShape, SpellShape
from ...domain.rules.aoe_calculator import calculate_aoe_cells
from ...manager.grid_manager import GridManager
from ..components.grid_cell_highlighter import GridCellHighlighter

logger = logging.getLogger(__name__)


class AoERenderer:
    """
    Renderizador utilitário desacoplado para sobreposição visual de
    Áreas de Efeito de Feitiços (Spell AoE Overlay) no Medusa VTT.
    Utiliza o componente GridCellHighlighter para desenhar em lote (Batch GPU)
    as células matriciais atingidas pelas 6 formas canônicas de D&D 5E,
    e renderiza o ponto de ancoragem místico dourado na origem da magia.
    """

    COLOR_FILL: Tuple[int, int, int, int] = GridCellHighlighter.COLOR_SPELL_AOE
    COLOR_OUTLINE: Tuple[int, int, int, int] = GridCellHighlighter.COLOR_OUTLINE_SPELL_AOE
    COLOR_ANCHOR: Tuple[int, int, int, int] = (241, 196, 15, 255)    # Ponto de ancoragem dourado místico
    COLOR_ANCHOR_RING: Tuple[int, int, int, int] = (255, 255, 255, 220)

    _shared_highlighter: Optional[GridCellHighlighter] = None

    @classmethod
    def get_shared_highlighter(cls, grid_manager: Optional[GridManager] = None) -> GridCellHighlighter:
        """Obtém ou instancia o GridCellHighlighter compartilhado."""
        if cls._shared_highlighter is None:
            cls._shared_highlighter = GridCellHighlighter(grid_manager=grid_manager)
        elif grid_manager is not None:
            cls._shared_highlighter.grid_manager = grid_manager
        return cls._shared_highlighter

    @classmethod
    def draw(
        cls,
        template: Optional[SpellTemplate],
        grid_manager: Optional[GridManager],
        draw_x: float,
        draw_y: float,
        scale: float,
        tilemap_engine: Optional[Any] = None,
        highlighter: Optional[GridCellHighlighter] = None,
    ) -> None:
        """
        Desenha o destaque matricial da AoE com base no template e nas dimensões/escala ativas do mapa.

        :param template: Estrutura SpellTemplate ativa. Se None, inativa ou invisível, nada é desenhado.
        :param grid_manager: GridManager ativo para leitura da métrica dinâmica de pixels_per_foot.
        :param draw_x: Offset X de renderização do mapa na viewport.
        :param draw_y: Offset Y de renderização do mapa na viewport.
        :param scale: Escala uniforme de conversão entre coordenadas de mundo e pixels de tela.
        :param tilemap_engine: Referência opcional ao TileMap para elevações de terreno.
        :param highlighter: Instância opcional de GridCellHighlighter (usa shared se None).
        """
        if template is None or not template.is_active or not template.is_visible:
            return

        if grid_manager is None or grid_manager.columns <= 0 or grid_manager.rows <= 0:
            return

        # 1. Cálculo das células atingidas pelo template canônico
        cells = calculate_aoe_cells(template, grid_manager, tilemap_engine)

        # 2. Renderização em lote matricial das células via GridCellHighlighter
        hl = highlighter or cls.get_shared_highlighter(grid_manager)
        hl.grid_manager = grid_manager
        hl.set_cells(cells, color=cls.COLOR_FILL)

        cell_w = grid_manager.cell_size * scale
        cell_h = grid_manager.cell_size * scale
        hl.draw(draw_x=draw_x, draw_y=draw_y, scale=scale, cell_w=cell_w, cell_h=cell_h)

        # 3. Renderização do Ponto de Ancoragem (círculo dourado de 4px na origem)
        world_ox, world_oy = template.origin_world
        screen_ox = draw_x + world_ox * scale
        screen_oy = draw_y + world_oy * scale

        arcade.draw_circle_filled(screen_ox, screen_oy, 4.0, cls.COLOR_ANCHOR)
        arcade.draw_circle_outline(screen_ox, screen_oy, 4.0, cls.COLOR_ANCHOR_RING, 1.0)

    @classmethod
    def draw_spell_overlay(
        cls,
        template: Optional[SpellTemplate],
        grid_origin_x: float,
        grid_origin_y: float,
        cell_size_px: float,
        grid_manager: Optional[GridManager] = None,
        feet_per_square: float = 5.0,
        is_dm: bool = True,
    ) -> None:
        """
        Renderiza os marcadores visuais do template de magia ativo (ponto de ancoragem, linha diretora e ângulo).
        """
        if template is None or not template.is_active or not template.is_visible:
            return

        world_cell_size = grid_manager.cell_size if grid_manager and grid_manager.cell_size > 0 else cell_size_px
        feet_per_sq = grid_manager.feet_per_square if grid_manager else max(0.1, float(feet_per_square))
        world_ox, world_oy = template.origin_world

        # Converte a origem em coordenadas de mundo (map pixels) para pixels de tela na viewport
        screen_ox = grid_origin_x + (world_ox / world_cell_size) * cell_size_px
        screen_oy = grid_origin_y + (world_oy / world_cell_size) * cell_size_px

        try:
            # Desenha a âncora central
            anchor_radius = 5.0 if is_dm else 4.0
            arcade.draw_circle_filled(screen_ox, screen_oy, anchor_radius, cls.COLOR_ANCHOR)
            arcade.draw_circle_outline(screen_ox, screen_oy, anchor_radius + 2.0, cls.COLOR_ANCHOR_RING, 1.5)

            # Se for cone/linha no lado do mestre, desenha linha de direção sutil
            if is_dm and template.shape in (AoEShape.CONE, AoEShape.LINE, SpellShape.CONE, SpellShape.LINE):
                rad = math.radians(template.rotation_degrees)
                dir_len = (template.size_feet / feet_per_sq) * cell_size_px
                end_x = screen_ox + math.cos(rad) * dir_len
                end_y = screen_oy + math.sin(rad) * dir_len
                arcade.draw_line(screen_ox, screen_oy, end_x, end_y, (241, 196, 15, 180), 1.5)
                arcade.draw_circle_filled(end_x, end_y, 3.0, (241, 196, 15, 220))
        except Exception as e:
            logger.debug(f"AoERenderer.draw_spell_overlay ignorado em ambiente sem janela ativa: {e}")
