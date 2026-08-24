import math
import time
from typing import Optional, List, Dict
import arcade
from ..manager.combat_manager import CombatManager
from ..domain.models.playablechar import PlayableCharacter
from ..domain.models.monster import Monster
from ..domain.models.entity import Entity


class InitiativeHUD:
    """
    Componente HUD de Fila de Iniciativa para a Tela dos Jogadores (PlayerWindow).
    Renderiza os tokens redondos (badges) fixados no topo do mapa, com:
      - 4 primeiras letras do nome do participante.
      - Cores distintas: Azul para Jogadores, Vermelho para Monstros.
      - Destaque visual (Glow / Highlight Dourado) com pulso para o turno ativo.
      - Mini badge com valor de iniciativa e indicador de HP.
    """

    def __init__(self, combat_manager: CombatManager) -> None:
        self.combat_manager = combat_manager
        self._text_cache: Dict[str, arcade.Text] = {}

    def _get_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool = True,
    ) -> arcade.Text:
        """Cache e atualização de objetos arcade.Text para alta performance."""
        cached = self._text_cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x="center",
                anchor_y="center",
                font_name=("Consolas", "Calibri", "Arial"),
            )
            self._text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
        return cached

    def draw(self, screen_width: int, screen_height: int) -> None:
        turn_order: List[Entity] = self.combat_manager.turn_order
        if not turn_order:
            return

        hud_height = 80
        center_y = screen_height - 45
        spacing = 80
        total_width = (len(turn_order) - 1) * spacing
        start_x = (screen_width - total_width) / 2

        # 1. Fundo translúcido do HUD (Glassmorphism Ribbon)
        ribbon_w = max(screen_width * 0.9, total_width + 120)
        ribbon_left = (screen_width - ribbon_w) / 2
        arcade.draw_rect_filled(
            arcade.XYWH(screen_width / 2, screen_height - 45, ribbon_w, hud_height),
            (15, 20, 30, 210),
        )
        arcade.draw_rect_outline(
            arcade.XYWH(screen_width / 2, screen_height - 45, ribbon_w, hud_height),
            (60, 75, 100, 180),
            1,
        )

        current_time = time.time()
        pulse = math.sin(current_time * 4.0) * 2.5

        active_combatant = self.combat_manager.active_character
        active_index = self.combat_manager.current_turn_index

        for idx, combatant in enumerate(turn_order):
            cx = start_x + idx * spacing
            cy = center_y
            is_active = (combatant == active_combatant) or (idx == active_index)

            # 2. Definição do Tipo e Paleta de Cores
            is_player = isinstance(combatant, PlayableCharacter)
            is_alive = combatant.is_alive

            if not is_alive:
                fill_color = (55, 60, 68, 230)
                border_color = (120, 120, 130, 255)
                text_color = (180, 180, 180, 255)
            elif is_player:
                fill_color = (25, 118, 210, 240)  # Azul Vibrante
                border_color = (100, 200, 255, 255)
                text_color = (255, 255, 255, 255)
            else:
                fill_color = (183, 28, 28, 240)   # Vermelho Carmim
                border_color = (255, 138, 128, 255)
                text_color = (255, 255, 255, 255)

            radius = 26
            if is_active:
                radius = 29
                cy += 2

            # 3. Destaque Visual (Glow / Highlight Dourado) para o Turno Ativo
            if is_active and is_alive:
                glow_radius = radius + 8 + pulse
                # Halo externo
                arcade.draw_circle_filled(
                    cx, cy, glow_radius, (255, 215, 0, 70)
                )
                # Anel de pulso
                arcade.draw_circle_outline(
                    cx, cy, radius + 5 + pulse * 0.5, (255, 235, 59, 220), 2
                )
                border_color = (255, 215, 0, 255)

                # Marcador "ATIVO" / Triângulo Dourado sobre o badge
                arrow_y = cy + radius + 7
                arcade.draw_triangle_filled(
                    cx - 5, arrow_y + 6,
                    cx + 5, arrow_y + 6,
                    cx, arrow_y,
                    (255, 215, 0, 255)
                )

            # 4. Desenha o Token Redondo
            # Sombra suave
            arcade.draw_circle_filled(cx, cy - 2, radius + 1, (0, 0, 0, 120))
            # Preenchimento
            arcade.draw_circle_filled(cx, cy, radius, fill_color)
            # Borda
            border_width = 3 if is_active else 2
            arcade.draw_circle_outline(cx, cy, radius, border_color, border_width)

            # 5. Texto com as 4 primeiras letras do nome (ex: BOLO, KOB1, CULT)
            short_name = combatant.name.strip()[:4].upper()
            txt_obj = self._get_text(
                f"token_txt_{combatant.uid}_{idx}",
                short_name,
                cx,
                cy + 1,
                text_color,
                11 if len(short_name) <= 4 else 9,
                bold=True,
            )
            txt_obj.draw()

            # 6. Mini Badge com a Iniciativa (Abaixo do Token)
            init_val = combatant.initiative_score
            init_badge_y = cy - radius - 2
            arcade.draw_circle_filled(cx, init_badge_y, 9, (20, 24, 33, 240))
            arcade.draw_circle_outline(cx, init_badge_y, 9, (255, 215, 0, 200), 1)
            init_txt = self._get_text(
                f"token_init_{combatant.uid}_{idx}",
                str(init_val),
                cx,
                init_badge_y,
                (255, 215, 0, 255),
                8,
                bold=True,
            )
            init_txt.draw()

            # 7. Marcador de Morte se abatido
            if not is_alive:
                arcade.draw_line(
                    cx - 14, cy - 14, cx + 14, cy + 14, (244, 67, 54, 255), 3
                )
                arcade.draw_line(
                    cx - 14, cy + 14, cx + 14, cy - 14, (244, 67, 54, 255), 3
                )
