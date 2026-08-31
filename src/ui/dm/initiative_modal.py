from typing import Dict, Optional, Callable
import arcade
from ...manager.session_manager import SessionManager
from ...domain.models.playablechar import PlayableCharacter


class InitiativeStagingModal:
    """
    Componente do Modal de Staging de Iniciativas (D&D 5E).
    Permite rolagem prévia, ajustes manuais finos via steppers [-] [+] e confirmação.
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.is_open: bool = False
        self.draft_initiatives: Dict[str, int] = {}
        self.text_cache: Dict[str, arcade.Text] = {}

    def open(self) -> None:
        """Abre o modal gerando uma rolagem preliminar de iniciativas sem alterar o combate."""
        self.draft_initiatives = self.combat_manager.generate_draft_initiatives()
        self.is_open = True

    def close(self) -> None:
        """Fecha o modal de staging."""
        self.is_open = False

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
        cached = self.text_cache.get(key)
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
            self.text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
        return cached

    def draw(self, w: float, h: float) -> None:
        """Desenha o overlay e o painel do modal de staging."""
        if not self.is_open:
            return

        # Fundo escuro translúcido
        arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), (0, 0, 0, 180))

        modal_w = 540
        modal_h = 440
        modal_cx = w / 2
        modal_cy = h / 2

        # Caixa do Modal
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (20, 25, 35, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (241, 196, 15, 255), 2)

        # Cabeçalho do Modal
        self._get_text("mod_title", "🎲 STAGING DE INICIATIVAS (D&D 5E)", modal_cx, modal_cy + modal_h / 2 - 26, (241, 196, 15, 255), 13, bold=True, anchor_x="center").draw()
        self._get_text("mod_sub", "Ajuste os valores rolados manualmente antes de iniciar a rodada:", modal_cx, modal_cy + modal_h / 2 - 50, (180, 190, 205, 255), 9, bold=False, anchor_x="center").draw()

        # Lista de Participantes e Scores
        combatants = self.combat_manager.combatants
        list_y = modal_cy + modal_h / 2 - 70
        row_h = 36

        for idx, combatant in enumerate(combatants[:6]):
            ry = list_y - idx * (row_h + 4) - row_h / 2
            arcade.draw_rect_filled(arcade.XYWH(modal_cx, ry, modal_w - 40, row_h), (30, 38, 52, 255))
            arcade.draw_rect_outline(arcade.XYWH(modal_cx, ry, modal_w - 40, row_h), (50, 65, 90, 200), 1)

            name_c = (100, 200, 255, 255) if isinstance(combatant, PlayableCharacter) else (255, 138, 128, 255)
            self._get_text(f"mod_n_{idx}", combatant.name[:18], modal_cx - modal_w / 2 + 35, ry, name_c, 10, bold=True, anchor_x="left").draw()

            mod_s = f"DEX: +{combatant.initiative_mod}" if combatant.initiative_mod >= 0 else f"DEX: {combatant.initiative_mod}"
            self._get_text(f"mod_m_{idx}", mod_s, modal_cx + 40, ry, (160, 175, 195, 255), 9, bold=False, anchor_x="center").draw()

            # Steppers de Ajuste [-] [Score] [+]
            score_val = self.draft_initiatives.get(combatant.uid, 10)

            # Botão [-]
            btn_minus_x = modal_cx + 120
            arcade.draw_rect_filled(arcade.XYWH(btn_minus_x, ry, 26, 24), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(btn_minus_x, ry, 26, 24), (70, 90, 120, 200), 1)
            self._get_text(f"mod_bm_{idx}", "[-]", btn_minus_x, ry, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Caixa do Valor
            val_x = modal_cx + 160
            arcade.draw_rect_filled(arcade.XYWH(val_x, ry, 40, 24), (15, 20, 28, 255))
            arcade.draw_rect_outline(arcade.XYWH(val_x, ry, 40, 24), (241, 196, 15, 200), 1)
            self._get_text(f"mod_val_{idx}", str(score_val), val_x, ry, (255, 255, 255, 255), 10, bold=True, anchor_x="center").draw()

            # Botão [+]
            btn_plus_x = modal_cx + 200
            arcade.draw_rect_filled(arcade.XYWH(btn_plus_x, ry, 26, 24), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(btn_plus_x, ry, 26, 24), (70, 90, 120, 200), 1)
            self._get_text(f"mod_bp_{idx}", "[+]", btn_plus_x, ry, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

        # Botões de Ação do Modal
        btn_y = modal_cy - modal_h / 2 + 40

        # Rolar Novamente
        arcade.draw_rect_filled(arcade.XYWH(modal_cx - 160, btn_y, 110, 34), (142, 68, 173, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx - 160, btn_y, 110, 34), (155, 89, 182, 255), 1)
        self._get_text("mod_b_reroll", "🎲 Rolar de Novo", modal_cx - 160, btn_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

        # Cancelar
        arcade.draw_rect_filled(arcade.XYWH(modal_cx - 40, btn_y, 90, 34), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx - 40, btn_y, 90, 34), (231, 76, 60, 255), 1)
        self._get_text("mod_b_cancel", "❌ Cancelar", modal_cx - 40, btn_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

        # Confirmar e Iniciar Combate
        arcade.draw_rect_filled(arcade.XYWH(modal_cx + 120, btn_y, 190, 34), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx + 120, btn_y, 190, 34), (46, 204, 113, 255), 2)
        self._get_text("mod_b_confirm", "✅ Confirmar & Iniciar", modal_cx + 120, btn_y, (255, 255, 255, 255), 10, bold=True, anchor_x="center").draw()

    def handle_click(self, x: float, y: float, w: float, h: float, on_confirmed_callback: Optional[Callable[[], None]] = None) -> bool:
        """Processa cliques no modal de staging de iniciativas."""
        if not self.is_open:
            return False

        modal_w = 540
        modal_h = 440
        modal_cx = w / 2
        modal_cy = h / 2

        # 1. Cliques nos Steppers [-] [+] dos Combatentes
        combatants = self.combat_manager.combatants
        list_y = modal_cy + modal_h / 2 - 70
        row_h = 36

        for idx, combatant in enumerate(combatants[:6]):
            ry = list_y - idx * (row_h + 4) - row_h / 2
            if abs(y - ry) <= 12:
                btn_minus_x = modal_cx + 120
                btn_plus_x = modal_cx + 200

                # Decrementar [-]
                if abs(x - btn_minus_x) <= 13:
                    cur = self.draft_initiatives.get(combatant.uid, 10)
                    self.draft_initiatives[combatant.uid] = max(1, cur - 1)
                    return True

                # Incrementar [+]
                if abs(x - btn_plus_x) <= 13:
                    cur = self.draft_initiatives.get(combatant.uid, 10)
                    self.draft_initiatives[combatant.uid] = cur + 1
                    return True

        btn_y = modal_cy - modal_h / 2 + 40

        # Rolar Novamente
        if abs(y - btn_y) <= 17 and abs(x - (modal_cx - 160)) <= 55:
            self.draft_initiatives = self.combat_manager.generate_draft_initiatives()
            return True

        # Cancelar
        if abs(y - btn_y) <= 17 and abs(x - (modal_cx - 40)) <= 45:
            self.close()
            return True

        # Confirmar e Iniciar Combate
        if abs(y - btn_y) <= 17 and abs(x - (modal_cx + 120)) <= 95:
            self.combat_manager.apply_initiatives(self.draft_initiatives)
            self.close()
            if on_confirmed_callback:
                on_confirmed_callback()
            return True

        return True
