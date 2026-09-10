import logging
from pathlib import Path
from typing import Any
import arcade
from ....domain.models.entity import EntityType
from ...utils.sprite_utils import SpriteFactory
from ...utils.ui_constants import Colors, Typography, Dimensions, Spacing, with_alpha

logger = logging.getLogger(__name__)


class AddTokenModalRenderer:
    """
    Renderizador do diálogo modal AddTokenModal (Mid-Combat Token Spawning).
    """

    @staticmethod
    def draw(modal: Any, screen_w: float, screen_h: float) -> None:
        """Desenha o backdrop e o diálogo centralizado Dark Fantasy."""
        if not modal.is_open:
            return

        # 1. Backdrop escuro translúcido
        arcade.draw_rect_filled(arcade.XYWH(screen_w / 2, screen_h / 2, screen_w, screen_h), (0, 0, 0, 190))

        modal_w = min(screen_w - 40, 520.0)
        modal_h = 490.0
        modal_cx = screen_w / 2
        modal_cy = screen_h / 2

        # 2. Caixa do Modal
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), Colors.BG_PANEL)
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), Colors.ACCENT_GOLD, Dimensions.BORDER_WIDTH_THICK)

        # 3. Cabeçalho
        hdr_y = modal_cy + modal_h / 2 - 20
        modal._get_text("atm_title", "➕ ADICIONAR TOKEN AO COMBATE", modal_cx, hdr_y, Colors.ACCENT_GOLD, Typography.SIZE_LABEL, bold=True, anchor_x="center").draw()
        sub_y = hdr_y - 16
        modal._get_text("atm_sub", "Crie um efeito mágico, invocação ou combatente dinâmico no grid:", modal_cx, sub_y, Colors.TEXT_SECONDARY, Typography.SIZE_MICRO, bold=False, anchor_x="center").draw()
        arcade.draw_line(modal_cx - modal_w / 2 + 16, sub_y - 8, modal_cx + modal_w / 2 - 16, sub_y - 8, Colors.BORDER_DEFAULT, Dimensions.BORDER_WIDTH_DEFAULT)

        # 4. Campo 1: Nome do Token (SmartTextInput)
        f1_y = sub_y - 26
        modal._get_text("atm_lbl_name", "NOME DO TOKEN *", modal_cx - modal_w / 2 + 24, f1_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()
        input_w = modal_w - 48
        input_h = 24
        modal.name_input.bounds = (modal_cx, f1_y - 16, input_w, input_h)
        modal.name_input.draw(modal_cx, f1_y - 16, input_w, input_h, modal.text_cache)

        if modal.validation_error:
            modal._get_text("atm_err", f"⚠️ {modal.validation_error}", modal_cx, f1_y - 32, Colors.DANGER, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 5. Campo 2: Tipo de Entidade (Jogador, Monstro, Neutro)
        f2_y = f1_y - 44
        modal._get_text("atm_lbl_type", "CATEGORIA / ALINHAMENTO TÁTICO", modal_cx - modal_w / 2 + 24, f2_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()

        btn_type_w = (modal_w - 56) / 3
        btn_type_h = 24
        btn_type_y = f2_y - 16

        # [ 👤 Jogador ]
        b_p_x = modal_cx - modal_w / 2 + 24 + 0 * (btn_type_w + 4) + btn_type_w / 2
        is_p_sel = modal.selected_type == EntityType.PLAYER
        p_bg = (25, 118, 210, 255) if is_p_sel else (25, 35, 48, 255)
        p_bd = Colors.TEXT_CYAN if is_p_sel else Colors.BORDER_DEFAULT
        arcade.draw_rect_filled(arcade.XYWH(b_p_x, btn_type_y, btn_type_w, btn_type_h), p_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_p_x, btn_type_y, btn_type_w, btn_type_h), p_bd, Dimensions.BORDER_WIDTH_THICK if is_p_sel else Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_bt_p", "👤 Jogador (PC)", b_p_x, btn_type_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # [ 👹 Monstro ]
        b_m_x = modal_cx - modal_w / 2 + 24 + 1 * (btn_type_w + 4) + btn_type_w / 2
        is_m_sel = modal.selected_type == EntityType.MONSTER
        m_bg = (183, 28, 28, 255) if is_m_sel else (38, 22, 25, 255)
        m_bd = Colors.TEXT_CRIMSON if is_m_sel else (75, 45, 50, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_m_x, btn_type_y, btn_type_w, btn_type_h), m_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_m_x, btn_type_y, btn_type_w, btn_type_h), m_bd, Dimensions.BORDER_WIDTH_THICK if is_m_sel else Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_bt_m", "👹 Monstro (NPC)", b_m_x, btn_type_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # [ ✨ Neutro/Magia ]
        b_n_x = modal_cx - modal_w / 2 + 24 + 2 * (btn_type_w + 4) + btn_type_w / 2
        is_n_sel = modal.selected_type == EntityType.NEUTRAL
        n_bg = (212, 143, 16, 255) if is_n_sel else (38, 32, 20, 255)
        n_bd = Colors.ACCENT_GOLD if is_n_sel else (75, 65, 40, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_n_x, btn_type_y, btn_type_w, btn_type_h), n_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_n_x, btn_type_y, btn_type_w, btn_type_h), n_bd, Dimensions.BORDER_WIDTH_THICK if is_n_sel else Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_bt_n", "✨ Neutro / Magia", b_n_x, btn_type_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 6. Campo 3: Porte / Tamanho da Criatura D&D 5E
        f_sz_y = btn_type_y - 30
        modal._get_text("atm_lbl_size", "PORTE / TAMANHO DA CRIATURA (D&D 5E)", modal_cx - modal_w / 2 + 24, f_sz_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()

        sz_count = len(modal.SIZE_OPTIONS)
        btn_sz_w = (modal_w - 48 - (sz_count - 1) * 4) / sz_count
        btn_sz_h = 24
        btn_sz_y = f_sz_y - 16

        for idx, (sz_code, sz_label, sz_footprint) in enumerate(modal.SIZE_OPTIONS):
            bx = modal_cx - modal_w / 2 + 24 + idx * (btn_sz_w + 4) + btn_sz_w / 2
            is_sz_sel = (modal.selected_size.lower() == sz_code.lower())
            sz_bg = (65, 50, 15, 255) if is_sz_sel else (25, 32, 44, 255)
            sz_bd = Colors.ACCENT_GOLD if is_sz_sel else Colors.BORDER_DEFAULT
            sz_txt_color = Colors.TEXT_WHITE if is_sz_sel else Colors.TEXT_SECONDARY

            arcade.draw_rect_filled(arcade.XYWH(bx, btn_sz_y, btn_sz_w, btn_sz_h), sz_bg)
            arcade.draw_rect_outline(arcade.XYWH(bx, btn_sz_y, btn_sz_w, btn_sz_h), sz_bd, Dimensions.BORDER_WIDTH_THICK if is_sz_sel else Dimensions.BORDER_WIDTH_DEFAULT)
            modal._get_text(f"atm_sz_{sz_code}", sz_label, bx, btn_sz_y, sz_txt_color, Typography.SIZE_MICRO, bold=is_sz_sel, anchor_x="center").draw()

        # 7. Campo 4: HP Inicial e CA (Steppers lado a lado)
        f3_y = btn_sz_y - 28
        half_w = (modal_w - 56) / 2

        # HP Stepper
        hp_cx = modal_cx - modal_w / 2 + 24 + half_w / 2
        modal._get_text("atm_lbl_hp", "HP MÁXIMO / ATUAL", hp_cx - half_w / 2, f3_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()

        hp_step_y = f3_y - 16
        # [-]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx - 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx - 45, hp_step_y, 28, 22), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_b_hp_m", "[-]", hp_cx - 45, hp_step_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        # [Valor]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx, hp_step_y, 44, 22), (15, 20, 28, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx, hp_step_y, 44, 22), Colors.BORDER_FOCUS, Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_v_hp", str(modal.hp_value), hp_cx, hp_step_y, Colors.SUCCESS, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        # [+]
        arcade.draw_rect_filled(arcade.XYWH(hp_cx + 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(hp_cx + 45, hp_step_y, 28, 22), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_b_hp_p", "[+]", hp_cx + 45, hp_step_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # CA Stepper
        ca_cx = modal_cx + 4 + half_w / 2
        modal._get_text("atm_lbl_ca", "CLASSE DE ARMADURA (CA)", ca_cx - half_w / 2, f3_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()
        # [-]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx - 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx - 45, hp_step_y, 28, 22), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_b_ca_m", "[-]", ca_cx - 45, hp_step_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        # [Valor]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx, hp_step_y, 44, 22), (15, 20, 28, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx, hp_step_y, 44, 22), Colors.BORDER_FOCUS, Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_v_ca", str(modal.ac_value), ca_cx, hp_step_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
        # [+]
        arcade.draw_rect_filled(arcade.XYWH(ca_cx + 45, hp_step_y, 28, 22), (45, 55, 70, 255))
        arcade.draw_rect_outline(arcade.XYWH(ca_cx + 45, hp_step_y, 28, 22), Colors.BTN_DEFAULT_BORDER, Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_b_ca_p", "[+]", ca_cx + 45, hp_step_y, Colors.ACCENT_GOLD, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 8. Campo 5: Posição na Fila de Iniciativas
        f4_y = hp_step_y - 28
        modal._get_text("atm_lbl_slot", "INSERÇÃO NA ORDEM DE INICIATIVA", modal_cx - modal_w / 2 + 24, f4_y, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()

        slot_btn_w = (modal_w - 52) / 2
        slot_btn_h = 24
        slot_y = f4_y - 16

        # [ ⏩ Próximo a Jogar ]
        b_nxt_x = modal_cx - modal_w / 2 + 24 + slot_btn_w / 2
        is_nxt = modal.initiative_slot == "next"
        nxt_bg = (39, 174, 96, 255) if is_nxt else (25, 38, 30, 255)
        nxt_bd = Colors.SUCCESS if is_nxt else (50, 75, 60, 200)
        arcade.draw_rect_filled(arcade.XYWH(b_nxt_x, slot_y, slot_btn_w, slot_btn_h), nxt_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_nxt_x, slot_y, slot_btn_w, slot_btn_h), nxt_bd, Dimensions.BORDER_WIDTH_THICK if is_nxt else Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_b_nxt", "⏩ Próximo a Jogar (Turno + 1)", b_nxt_x, slot_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # [ ⏭️ Final da Rodada ]
        b_end_x = modal_cx + 4 + slot_btn_w / 2
        is_end = modal.initiative_slot == "end"
        end_bg = Colors.PC_BLUE if is_end else (25, 35, 48, 255)
        end_bd = Colors.INFO if is_end else Colors.BORDER_DEFAULT
        arcade.draw_rect_filled(arcade.XYWH(b_end_x, slot_y, slot_btn_w, slot_btn_h), end_bg)
        arcade.draw_rect_outline(arcade.XYWH(b_end_x, slot_y, slot_btn_w, slot_btn_h), end_bd, Dimensions.BORDER_WIDTH_THICK if is_end else Dimensions.BORDER_WIDTH_DEFAULT)
        modal._get_text("atm_b_end", "⏭️ Final da Rodada (Último)", b_end_x, slot_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # 9. Campo 6: Prévia do Badge / Seletor de Arte
        f5_y = slot_y - 26
        prev_name = modal.name_input.text.strip() or "TOKEN"
        prev_cx = modal_cx - modal_w / 2 + 36
        prev_cy = f5_y - 12

        SpriteFactory.draw_tactical_token(
            name=prev_name,
            is_player=(modal.selected_type == EntityType.PLAYER),
            x=prev_cx,
            y=prev_cy,
            radius=16,
            is_alive=True,
            is_hidden=False,
            is_selected=False,
            is_active=False,
            text_cache=modal.text_cache,
            token_key="modal_preview_token",
            entity_type=modal.selected_type,
        )

        sprite_label = "Badge Circular Procedural" if modal.selected_sprite_idx == 0 else Path(modal.available_sprites[modal.selected_sprite_idx]).name
        modal._get_text("atm_spr_lbl", f"Arte: {sprite_label} • Porte: {modal.selected_size}", prev_cx + 26, prev_cy + 5, Colors.TEXT_PRIMARY, Typography.SIZE_MICRO, bold=True).draw()
        modal._get_text("atm_spr_sub", "Moldura e diâmetro de órbita adaptados dinamicamente", prev_cx + 26, prev_cy - 7, Colors.TEXT_MUTED, Typography.SIZE_MICRO, bold=False).draw()

        # 10. Botões de Ação do Rodapé do Modal
        btn_foot_y = modal_cy - modal_h / 2 + 26
        btn_action_w = (modal_w - 52) / 2

        # [ ❌ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 24 + btn_action_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_can_x, btn_foot_y, btn_action_w, Dimensions.BTN_HEIGHT_COMPACT), Colors.NPC_RED)
        arcade.draw_rect_outline(arcade.XYWH(b_can_x, btn_foot_y, btn_action_w, Dimensions.BTN_HEIGHT_COMPACT), Colors.DANGER, Dimensions.BORDER_WIDTH_ACTIVE)
        modal._get_text("atm_b_cancel", "❌ Cancelar", b_can_x, btn_foot_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()

        # [ 📍 Posicionar no Mapa ]
        b_pos_x = modal_cx + 4 + btn_action_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_pos_x, btn_foot_y, btn_action_w, Dimensions.BTN_HEIGHT_COMPACT), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_pos_x, btn_foot_y, btn_action_w, Dimensions.BTN_HEIGHT_COMPACT), Colors.SUCCESS, Dimensions.BORDER_WIDTH_THICK)
        modal._get_text("atm_b_confirm", "📍 Posicionar no Mapa", b_pos_x, btn_foot_y, Colors.TEXT_WHITE, Typography.SIZE_MICRO, bold=True, anchor_x="center").draw()
