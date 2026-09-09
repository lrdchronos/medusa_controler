import logging
import os
import math
from typing import Optional, Dict, Any, Tuple, Callable
import arcade
from arcade.camera import Camera2D
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.entity import Entity, EntityType, DynamicToken
from ...domain.models.playablechar import PlayableCharacter
from ..utils.sprite_utils import SpriteFactory
from ..utils.tilemap_renderer import TileMapRenderer
from ..utils.aoe_renderer import AoERenderer
from ..components.grid_cell_highlighter import GridCellHighlighter
from ..renderers.token_status_renderer import TokenStatusRenderer
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

        # Retângulo de desenho calculado para manter a proporção exata: (draw_x, draw_y, draw_w, draw_h)
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
        # Validação defensiva (Poka-Yoke): ignora formatos não-imagem
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
        else:
            map_path = getattr(self.combat_manager, "map_file", getattr(self.combat_manager, "map_image_path", None))
            tex = self._get_texture(map_path) if map_path else None
            if tex is not None:
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

        # 2.5. Renderização da Camada de Névoa de Guerra (Visão do Mestre - Semi-Translúcida com borda)
        fog_mgr = self.combat_manager.fog_manager
        fogged_cells = fog_mgr.get_fogged_cells()
        if fogged_cells:
            for (f_col, f_row) in fogged_cells:
                if 0 <= f_col < grid_mgr.columns and 0 <= f_row < grid_mgr.rows:
                    fcx = draw_x + (f_col + 0.5) * cell_w
                    fcy = draw_y + (f_row + 0.5) * cell_h
                    arcade.draw_rect_filled(
                        arcade.XYWH(fcx, fcy, cell_w, cell_h),
                        (20, 20, 30, 160),
                    )
                    arcade.draw_rect_outline(
                        arcade.XYWH(fcx, fcy, cell_w, cell_h),
                        (80, 90, 110, 180),
                        1.0,
                    )

        # 3. Renderização de Tokens
        active_combatant = self.combat_manager.active_character

        for combatant in self.combat_manager.combatants:
            pos = combatant.position
            px = pos.get("x", 0)
            py = pos.get("y", 0)
            num_squares = getattr(combatant, "size_in_squares", 1)

            if combatant.uid == self._dragged_combatant_uid:
                cx, cy = self._drag_world_pos
            else:
                cx = draw_x + (float(px) + num_squares / 2.0) * cell_w
                cy = draw_y + (float(py) + num_squares / 2.0) * cell_h

            is_selected = (combatant.uid == selected_combatant_uid)
            is_active = (combatant == active_combatant)
            is_player = getattr(combatant, "is_player", isinstance(combatant, PlayableCharacter))
            etype = getattr(combatant, "entity_type", "player" if is_player else "monster")
            token_radius = (min(cell_w, cell_h) * num_squares * 0.88) / 2.0

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
                entity_type=etype,
            )

            # Renderização dos Badges Orbitais de Vida e Condições Táticas (Relógio 12h)
            TokenStatusRenderer.draw(
                entity=combatant,
                center_x=cx,
                center_y=cy,
                token_radius=token_radius,
                scale_factor=scale,
            )

        # 3.5. Prévia Translúcida de Posicionamento de Token (PLACING_TOKEN)
        if self._is_placing_token and self._placing_token_data:
            p_size = self._placing_token_data.get("size", "Medium")
            p_squares = grid_mgr.get_size_in_squares(p_size)
            token_radius = (min(cell_w, cell_h) * p_squares * 0.88) / 2.0
            t_name = self._placing_token_data.get("name", "TOKEN")
            t_type = self._placing_token_data.get("entity_type", EntityType.NEUTRAL)
            is_p = (t_type == EntityType.PLAYER or str(t_type).lower() == "player")

            if self._hover_grid_cell is not None:
                h_col, h_row = self._hover_grid_cell
                if grid_mgr.is_area_valid(h_col, h_row, p_squares):
                    hcx = draw_x + (float(h_col) + p_squares / 2.0) * cell_w
                    hcy = draw_y + (float(h_row) + p_squares / 2.0) * cell_h
                    is_walk = self.combat_manager.is_walkable_for_size(h_col, h_row, p_size)

                    area_w = cell_w * p_squares
                    area_h = cell_h * p_squares

                    # Realce da área hover
                    if is_walk:
                        arcade.draw_rect_filled(arcade.XYWH(hcx, hcy, area_w, area_h), (46, 204, 113, 70))
                        arcade.draw_rect_outline(arcade.XYWH(hcx, hcy, area_w, area_h), (46, 204, 113, 220), 2.0)
                    else:
                        arcade.draw_rect_filled(arcade.XYWH(hcx, hcy, area_w, area_h), (231, 76, 60, 90))
                        arcade.draw_rect_outline(arcade.XYWH(hcx, hcy, area_w, area_h), (231, 76, 60, 220), 2.0)

                    # Token translúcido posicionado no centro da criatura
                    SpriteFactory.draw_tactical_token(
                        name=t_name,
                        is_player=is_p,
                        x=hcx,
                        y=hcy,
                        radius=token_radius,
                        is_alive=True,
                        is_hidden=False,
                        is_selected=True,
                        entity_type=t_type,
                        text_cache=self._text_cache,
                        token_key="placing_preview",
                    )

        # 4. Projeção Tática de Áreas de Efeito de Feitiços (Spell AoE Overlay)
        AoERenderer.draw(
            template=self.combat_manager.active_spell_template,
            grid_manager=grid_mgr,
            draw_x=draw_x,
            draw_y=draw_y,
            scale=scale,
            tilemap_engine=tile_map,
            highlighter=self._aoe_highlighter,
        )

        # Banner Superior do Mini-Mapa
        if self._is_placing_token and self._placing_token_data:
            arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, banner_h), (24, 48, 70, 245))
            arcade.draw_line(vx, vy + vh - banner_h, vx + vw, vy + vh - banner_h, (241, 196, 15, 255), 1.5)
            t_name = self._placing_token_data.get("name", "")
            banner_txt = f"📍 POSICIONAR: '{t_name}' • Clique numa célula válida (ESC / Dir cancela)"
            self._get_text("dm_map_placing_hdr", banner_txt, vx + 16, vy + vh - 18, (241, 196, 15, 255), 9.5, bold=True).draw()
        else:
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

    def handle_mouse_motion(self, x: float, y: float) -> bool:
        """
        Trata o movimento do mouse sobre o minimapa.
        Se em modo de posicionamento de token (PLACING_TOKEN):
          - Atualiza a célula sob o mouse para exibir prévia e snap-to-grid.
        Se a projeção de feitiço estiver ativa:
          - Converte as coordenadas da tela para coordenadas de mundo reais considerando offset e escala.
          - Atualiza origin_world no SpellTemplate.
          - Notifica os ouvintes (DMWindow e PlayerWindow) para redesenho reativo.
        """
        grid_mgr = self.combat_manager.grid_manager
        draw_x, draw_y, draw_w, draw_h = self._last_draw_rect

        # 1. Modo de Posicionamento de Token (PLACING_TOKEN)
        if self._is_placing_token:
            if grid_mgr is not None and draw_w > 0 and draw_h > 0:
                if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                    cell_w = draw_w / grid_mgr.columns
                    cell_h = draw_h / grid_mgr.rows
                    p_size = (self._placing_token_data or {}).get("size", "Medium")
                    p_squares = grid_mgr.get_size_in_squares(p_size)

                    lx = float(x) - draw_x
                    ly = float(y) - draw_y

                    # Snapping:
                    # Para 1x1 e 3x3 (ímpares): centro da célula
                    # Para 2x2 e 4x4 (pares): interseção de linhas da grade
                    if p_squares % 2 == 1:
                        col = int(math.floor(lx / cell_w)) - (p_squares // 2)
                        row = int(math.floor(ly / cell_h)) - (p_squares // 2)
                    else:
                        col = int(round(lx / cell_w)) - (p_squares // 2)
                        row = int(round(ly / cell_h)) - (p_squares // 2)

                    col = max(0, min(grid_mgr.columns - p_squares, col))
                    row = max(0, min(grid_mgr.rows - p_squares, row))

                    if grid_mgr.is_area_valid(col, row, p_squares):
                        self._hover_grid_cell = (col, row)
                        return True
            self._hover_grid_cell = None
            return True

        # 2. Projeção Tática de Magia
        tpl = self.combat_manager.active_spell_template
        if grid_mgr is None or tpl is None or not tpl.is_active:
            return False

        if draw_w <= 0 or draw_h <= 0 or grid_mgr.map_width <= 0:
            return False

        # Verifica se o cursor está sobre a área do mapa desenhado
        if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
            local_x = float(x) - draw_x
            local_y = float(y) - draw_y
            scale = draw_w / grid_mgr.map_width

            world_x = max(0.0, min(grid_mgr.map_width, local_x / scale))
            world_y = max(0.0, min(grid_mgr.map_height, local_y / scale))

            self.combat_manager.update_spell_origin(world_x, world_y)
            return True
        else:
            self.handle_mouse_leave()
            return False

    def handle_mouse_scroll(
        self,
        x: float,
        y: float,
        scroll_x: float,
        scroll_y: float,
        is_ctrl: Optional[bool] = None,
        is_alt: Optional[bool] = None,
    ) -> bool:
        """
        Trata rotação da roda do mouse sobre o minimapa.
        Se a projeção estiver ativa e o cursor sobre o minimapa:
          - Scroll simples (livre): Rotaciona o ângulo horizontal (yaw) em passos de 2°.
          - Ctrl + Scroll: Rotaciona o ângulo horizontal (yaw) em passos rápidos de 15°.
          - Alt + Scroll: Altera a inclinação vertical (pitch) em passos de 15°.
          - Interrompe a propagação do evento.
        """
        grid_mgr = self.combat_manager.grid_manager
        tpl = self.combat_manager.active_spell_template
        if grid_mgr is None or tpl is None or not tpl.is_active:
            return False

        draw_x, draw_y, draw_w, draw_h = self._last_draw_rect
        if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
            alt_active = is_alt if is_alt is not None else getattr(self.window, "is_alt_held", False)
            if alt_active:
                step_pitch = 15.0
                delta = step_pitch if scroll_y > 0 else -step_pitch
                self.combat_manager.adjust_spell_pitch(delta)
            else:
                ctrl_active = is_ctrl if is_ctrl is not None else getattr(self.window, "is_ctrl_held", False)
                step_yaw = 15.0 if ctrl_active else 2.0
                delta = step_yaw if scroll_y > 0 else -step_yaw
                self.combat_manager.rotate_spell(delta)
            return True

        return False

    def handle_mouse_leave(self) -> None:
        """Desativa a visibilidade temporária da projeção quando o mouse sai dos limites do minimapa."""
        if self._is_placing_token:
            self._hover_grid_cell = None
        self.combat_manager.set_spell_visibility(False)

    def handle_mouse_press(
        self,
        x: float,
        y: float,
        split_x: float,
        h: float,
        button: int = arcade.MOUSE_BUTTON_LEFT,
        on_select_combatant: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Inicia posicionamento de token, edição de névoa ou drag & drop de token."""
        grid_mgr = self.combat_manager.grid_manager
        if grid_mgr is None:
            return False

        draw_x, draw_y, draw_w, draw_h = self._last_draw_rect
        if draw_w <= 0 or draw_h <= 0:
            return False

        cell_w = draw_w / grid_mgr.columns
        cell_h = draw_h / grid_mgr.rows

        # Prioridade 0: Modo de Posicionamento de Token Ativo (PLACING_TOKEN)
        if self._is_placing_token:
            # Botão Direito cancela o modo de posicionamento
            if button == arcade.MOUSE_BUTTON_RIGHT or button == 4:
                self.cancel_placing_token()
                return True

            if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                local_x = float(x) - draw_x
                local_y = float(y) - draw_y
                t_data = self._placing_token_data or {}
                p_size = t_data.get("size", "Medium")
                p_squares = grid_mgr.get_size_in_squares(p_size)

                if p_squares % 2 == 1:
                    col = int(math.floor(local_x / cell_w)) - (p_squares // 2)
                    row = int(math.floor(local_y / cell_h)) - (p_squares // 2)
                else:
                    col = int(round(local_x / cell_w)) - (p_squares // 2)
                    row = int(round(local_y / cell_h)) - (p_squares // 2)

                col = max(0, min(grid_mgr.columns - p_squares, col))
                row = max(0, min(grid_mgr.rows - p_squares, row))

                if grid_mgr.is_area_valid(col, row, p_squares):
                    if self.combat_manager.is_walkable_for_size(col, row, p_size):
                        etype = t_data.get("entity_type", EntityType.NEUTRAL)
                        token_entity = DynamicToken(
                            name=t_data.get("name", "Token"),
                            max_hp=int(t_data.get("max_hp", 1)),
                            armor_class=int(t_data.get("armor_class", 10)),
                            entity_type=etype,
                            token_sprite=t_data.get("token_sprite"),
                            size=p_size,
                        )
                        slot = t_data.get("initiative_slot", "next")
                        self.combat_manager.spawn_combatant(token_entity, (col, row), initiative_slot=slot)
                        if self._on_token_spawn_callback:
                            self._on_token_spawn_callback(token_entity, (col, row), slot)
                        self.cancel_placing_token()
                        return True
                    else:
                        logger.warning(f"Área sob ({col}, {row}) ({p_size}) possui células bloqueadas para posicionamento.")
                        return True
            return True

        # Prioridade 1: Ferramenta Manual de Névoa de Guerra ativa no painel do Mestre
        if self.fog_panel is not None and self.fog_panel.is_tool_active:
            if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                local_x = float(x) - draw_x
                local_y = float(y) - draw_y
                col = int(math.floor(local_x / cell_w))
                row = int(math.floor(local_y / cell_h))
                if 0 <= col < grid_mgr.columns and 0 <= row < grid_mgr.rows:
                    if self.fog_panel.active_tool == FogTool.ADD:
                        self.combat_manager.fog_manager.add_fog(col, row)
                    elif self.fog_panel.active_tool == FogTool.REVEAL:
                        self.combat_manager.fog_manager.remove_fog(col, row)
                    self._is_brushing = True
                    self._last_fog_cell = (col, row)
                    return True

        # Prioridade 2: Drag & Drop de Tokens
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
        """Trata arraste contínuo de pincel de névoa ou posicionamento de token."""
        # 1. Pincel Contínuo de Névoa de Guerra
        if (
            self._is_brushing
            and self.fog_panel is not None
            and self.fog_panel.is_tool_active
            and self.fog_panel.brush_mode == BrushMode.CONTINUOUS
        ):
            grid_mgr = self.combat_manager.grid_manager
            if grid_mgr is not None:
                draw_x, draw_y, draw_w, draw_h = self._last_draw_rect
                if draw_x <= x <= draw_x + draw_w and draw_y <= y <= draw_y + draw_h:
                    cell_w = draw_w / grid_mgr.columns
                    cell_h = draw_h / grid_mgr.rows
                    col = int(math.floor((float(x) - draw_x) / cell_w))
                    row = int(math.floor((float(y) - draw_y) / cell_h))
                    if 0 <= col < grid_mgr.columns and 0 <= row < grid_mgr.rows:
                        if (col, row) != self._last_fog_cell:
                            if self.fog_panel.active_tool == FogTool.ADD:
                                self.combat_manager.fog_manager.add_fog(col, row)
                            elif self.fog_panel.active_tool == FogTool.REVEAL:
                                self.combat_manager.fog_manager.remove_fog(col, row)
                            self._last_fog_cell = (col, row)
            return

        # 2. Atualiza posição visual do token arrastado
        if self._dragged_combatant_uid is not None:
            self._drag_world_pos = (float(x), float(y))

    def handle_mouse_release(self, x: float, y: float, split_x: float) -> None:
        """Finaliza arraste de pincel de névoa ou aplica Snap-to-Grid no token."""
        if self._is_brushing:
            self._is_brushing = False
            self._last_fog_cell = None
            return

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

                # Validação tática de movimentação via TileMap / CombatManager com suporte a tamanho
                c_size = getattr(combatant, "size", "Medium")
                if not self.combat_manager.is_walkable_for_size(clamped_col, clamped_row, c_size):
                    prev_pos = combatant.position
                    prev_x = prev_pos.get("x", 0)
                    prev_y = prev_pos.get("y", 0)
                    logger.warning(
                        f"Movimento bloqueado para '{combatant.name}' ({c_size}): célula ou área sob ({clamped_col}, {clamped_row}) "
                        f"possui blocks_movement=True. Revertendo para ({prev_x}, {prev_y})."
                    )
                else:
                    self.combat_manager.set_combatant_position(self._dragged_combatant_uid, clamped_col, clamped_row)

            self._dragged_combatant_uid = None

