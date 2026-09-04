import math
import time
import logging
from typing import Optional, List, Dict, Tuple
import arcade
from ..manager.combat_manager import CombatManager
from ..domain.models.playablechar import PlayableCharacter
from ..domain.models.monster import Monster
from ..domain.models.entity import Entity

logger = logging.getLogger(__name__)


class InitiativeHUD:
    """
    Componente HUD de Fila de Iniciativa para a Tela dos Jogadores (PlayerWindow).
    Renderiza os tokens redondos (badges) fixados no topo do mapa, com:
      - 4 primeiras letras do nome do participante.
      - Cores distintas: Azul para Jogadores, Vermelho para Monstros.
      - Destaque visual (Glow / Highlight Dourado) com pulso para o turno ativo.
      - Mini badge com valor de iniciativa e indicador de HP.
      - Janela deslizante (Sliding Window) com indicadores de overflow para listas grandes de combatentes.
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
            cached.text = text
        return cached

    def get_visible_window(self, screen_width: int, spacing: float = 80.0) -> Tuple[int, int, List[Entity], bool, bool]:
        """
        Calcula a fatia da janela deslizante (start_idx, end_idx, visible_entities, has_prev, has_next)
        com base na largura útil da tela e na posição do combatente do turno ativo.
        """
        turn_order = [c for c in self.combat_manager.turn_order if not c.is_hidden]
        if not turn_order:
            return (0, 0, [], False, False)

        max_visible = max(3, int((screen_width - 160) // spacing))
        active_combatant = self.combat_manager.active_character

        if len(turn_order) > max_visible:
            active_idx = 0
            if active_combatant and active_combatant in turn_order:
                active_idx = turn_order.index(active_combatant)

            half = max_visible // 2
            start_idx = active_idx - half
            if start_idx + max_visible > len(turn_order):
                start_idx = len(turn_order) - max_visible
            if start_idx < 0:
                start_idx = 0
            end_idx = min(len(turn_order), start_idx + max_visible)
            visible_turn_order = turn_order[start_idx:end_idx]
            return (start_idx, end_idx, visible_turn_order, start_idx > 0, end_idx < len(turn_order))
        else:
            return (0, len(turn_order), turn_order, False, False)

    def draw(self, screen_width: int, screen_height: int) -> None:
        # Regra de Ocultação Tática: criaturas ocultas não aparecem no HUD dos jogadores
        spacing = 80.0
        start_idx, end_idx, visible_turn_order, has_prev, has_next = self.get_visible_window(screen_width, spacing)
        if not visible_turn_order:
            return

        total_in_order = len([c for c in self.combat_manager.turn_order if not c.is_hidden])
        prev_count = start_idx
        next_count = total_in_order - end_idx

        hud_height = 80
        center_y = screen_height - 45
        total_width = (len(visible_turn_order) - 1) * spacing
        start_x = (screen_width - total_width) / 2

        # 1. Overlay Flutuante Translúcido (Floating Transparent Capsule)
        extra_w = 120 if (has_prev or has_next) else 80
        capsule_w = total_width + extra_w
        capsule_h = 76
        arcade.draw_rect_filled(
            arcade.XYWH(screen_width / 2, center_y - 2, capsule_w, capsule_h),
            (10, 14, 20, 140),
        )
        arcade.draw_rect_outline(
            arcade.XYWH(screen_width / 2, center_y - 2, capsule_w, capsule_h),
            (60, 80, 110, 90),
            1,
        )

        # Indicador de Overflow à Esquerda (◀ +N)
        if has_prev:
            prev_x = start_x - 50
            arcade.draw_rect_filled(arcade.XYWH(prev_x, center_y, 36, 28), (20, 26, 36, 220))
            arcade.draw_rect_outline(arcade.XYWH(prev_x, center_y, 36, 28), (241, 196, 15, 180), 1)
            self._get_text("hud_ovf_left", f"◀+{prev_count}", prev_x, center_y, (241, 196, 15, 255), 8, bold=True).draw()

        # Indicador de Overflow à Direita (+N ▶)
        if has_next:
            next_x = start_x + (len(visible_turn_order) - 1) * spacing + 50
            arcade.draw_rect_filled(arcade.XYWH(next_x, center_y, 36, 28), (20, 26, 36, 220))
            arcade.draw_rect_outline(arcade.XYWH(next_x, center_y, 36, 28), (241, 196, 15, 180), 1)
            self._get_text("hud_ovf_right", f"+{next_count}▶", next_x, center_y, (241, 196, 15, 255), 8, bold=True).draw()

        current_time = time.time()
        pulse = math.sin(current_time * 4.0) * 2.5

        active_combatant = self.combat_manager.active_character

        for idx, combatant in enumerate(visible_turn_order):
            actual_idx = start_idx + idx
            cx = start_x + idx * spacing
            cy = center_y
            is_active = (combatant == active_combatant)

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
            # Borda principal
            border_width = 3 if is_active else 2
            arcade.draw_circle_outline(cx, cy, radius, border_color, border_width)

            # Contorno de Vitalidade Semântica para Monstros
            if not is_player and is_alive:
                vit_col = combatant.vitality_color
                arcade.draw_circle_outline(cx, cy, radius - 3, vit_col, 1.5)

            # 5. Texto com as 4 primeiras letras do nome (ex: BOLO, KOB1, CULT)
            short_name = combatant.name.strip()[:4].upper()
            txt_obj = self._get_text(
                f"token_txt_{combatant.uid}_{actual_idx}",
                short_name,
                cx,
                cy + 1,
                text_color,
                11 if len(short_name) <= 4 else 9,
                bold=True,
            )
            txt_obj.draw()

            # 6. Indicador Semântico de Vida (Health Pip / Badge) no canto inferior direito para Monstros
            if not is_player:
                pip_x = cx + radius * 0.68
                pip_y = cy - radius * 0.68
                pip_r = 6.5

                # Sombra / Contorno externo escuro
                arcade.draw_circle_filled(pip_x, pip_y, pip_r + 1.5, (10, 14, 20, 255))
                arcade.draw_circle_outline(pip_x, pip_y, pip_r + 1.5, (40, 50, 70, 230), 1)

                # Preenchimento com a cor semântica de vitalidade (🟢 >80%, 🟡 30-80%, 🔴 <=30%, 💀 <=0)
                pip_color = combatant.vitality_color
                arcade.draw_circle_filled(pip_x, pip_y, pip_r, pip_color)
                arcade.draw_circle_outline(pip_x, pip_y, pip_r, (255, 255, 255, 140), 1)

                # Brilho / Gloss especular superior
                if is_alive:
                    arcade.draw_circle_filled(pip_x - 1.5, pip_y + 1.5, 1.8, (255, 255, 255, 180))

            # 7. Mini Badge com a Iniciativa (Abaixo do Token)
            init_val = combatant.initiative_score
            init_badge_y = cy - radius - 2
            arcade.draw_circle_filled(cx, init_badge_y, 9, (20, 24, 33, 240))
            arcade.draw_circle_outline(cx, init_badge_y, 9, (255, 215, 0, 200), 1)
            init_txt = self._get_text(
                f"token_init_{combatant.uid}_{actual_idx}",
                str(init_val),
                cx,
                init_badge_y,
                (255, 215, 0, 255),
                8,
                bold=True,
            )
            init_txt.draw()

            # 8. Marcador de Morte se abatido
            if not is_alive:
                arcade.draw_line(
                    cx - 14, cy - 14, cx + 14, cy + 14, (244, 67, 54, 255), 3
                )
                arcade.draw_line(
                    cx - 14, cy + 14, cx + 14, cy - 14, (244, 67, 54, 255), 3
                )

