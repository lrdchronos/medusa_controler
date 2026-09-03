import logging
import math
import os
import time
from typing import Optional, Dict, Any, Tuple
import arcade
from arcade.camera import Camera2D
from ..manager.session_manager import SessionManager, DisplayState
from .initiative_hud import InitiativeHUD
from .utils.sprite_utils import SpriteFactory, CombatToken
from .utils.tilemap_renderer import TileMapRenderer
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

    def _get_texture(self, file_path: Optional[str]) -> Optional[arcade.Texture]:
        """Carrega e armazena em cache texturas de imagens."""
        if not file_path or not os.path.isfile(file_path):
            return None
        resolved = str(os.path.abspath(file_path))
        if resolved not in self._texture_cache:
            try:
                self._texture_cache[resolved] = arcade.load_texture(resolved)
            except Exception as e:
                logger.error(f"Erro ao carregar textura '{resolved}': {e}")
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

    def on_resize(self, width: int, height: int) -> None:
        """Atualiza dimensões da janela e da câmera dos jogadores."""
        self.switch_to()
        arcade.set_window(self)
        super().on_resize(width, height)
        if hasattr(self, "player_camera"):
            self.player_camera.match_window()

    def on_draw(self) -> None:
        self.switch_to()
        arcade.set_window(self)
        self.use()
        self.clear()

        w, h = self.width, self.height
        current_state = self.session_manager.display_state

        if current_state == DisplayState.IDLE:
            self._draw_idle_screen(w, h)

        elif current_state == DisplayState.PROJECTION:
            self._draw_projection_screen(w, h)

        elif current_state == DisplayState.COMBAT:
            self._draw_combat_screen(w, h)

    # --- 1. ESTADO IDLE (TELA DE DESCANSO / ESPERA) ---

    def _draw_idle_screen(self, w: int, h: int) -> None:
        """Desenha a tela de espera com estilo Dark Fantasy elegante."""
        # Fundo degradê escuro
        arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), (14, 18, 24, 255))

        # Grade geométrica sutil de fundo
        for x in range(0, w, 60):
            arcade.draw_line(x, 0, x, h, (25, 32, 42, 70), 1)
        for y in range(0, h, 60):
            arcade.draw_line(0, y, w, y, (25, 32, 42, 70), 1)

        center_x = w / 2
        center_y = h / 2 + 30

        # Renderização do Sprite do Sigil Místico animado (48x48 escalado para 92px)
        self.sigil_sprite.position = (center_x, center_y)
        self.idle_sprites.draw(pixelated=True)

        # Título principal
        title_txt = self._get_cached_text(
            "idle_title",
            "MEDUSA  VTT",
            center_x,
            center_y - 120,
            (241, 196, 15, 255),
            26,
            bold=True,
        )
        title_txt.draw()

        # Subtítulo / Status
        status_txt = self._get_cached_text(
            "idle_subtitle",
            "Mesa Digital D&D 5E  •  Aguardando o Mestre...",
            center_x,
            center_y - 160,
            (160, 175, 195, 220),
            13,
            bold=False,
        )
        status_txt.draw()

    # --- 2. ESTADO PROJECTION (SHOWCASE COM ASPECT RATIO FIT) ---

    def _draw_projection_screen(self, w: int, h: int) -> None:
        """
        Projeta a imagem selecionada pelo Mestre mantendo a proporção de aspecto (Aspect Ratio Fit / Contain).
        Oculta completamente o HUD de iniciativas.
        """
        # Fundo cinemático escuro
        arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), (8, 10, 14, 255))

        image_path = self.session_manager.projected_image_path
        tex = self._get_texture(image_path)

        if tex is not None:
            # Margem de respiro na tela
            margin = 40
            avail_w = max(100, w - margin * 2)
            avail_h = max(100, h - margin * 2)

            # Cálculo de Aspect Ratio Fit (Contain)
            scale = min(avail_w / tex.width, avail_h / tex.height)
            render_w = tex.width * scale
            render_h = tex.height * scale

            # Sombra suave sob a imagem
            arcade.draw_rect_filled(
                arcade.XYWH(w / 2, h / 2 - 4, render_w + 10, render_h + 10),
                (0, 0, 0, 160),
            )

            # Renderiza a imagem projetada
            arcade.draw_texture_rect(
                tex,
                arcade.XYWH(w / 2, h / 2, render_w, render_h),
            )

            # Borda com acabamento elegante
            arcade.draw_rect_outline(
                arcade.XYWH(w / 2, h / 2, render_w, render_h),
                (180, 150, 90, 180),
                2,
            )
        else:
            err_txt = self._get_cached_text(
                "proj_err",
                "Imagem não encontrada ou formato inválido.",
                w / 2,
                h / 2,
                (230, 80, 80, 255),
                14,
                bold=True,
            )
            err_txt.draw()

    # --- 3. ESTADO COMBAT (MAPA + TOKENS VISÍVEIS + INITIATIVE HUD NO TOPO) ---

    def _calculate_combat_layout(
        self, w: float, h: float
    ) -> Optional[Tuple[float, float, float, float, float, float, int, int]]:
        """
        Calcula o layout de enquadramento do mapa de combate e dimensões das células.
        Retorna (draw_x, draw_y, draw_w, draw_h, cell_w, cell_h, columns, rows) ou None.
        """
        combat_manager = self.session_manager.combat_manager
        grid_mgr = combat_manager.grid_manager
        if grid_mgr is None or grid_mgr.columns <= 0 or grid_mgr.rows <= 0:
            return None

        world_w = grid_mgr.map_width
        world_h = grid_mgr.map_height
        if world_w <= 0 or world_h <= 0:
            return None

        # Enquadramento Aspect-Fill (100% da viewport preenchida sem distorção anamórfica nem barras pretas)
        scale = max(float(w) / world_w, float(h) / world_h)
        draw_w = world_w * scale
        draw_h = world_h * scale

        # Centraliza o mapa simetricamente na tela dos jogadores
        draw_x = (float(w) - draw_w) / 2.0
        draw_y = (float(h) - draw_h) / 2.0

        cell_w = draw_w / grid_mgr.columns
        cell_h = draw_h / grid_mgr.rows

        return draw_x, draw_y, draw_w, draw_h, cell_w, cell_h, grid_mgr.columns, grid_mgr.rows

    def _update_tokens(self, delta_time: float) -> None:
        """
        Sincroniza os alvos dos tokens com o CombatManager e executa a interpolação suave (Lerp).
        Quando o Mestre atualiza a posição no grid, apenas target_x e target_y são atualizados.
        """
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

            target_x = draw_x + (px + 0.5) * cell_w
            target_y = draw_y + (py + 0.5) * cell_h
            is_player = isinstance(combatant, PlayableCharacter)

            if combatant.uid not in self.token_sprites:
                # Novo token: inicializa imediatamente no destino
                token = CombatToken(
                    uid=combatant.uid,
                    name=combatant.name,
                    is_player=is_player,
                    target_x=target_x,
                    target_y=target_y,
                )
                self.token_sprites[combatant.uid] = token
            else:
                token = self.token_sprites[combatant.uid]
                token.name = combatant.name
                token.is_player = is_player
                # Atualiza APENAS as coordenadas alvo (target_x, target_y)
                token.target_x = target_x
                token.target_y = target_y

            # Executa a interpolação Lerp a cada frame
            if delta_time > 0:
                token.update_lerp(delta_time)

        # Remove tokens de entidades que saíram do combate
        for uid in list(self.token_sprites.keys()):
            if uid not in active_uids:
                del self.token_sprites[uid]

    def _draw_combat_screen(self, w: int, h: int) -> None:
        """
        Renderiza o mapa de combate na tela dos jogadores com a PlayerCamera,
        mantendo a proporção exata e o Grid Tático de alto contraste idênticos à DMWindow,
        desenhando os tokens dos participantes VISÍVEIS com interpolação suave e a Fila de Iniciativas no topo.
        """
        combat_manager = self.session_manager.combat_manager
        map_path = getattr(combat_manager, "map_file", getattr(combat_manager, "map_image_path", None))
        tex = self._get_texture(map_path)

        layout = self._calculate_combat_layout(w, h)
        if layout is None:
            return

        draw_x, draw_y, draw_w, draw_h, cell_w, cell_h, cols, rows = layout

        # Fundo escuro da tela
        arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), (14, 18, 24, 255))

        # 1. Mapa de Fundo (TileMap Modular em GPU ou Textura Única sem distorção)
        tile_map = combat_manager.tile_map
        if tile_map is not None:
            if self._tilemap_renderer is None or self._tilemap_renderer.tile_map != tile_map:
                self._tilemap_renderer = TileMapRenderer(tile_map=tile_map, grid_manager=combat_manager.grid_manager)
            self._tilemap_renderer.update_layout(draw_x, draw_y, cell_w, cell_h)
            self._tilemap_renderer.draw(pixelated=True)
            arcade.draw_rect_outline(
                arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h),
                (60, 80, 110, 220),
                1.5,
            )
        elif tex is not None:
            arcade.draw_texture_rect(
                tex,
                arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h),
            )
            arcade.draw_rect_outline(
                arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h),
                (60, 80, 110, 220),
                1.5,
            )
        else:
            arcade.draw_rect_filled(
                arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h),
                (24, 32, 28, 255),
            )
            arcade.draw_rect_outline(
                arcade.XYWH(draw_x + draw_w / 2, draw_y + draw_h / 2, draw_w, draw_h),
                (60, 80, 110, 220),
                1.5,
            )

        # 2. Linhas do Grid Tático de ALTO CONTRASTE (Luminous Steel Cyan) na Tela dos Jogadores
        grid_color = (130, 205, 255, 175)

        for c in range(cols + 1):
            gx = draw_x + c * cell_w
            arcade.draw_line(gx, draw_y, gx, draw_y + draw_h, grid_color, 1.2)

        for r in range(rows + 1):
            gy = draw_y + r * cell_h
            arcade.draw_line(draw_x, gy, draw_x + draw_w, gy, grid_color, 1.2)

        # Sincroniza posições alvo se ainda não sincronizadas
        self._update_tokens(0.0)

        # 3. Renderização de Tokens das Entidades VISÍVEIS
        active_combatant = combat_manager.active_character

        for combatant in combat_manager.combatants:
            # Regra de Visibilidade Tática: Entidades ocultas NÃO são renderizadas na tela dos jogadores!
            if combatant.is_hidden:
                continue

            token = self.token_sprites.get(combatant.uid)
            if token is not None:
                cx = token.center_x
                cy = token.center_y
            else:
                pos = combatant.position
                px = pos.get("x", 0)
                py = pos.get("y", 0)
                cx = draw_x + (px + 0.5) * cell_w
                cy = draw_y + (py + 0.5) * cell_h

            is_player = isinstance(combatant, PlayableCharacter)
            is_active = (combatant == active_combatant)
            token_radius = (min(cell_w, cell_h) * 0.88) / 2.0

            SpriteFactory.draw_tactical_token(
                name=combatant.name,
                is_player=is_player,
                x=cx,
                y=cy,
                radius=token_radius,
                is_alive=combatant.is_alive,
                is_hidden=False,
                is_selected=False,
                is_active=is_active,
                text_cache=self._text_cache,
                token_key=combatant.uid,
            )

        # 4. Fila de Iniciativas como Overlay Flutuante Translúcido no Topo da Tela
        self.hud.draw(w, h)

    def on_update(self, delta_time: float) -> None:
        """Ciclo de atualização: animação IDLE e interpolação suave de tokens em COMBAT."""
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
            self._update_tokens(delta_time)

        elif current_state == DisplayState.PROJECTION:
            if self.token_sprites:
                self.token_sprites.clear()

        if self.dm_window is not None and hasattr(self.dm_window, "pump_events"):
            try:
                self.dm_window.pump_events()
            except Exception:
                pass

