import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple, Union
import arcade
from ...domain.models.entity import Entity, EntityType, DynamicToken
from ..utils.text_input import SmartTextInput
from ..utils.sprite_utils import SpriteFactory

logger = logging.getLogger(__name__)


class AddTokenModal:
    """
    Modal flutuante para Criação e Inserção Dinâmica de Tokens durante o Combate (Mid-Combat Token Spawning).
    Permite ao Mestre configurar:
      1. Nome do Token (SmartTextInput obrigatório).
      2. Tipo de Entidade (Jogador, Monstro, Neutro/Magia).
      3. HP Máximo/Inicial e Classe de Armadura (CA).
      4. Inserção na Iniciativa ('next' = Próximo a Jogar, 'end' = Final da Rodada).
      5. Seleção de Textura / Arte de Token (com fallback para badge circular procedural).
      6. Confirmação para transicionar o Mini-Mapa para o modo de posicionamento (PLACING_TOKEN).
    """

    def __init__(self, on_confirm: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.on_confirm: Optional[Callable[[Dict[str, Any]], None]] = on_confirm
        self.is_open: bool = False

        # Configurações do Token
        self.name_input: SmartTextInput = SmartTextInput(
            widget_id="modal_tkn_name",
            placeholder="Nome (ex: Arma Espiritual, Reforço 1...)",
            initial_text="",
            max_length=40,
            font_size=9,
            padding_left=8.0,
        )
        self.selected_type: EntityType = EntityType.NEUTRAL
        self.hp_value: int = 1
        self.ac_value: int = 10
        self.initiative_slot: str = "next"  # "next" ou "end"
        self.selected_sprite_path: Optional[str] = None

        # Lista de assets de tokens disponíveis
        self.available_sprites: List[str] = []
        self.selected_sprite_idx: int = 0
        self.text_cache: Dict[str, arcade.Text] = {}
        self.validation_error: Optional[str] = None

        self._refresh_available_sprites()

    def _refresh_available_sprites(self) -> None:
        """Varre a pasta assets/sprites/tokens/ para listar texturas disponíveis."""
        tokens_dir = Path("assets/sprites/tokens")
        try:
            tokens_dir.mkdir(parents=True, exist_ok=True)
            files = [str(f) for f in tokens_dir.glob("*.png")] + [str(f) for f in tokens_dir.glob("*.jpg")]
            self.available_sprites = ["procedural"] + sorted(files)
        except Exception as e:
            logger.debug(f"Aviso ao varrer pasta de tokens: {e}")
            self.available_sprites = ["procedural"]
        self.selected_sprite_idx = 0
        self.selected_sprite_path = None

    def open(self) -> None:
        """Abre o modal redefinindo os campos para os valores padrão."""
        self._refresh_available_sprites()
        self.name_input.clear()
        self.name_input.focus()
        self.selected_type = EntityType.NEUTRAL
        self.hp_value = 1
        self.ac_value = 10
        self.initiative_slot = "next"
        self.selected_sprite_idx = 0
        self.selected_sprite_path = None
        self.validation_error = None
        self.is_open = True
        logger.info("Modal AddTokenModal aberto.")

    def close(self) -> None:
        """Fecha o modal."""
        self.is_open = False
        self.name_input.blur()
        self.validation_error = None
        logger.info("Modal AddTokenModal fechado.")

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
            cached.text = text
        return cached

    def draw(self, screen_w: float, screen_h: float) -> None:
        """Desenha o backdrop e o diálogo centralizado Dark Fantasy."""
        if not self.is_open:
            return

        # 1. Backdrop escuro translúcido cobrindo a tela inteira
        arcade.draw_rect_filled(arcade.XYWH(screen_w / 2, screen_h / 2, screen_w, screen_h), (0, 0, 0, 190))

        modal_w = min(screen_w - 40, 520.0)
        modal_h = 440.0
        modal_cx = screen_w / 2
        modal_cy = screen_h / 2

        # 2. Caixa do Modal
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (20, 26, 36, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (241, 196, 15, 255), 2.0)

        # 3. Cabeçalho
        hdr_y = modal_cy + modal_h / 2 - 24
        self._get_text("atm_title", "➕ ADICIONAR TOKEN AO COMBATE", modal_cx, hdr_y, (241, 196, 15, 255), 11, bold=True, anchor_x="center").draw()
        sub_y = hdr_y - 18
        self._get_text("atm_sub", "Crie um efeito mágico, invocação ou combatente dinâmico no grid:", modal_cx, sub_y, (170, 185, 205, 255), 8, bold=False, anchor_x="center").draw()
        arcade.draw_line(modal_cx - modal_w / 2 + 16, sub_y - 10, modal_cx + modal_w / 2 - 16, sub_y - 10, (50, 65, 90, 180), 1.0)

        # 4. Campo 1: Nome do Token (SmartTextInput)
        f1_y = sub_y - 32
        self._get_text("atm_lbl_name", "NOME DO TOKEN *", modal_cx - modal_w / 2 + 24, f1_y, (200, 215, 235, 255), 8, bold=True).draw()
        input_w = modal_w - 48
        input_h = 28
        self.name_input.bounds = (modal_cx, f1_y - 20, input_w, input_h)
        self.name_input.draw(modal_cx, f1_y - 20, input_w, input_h, self.text_cache)

        if self.validation_error:
            self._get_text("atm_err", f"⚠️ {self.validation_error}", modal_cx, f1_y - 42, (231, 76, 60, 255), 7.5, bold=True, anchor_x="center").draw()

        # 5. Campo 2: Tipo de Entidade (Jogador, Monstro, Neutro)
        f2_y = f1_y - 60
        self._get_text("atm_lbl_type", "CATEGORIA / ALINHAMENTO TÁTICO", modal_cx - modal_w / 2 + 24, f2_y, (200, 215, 235, 255), 8, bold=True).draw()
        
        btn_type_w = (modal_w - 56) / 3
        btn_type_h = 28
        btn_type_y = f2_y - 20

        # [ 👤 Jogador ]
        b_p_x = modal_cx - modal_w / 2 + 24 + 0 * (btn_type_w + 4) + btn_type_w / 2
        is_p_sel = self.selected_type == EntityType.PLAYER
        p_bg = (25, 118, 210, 255) if is_p_sel else (25, 35, 48, 255)
        p_bd = (100, 200, 255, 255) if is_p_sel else (50, 70, 95, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_p_x, btn_type_y, btn_type_w, btn_type_h), p_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_p_x, btn_type_y, btn_type_w, btn_type_h), p_bd, 2.0 if is_p_sel else 1.0)
        self._get_text("atm_bt_p", "👤 Jogador (PC)", b_p_x, btn_type_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # [ 👹 Monstro ]
        b_m_x = modal_cx - modal_w / 2 + 24 + 1 * (btn_type_w + 4) + btn_type_w / 2
        is_m_sel = self.selected_type == EntityType.MONSTER
        m_bg = (183, 28, 28, 255) if is_m_sel else (38, 22, 25, 255)
        m_bd = (255, 138, 128, 255) if is_m_sel else (75, 45, 50, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_m_x, btn_type_y, btn_type_w, btn_type_h), m_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_m_x, btn_type_y, btn_type_w, btn_type_h), m_bd, 2.0 if is_m_sel else 1.0)
        self._get_text("atm_bt_m", "👹 Monstro (NPC)", b_m_x, btn_type_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # [ ✨ Neutro/Magia ]
        b_n_x = modal_cx - modal_w / 2 + 24 + 2 * (btn_type_w + 4) + btn_type_w / 2
        is_n_sel = self.selected_type == EntityType.NEUTRAL
        n_bg = (212, 143, 16, 255) if is_n_sel else (38, 32, 20, 255)
        n_bd = (241, 196, 15, 255) if is_n_sel else (75, 65, 40, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_n_x, btn_type_y, btn_type_w, btn_type_h), n_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_n_x, btn_type_y, btn_type_w, btn_type_h), n_bd, 2.0 if is_n_sel else 1.0)
        self._get_text("atm_bt_n", "✨ Neutro / Magia", b_n_x, btn_type_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 6. Campo 3 & 4: HP Inicial e CA (Steppers lado a lado)
        f3_y = btn_type_y - 32
        half_w = (modal_w - 56) / 2

        # HP Stepper
        hp_cx = modal_cx - modal_w / 2 + 24 + half_w / 2
        self._get_text("atm_lbl_hp", "HP MÁXIMO / ATUAL", hp_cx - half_w / 2, f3_y, (200, 215, 235, 255), 8, bold=True).draw()
        
        hp_step_y = f3_y - 20
        # [-]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx - 45, hp_step_y, 28, 24), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx - 45, hp_step_y, 28, 24), (70, 90, 120, 200), 1)
        self._get_text("atm_b_hp_m", "[-]", hp_cx - 45, hp_step_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()
        # [Valor]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx, hp_step_y, 44, 24), (15, 20, 28, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx, hp_step_y, 44, 24), (241, 196, 15, 200), 1)
        self._get_text("atm_v_hp", str(self.hp_value), hp_cx, hp_step_y, (46, 204, 113, 255), 9, bold=True, anchor_x="center").draw()
        # [+]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx + 45, hp_step_y, 28, 24), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx + 45, hp_step_y, 28, 24), (70, 90, 120, 200), 1)
        self._get_text("atm_b_hp_p", "[+]", hp_cx + 45, hp_step_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

        # CA Stepper
        ca_cx = modal_cx + 4 + half_w / 2
        self._get_text("atm_lbl_ca", "CLASSE DE ARMADURA (CA)", ca_cx - half_w / 2, f3_y, (200, 215, 235, 255), 8, bold=True).draw()
        # [-]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx - 45, hp_step_y, 28, 24), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx - 45, hp_step_y, 28, 24), (70, 90, 120, 200), 1)
        self._get_text("atm_b_ca_m", "[-]", ca_cx - 45, hp_step_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()
        # [Valor]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx, hp_step_y, 44, 24), (15, 20, 28, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx, hp_step_y, 44, 24), (241, 196, 15, 200), 1)
        self._get_text("atm_v_ca", str(self.ac_value), ca_cx, hp_step_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()
        # [+]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx + 45, hp_step_y, 28, 24), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx + 45, hp_step_y, 28, 24), (70, 90, 120, 200), 1)
        self._get_text("atm_b_ca_p", "[+]", ca_cx + 45, hp_step_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

        # 7. Campo 5: Posição na Fila de Iniciativas
        f4_y = hp_step_y - 32
        self._get_text("atm_lbl_slot", "INSERÇÃO NA ORDEM DE INICIATIVA", modal_cx - modal_w / 2 + 24, f4_y, (200, 215, 235, 255), 8, bold=True).draw()

        slot_btn_w = (modal_w - 52) / 2
        slot_btn_h = 28
        slot_y = f4_y - 20

        # [ ⏩ Próximo a Jogar ]
        b_nxt_x = modal_cx - modal_w / 2 + 24 + slot_btn_w / 2
        is_nxt = self.initiative_slot == "next"
        nxt_bg = (39, 174, 96, 255) if is_nxt else (25, 38, 30, 255)
        nxt_bd = (46, 204, 113, 255) if is_nxt else (50, 75, 60, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_nxt_x, slot_y, slot_btn_w, slot_btn_h), nxt_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_nxt_x, slot_y, slot_btn_w, slot_btn_h), nxt_bd, 2.0 if is_nxt else 1.0)
        self._get_text("atm_b_nxt", "⏩ Próximo a Jogar (Turno + 1)", b_nxt_x, slot_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # [ ⏭️ Final da Rodada ]
        b_end_x = modal_cx + 4 + slot_btn_w / 2
        is_end = self.initiative_slot == "end"
        end_bg = (41, 128, 185, 255) if is_end else (25, 35, 48, 255)
        end_bd = (52, 152, 219, 255) if is_end else (50, 70, 95, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_end_x, slot_y, slot_btn_w, slot_btn_h), end_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_end_x, slot_y, slot_btn_w, slot_btn_h), end_bd, 2.0 if is_end else 1.0)
        self._get_text("atm_b_end", "⏭️ Final da Rodada (Último)", b_end_x, slot_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

        # 8. Campo 6: Prévia do Badge / Seletor de Arte
        f5_y = slot_y - 32
        prev_name = self.name_input.text.strip() or "TOKEN"
        prev_cx = modal_cx - modal_w / 2 + 40
        prev_cy = f5_y - 12

        SpriteFactory.draw_tactical_token(
            name=prev_name,
            is_player=(self.selected_type == EntityType.PLAYER),
            x=prev_cx,
            y=prev_cy,
            radius=18,
            is_alive=True,
            is_hidden=False,
            is_selected=False,
            is_active=False,
            text_cache=self.text_cache,
            token_key="modal_preview_token",
            entity_type=self.selected_type,
        )

        sprite_label = "Badge Procedural Circular (Iniciais do Nome)" if self.selected_sprite_idx == 0 else Path(self.available_sprites[self.selected_sprite_idx]).name
        self._get_text("atm_spr_lbl", f"Arte: {sprite_label}", prev_cx + 28, prev_cy + 6, (220, 230, 245, 255), 8, bold=True).draw()
        self._get_text("atm_spr_sub", "Moldura e preenchimento adaptados ao alinhamento tático", prev_cx + 28, prev_cy - 8, (150, 165, 185, 255), 7, bold=False).draw()

        # 9. Botões de Ação do Rodapé do Modal
        btn_foot_y = modal_cy - modal_h / 2 + 30
        btn_action_w = (modal_w - 52) / 2

        # [ ❌ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 24 + btn_action_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_can_x, btn_foot_y, btn_action_w, 32), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_can_x, btn_foot_y, btn_action_w, 32), (231, 76, 60, 255), 1.5)
        self._get_text("atm_b_cancel", "❌ Cancelar", b_can_x, btn_foot_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

        # [ 📍 Posicionar no Mapa ]
        b_pos_x = modal_cx + 4 + btn_action_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_pos_x, btn_foot_y, btn_action_w, 32), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_pos_x, btn_foot_y, btn_action_w, 32), (46, 204, 113, 255), 2.0)
        self._get_text("atm_b_confirm", "📍 Posicionar no Mapa", b_pos_x, btn_foot_y, (255, 255, 255, 255), 9.5, bold=True, anchor_x="center").draw()

    def handle_click(self, x: float, y: float, screen_w: float, screen_h: float) -> bool:
        """Processa cliques no modal."""
        if not self.is_open:
            return False

        modal_w = min(screen_w - 40, 520.0)
        modal_h = 440.0
        modal_cx = screen_w / 2
        modal_cy = screen_h / 2

        # 1. Clique no campo de texto
        f1_y = modal_cy + modal_h / 2 - 24 - 18 - 32
        input_w = modal_w - 48
        input_h = 28
        if abs(x - modal_cx) <= input_w / 2 and abs(y - (f1_y - 20)) <= input_h / 2:
            self.name_input.handle_mouse_press(x, y)
            return True
        else:
            self.name_input.blur()

        # 2. Seleção de Tipo de Entidade (Jogador, Monstro, Neutro)
        f2_y = f1_y - 60
        btn_type_w = (modal_w - 56) / 3
        btn_type_h = 28
        btn_type_y = f2_y - 20

        if abs(y - btn_type_y) <= btn_type_h / 2:
            # Jogador
            b_p_x = modal_cx - modal_w / 2 + 24 + 0 * (btn_type_w + 4) + btn_type_w / 2
            if abs(x - b_p_x) <= btn_type_w / 2:
                self.selected_type = EntityType.PLAYER
                return True

            # Monstro
            b_m_x = modal_cx - modal_w / 2 + 24 + 1 * (btn_type_w + 4) + btn_type_w / 2
            if abs(x - b_m_x) <= btn_type_w / 2:
                self.selected_type = EntityType.MONSTER
                return True

            # Neutro
            b_n_x = modal_cx - modal_w / 2 + 24 + 2 * (btn_type_w + 4) + btn_type_w / 2
            if abs(x - b_n_x) <= btn_type_w / 2:
                self.selected_type = EntityType.NEUTRAL
                return True

        # 3. Steppers de HP e CA
        f3_y = btn_type_y - 32
        hp_step_y = f3_y - 20
        half_w = (modal_w - 56) / 2
        hp_cx = modal_cx - modal_w / 2 + 24 + half_w / 2
        ca_cx = modal_cx + 4 + half_w / 2

        if abs(y - hp_step_y) <= 12:
            # HP [-]
            if abs(x - (hp_cx - 45)) <= 14:
                self.hp_value = max(1, self.hp_value - 1)
                return True
            # HP [+]
            if abs(x - (hp_cx + 45)) <= 14:
                self.hp_value = min(999, self.hp_value + 1)
                return True

            # CA [-]
            if abs(x - (ca_cx - 45)) <= 14:
                self.ac_value = max(0, self.ac_value - 1)
                return True
            # CA [+]
            if abs(x - (ca_cx + 45)) <= 14:
                self.ac_value = min(40, self.ac_value + 1)
                return True

        # 4. Seleção de Slot de Iniciativa ('next' vs 'end')
        f4_y = hp_step_y - 32
        slot_btn_w = (modal_w - 52) / 2
        slot_btn_h = 28
        slot_y = f4_y - 20

        if abs(y - slot_y) <= slot_btn_h / 2:
            # Próximo
            b_nxt_x = modal_cx - modal_w / 2 + 24 + slot_btn_w / 2
            if abs(x - b_nxt_x) <= slot_btn_w / 2:
                self.initiative_slot = "next"
                return True

            # Final
            b_end_x = modal_cx + 4 + slot_btn_w / 2
            if abs(x - b_end_x) <= slot_btn_w / 2:
                self.initiative_slot = "end"
                return True

        # 5. Botões de Ação do Rodapé
        btn_foot_y = modal_cy - modal_h / 2 + 30
        btn_action_w = (modal_w - 52) / 2

        # [ ❌ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 24 + btn_action_w / 2
        if abs(y - btn_foot_y) <= 16 and abs(x - b_can_x) <= btn_action_w / 2:
            self.close()
            return True

        # [ 📍 Posicionar no Mapa ]
        b_pos_x = modal_cx + 4 + btn_action_w / 2
        if abs(y - btn_foot_y) <= 16 and abs(x - b_pos_x) <= btn_action_w / 2:
            self._handle_confirm()
            return True

        # Clique fora da caixa fecha o modal
        if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
            self.close()
            return True

        return True

    def _handle_confirm(self) -> None:
        """Valida os dados e dispara o callback de confirmação."""
        token_name = self.name_input.text.strip()
        if not token_name:
            self.validation_error = "O nome do token é obrigatório!"
            return

        self.validation_error = None
        token_data = {
            "name": token_name,
            "entity_type": self.selected_type,
            "max_hp": self.hp_value,
            "current_hp": self.hp_value,
            "armor_class": self.ac_value,
            "initiative_slot": self.initiative_slot,
            "token_sprite": self.selected_sprite_path,
        }

        logger.info(f"AddTokenModal confirmado: {token_data}")
        self.close()

        if self.on_confirm:
            self.on_confirm(token_data)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Processa teclas no modal (ex: ESC para fechar, Enter para confirmar)."""
        if not self.is_open:
            return False

        if symbol == arcade.key.ESCAPE:
            self.close()
            return True

        if symbol == arcade.key.ENTER:
            self._handle_confirm()
            return True

        return self.name_input.handle_key_press(symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        if self.is_open:
            self.name_input.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        if not self.is_open:
            return False
        return self.name_input.handle_text_input(text)

    def on_update(self, dt: float) -> None:
        if self.is_open:
            self.name_input.on_update(dt)
