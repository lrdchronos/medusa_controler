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
      3. Porte / Tamanho da Criatura (Miúdo, Médio, Grande, Enorme, Imenso).
      4. HP Máximo/Inicial e Classe de Armadura (CA).
      5. Inserção na Iniciativa ('next' = Próximo a Jogar, 'end' = Final da Rodada).
      6. Seleção de Textura / Arte de Token (com fallback para badge circular procedural).
      7. Confirmação para transicionar o Mini-Mapa para o modo de posicionamento (PLACING_TOKEN).
    """

    SIZE_OPTIONS: List[Tuple[str, str, str]] = [
        ("Tiny", "Miúdo (1x1)", "1x1"),
        ("Medium", "Médio (1x1)", "1x1"),
        ("Large", "Grande (2x2)", "2x2"),
        ("Huge", "Enorme (3x3)", "3x3"),
        ("Gargantuan", "Imenso (4x4)", "4x4"),
    ]

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
        self.selected_size: str = "Medium"
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
        self.selected_size = "Medium"
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
        modal_h = 490.0
        modal_cx = screen_w / 2
        modal_cy = screen_h / 2

        # 2. Caixa do Modal
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (20, 26, 36, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (241, 196, 15, 255), 2.0)

        # 3. Cabeçalho
        hdr_y = modal_cy + modal_h / 2 - 20
        self._get_text("atm_title", "➕ ADICIONAR TOKEN AO COMBATE", modal_cx, hdr_y, (241, 196, 15, 255), 10.5, bold=True, anchor_x="center").draw()
        sub_y = hdr_y - 16
        self._get_text("atm_sub", "Crie um efeito mágico, invocação ou combatente dinâmico no grid:", modal_cx, sub_y, (170, 185, 205, 255), 7.5, bold=False, anchor_x="center").draw()
        arcade.draw_line(modal_cx - modal_w / 2 + 16, sub_y - 8, modal_cx + modal_w / 2 - 16, sub_y - 8, (50, 65, 90, 180), 1.0)

        # 4. Campo 1: Nome do Token (SmartTextInput)
        f1_y = sub_y - 26
        self._get_text("atm_lbl_name", "NOME DO TOKEN *", modal_cx - modal_w / 2 + 24, f1_y, (200, 215, 235, 255), 7.5, bold=True).draw()
        input_w = modal_w - 48
        input_h = 24
        self.name_input.bounds = (modal_cx, f1_y - 16, input_w, input_h)
        self.name_input.draw(modal_cx, f1_y - 16, input_w, input_h, self.text_cache)

        if self.validation_error:
            self._get_text("atm_err", f"⚠️ {self.validation_error}", modal_cx, f1_y - 32, (231, 76, 60, 255), 7.5, bold=True, anchor_x="center").draw()

        # 5. Campo 2: Tipo de Entidade (Jogador, Monstro, Neutro)
        f2_y = f1_y - 44
        self._get_text("atm_lbl_type", "CATEGORIA / ALINHAMENTO TÁTICO", modal_cx - modal_w / 2 + 24, f2_y, (200, 215, 235, 255), 7.5, bold=True).draw()
        
        btn_type_w = (modal_w - 56) / 3
        btn_type_h = 24
        btn_type_y = f2_y - 16

        # [ 👤 Jogador ]
        b_p_x = modal_cx - modal_w / 2 + 24 + 0 * (btn_type_w + 4) + btn_type_w / 2
        is_p_sel = self.selected_type == EntityType.PLAYER
        p_bg = (25, 118, 210, 255) if is_p_sel else (25, 35, 48, 255)
        p_bd = (100, 200, 255, 255) if is_p_sel else (50, 70, 95, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_p_x, btn_type_y, btn_type_w, btn_type_h), p_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_p_x, btn_type_y, btn_type_w, btn_type_h), p_bd, 2.0 if is_p_sel else 1.0)
        self._get_text("atm_bt_p", "👤 Jogador (PC)", b_p_x, btn_type_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # [ 👹 Monstro ]
        b_m_x = modal_cx - modal_w / 2 + 24 + 1 * (btn_type_w + 4) + btn_type_w / 2
        is_m_sel = self.selected_type == EntityType.MONSTER
        m_bg = (183, 28, 28, 255) if is_m_sel else (38, 22, 25, 255)
        m_bd = (255, 138, 128, 255) if is_m_sel else (75, 45, 50, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_m_x, btn_type_y, btn_type_w, btn_type_h), m_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_m_x, btn_type_y, btn_type_w, btn_type_h), m_bd, 2.0 if is_m_sel else 1.0)
        self._get_text("atm_bt_m", "👹 Monstro (NPC)", b_m_x, btn_type_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # [ ✨ Neutro/Magia ]
        b_n_x = modal_cx - modal_w / 2 + 24 + 2 * (btn_type_w + 4) + btn_type_w / 2
        is_n_sel = self.selected_type == EntityType.NEUTRAL
        n_bg = (212, 143, 16, 255) if is_n_sel else (38, 32, 20, 255)
        n_bd = (241, 196, 15, 255) if is_n_sel else (75, 65, 40, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_n_x, btn_type_y, btn_type_w, btn_type_h), n_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_n_x, btn_type_y, btn_type_w, btn_type_h), n_bd, 2.0 if is_n_sel else 1.0)
        self._get_text("atm_bt_n", "✨ Neutro / Magia", b_n_x, btn_type_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # 6. Campo 3: Porte / Tamanho da Criatura D&D 5E
        f_sz_y = btn_type_y - 30
        self._get_text("atm_lbl_size", "PORTE / TAMANHO DA CRIATURA (D&D 5E)", modal_cx - modal_w / 2 + 24, f_sz_y, (200, 215, 235, 255), 7.5, bold=True).draw()

        sz_count = len(self.SIZE_OPTIONS)
        btn_sz_w = (modal_w - 48 - (sz_count - 1) * 4) / sz_count
        btn_sz_h = 24
        btn_sz_y = f_sz_y - 16

        for idx, (sz_code, sz_label, sz_footprint) in enumerate(self.SIZE_OPTIONS):
            bx = modal_cx - modal_w / 2 + 24 + idx * (btn_sz_w + 4) + btn_sz_w / 2
            is_sz_sel = (self.selected_size.lower() == sz_code.lower())
            sz_bg = (65, 50, 15, 255) if is_sz_sel else (25, 32, 44, 255)
            sz_bd = (241, 196, 15, 255) if is_sz_sel else (50, 68, 92, 200)
            sz_txt_color = (255, 255, 255, 255) if is_sz_sel else (180, 195, 215, 255)

            arcade.draw_rect_filled(arcade.XYWH(bx, btn_sz_y, btn_sz_w, btn_sz_h), sz_bg)
            arcade.draw_rect_outline(arcade.XYWH(bx, btn_sz_y, btn_sz_w, btn_sz_h), sz_bd, 2.0 if is_sz_sel else 1.0)
            self._get_text(f"atm_sz_{sz_code}", sz_label, bx, btn_sz_y, sz_txt_color, 7, bold=is_sz_sel, anchor_x="center").draw()

        # 7. Campo 4: HP Inicial e CA (Steppers lado a lado)
        f3_y = btn_sz_y - 28
        half_w = (modal_w - 56) / 2

        # HP Stepper
        hp_cx = modal_cx - modal_w / 2 + 24 + half_w / 2
        self._get_text("atm_lbl_hp", "HP MÁXIMO / ATUAL", hp_cx - half_w / 2, f3_y, (200, 215, 235, 255), 7.5, bold=True).draw()
        
        hp_step_y = f3_y - 16
        # [-]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx - 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx - 45, hp_step_y, 28, 22), (70, 90, 120, 200), 1)
        self._get_text("atm_b_hp_m", "[-]", hp_cx - 45, hp_step_y, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()
        # [Valor]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx, hp_step_y, 44, 22), (15, 20, 28, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx, hp_step_y, 44, 22), (241, 196, 15, 200), 1)
        self._get_text("atm_v_hp", str(self.hp_value), hp_cx, hp_step_y, (46, 204, 113, 255), 8.5, bold=True, anchor_x="center").draw()
        # [+]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx + 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx + 45, hp_step_y, 28, 22), (70, 90, 120, 200), 1)
        self._get_text("atm_b_hp_p", "[+]", hp_cx + 45, hp_step_y, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()

        # CA Stepper
        ca_cx = modal_cx + 4 + half_w / 2
        self._get_text("atm_lbl_ca", "CLASSE DE ARMADURA (CA)", ca_cx - half_w / 2, f3_y, (200, 215, 235, 255), 7.5, bold=True).draw()
        # [-]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx - 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx - 45, hp_step_y, 28, 22), (70, 90, 120, 200), 1)
        self._get_text("atm_b_ca_m", "[-]", ca_cx - 45, hp_step_y, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()
        # [Valor]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx, hp_step_y, 44, 22), (15, 20, 28, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx, hp_step_y, 44, 22), (241, 196, 15, 200), 1)
        self._get_text("atm_v_ca", str(self.ac_value), ca_cx, hp_step_y, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()
        # [+]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx + 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx + 45, hp_step_y, 28, 22), (70, 90, 120, 200), 1)
        self._get_text("atm_b_ca_p", "[+]", ca_cx + 45, hp_step_y, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()

        # 8. Campo 5: Posição na Fila de Iniciativas
        f4_y = hp_step_y - 28
        self._get_text("atm_lbl_slot", "INSERÇÃO NA ORDEM DE INICIATIVA", modal_cx - modal_w / 2 + 24, f4_y, (200, 215, 235, 255), 7.5, bold=True).draw()

        slot_btn_w = (modal_w - 52) / 2
        slot_btn_h = 24
        slot_y = f4_y - 16

        # [ ⏩ Próximo a Jogar ]
        b_nxt_x = modal_cx - modal_w / 2 + 24 + slot_btn_w / 2
        is_nxt = self.initiative_slot == "next"
        nxt_bg = (39, 174, 96, 255) if is_nxt else (25, 38, 30, 255)
        nxt_bd = (46, 204, 113, 255) if is_nxt else (50, 75, 60, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_nxt_x, slot_y, slot_btn_w, slot_btn_h), nxt_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_nxt_x, slot_y, slot_btn_w, slot_btn_h), nxt_bd, 2.0 if is_nxt else 1.0)
        self._get_text("atm_b_nxt", "⏩ Próximo a Jogar (Turno + 1)", b_nxt_x, slot_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # [ ⏭️ Final da Rodada ]
        b_end_x = modal_cx + 4 + slot_btn_w / 2
        is_end = self.initiative_slot == "end"
        end_bg = (41, 128, 185, 255) if is_end else (25, 35, 48, 255)
        end_bd = (52, 152, 219, 255) if is_end else (50, 70, 95, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_end_x, slot_y, slot_btn_w, slot_btn_h), end_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_end_x, slot_y, slot_btn_w, slot_btn_h), end_bd, 2.0 if is_end else 1.0)
        self._get_text("atm_b_end", "⏭️ Final da Rodada (Último)", b_end_x, slot_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # 9. Campo 6: Prévia do Badge / Seletor de Arte
        f5_y = slot_y - 26
        prev_name = self.name_input.text.strip() or "TOKEN"
        prev_cx = modal_cx - modal_w / 2 + 36
        prev_cy = f5_y - 12

        SpriteFactory.draw_tactical_token(
            name=prev_name,
            is_player=(self.selected_type == EntityType.PLAYER),
            x=prev_cx,
            y=prev_cy,
            radius=16,
            is_alive=True,
            is_hidden=False,
            is_selected=False,
            is_active=False,
            text_cache=self.text_cache,
            token_key="modal_preview_token",
            entity_type=self.selected_type,
        )

        sprite_label = "Badge Circular Procedural" if self.selected_sprite_idx == 0 else Path(self.available_sprites[self.selected_sprite_idx]).name
        self._get_text("atm_spr_lbl", f"Arte: {sprite_label} • Porte: {self.selected_size}", prev_cx + 26, prev_cy + 5, (220, 230, 245, 255), 7.5, bold=True).draw()
        self._get_text("atm_spr_sub", "Moldura e diâmetro de órbita adaptados dinamicamente", prev_cx + 26, prev_cy - 7, (150, 165, 185, 255), 6.5, bold=False).draw()

        # 10. Botões de Ação do Rodapé do Modal
        btn_foot_y = modal_cy - modal_h / 2 + 26
        btn_action_w = (modal_w - 52) / 2

        # [ ❌ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 24 + btn_action_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_can_x, btn_foot_y, btn_action_w, 28), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_can_x, btn_foot_y, btn_action_w, 28), (231, 76, 60, 255), 1.5)
        self._get_text("atm_b_cancel", "❌ Cancelar", b_can_x, btn_foot_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # [ 📍 Posicionar no Mapa ]
        b_pos_x = modal_cx + 4 + btn_action_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_pos_x, btn_foot_y, btn_action_w, 28), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_pos_x, btn_foot_y, btn_action_w, 28), (46, 204, 113, 255), 2.0)
        self._get_text("atm_b_confirm", "📍 Posicionar no Mapa", b_pos_x, btn_foot_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

    def handle_click(self, x: float, y: float, screen_w: float, screen_h: float) -> bool:
        """Processa cliques no modal."""
        if not self.is_open:
            return False

        modal_w = min(screen_w - 40, 520.0)
        modal_h = 490.0
        modal_cx = screen_w / 2
        modal_cy = screen_h / 2

        # 1. Clique no campo de texto
        f1_y = modal_cy + modal_h / 2 - 20 - 16 - 26
        input_w = modal_w - 48
        input_h = 24
        if abs(x - modal_cx) <= input_w / 2 and abs(y - (f1_y - 16)) <= input_h / 2:
            self.name_input.handle_mouse_press(x, y)
            return True
        else:
            self.name_input.blur()

        # 2. Seleção de Tipo de Entidade (Jogador, Monstro, Neutro)
        f2_y = f1_y - 44
        btn_type_w = (modal_w - 56) / 3
        btn_type_h = 24
        btn_type_y = f2_y - 16

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

        # 3. Seleção de Porte / Tamanho (Miúdo, Médio, Grande, Enorme, Imenso)
        f_sz_y = btn_type_y - 30
        sz_count = len(self.SIZE_OPTIONS)
        btn_sz_w = (modal_w - 48 - (sz_count - 1) * 4) / sz_count
        btn_sz_h = 24
        btn_sz_y = f_sz_y - 16

        if abs(y - btn_sz_y) <= btn_sz_h / 2:
            for idx, (sz_code, _, _) in enumerate(self.SIZE_OPTIONS):
                bx = modal_cx - modal_w / 2 + 24 + idx * (btn_sz_w + 4) + btn_sz_w / 2
                if abs(x - bx) <= btn_sz_w / 2:
                    self.selected_size = sz_code
                    logger.info(f"Porte selecionado no modal: '{self.selected_size}'.")
                    return True

        # 4. Steppers de HP e CA
        f3_y = btn_sz_y - 28
        hp_step_y = f3_y - 16
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

        # 5. Seleção de Slot de Iniciativa ('next' vs 'end')
        f4_y = hp_step_y - 28
        slot_btn_w = (modal_w - 52) / 2
        slot_btn_h = 24
        slot_y = f4_y - 16

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

        # 6. Botões de Ação do Rodapé
        btn_foot_y = modal_cy - modal_h / 2 + 26
        btn_action_w = (modal_w - 52) / 2

        # [ ❌ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 24 + btn_action_w / 2
        if abs(y - btn_foot_y) <= 14 and abs(x - b_can_x) <= btn_action_w / 2:
            self.close()
            return True

        # [ 📍 Posicionar no Mapa ]
        b_pos_x = modal_cx + 4 + btn_action_w / 2
        if abs(y - btn_foot_y) <= 14 and abs(x - b_pos_x) <= btn_action_w / 2:
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
            "size": self.selected_size,
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
