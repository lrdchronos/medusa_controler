import math
import os
import time
from typing import Optional, Dict, Any
import arcade
from ..manager.session_manager import SessionManager, DisplayState
from .initiative_hud import InitiativeHUD


class PlayerWindow(arcade.Window):
    """
    Tela dos Jogadores (Player Screen) do Medusa VTT.
    Implementa a Máquina de Estados de Exibição (DisplayState):
      1. IDLE: Tela de descanso/espera imersiva ("Aguardando o Mestre...").
      2. PROJECTION: Projeção de imagens avulsas (NPCs, cenários, itens) com Aspect Ratio Fit (Contain).
      3. COMBAT: Renderização do mapa limpo do encontro (sem tokens sobre o mapa)
                 com a fita de iniciativas (InitiativeHUD) no topo.
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
        self.session_manager = session_manager
        self.dm_window = dm_window
        self.hud = InitiativeHUD(session_manager.combat_manager)

        self._texture_cache: Dict[str, arcade.Texture] = {}
        self._text_cache: Dict[str, arcade.Text] = {}

    def _get_texture(self, file_path: Optional[str]) -> Optional[arcade.Texture]:
        """Carrega e armazena em cache texturas de imagens."""
        if not file_path or not os.path.isfile(file_path):
            return None
        resolved = str(os.path.abspath(file_path))
        if resolved not in self._texture_cache:
            try:
                self._texture_cache[resolved] = arcade.load_texture(resolved)
            except Exception as e:
                print(f"[PlayerWindow] Erro ao carregar textura '{resolved}': {e}")
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

    def on_draw(self) -> None:
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

        pulse = math.sin(time.time() * 2.5) * 4.0
        center_x = w / 2
        center_y = h / 2 + 30

        # Brasão / Sigil místico central
        arcade.draw_circle_filled(center_x, center_y, 75 + pulse * 0.5, (241, 196, 15, 20))
        arcade.draw_circle_outline(center_x, center_y, 70, (212, 172, 13, 160), 2)
        arcade.draw_circle_outline(center_x, center_y, 82 + pulse, (241, 196, 15, 80), 1)

        # Geometria do Sigil
        arcade.draw_line(center_x - 50, center_y, center_x + 50, center_y, (212, 172, 13, 120), 1)
        arcade.draw_line(center_x, center_y - 50, center_x, center_y + 50, (212, 172, 13, 120), 1)
        arcade.draw_rect_outline(arcade.XYWH(center_x, center_y, 50, 50), (241, 196, 15, 140), 1)

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

    # --- 3. ESTADO COMBAT (MAPA LIMPO + INITIATIVE HUD NO TOPO) ---

    def _draw_combat_screen(self, w: int, h: int) -> None:
        """
        Renderiza o mapa de combate limpo na área central (sem tokens no meio do mapa)
        e a Fila de Iniciativas exclusivamente fixada no topo da tela.
        """
        combat_manager = self.session_manager.combat_manager
        map_path = combat_manager.map_file
        tex = self._get_texture(map_path)

        if tex is not None:
            # Renderiza o mapa de fundo limpo ocupando a tela
            arcade.draw_texture_rect(
                tex,
                arcade.XYWH(w / 2, h / 2, w, h),
            )
        else:
            # Fallback de grid procedural tático
            arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), (24, 32, 28, 255))
            for x in range(0, w, 50):
                arcade.draw_line(x, 0, x, h, (40, 52, 45, 120), 1)
            for y in range(0, h, 50):
                arcade.draw_line(0, y, w, y, (40, 52, 45, 120), 1)

        # Renderiza a Fila de Iniciativas EXCLUSIVAMENTE no Topo da Tela
        self.hud.draw(w, h)

        # Banner Inferior Informativo
        self._draw_bottom_banner(w, h)

    def _draw_bottom_banner(self, w: int, h: int) -> None:
        """Exibe o rodapé com informações do encontro, rodada e combatente ativo."""
        banner_h = 36
        arcade.draw_rect_filled(
            arcade.XYWH(w / 2, banner_h / 2, w, banner_h),
            (10, 14, 20, 230),
        )
        arcade.draw_line(0, banner_h, w, banner_h, (40, 50, 70, 180), 1)

        combat_manager = self.session_manager.combat_manager
        active = combat_manager.active_character
        if active:
            active_info = f"Turno Ativo: {active.name} | HP: {active.current_hp}/{active.max_hp} | CA: {active.armor_class}"
        else:
            active_info = "Aguardando início do combate (Clique em 'Rolar Iniciativas' no Mestre)"

        banner_text_str = f"⚔️ {combat_manager.title} • Rodada {combat_manager.round_number} • {active_info}"

        txt = self._get_cached_text(
            "combat_banner",
            banner_text_str,
            20,
            banner_h / 2,
            (240, 240, 245, 255),
            11,
            bold=True,
            anchor_x="left",
            anchor_y="center",
        )
        txt.draw()

    def on_update(self, delta_time: float) -> None:
        """Ciclo de atualização: bombeia eventos da janela do Mestre."""
        if self.dm_window is not None:
            self.dm_window.pump_events()
