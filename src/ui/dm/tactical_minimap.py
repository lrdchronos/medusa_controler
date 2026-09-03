import logging
import os
import math
from typing import Optional, Dict, Any, Tuple, Callable
import arcade
from arcade.camera import Camera2D
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.playablechar import PlayableCharacter
from ..utils.sprite_utils import SpriteFactory
from ..utils.tilemap_renderer import TileMapRenderer

logger = logging.getLogger(__name__)


class TacticalMiniMap:
    """
    Componente do Mini-Mapa Tático Interativo (Lado Direito da DMWindow).
    Suporta Dupla Câmera, Grid Matricial de Alto Contraste, Proporção Idêntica à tela dos jogadores,
    Drag & Drop de Tokens e Espelhamento nos estados IDLE/PROJECTION.
    """

    def __init__(self, window: arcade.Window, session_manager: SessionManager) -> None:
        self.window = window
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager

        self.dm_camera = Camera2D(window=window)
        self._texture_cache: Dict[str, arcade.Texture] = {}
        self._text_cache: Dict[str, arcade.Text] = {}
        self._tilemap_renderer: Optional[TileMapRenderer] = None

        # Retângulo de desenho calculado para manter a proporção exata: (draw_x, draw_y, draw_w, draw_h)
        self._last_draw_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

        # Estado de Drag & Drop
        self._dragged_combatant_uid: Optional[str] = None
        self._drag_world_pos: Tuple[float, float] = (0.0, 0.0)

        self.update_viewport()

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
        resolved = str(os.path.abspath(file_path))
        if resolved not in self._texture_cache:
            try:
                self._texture_cache[resolved] = arcade.load_texture(resolved)
            except Exception:
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
        return cached

    def draw(self, split_x: float, h: float, w: float, selected_combatant_uid: Optional[str]) -> None:
        """Renderiza o lado direito com base no estado da sessão."""
        right_w = w - split_x
        state = self.session_manager.display_state

        if state == DisplayState.COMBAT:
            self._draw_tactical_map(split_x, 0, right_w, h, selected_combatant_uid)
        elif state == DisplayState.PROJECTION:
            self._draw_showcase_preview(split_x, 0, right_w, h)
        else:
            self._draw_idle_mirror(split_x, 0, right_w, h)

    def _draw_tactical_map(self, vx: float, vy: float, vw: float, vh: float, selected_combatant_uid: Optional[str]) -> None:
        """
        Desenha o mapa tático, o grid de alto contraste e os tokens mantendo a proporção exata
        e a correspondência de coordenadas com a tela dos jogadores.
        """
        map_path = getattr(self.combat_manager, "map_file", getattr(self.combat_manager, "map_image_path", None))
        tex = self._get_texture(map_path)

        grid_mgr = self.combat_manager.grid_manager
        if grid_mgr is None:
            return

        world_w = grid_mgr.map_width
        world_h = grid_mgr.map_height

        # Espaço disponível reservando margens e o banner superior
        banner_h = 36
        margin = 12
        avail_w = vw - margin * 2
        avail_h = vh - banner_h - margin * 2

        scale = min(avail_w / world_w, avail_h / world_h)
        draw_w = world_w * scale
        draw_h = world_h * scale

        draw_x = vx + (vw - draw_w) / 2
        draw_y = vy + (vh - banner_h - draw_h) / 2

        cell_w = draw_w / grid_mgr.columns
        cell_h = draw_h / grid_mgr.rows

        # Armazena o retângulo de projeção para o cálculo de cliques de drag & drop
        self._last_draw_rect = (draw_x, draw_y, draw_w, draw_h)

        # Fundo do viewport do Mini-Mapa
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), (12, 16, 22, 255))

        # 1. Mapa de Batalha com Proporção Preservada (TileMap Modular ou Imagem Única)
        tile_map = self.combat_manager.tile_map
        if tile_map is not None:
            if self._tilemap_renderer is None or self._tilemap_renderer.tile_map != tile_map:
                self._tilemap_renderer = TileMapRenderer(tile_map=tile_map, grid_manager=grid_mgr)
            tile_w = draw_w / float(tile_map.width)
            tile_h = draw_h / float(tile_map.height)
            self._tilemap_renderer.update_layout(draw_x, draw_y, tile_w, tile_h)
            self._tilemap_renderer.draw(pixelated=True)
            arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (60, 80, 110, 220), 1.5)
        elif tex is not None:
            arcade.draw_texture_rect(tex, arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h))
            arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (60, 80, 110, 220), 1.5)
        else:
            arcade.draw_rect_filled(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (24, 32, 28, 255))
            arcade.draw_rect_outline(arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h), (60, 80, 110, 220), 1.5)

        # 2. Linhas do Grid Tático de ALTO CONTRASTE (Luminous Steel Cyan)
        grid_color = (130, 205, 255, 175)

        for c in range(grid_mgr.columns + 1):
            lx = draw_x + c * cell_w
            arcade.draw_line(lx, draw_y, lx, draw_y + draw_h, grid_color, 1.2)

        for r in range(grid_mgr.rows + 1):
            ly = draw_y + r * cell_h
            arcade.draw_line(draw_x, ly, draw_x + draw_w, ly, grid_color, 1.2)

        # 3. Renderização de Tokens
        active_combatant = self.combat_manager.active_character

        for combatant in self.combat_manager.combatants:
            pos = combatant.position
            px = pos.get("x", 0)
            py = pos.get("y", 0)

            if combatant.uid == self._dragged_combatant_uid:
                cx, cy = self._drag_world_pos
            else:
                cx = draw_x + (px + 0.5) * cell_w
                cy = draw_y + (py + 0.5) * cell_h

            is_selected = (combatant.uid == selected_combatant_uid)
            is_active = (combatant == active_combatant)
            is_player = isinstance(combatant, PlayableCharacter)
            token_radius = (min(cell_w, cell_h) * 0.88) / 2.0

            SpriteFactory.draw_tactical_token(
                name=combatant.name,
                is_player=is_player,
                x=cx,
                y=cy,
                radius=token_radius,
                is_alive=combatant.is_alive,
                is_hidden=combatant.is_hidden,
                is_selected=is_selected,
                is_active=is_active,
                text_cache=self._text_cache,
            )

        # Banner Superior do Mini-Mapa
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, banner_h), (12, 16, 22, 230))
        arcade.draw_line(vx, vy + vh - banner_h, vx + vw, vy + vh - banner_h, (50, 65, 90, 200), 1)

        map_title = f"🗺️ MINI-MAPA TÁTICO (MESTRE) • Grid {grid_mgr.columns}x{grid_mgr.rows} ({grid_mgr.feet_per_square}ft/sq)"
        self._get_text("dm_map_hdr", map_title, vx + 16, vy + vh - 18, (241, 196, 15, 255), 10, bold=True).draw()

    def _draw_showcase_preview(self, vx: float, vy: float, vw: float, vh: float) -> None:
        """Exibe miniatura da imagem projetada."""
        img_path = self.session_manager.projected_image_path
        tex = self._get_texture(img_path)

        margin = 30
        prev_w = vw - margin * 2
        prev_h = vh - margin * 2 - 40

        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), (16, 20, 28, 255))
        if tex is not None:
            arcade.draw_texture_rect(tex, arcade.XYWH(vx + vw / 2, vy + vh / 2 - 10, prev_w, prev_h))
            arcade.draw_rect_outline(arcade.XYWH(vx + vw / 2, vy + vh / 2 - 10, prev_w, prev_h), (52, 152, 219, 200), 2)
        else:
            self._get_text("shw_no_img", "Nenhuma imagem projetada no momento.", vx + vw / 2, vy + vh / 2, (180, 190, 205, 255), 11, bold=False, anchor_x="center").draw()

        # Banner Superior
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, 36), (12, 16, 22, 220))
        self._get_text("dm_proj_hdr", "🖼️ ESPELHO DE PROJEÇÃO (SHOWCASE)", vx + 16, vy + vh - 18, (52, 152, 219, 255), 10, bold=True).draw()

    def _draw_idle_mirror(self, vx: float, vy: float, vw: float, vh: float) -> None:
        """Exibe espelho da tela de descanso (IDLE)."""
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), (14, 18, 24, 255))
        for x in range(int(vx), int(vx + vw), 40):
            arcade.draw_line(x, vy, x, vy + vh, (25, 32, 42, 60), 1)

        self._get_text("idle_prev_t", "MEDUSA VTT", vx + vw / 2, vy + vh / 2 + 10, (241, 196, 15, 255), 18, bold=True, anchor_x="center").draw()
        self._get_text("idle_prev_s", "Tela dos Jogadores em Espera (IDLE)", vx + vw / 2, vy + vh / 2 - 20, (160, 175, 195, 255), 10, bold=False, anchor_x="center").draw()

        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, 36), (12, 16, 22, 220))
        self._get_text("dm_idle_hdr", "🟢 ESPELHO DE ESPERA (IDLE)", vx + 16, vy + vh - 18, (46, 204, 113, 255), 10, bold=True).draw()

    # --- PROCESSAMENTO DE EVENTOS DE MOUSE ---

    def handle_mouse_press(self, x: float, y: float, split_x: float, h: float, on_select_combatant: Optional[Callable[[str], None]] = None) -> bool:
        """Inicia drag & drop de token sob o cursor do mouse."""
        grid_mgr = self.combat_manager.grid_manager
        if grid_mgr is None:
            return False

        draw_x, draw_y, draw_w, draw_h = self._last_draw_rect
        cell_w = draw_w / grid_mgr.columns
        cell_h = draw_h / grid_mgr.rows
        radius = (min(cell_w, cell_h) * 0.88) / 2.0

        for combatant in reversed(self.combat_manager.combatants):
            pos = combatant.position
            px = pos.get("x", 0)
            py = pos.get("y", 0)

            cx = draw_x + (px + 0.5) * cell_w
            cy = draw_y + (py + 0.5) * cell_h

            dist_sq = (x - cx) ** 2 + (y - cy) ** 2
            if dist_sq <= (radius + 6) ** 2:
                self._dragged_combatant_uid = combatant.uid
                self._drag_world_pos = (float(x), float(y))
                if on_select_combatant:
                    on_select_combatant(combatant.uid)
                return True

        return False

    def handle_mouse_drag(self, x: float, y: float) -> None:
        """Atualiza a posição do token arrastado."""
        if self._dragged_combatant_uid is not None:
            self._drag_world_pos = (float(x), float(y))

    def handle_mouse_release(self, x: float, y: float, split_x: float) -> None:
        """Aplica Snap-to-Grid no token arrastado mapeando precisamente para a célula matricial correspondente com validação tática."""
        if self._dragged_combatant_uid is not None:
            combatant = self.combat_manager.get_combatant(self._dragged_combatant_uid)
            grid_mgr = self.combat_manager.grid_manager
            if grid_mgr is not None and combatant is not None:
                draw_x, draw_y, draw_w, draw_h = self._last_draw_rect
                cell_w = draw_w / grid_mgr.columns
                cell_h = draw_h / grid_mgr.rows

                local_x = float(x) - draw_x
                local_y = float(y) - draw_y

                col = int(math.floor(local_x / cell_w))
                row = int(math.floor(local_y / cell_h))

                clamped_col = max(0, min(grid_mgr.columns - 1, col))
                clamped_row = max(0, min(grid_mgr.rows - 1, row))

                # Validação tática de movimentação via TileMap / CombatManager
                if not self.combat_manager.is_walkable(clamped_col, clamped_row):
                    prev_pos = combatant.position
                    prev_x = prev_pos.get("x", 0)
                    prev_y = prev_pos.get("y", 0)
                    logger.warning(
                        f"Movimento bloqueado para '{combatant.name}': célula ({clamped_col}, {clamped_row}) "
                        f"possui blocks_movement=True. Revertendo para ({prev_x}, {prev_y})."
                    )
                else:
                    self.combat_manager.set_combatant_position(self._dragged_combatant_uid, clamped_col, clamped_row)

            self._dragged_combatant_uid = None

