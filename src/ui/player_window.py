import logging
import os
from typing import Optional, Dict, Any, Tuple
import arcade
from arcade.camera import Camera2D
from ..manager.session_manager import SessionManager, DisplayState
from ..manager.grid_manager import GridManager
from .initiative_hud import InitiativeHUD
from .sprites.sprite_factory import SpriteFactory
from .sprites.combat_token import CombatToken
from .utils.tilemap_renderer import TileMapRenderer
from .components.grid_cell_highlighter import GridCellHighlighter
from .renderers.player_view_renderer import PlayerViewRenderer
from ..domain.models.playablechar import PlayableCharacter

logger = logging.getLogger(__name__)


class PlayerWindow(arcade.Window):
    """
    Tela dos Jogadores (Player Screen) do Medusa VTT.
    Implementa a Máquina de Estados de Exibição (DisplayState):
      1. IDLE: Tela de descanso/espera imersiva ("Aguardando o Mestre...").
      2. PROJECTION: Projeção de imagens avulsas (NPCs, cenários, itens) com Aspect Ratio Fit (Contain).
      3. COMBAT: Renderização do mapa e tokens visíveis com a PlayerCamera em tela cheia
                 e a fita de iniciativas (InitiativeHUD) no topo.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        dm_window: Optional[Any] = None,
        width: int = 1024,
        height: int = 768,
        title: str = "Medusa VTT - Tela dos Jogadores",
    ) -> None:
        super().__init__(width, height, title, resizable=True)
        self.switch_to()
        arcade.set_window(self)

        self.session_manager = session_manager
        self.dm_window = dm_window
        self.hud = InitiativeHUD(session_manager.combat_manager)

        self._texture_cache: Dict[str, arcade.Texture] = {}
        self._text_cache: Dict[str, arcade.Text] = {}
        self._tilemap_renderer: Optional[TileMapRenderer] = None
        self._aoe_highlighter: Optional[GridCellHighlighter] = None
        self._movement_highlighter: Optional[GridCellHighlighter] = None

        # Dicionário de sprites de tokens com interpolação suave (Lerp)
        self.token_sprites: Dict[str, CombatToken] = {}

        # Câmera dos Jogadores (PlayerCamera) cobrindo a tela cheia
        self.player_camera = Camera2D(window=self)

        # Sprite animado do Sigil Místico para a tela IDLE (48x48 escalado para 92px)
        self.idle_sprites = arcade.SpriteList()
        self.sigil_sprite = SpriteFactory.create_sprite(
            sheet_path="assets/sprites/medusa_idle_1.png",
            x=self.width / 2,
            y=self.height / 2 + 30,
            width=48,
            height=48,
            target_size=92,
            frame_count=5,
        )
        self.idle_sprites.append(self.sigil_sprite)

        # Controle de temporizador da animação IDLE (0.20s por quadro)
        self._idle_anim_timer: float = 0.0
        self._idle_cur_frame: int = 0
        self._idle_frame_duration: float = 0.20

        # Registro de Listeners de Ciclo de Vida e Sessão
        self._listeners_cleaned: bool = False
        self._on_session_changed_listener = self._on_session_changed
        self._on_combat_changed_listener = self._on_combat_changed
        self.session_manager.add_listener(self._on_session_changed_listener)
        self.session_manager.combat_manager.add_listener(self._on_combat_changed_listener)

        if self.dm_window is not None:
            self.dm_window.player_window = self

        logger.info("PlayerWindow instanciada e conectada ao SessionManager.")

    def _get_texture(self, file_path: Optional[str]) -> Optional[arcade.Texture]:
        """Carrega e armazena em cache texturas de imagens."""
        if not file_path or not os.path.isfile(file_path):
            return None
        if str(file_path).lower().endswith((".json", ".xml", ".txt", ".csv")):
            return None
        resolved = str(os.path.abspath(file_path))
        if resolved not in self._texture_cache:
            try:
                self._texture_cache[resolved] = arcade.load_texture(resolved)
            except Exception as e:
                logger.error(f"Erro ao carregar textura '{resolved}': {e}")
                self._texture_cache[resolved] = None
                return None
        return self._texture_cache.get(resolved)

    def _get_cached_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool = True,
        anchor_x: str = "center",
        anchor_y: str = "center",
    ) -> arcade.Text:
        """Cache e atualização de objetos arcade.Text para desenho otimizado."""
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

    @property
    def resizable(self) -> bool:
        """Indica se a janela é redimensionável."""
        return bool(getattr(self, "_resizable", True))

    def toggle_fullscreen(self) -> None:
        """Alterna a PlayerWindow entre tela cheia e modo janela."""
        target_state = not self.fullscreen
        self.set_fullscreen(target_state)
        state_str = "tela cheia" if target_state else "modo janela"
        logger.info(f"PlayerWindow colocada em {state_str}.")

    def switch_to(self) -> None:
        """Ativa o contexto OpenGL da PlayerWindow se a janela estiver aberta e com contexto válido."""
        if getattr(self, "context", None) is None or getattr(self, "_closed", False):
            return
        try:
            super().switch_to()
        except Exception:
            pass

    def reconnect_listeners(self) -> None:
        """Reconecta listeners ao SessionManager e CombatManager ao reexibir a janela."""
        if getattr(self, "_listeners_cleaned", True):
            if hasattr(self, "_on_session_changed_listener"):
                self.session_manager.add_listener(self._on_session_changed_listener)
            if hasattr(self, "_on_combat_changed_listener"):
                self.session_manager.combat_manager.add_listener(self._on_combat_changed_listener)
            self._listeners_cleaned = False
            logger.info("PlayerWindow exibida e reconectada ao SessionManager.")

    def on_resize(self, width: int, height: int) -> None:
        """Atualiza dimensões da janela e da câmera dos jogadores proporcionalmente à resolução do monitor."""
        if not getattr(self, "visible", True) or getattr(self, "context", None) is None or getattr(self, "_closed", False):
            return
        self.switch_to()
        arcade.set_window(self)
        super().on_resize(width, height)
        if hasattr(self, "player_camera") and hasattr(self.player_camera, "match_window"):
            self.player_camera.match_window()
        layout = self._calculate_combat_layout(width, height)
        if layout is not None:
            draw_x, draw_y, draw_w, draw_h, cell_w, cell_h, cols, rows = layout
            logger.debug(
                f"PlayerWindow on_resize ({width}x{height}): Grid combat viewport={draw_w:.1f}x{draw_h:.1f} "
                f"em offset=({draw_x:.1f}, {draw_y:.1f}), cell={cell_w:.1f}x{cell_h:.1f}."
            )
        logger.info(f"PlayerWindow redimensionada para {width}x{height} (fullscreen={self.fullscreen}). Viewport recalculada.")

    def _calculate_combat_layout(
        self, w: float, h: float
    ) -> Optional[Tuple[float, float, float, float, float, float, int, int]]:
        """Calcula o layout de enquadramento do mapa de combate e dimensões das células."""
        combat_manager = self.session_manager.combat_manager
        grid_mgr = combat_manager.grid_manager
        if grid_mgr is None or grid_mgr.columns <= 0 or grid_mgr.rows <= 0:
            return None

        draw_x, draw_y, draw_w, draw_h = PlayerViewRenderer.calculate_draw_rect(w, h, grid_mgr)
        cell_w = draw_w / grid_mgr.columns
        cell_h = draw_h / grid_mgr.rows
        return draw_x, draw_y, draw_w, draw_h, cell_w, cell_h, grid_mgr.columns, grid_mgr.rows

    def _update_tokens(self, delta_time: float) -> None:
        """Sincroniza os alvos dos tokens com o CombatManager e executa a interpolação suave (Lerp)."""
        combat_manager = self.session_manager.combat_manager
        if not combat_manager.combatants:
            self.token_sprites.clear()
            return

        layout = self._calculate_combat_layout(self.width, self.height)
        if layout is None:
            return

        draw_x, draw_y, draw_w, draw_h, cell_w, cell_h, cols, rows = layout
        active_uids = set()

        for combatant in combat_manager.combatants:
            active_uids.add(combatant.uid)
            pos = combatant.position
            px = pos.get("x", 0)
            py = pos.get("y", 0)
            num_squares = getattr(combatant, "size_in_squares", 1)

            target_x = draw_x + (float(px) + num_squares / 2.0) * cell_w
            target_y = draw_y + (float(py) + num_squares / 2.0) * cell_h
            is_player = getattr(combatant, "is_player", isinstance(combatant, PlayableCharacter))
            etype = getattr(combatant, "entity_type", "player" if is_player else "monster")

            if combatant.uid not in self.token_sprites:
                token = CombatToken(
                    uid=combatant.uid,
                    name=combatant.name,
                    is_player=is_player,
                    target_x=target_x,
                    target_y=target_y,
                    entity_type=etype,
                )
                self.token_sprites[combatant.uid] = token
            else:
                token = self.token_sprites[combatant.uid]
                token.name = combatant.name
                token.is_player = is_player
                token.entity_type = etype
                token.target_x = target_x
                token.target_y = target_y

            if delta_time > 0:
                token.update_lerp(delta_time)

        for uid in list(self.token_sprites.keys()):
            if uid not in active_uids:
                del self.token_sprites[uid]

    def _draw_idle_screen(self, w: int, h: int) -> None:
        self.sigil_sprite.position = (w / 2, h / 2 + 30)
        PlayerViewRenderer.draw_idle(
            window_width=w,
            window_height=h,
            idle_sprites=self.idle_sprites,
            text_cache=self._text_cache,
        )

    def _draw_projection_screen(self, w: int, h: int) -> None:
        PlayerViewRenderer.draw_projection(
            window_width=w,
            window_height=h,
            projected_image_path=self.session_manager.projected_image_path,
            texture_cache=self._texture_cache,
            text_cache=self._text_cache,
        )

    def _draw_combat_screen(self, w: int, h: int) -> None:
        combat_manager = self.session_manager.combat_manager
        tile_map = combat_manager.tile_map
        if tile_map is not None:
            if self._tilemap_renderer is None or self._tilemap_renderer.tile_map != tile_map:
                self._tilemap_renderer = TileMapRenderer(tile_map=tile_map, grid_manager=combat_manager.grid_manager)

        if combat_manager.grid_manager is not None:
            if self._aoe_highlighter is None:
                self._aoe_highlighter = GridCellHighlighter(grid_manager=combat_manager.grid_manager)
            else:
                self._aoe_highlighter.grid_manager = combat_manager.grid_manager

            if self._movement_highlighter is None:
                self._movement_highlighter = GridCellHighlighter(grid_manager=combat_manager.grid_manager)
            else:
                self._movement_highlighter.grid_manager = combat_manager.grid_manager

        dm_win = self.dm_window
        sel_uid = getattr(dm_win, "selected_combatant_uid", None) if dm_win else None
        sel_cell = getattr(getattr(dm_win, "mini_map", None), "selected_target_cell", None) if dm_win else None
        is_fog_active = False
        if dm_win and hasattr(dm_win, "combat_tab") and getattr(dm_win.combat_tab, "fog_panel", None):
            is_fog_active = dm_win.combat_tab.fog_panel.is_tool_active

        self._update_tokens(0.0)
        PlayerViewRenderer.draw_combat(
            window_width=w,
            window_height=h,
            combat_manager=combat_manager,
            texture_cache=self._texture_cache,
            text_cache=self._text_cache,
            tilemap_renderer=self._tilemap_renderer,
            aoe_highlighter=self._aoe_highlighter,
            token_sprites=self.token_sprites,
            hud=self.hud,
            movement_highlighter=self._movement_highlighter,
            selected_target_cell=sel_cell,
            selected_combatant_uid=sel_uid,
            is_fog_active=is_fog_active,
        )

    def on_draw(self) -> None:
        if not getattr(self, "visible", True) or getattr(self, "context", None) is None or getattr(self, "_closed", False):
            return
        self.switch_to()
        arcade.set_window(self)
        self.use()
        if hasattr(self, "default_camera"):
            self.default_camera.use()
        self.clear()

        w, h = self.width, self.height
        current_state = self.session_manager.display_state

        if current_state == DisplayState.IDLE:
            self._draw_idle_screen(w, h)
        elif current_state == DisplayState.PROJECTION:
            self._draw_projection_screen(w, h)
        elif current_state == DisplayState.COMBAT:
            self._draw_combat_screen(w, h)

    def on_update(self, delta_time: float) -> None:
        """Ciclo de atualização: animação IDLE e interpolação suave de tokens em COMBAT."""
        if (
            not getattr(self, "visible", True)
            or getattr(self, "context", None) is None
            or getattr(self, "_closed", False)
            or getattr(self, "_listeners_cleaned", False)
        ):
            return
        self.switch_to()
        arcade.set_window(self)

        current_state = self.session_manager.display_state

        if current_state == DisplayState.IDLE and self.sigil_sprite.textures:
            if self.token_sprites:
                self.token_sprites.clear()
            self._idle_anim_timer += delta_time
            if self._idle_anim_timer >= self._idle_frame_duration:
                advance = int(self._idle_anim_timer // self._idle_frame_duration)
                self._idle_anim_timer %= self._idle_frame_duration
                self._idle_cur_frame = (self._idle_cur_frame + advance) % len(self.sigil_sprite.textures)
                self.sigil_sprite.texture = self.sigil_sprite.textures[self._idle_cur_frame]

        elif current_state == DisplayState.COMBAT:
            if self._tilemap_renderer is not None:
                self._tilemap_renderer.update(delta_time)
            self._update_tokens(delta_time)

        elif current_state == DisplayState.PROJECTION:
            if self.token_sprites:
                self.token_sprites.clear()

        if self.dm_window is not None and hasattr(self.dm_window, "pump_events"):
            try:
                self.dm_window.pump_events()
            except Exception:
                pass

    def _on_session_changed(self) -> None:
        """Listener reativo para mudanças de estado de exibição na sessão."""
        state = self.session_manager.display_state
        if state != DisplayState.COMBAT:
            self.token_sprites.clear()
            if self._tilemap_renderer is not None:
                self._tilemap_renderer = None

    def _on_combat_changed(self) -> None:
        """Listener reativo para atualizações táticas no CombatManager."""
        pass

    def cleanup_resources(self, hard: bool = False) -> None:
        """Desinscreve listeners de sessão e combate e libera recursos."""
        if getattr(self, "_listeners_cleaned", False) and not hard:
            return
        self._listeners_cleaned = True

        try:
            if hasattr(self, "_on_session_changed_listener"):
                self.session_manager.remove_listener(self._on_session_changed_listener)
        except Exception as e:
            logger.debug(f"Erro ao desinscrever listener de sessão da PlayerWindow: {e}")

        try:
            if hasattr(self, "_on_combat_changed_listener"):
                self.session_manager.combat_manager.remove_listener(self._on_combat_changed_listener)
        except Exception as e:
            logger.debug(f"Erro ao desinscrever listener de combate da PlayerWindow: {e}")

        if hard:
            self._closed = True
            try:
                import pyglet
                if hasattr(self, "_dispatch_updates"):
                    pyglet.clock.unschedule(self._dispatch_updates)
                if hasattr(self, "_dispatch_frame"):
                    pyglet.clock.unschedule(self._dispatch_frame)
            except Exception:
                pass

            self._texture_cache.clear()
            self._text_cache.clear()
            self.token_sprites.clear()
            self._tilemap_renderer = None
            logger.info("Recursos e listeners da PlayerWindow liberados definitivamente (hard close).")
        else:
            logger.info("Listeners da PlayerWindow pausados graciosamente (soft close).")

    def on_close(self) -> None:
        """Oculta a PlayerWindow graciosamente pelo SO ('X') preservando o contexto OpenGL."""
        logger.info("PlayerWindow ocultada via evento on_close e listeners pausados.")
        self.set_visible(False)
        self.cleanup_resources(hard=False)
        if self.dm_window is not None and hasattr(self.dm_window, "notify_player_window_closed"):
            try:
                self.dm_window.notify_player_window_closed()
            except Exception as e:
                logger.debug(f"Erro ao notificar DMWindow sobre fechamento da PlayerWindow: {e}")

    def close(self, hard: bool = False) -> None:
        """Fecha a janela (soft close ocultando ou hard close destruindo)."""
        if hard:
            self.cleanup_resources(hard=True)
            try:
                super().close()
            except Exception as e:
                logger.debug(f"Aviso no encerramento de super().close() da PlayerWindow: {e}")
        else:
            self.set_visible(False)
            self.cleanup_resources(hard=False)
            if self.dm_window is not None and hasattr(self.dm_window, "notify_player_window_closed"):
                try:
                    self.dm_window.notify_player_window_closed()
                except Exception as e:
                    logger.debug(f"Erro ao notificar DMWindow sobre fechamento da PlayerWindow: {e}")
