import math
import os
from typing import Optional, Dict, Any
import arcade
from ..manager.combat_manager import CombatManager
from .initiative_hud import InitiativeHUD
from ..domain.models.playablechar import PlayableCharacter
from ..domain.models.monster import Monster


class PlayerWindow(arcade.Window):
    """
    Tela dos Jogadores (Player Screen) do Medusa VTT.
    Renderiza o mapa de fundo em alta definição, posiciona tokens no grid
    e exibe o InitiativeHUD no topo da tela com sincronização contínua.
    """

    def __init__(
        self,
        combat_manager: CombatManager,
        dm_window: Optional[Any] = None,
        width: int = 1024,
        height: int = 768,
        title: str = "Medusa VTT - Tela dos Jogadores",
    ) -> None:
        super().__init__(width, height, title, resizable=True)
        self.combat_manager = combat_manager
        self.dm_window = dm_window
        self.hud = InitiativeHUD(combat_manager)

        self.map_texture: Optional[arcade.Texture] = None
        self._load_map_texture()

        # Grid settings
        self.grid_size = 50
        self.grid_origin_x = 80
        self.grid_origin_y = 120

        # Text labels
        self._title_text: Optional[arcade.Text] = None
        self._banner_text: Optional[arcade.Text] = None
        self._token_texts: Dict[str, arcade.Text] = {}

    def _load_map_texture(self) -> None:
        map_path = self.combat_manager.map_file
        if map_path and os.path.isfile(map_path):
            try:
                self.map_texture = arcade.load_texture(map_path)
            except Exception as e:
                print(f"[PlayerWindow] Erro ao carregar textura do mapa '{map_path}': {e}")
                self.map_texture = None

    def on_draw(self) -> None:
        self.clear()

        w, h = self.width, self.height

        # 1. Renderiza o Mapa de Fundo ou Grid Procedural
        if self.map_texture:
            arcade.draw_texture_rect(
                self.map_texture,
                arcade.XYWH(w / 2, h / 2, w, h),
            )
        else:
            self._draw_procedural_background(w, h)

        # 2. Renderiza Tokens dos Combatentes no Grid do Mapa
        self._draw_combatants_on_map()

        # 3. Renderiza o InitiativeHUD no Topo
        self.hud.draw(w, h)

        # 4. Renderiza Banner Informativo Inferior (Rodada e Turno Ativo)
        self._draw_bottom_banner(w, h)

    def _draw_procedural_background(self, w: int, h: int) -> None:
        """Desenha um fundo tático estilizado caso a imagem do mapa não esteja disponível."""
        arcade.draw_rect_filled(
            arcade.XYWH(w / 2, h / 2, w, h),
            (24, 32, 28, 255),
        )
        # Grid lines
        for x in range(0, w, 50):
            arcade.draw_line(x, 0, x, h, (40, 52, 45, 120), 1)
        for y in range(0, h, 50):
            arcade.draw_line(0, y, w, y, (40, 52, 45, 120), 1)

    def _draw_combatants_on_map(self) -> None:
        """Desenha os tokens dos combatentes em suas posições (x, y) no grid tático."""
        active = self.combat_manager.active_character

        for combatant in self.combat_manager.combatants:
            pos = combatant.position
            gx = self.grid_origin_x + pos.get("x", 0) * self.grid_size
            gy = self.grid_origin_y + pos.get("y", 0) * self.grid_size

            is_active = combatant == active
            is_player = isinstance(combatant, PlayableCharacter)
            is_alive = combatant.is_alive

            token_r = 18
            if is_active:
                token_r = 21
                # Golden glow no mapa
                arcade.draw_circle_filled(gx, gy, token_r + 6, (255, 215, 0, 90))
                arcade.draw_circle_outline(gx, gy, token_r + 4, (255, 235, 59, 230), 2)

            if not is_alive:
                color = (60, 60, 65, 200)
                border = (120, 120, 120, 255)
            elif is_player:
                color = (30, 136, 229, 230)
                border = (100, 200, 255, 255)
            else:
                color = (198, 40, 40, 230)
                border = (255, 138, 128, 255)

            arcade.draw_circle_filled(gx, gy, token_r, color)
            arcade.draw_circle_outline(gx, gy, token_r, border, 2)

            # Mini nome
            initials = combatant.name[:3].upper()
            t_key = f"map_tok_{combatant.uid}"
            t_obj = self._token_texts.get(t_key)
            if t_obj is None or t_obj.text != initials:
                t_obj = arcade.Text(
                    text=initials,
                    x=gx,
                    y=gy,
                    color=(255, 255, 255, 255),
                    font_size=8,
                    bold=True,
                    anchor_x="center",
                    anchor_y="center",
                )
                self._token_texts[t_key] = t_obj
            else:
                t_obj.x = gx
                t_obj.y = gy
            t_obj.draw()

    def _draw_bottom_banner(self, w: int, h: int) -> None:
        """Exibe o rodapé com informações do encontro e rodada."""
        banner_h = 36
        arcade.draw_rect_filled(
            arcade.XYWH(w / 2, banner_h / 2, w, banner_h),
            (10, 14, 20, 220),
        )
        arcade.draw_line(0, banner_h, w, banner_h, (40, 50, 70, 180), 1)

        active = self.combat_manager.active_character
        if active:
            active_info = f"Turno Ativo: {active.name} | HP: {active.current_hp}/{active.max_hp} | CA: {active.armor_class}"
        else:
            active_info = "Aguardando início do combate (Clique em 'Rolar Iniciativas' no Mestre)"

        banner_text_str = f"⚔️ {self.combat_manager.title} • Rodada {self.combat_manager.round_number} • {active_info}"

        if self._banner_text is None or self._banner_text.text != banner_text_str:
            self._banner_text = arcade.Text(
                text=banner_text_str,
                x=20,
                y=banner_h / 2,
                color=(240, 240, 245, 255),
                font_size=11,
                bold=True,
                anchor_x="left",
                anchor_y="center",
                font_name=("Consolas", "Calibri", "Arial"),
            )
        self._banner_text.draw()

    def on_update(self, delta_time: float) -> None:
        """Ciclo de atualização: bombeia eventos da janela do Mestre se acoplada."""
        if self.dm_window is not None:
            self.dm_window.pump_events()
