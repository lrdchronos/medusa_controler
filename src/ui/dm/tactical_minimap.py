import logging
import os
import math
from typing import Optional, Dict, Any, Tuple, Callable
import arcade
from arcade.camera import Camera2D
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.entity import Entity, EntityType, DynamicToken
from ..utils.tilemap_renderer import TileMapRenderer
from ..components.grid_cell_highlighter import GridCellHighlighter
from ..renderers.minimap_renderer import MiniMapRenderer
from .handlers.minimap_input_handler import MiniMapInputHandler
from .fog_control_panel import FogControlPanel, FogTool, BrushMode

logger = logging.getLogger(__name__)


class TacticalMiniMap:
    """
    Componente do Mini-Mapa Tático Interativo (Lado Direito da DMWindow).
    Suporta Dupla Câmera, Grid Matricial de Alto Contraste, Proporção Idêntica à tela dos jogadores,
    Camada Translúcida de Névoa de Guerra do Mestre, Pincel/Clique Unitário de Névoa,
    Drag & Drop de Tokens, Posicionamento Interativo de Tokens (PLACING_TOKEN) e Espelhamento nos estados IDLE/PROJECTION.
    """

    def __init__(
        self,
        window: arcade.Window,
        session_manager: SessionManager,
        fog_panel: Optional[FogControlPanel] = None,
    ) -> None:
        self.window = window
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.fog_panel: Optional[FogControlPanel] = fog_panel

        self.dm_camera = Camera2D(window=window)
        self._texture_cache: Dict[str, arcade.Texture] = {}
        self._text_cache: Dict[str, arcade.Text] = {}
        self._tilemap_renderer: Optional[TileMapRenderer] = None
        self._aoe_highlighter: Optional[GridCellHighlighter] = None

        self._last_draw_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

        # Estado de Arraste e Pincel de Névoa
        self._is_brushing: bool = False
        self._last_fog_cell: Optional[Tuple[int, int]] = None

        # Estado de Drag & Drop de Tokens
        self._dragged_combatant_uid: Optional[str] = None
        self._drag_world_pos: Tuple[float, float] = (0.0, 0.0)

        # Estado de Posicionamento Interativo de Token (PLACING_TOKEN)
        self._is_placing_token: bool = False
        self._placing_token_data: Optional[Dict[str, Any]] = None
        self._hover_grid_cell: Optional[Tuple[int, int]] = None
        self._on_token_spawn_callback: Optional[Callable[[Entity, Tuple[int, int], str], None]] = None

        self.update_viewport()

    @property
    def is_placing_token(self) -> bool:
        """Indica se o mini-mapa está no estado transitório de posicionamento de token."""
        return self._is_placing_token

    def start_placing_token(
        self,
        token_data: Dict[str, Any],
        on_spawn: Optional[Callable[[Entity, Tuple[int, int], str], None]] = None,
    ) -> None:
        """Ativa o modo de posicionamento de token no grid do mini-mapa."""
        self._is_placing_token = True
        self._placing_token_data = token_data.copy()
        self._on_token_spawn_callback = on_spawn
        self._hover_grid_cell = None
        logger.info(f"TacticalMiniMap: modo PLACING_TOKEN iniciado para '{token_data.get('name')}'.")

    def cancel_placing_token(self) -> None:
        """Cancela o modo de posicionamento de token e restaura a interação normal."""
        if self._is_placing_token:
            logger.info("TacticalMiniMap: modo PLACING_TOKEN cancelado.")
        self._is_placing_token = False
        self._placing_token_data = None
        self._hover_grid_cell = None
        self._on_token_spawn_callback = None

    def update_viewport(self) -> None:
        """Configura a viewport da DMCamera para a metade direita da janela."""
        w, h = self.window.width, self.window.height
        left = float(w) * 0.50
        right = float(w)
        bottom = 0.0
        top = float(h)

        self.dm_camera.viewport = arcade.types.LRBT(
            left=left,
            right=right,
            bottom=bottom,
            top=top,
        )
        self.dm_camera.position = (float(w) * 0.25, float(h) * 0.50)

    def _get_texture(self, file_path: Optional[str]) -> Optional[arcade.Texture]:
        if not file_path or not os.path.isfile(file_path):
            return None
        if str(file_path).lower().endswith((".json", ".xml", ".txt", ".csv")):
            return None
        resolved = str(os.path.abspath(file_path))
        if resolved not in self._texture_cache:
            try:
                self._texture_cache[resolved] = arcade.load_texture(resolved)
            except Exception:
                self._texture_cache[resolved] = None
                return None
        return self._texture_cache.get(resolved)

    def _get_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool = True,
        anchor_x: str = "left",
        anchor_y: str = "center",
    ) -> arcade.Text:
        cached = self._text_cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            self._text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        return cached

    def _calculate_draw_rect(self) -> Tuple[float, float, float, float]:
        """Calcula o retângulo de renderização com Contain / Aspect Ratio proporcional."""
        panel_w = float(self.window.width) * 0.50
        panel_h = float(self.window.height)

        pad_x = 16.0
        pad_y = 16.0
        avail_w = max(10.0, panel_w - (pad_x * 2))
        avail_h = max(10.0, panel_h - (pad_y * 2))

        aspect = 16.0 / 9.0
        if self.session_manager.display_state == DisplayState.COMBAT:
            grid_mgr = self.combat_manager.grid_manager
            if grid_mgr is not None and grid_mgr.columns > 0 and grid_mgr.rows > 0:
                aspect = float(grid_mgr.columns) / float(grid_mgr.rows)

        if (avail_w / avail_h) > aspect:
            draw_h = avail_h
            draw_w = draw_h * aspect
        else:
            draw_w = avail_w
            draw_h = draw_w / aspect

        draw_x = (panel_w - draw_w) / 2.0
        draw_y = (panel_h - draw_h) / 2.0

        self._last_draw_rect = (draw_x, draw_y, draw_w, draw_h)
        return self._last_draw_rect

    def screen_to_minimap_coords(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Converte coordenadas da tela para o espaço do minimapa."""
        return MiniMapInputHandler.screen_to_minimap_coords(screen_x, screen_y, self.window, self.dm_camera)

    def draw(
        self,
        split_x: Optional[float] = None,
        h: Optional[float] = None,
        w: Optional[float] = None,
        selected_combatant_uid: Optional[str] = None,
    ) -> None:
        """Renderiza todo o conteúdo da metade direita da tela do Mestre."""
        self.update_viewport()
        draw_rect = self._calculate_draw_rect()

        if self.combat_manager.map_type == "tilemap" and self.combat_manager.tile_map is not None:
            if self._tilemap_renderer is None or self._tilemap_renderer.tile_map != self.combat_manager.tile_map:
                try:
                    self._tilemap_renderer = TileMapRenderer(tile_map=self.combat_manager.tile_map)
                except Exception as e:
                    logger.warning(f"Erro ao instanciar TileMapRenderer para TacticalMiniMap: {e}")
                    self._tilemap_renderer = None

        if self._aoe_highlighter is None:
            self._aoe_highlighter = GridCellHighlighter(
                grid_manager=self.combat_manager.grid_manager,
                fill_color=(241, 196, 15, 60),
                outline_color=(241, 196, 15, 200),
                outline_width=1.5,
            )
        elif self._aoe_highlighter.grid_manager != self.combat_manager.grid_manager:
            self._aoe_highlighter.grid_manager = self.combat_manager.grid_manager

        self.dm_camera.use()
        MiniMapRenderer.draw_content(
            window_width=self.window.width,
            window_height=self.window.height,
            draw_rect=draw_rect,
            session_manager=self.session_manager,
            texture_cache=self._texture_cache,
            text_cache=self._text_cache,
            tilemap_renderer=self._tilemap_renderer,
            aoe_highlighter=self._aoe_highlighter,
            is_placing_token=self._is_placing_token,
            placing_token_data=self._placing_token_data,
            hover_grid_cell=self._hover_grid_cell,
            dragged_combatant_uid=self._dragged_combatant_uid,
            drag_world_pos=self._drag_world_pos,
        )

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> bool:
        return MiniMapInputHandler.on_mouse_press(x, y, button, modifiers, self)

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int) -> bool:
        return MiniMapInputHandler.on_mouse_drag(x, y, dx, dy, buttons, modifiers, self)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        MiniMapInputHandler.on_mouse_release(x, y, button, modifiers, self)

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        MiniMapInputHandler.on_mouse_motion(x, y, dx, dy, self)

    def on_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        return MiniMapInputHandler.on_mouse_scroll(x, y, scroll_x, scroll_y, self)

    def handle_mouse_press(
        self,
        x: float,
        y: float,
        button: int = arcade.MOUSE_BUTTON_LEFT,
        modifiers: int = 0,
        split_x: Optional[float] = None,
    ) -> bool:
        """Alias de compatibilidade para tratamento de clique do mouse."""
        return self.on_mouse_press(x, y, button, modifiers)

    def handle_mouse_drag(
        self,
        x: float,
        y: float,
        dx: float = 0.0,
        dy: float = 0.0,
        buttons: int = arcade.MOUSE_BUTTON_LEFT,
        modifiers: int = 0,
        split_x: Optional[float] = None,
    ) -> bool:
        """Alias de compatibilidade para tratamento de arraste do mouse."""
        return self.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def handle_mouse_release(
        self,
        x: float,
        y: float,
        button: int = arcade.MOUSE_BUTTON_LEFT,
        modifiers: int = 0,
        split_x: Optional[float] = None,
    ) -> None:
        """Alias de compatibilidade para soltura do mouse."""
        self.on_mouse_release(x, y, button, modifiers)

    def handle_mouse_motion(
        self,
        x: float,
        y: float,
        dx: float = 0.0,
        dy: float = 0.0,
        split_x: Optional[float] = None,
    ) -> None:
        """Alias de compatibilidade para movimento do mouse."""
        self.on_mouse_motion(x, y, dx, dy)

    def handle_mouse_scroll(
        self,
        x: float,
        y: float,
        scroll_x: float = 0.0,
        scroll_y: float = 0.0,
        is_ctrl: bool = False,
        is_alt: bool = False,
    ) -> bool:
        """Alias de compatibilidade para scroll com modificadores Ctrl / Alt."""
        return MiniMapInputHandler.on_mouse_scroll(
            x, y, scroll_x, scroll_y, self, is_ctrl=is_ctrl, is_alt=is_alt
        )

    def handle_mouse_leave(self) -> None:
        """Chamado quando o mouse deixa a área do minimapa."""
        self._hover_grid_cell = None

    def _draw_tactical_map(
        self,
        panel_x: float,
        panel_y: float,
        panel_w: float,
        panel_h: float,
        combat_manager: Any = None,
    ) -> None:
        """Método de compatibilidade para inicialização/desenho direto do renderizador de mapa."""
        if self.combat_manager.map_type == "tilemap" and self.combat_manager.tile_map is not None:
            if self._tilemap_renderer is None or self._tilemap_renderer.tile_map != self.combat_manager.tile_map:
                try:
                    self._tilemap_renderer = TileMapRenderer(tile_map=self.combat_manager.tile_map)
                except Exception as e:
                    logger.warning(f"Erro ao instanciar TileMapRenderer para TacticalMiniMap: {e}")
                    self._tilemap_renderer = None

