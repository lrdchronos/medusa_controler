import logging
from typing import Optional, List, Dict, Any, Callable, Tuple
import arcade
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.playablechar import PlayableCharacter
from ...domain.models.entity import Entity, EntityType, DynamicToken
from ..components.discrete_scroll_list import DiscreteScrollList
from ..utils.status_icon_atlas import StatusIconAtlas
from .spell_aoe_panel import SpellAoEPanel
from .fog_control_panel import FogControlPanel
from .add_token_modal import AddTokenModal

logger = logging.getLogger(__name__)

class CombatTabView:
    """
    Componente da Aba de Combate Ativo (Barra de Ações de Turno, Inserção Dinâmica de Tokens,
    Painel de Feitiços AoE, Painel de Névoa de Guerra, Roster de Combatentes com DiscreteScrollList,
    Despachante de Dano/Cura e Save State).
    """

    def __init__(self, session_manager: SessionManager, dm_window: Optional[Any] = None) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.dm_window = dm_window
        self.selected_combatant_uid: Optional[str] = None
        self.custom_hp_value: int = 8
        self.text_cache: Dict[str, arcade.Text] = {}
        self.spell_aoe_panel = SpellAoEPanel(session_manager=self.session_manager)
        self.fog_panel = FogControlPanel(
            fog_manager=self.combat_manager.fog_manager,
            dimensions_provider=self._get_grid_dimensions,
            save_callback=self.combat_manager.save_fog_to_encounter_file,
        )
        self.add_token_modal = AddTokenModal(on_confirm=self._handle_add_token_confirm)

        # Componente OOD reutilizável para Paginação e Rolagem Discreta de Combatentes
        self.__item_height: int = 24
        self.__spacing: int = 2
        self.__scroll_list = DiscreteScrollList(
            item_height=self.__item_height,
            spacing=self.__spacing,
            visible_item_count=4,
        )

        # Notificação Toast de Confirmação de Salvamento
        self.toast_message: Optional[str] = None
        self.toast_timer: float = 0.0

        # Modal de Confirmação ao Finalizar Combate (Limpar ou Manter Save)
        self.pending_end_combat_modal: bool = False

    @property
    def scroll_list(self) -> DiscreteScrollList:
        """Referência ao componente OOD de rolagem discreta de combatentes."""
        return self.__scroll_list

    def _handle_add_token_confirm(self, token_data: Dict[str, Any]) -> None:
        """Aciona o modo PLACING_TOKEN no TacticalMiniMap após confirmação do modal."""
        if self.dm_window is not None and hasattr(self.dm_window, "mini_map"):
            self.dm_window.mini_map.start_placing_token(
                token_data=token_data,
                on_spawn=self._on_token_spawned,
            )
            logger.info(f"Modo de posicionamento ativado no TacticalMiniMap para '{token_data.get('name')}'.")
        else:
            # Fallback direto caso mini_map não esteja acessível
            etype = token_data.get("entity_type", EntityType.NEUTRAL)
            token_entity = DynamicToken(
                name=token_data.get("name", "Token"),
                max_hp=int(token_data.get("max_hp", 1)),
                armor_class=int(token_data.get("armor_class", 10)),
                entity_type=etype,
                token_sprite=token_data.get("token_sprite"),
                size=token_data.get("size", "Medium"),
            )
            slot = token_data.get("initiative_slot", "next")
            self.combat_manager.spawn_combatant(token_entity, (0, 0), initiative_slot=slot)
            self.ensure_valid_selection()

    def _on_token_spawned(self, entity: Entity, position: Tuple[int, int], slot: str) -> None:
        """Callback invocado após inserção do token no mini-mapa."""
        self.selected_combatant_uid = entity.uid
        self.ensure_valid_selection()
        logger.info(f"Token '{entity.name}' inserido e selecionado com sucesso em {position}.")

    def _get_grid_dimensions(self) -> Tuple[int, int]:
        """Retorna dimensões (colunas, linhas) da grade tática ativa."""
        grid_mgr = self.combat_manager.grid_manager
        if grid_mgr is not None:
            return (grid_mgr.columns, grid_mgr.rows)
        return (25, 14)


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

    def ensure_valid_selection(self) -> None:
        """Garante que haja um combatente válido selecionado."""
        combatants = self.combat_manager.combatants
        if combatants:
            if not self.selected_combatant_uid or not any(c.uid == self.selected_combatant_uid for c in combatants):
                self.selected_combatant_uid = combatants[0].uid
        else:
            self.selected_combatant_uid = None

    def trigger_save_combat(self) -> None:
        """Salva o estado atual de combate e dispara toast de confirmação."""
        success = self.combat_manager.save_combat_state()
        if success:
            self.toast_message = "Progresso do combate salvo com sucesso!"
            self.toast_timer = 3.0
            logger.info("Progresso do combate salvo com sucesso pelo usuário.")
        else:
            self.toast_message = "Falha ao salvar progresso do combate!"
            self.toast_timer = 3.0

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha todo o painel de combate ativo."""
        self.ensure_valid_selection()
        
        # Atualiza timer do toast
        if self.toast_timer > 0:
            self.toast_timer -= 1/60 # Simplificação: assumindo 60fps

        # 1. Barra de Ações Rápidas de Combate (6 Botões OOD)
        bar_y = top_y - 20
        btn_w = (panel_w - 44) / 6
        btn_h = 28

        # Botão 1: Rolar Iniciativas (Abre Modal de Staging)
        b1_x = 12 + 0 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b1_x, bar_y, btn_w, btn_h), (142, 68, 173, 255))
        arcade.draw_rect_outline(arcade.XYWH(b1_x, bar_y, btn_w, btn_h), (155, 89, 182, 255), 1)
        self._get_text("cm_b_init", "🎲 Inic", b1_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 2: Adicionar Token Dinâmico (Mid-Combat Spawn)
        b2_x = 12 + 1 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b2_x, bar_y, btn_w, btn_h), (243, 156, 18, 255))
        arcade.draw_rect_outline(arcade.XYWH(b2_x, bar_y, btn_w, btn_h), (241, 196, 15, 255), 1)
        self._get_text("cm_b_add_tkn", "➕ Token", b2_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 3: Turno Anterior
        b3_x = 12 + 2 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b3_x, bar_y, btn_w, btn_h), (41, 128, 185, 255))
        arcade.draw_rect_outline(arcade.XYWH(b3_x, bar_y, btn_w, btn_h), (52, 152, 219, 255), 1)
        self._get_text("cm_b_prev", "◀ Turno", b3_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 4: Próximo Turno
        b4_x = 12 + 3 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b4_x, bar_y, btn_w, btn_h), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b4_x, bar_y, btn_w, btn_h), (46, 204, 113, 255), 1)
        self._get_text("cm_b_next", "▶ Turno", b4_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 5: Pausar e Salvar Combate
        b5_x = 12 + 4 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b5_x, bar_y, btn_w, btn_h), (211, 84, 0, 255))
        arcade.draw_rect_outline(arcade.XYWH(b5_x, bar_y, btn_w, btn_h), (230, 126, 34, 255), 1)
        self._get_text("cm_b_save", "💾 Salvar", b5_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # Botão 6: Finalizar Combate
        b6_x = 12 + 5 * (btn_w + 4) + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b6_x, bar_y, btn_w, btn_h), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b6_x, bar_y, btn_w, btn_h), (231, 76, 60, 255), 1)
        self._get_text("cm_b_end", "🏁 Sair", b6_x, bar_y, (255, 255, 255, 255), 7.5, bold=True, anchor_x="center").draw()

        # 2. Informação de Rodada e Turno Ativo
        info_y = bar_y - 24
        active_char = self.combat_manager.active_character
        round_num = getattr(self.combat_manager, "round_number", getattr(self.combat_manager, "current_round", 1))
        turn_str = f"⚔️ Rodada: {round_num} • Turno Ativo: {active_char.name if active_char else 'Nenhum'}"
        self._get_text("cm_info_turn", turn_str, 16, info_y, (241, 196, 15, 255), 9, bold=True).draw()

        # Notificação Toast Flutuante de Salvamento
        if self.toast_timer > 0 and self.toast_message:
            toast_alpha = min(255, int((self.toast_timer / 0.4) * 255)) if self.toast_timer < 0.4 else 255
            toast_bg = (20, 60, 35, min(240, toast_alpha))
            toast_bd = (46, 204, 113, toast_alpha)
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, info_y, panel_w - 30, 22), toast_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, info_y, panel_w - 30, 22), toast_bd, 1.2)
            self._get_text("cm_toast", f"💾 {self.toast_message}", panel_w / 2, info_y, (255, 255, 255, toast_alpha), 8.5, bold=True, anchor_x="center").draw()

        # 3. Painel de Feitiços (Spell AoE Overlay)
        spell_next_y = self.spell_aoe_panel.draw(panel_w, info_y - 12)

        # 4. Painel de Névoa de Guerra (Fog of War Control Panel)
        fog_next_y = self.fog_panel.draw(panel_w, spell_next_y)

        # 5. Tabela de Combatentes (Roster) com DiscreteScrollList
        table_top = fog_next_y
        table_h = 22
        table_y = table_top - table_h / 2

        # Cabeçalho da Tabela
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), (28, 36, 48, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, table_y, panel_w - 24, table_h), (50, 65, 90, 200), 1)

        self._get_text("th_turn", "TURNO", 28, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="left").draw()
        self._get_text("th_name", "NOME", 85, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="left").draw()
        self._get_text("th_type", "TIPO", 240, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_hp", "HP", 305, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_ca", "CA", 365, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_mod", "MOD", 405, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_init", "INIC", 445, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_status", "STATUS", 500, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()
        self._get_text("th_vis", "VIS", panel_w - 40, table_y, (180, 190, 205, 255), 8, bold=True, anchor_x="center").draw()

        # Linhas de Combatentes (Turn Order ou Lista Geral) com Paginação Discreta
        combatants = self.combat_manager.turn_order if self.combat_manager.has_combat_started else self.combat_manager.combatants
        panels_collapsed = (1 if self.spell_aoe_panel.is_collapsed else 0) + (1 if self.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2

        self.__scroll_list.items = combatants
        self.__scroll_list.visible_item_count = max_rows
        list_w = panel_w - 24
        list_h = max_rows * (self.__item_height + self.__spacing)
        list_x = 12
        list_top_y = table_top - table_h
        self.__scroll_list.set_bounds(list_x, list_top_y, list_w, list_h)
        self.__scroll_list.set_style(draw_frame=False)

        visible_list = self.__scroll_list.visible_items
        for slot_idx, (actual_idx, combatant) in enumerate(visible_list):
            slot_cx, slot_cy, slot_w, slot_h = self.__scroll_list.get_slot_rect(slot_idx)
            is_active = (combatant == active_char)
            is_selected = (combatant.uid == self.selected_combatant_uid)

            if is_selected:
                row_bg = (45, 62, 85, 255)
                row_border = (241, 196, 15, 255)
            elif is_active:
                row_bg = (24, 50, 40, 255)
                row_border = (46, 204, 113, 200)
            else:
                row_bg = (18, 24, 34, 255) if actual_idx % 2 == 0 else (22, 28, 40, 255)
                row_border = (50, 65, 90, 150)

            arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), row_bg)
            arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), row_border, 1.2 if (is_selected or is_active) else 0.8)

            # Turn Indicator
            turn_mark = "▶" if is_active else str(actual_idx + 1)
            turn_color = (46, 204, 113, 255) if is_active else (140, 155, 175, 255)
            self._get_text(f"r_turn_{actual_idx}", turn_mark, 28, slot_cy, turn_color, 8, bold=True, anchor_x="center").draw()

            # Name & Type Logic (Player / Monster / Neutral)
            etype = getattr(combatant, "entity_type", EntityType.PLAYER if isinstance(combatant, PlayableCharacter) else EntityType.MONSTER)
            is_neu = getattr(combatant, "is_neutral", False) or etype == EntityType.NEUTRAL or str(etype).lower() == "neutral"
            is_ply = getattr(combatant, "is_player", False) or isinstance(combatant, PlayableCharacter) or etype == EntityType.PLAYER or str(etype).lower() == "player"

            if is_neu:
                name_color = (241, 196, 15, 255)
                type_str = "NEUTRO"
                type_color = (241, 196, 15, 255)
            elif is_ply:
                name_color = (100, 200, 255, 255)
                type_str = "PJ"
                type_color = (100, 200, 255, 255)
            else:
                name_color = (255, 138, 128, 255)
                type_str = "NPC"
                type_color = (255, 138, 128, 255)

            self._get_text(f"r_name_{actual_idx}", combatant.name[:18], 55, slot_cy, name_color, 8, bold=True).draw()
            self._get_text(f"r_type_{actual_idx}", type_str, 240, slot_cy, type_color, 7.5, bold=False, anchor_x="center").draw()

            # HP
            hp_str = f"{combatant.current_hp}/{combatant.max_hp}"
            hp_c = (46, 204, 113, 255) if combatant.current_hp > (combatant.max_hp / 2) else (231, 76, 60, 255)
            self._get_text(f"r_hp_{actual_idx}", hp_str, 305, slot_cy, hp_c, 8, bold=True, anchor_x="center").draw()

            # CA
            self._get_text(f"r_ca_{actual_idx}", str(combatant.armor_class), 365, slot_cy, (241, 196, 15, 255), 8, bold=True, anchor_x="center").draw()

            # Mod
            mod_str = f"{combatant.initiative_mod:+d}"
            self._get_text(f"r_mod_{actual_idx}", mod_str, 405, slot_cy, (180, 190, 205, 255), 8, bold=False, anchor_x="center").draw()

            # Init
            self._get_text(f"r_init_{actual_idx}", str(combatant.initiative_score), 445, slot_cy, (230, 235, 245, 255), 8, bold=True, anchor_x="center").draw()

            # Status
            status_str = "Vivo" if combatant.is_alive else "Incapacitado"
            status_c = (46, 204, 113, 255) if combatant.is_alive else (192, 57, 43, 255)
            self._get_text(f"r_stat_{actual_idx}", status_str, 500, slot_cy, status_c, 7, bold=False, anchor_x="center").draw()

            # Visibility Toggle Icon
            vis_icon = "👁️❌" if combatant.is_hidden else "👁️"
            self._get_text(f"r_vis_{actual_idx}", vis_icon, panel_w - 40, slot_cy, (255, 255, 255, 255), 9, bold=False, anchor_x="center").draw()

        # Indicador visual de rolagem / Barra de rolagem
        if len(combatants) > self.__scroll_list.visible_item_count:
            self.__scroll_list._draw_scroll_indicator(self.text_cache)

        # 5. Painel Inferior: Despachante de Dano / Cura do Alvo Selecionado
        rendered_rows = min(len(combatants), max_rows)
        disp_top = table_top - table_h - rendered_rows * (self.__item_height + self.__spacing) - 8
        disp_h = 168
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, disp_top - disp_h / 2, panel_w - 24, disp_h), (18, 24, 34, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, disp_top - disp_h / 2, panel_w - 24, disp_h), (50, 65, 90, 200), 1)

        sel_combatant = self.combat_manager.get_combatant(self.selected_combatant_uid or "")
        if sel_combatant:
            # Resumo do Alvo
            size_str = getattr(sel_combatant, "size", "Medium")
            self._get_text("disp_title", f"ALVO SELECIONADO: {sel_combatant.name.upper()} ({size_str})", 24, disp_top - 14, (241, 196, 15, 255), 9, bold=True).draw()
            hp_info = f"HP: {sel_combatant.current_hp}/{sel_combatant.max_hp} • CA: {sel_combatant.armor_class} • Inic: {sel_combatant.initiative_score} • Tam: {size_str}"
            self._get_text("disp_hp_info", hp_info, 24, disp_top - 28, (200, 210, 225, 255), 8, bold=False).draw()

            # Barra de Vida Visual
            bar_w = panel_w - 60
            bar_h = 8
            bar_y = disp_top - 40
            pct = max(0.0, min(1.0, sel_combatant.current_hp / max(1, sel_combatant.max_hp)))

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, bar_y, bar_w, bar_h), (40, 45, 55, 255))
            if pct > 0:
                fill_w = bar_w * pct
                hp_bar_color = (46, 204, 113, 255) if pct > 0.5 else ((241, 196, 15, 255) if pct > 0.2 else (231, 76, 60, 255))
                arcade.draw_rect_filled(arcade.XYWH(30 + fill_w / 2, bar_y, fill_w, bar_h), hp_bar_color)

            # Botões Rápidos de Dano (-1, -5, -10, -20)
            btn_dmg_y = disp_top - 62
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70) / 8

            for i, val in enumerate(dmg_vals):
                bx = 30 + i * (dmg_btn_w + 4) + dmg_btn_w / 2
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (192, 57, 43, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (231, 76, 60, 255), 1)
                self._get_text(f"b_dmg_{val}", str(val), bx, btn_dmg_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botões Rápidos de Cura (+1, +5, +10, +20)
            heal_vals = [1, 5, 10, 20]
            for i, val in enumerate(heal_vals):
                bx = 30 + (i + 4) * (dmg_btn_w + 4) + dmg_btn_w / 2
                arcade.draw_rect_filled(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (39, 174, 96, 255))
                arcade.draw_rect_outline(arcade.XYWH(bx, btn_dmg_y, dmg_btn_w, 20), (46, 204, 113, 255), 1)
                self._get_text(f"b_heal_{val}", f"+{val}", bx, btn_dmg_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Linha Customizada de Dano/Cura
            custom_y = disp_top - 90

            # Stepper [-]
            arcade.draw_rect_filled(arcade.XYWH(45, custom_y, 26, 22), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(45, custom_y, 26, 22), (70, 90, 120, 200), 1)
            self._get_text("b_cust_minus", "[-]", 45, custom_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Caixa do Valor
            arcade.draw_rect_filled(arcade.XYWH(90, custom_y, 48, 22), (15, 20, 28, 255))
            arcade.draw_rect_outline(arcade.XYWH(90, custom_y, 48, 22), (241, 196, 15, 200), 1)
            self._get_text("cust_val_t", str(self.custom_hp_value), 90, custom_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

            # Stepper [+]
            arcade.draw_rect_filled(arcade.XYWH(135, custom_y, 26, 22), (45, 55, 70, 255))
            arcade.draw_rect_outline(arcade.XYWH(135, custom_y, 26, 22), (70, 90, 120, 200), 1)
            self._get_text("b_cust_plus", "[+]", 135, custom_y, (241, 196, 15, 255), 9, bold=True, anchor_x="center").draw()

            # Botão Aplicar Dano Customizado
            arcade.draw_rect_filled(arcade.XYWH(215, custom_y, 100, 22), (192, 57, 43, 255))
            arcade.draw_rect_outline(arcade.XYWH(215, custom_y, 100, 22), (231, 76, 60, 255), 1)
            self._get_text("b_apply_dmg", f"⚔️ Dano ({self.custom_hp_value})", 215, custom_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botão Aplicar Cura Customizada
            arcade.draw_rect_filled(arcade.XYWH(325, custom_y, 100, 22), (39, 174, 96, 255))
            arcade.draw_rect_outline(arcade.XYWH(325, custom_y, 100, 22), (46, 204, 113, 255), 1)
            self._get_text("b_apply_heal", f"💚 Cura ({self.custom_hp_value})", 325, custom_y, (255, 255, 255, 255), 8, bold=True, anchor_x="center").draw()

            # Botão Ocultar / Revelar no Grid
            vis_str = "👁️ Revelar" if sel_combatant.is_hidden else "👁️ Ocultar"
            vis_bg = (120, 40, 31, 255) if sel_combatant.is_hidden else (52, 73, 94, 255)
            arcade.draw_rect_filled(arcade.XYWH(panel_w - 75, custom_y, 90, 22), vis_bg)
            arcade.draw_rect_outline(arcade.XYWH(panel_w - 75, custom_y, 90, 22), (100, 120, 150, 200), 1)
            self._get_text("b_toggle_vis", vis_str, panel_w - 75, custom_y, (240, 240, 245, 255), 8, bold=True, anchor_x="center").draw()

            # 5.4. Painel de Condições Canônicas D&D 5E (11 Toggles)
            cond_title_y = disp_top - 114
            self._get_text("disp_cond_title", "CONDIÇÕES TÁTICAS (D&D 5E):", 24, cond_title_y, (180, 190, 205, 255), 7.5, bold=True).draw()

            cond_names = StatusIconAtlas.get_condition_names()
            cond_btn_y = disp_top - 140
            cond_btn_h = 24
            cond_spacing = 3
            cond_total_w = panel_w - 48
            cond_btn_w = (cond_total_w - (len(cond_names) - 1) * cond_spacing) / len(cond_names)

            for idx, cond_name in enumerate(cond_names):
                bx = 24 + idx * (cond_btn_w + cond_spacing) + cond_btn_w / 2
                is_active = sel_combatant.has_condition(cond_name)
                tex = StatusIconAtlas.get_condition_texture(cond_name)

                if is_active:
                    bg_color = (65, 50, 15, 255)
                    border_color = (241, 196, 15, 255)
                    border_w = 2.0
                else:
                    bg_color = (24, 30, 42, 255)
                    border_color = (50, 65, 88, 180)
                    border_w = 1.0

                arcade.draw_rect_filled(arcade.XYWH(bx, cond_btn_y, cond_btn_w, cond_btn_h), bg_color)
                arcade.draw_rect_outline(arcade.XYWH(bx, cond_btn_y, cond_btn_w, cond_btn_h), border_color, border_w)

                if tex is not None:
                    arcade.draw_texture_rect(
                        tex,
                        arcade.XYWH(bx, cond_btn_y, 13, 13),
                        pixelated=True,
                    )

        # 6. Modal de Confirmação ao Finalizar Combate (Limpar ou Manter Save)
        if self.pending_end_combat_modal:
            self._draw_end_combat_modal(panel_w, top_y)

    def _draw_end_combat_modal(self, panel_w: float, top_y: float) -> None:
        """Renderiza o modal de confirmação para finalizar combate e limpar ou manter o save."""
        # Backdrop semitransparente
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, top_y / 2, panel_w, top_y), (10, 14, 20, 220))

        modal_w = min(panel_w - 24, 460.0)
        modal_h = 190.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2

        # Caixa do Diálogo Dark Fantasy
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (22, 28, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (192, 57, 43, 255), 2.0)

        # Cabeçalho de Alerta
        self._get_text("end_mod_hdr", "🏁 FINALIZAR COMBATE TÁTICO", modal_cx, modal_cy + modal_h / 2 - 20, (241, 196, 15, 255), 10, bold=True, anchor_x="center").draw()

        # Mensagem do Modal
        msg_line1 = "Deseja encerrar o combate e limpar o save residual do disco,"
        msg_line2 = "ou manter o arquivo de progresso salvo para consultas futuras?"
        self._get_text("end_mod_m1", msg_line1, modal_cx, modal_cy + 22, (220, 225, 235, 255), 8.5, bold=False, anchor_x="center").draw()
        self._get_text("end_mod_m2", msg_line2, modal_cx, modal_cy + 5, (241, 196, 15, 255), 8.5, bold=True, anchor_x="center").draw()

        # Botões de Ação
        btn_y = modal_cy - modal_h / 2 + 55
        btn_w = (modal_w - 32) / 2

        # 1. [ 🗑️ Limpar Save & Sair ]
        b_clean_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_clean_x, btn_y, btn_w - 4, 32), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_clean_x, btn_y, btn_w - 4, 32), (231, 76, 60, 255), 2)
        self._get_text("end_mod_b_clean", "🗑️ Limpar Save & Sair", b_clean_x, btn_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # 2. [ 💾 Manter Save & Sair ]
        b_keep_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_keep_x, btn_y, btn_w - 4, 32), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_keep_x, btn_y, btn_w - 4, 32), (46, 204, 113, 255), 2)
        self._get_text("end_mod_b_keep", "💾 Manter Save & Sair", b_keep_x, btn_y, (255, 255, 255, 255), 8.5, bold=True, anchor_x="center").draw()

        # 3. [ ❌ Cancelar ]
        btn_can_y = modal_cy - modal_h / 2 + 20
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, btn_can_y, modal_w - 28, 24), (70, 90, 120, 200), 1)
        self._get_text("end_mod_b_can", "❌ Cancelar", modal_cx, btn_can_y, (200, 210, 225, 255), 8, bold=True, anchor_x="center").draw()

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        open_initiative_modal_callback: Callable[[], None],
    ) -> bool:
        """Processa cliques na aba de combate ativo."""
        # 0. Interceptação Modal de Criação e Inserção de Token (AddTokenModal)
        if self.add_token_modal.is_open:
            win_w = self.dm_window.width if self.dm_window is not None else panel_w
            win_h = self.dm_window.height if self.dm_window is not None else top_y
            return self.add_token_modal.handle_click(x, y, win_w, win_h)

        # Interceptação Modal de Encerramento com Save
        if self.pending_end_combat_modal:
            modal_w = min(panel_w - 24, 460.0)
            modal_h = 190.0
            modal_cx = panel_w / 2
            modal_cy = top_y / 2
            btn_y = modal_cy - modal_h / 2 + 55
            btn_w = (modal_w - 32) / 2

            b_clean_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
            b_keep_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
            btn_can_y = modal_cy - modal_h / 2 + 20

            # Clique em [ 🗑️ Limpar Save & Sair ]
            if abs(y - btn_y) <= 16 and abs(x - b_clean_x) <= (btn_w - 4) / 2:
                logger.info("Encerrando combate e limpando save do disco.")
                self.combat_manager.delete_save_state()
                self.pending_end_combat_modal = False
                self.session_manager.end_combat(DisplayState.IDLE)
                return True

            # Clique em [ 💾 Manter Save & Sair ]
            if abs(y - btn_y) <= 16 and abs(x - b_keep_x) <= (btn_w - 4) / 2:
                logger.info("Encerrando combate preservando save no disco.")
                self.pending_end_combat_modal = False
                self.session_manager.end_combat(DisplayState.IDLE)
                return True

            # Clique em [ ❌ Cancelar ]
            if abs(y - btn_can_y) <= 12 and abs(x - modal_cx) <= (modal_w - 28) / 2:
                logger.info("Encerramento de combate cancelado pelo usuário.")
                self.pending_end_combat_modal = False
                return True

            # Clique fora fecha modal
            if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
                self.pending_end_combat_modal = False
                return True

            return True

        # 1. Barra de Ações Rápidas de Combate (6 Botões OOD)
        bar_y = top_y - 20
        btn_w = (panel_w - 44) / 6
        btn_h = 28

        if abs(y - bar_y) <= btn_h / 2:
            # Botão 1: Rolar Iniciativas
            b1_x = 12 + 0 * (btn_w + 4) + btn_w / 2
            if abs(x - b1_x) <= btn_w / 2:
                open_initiative_modal_callback()
                return True

            # Botão 2: Adicionar Token Dinâmico
            b2_x = 12 + 1 * (btn_w + 4) + btn_w / 2
            if abs(x - b2_x) <= btn_w / 2:
                self.add_token_modal.open()
                return True

            # Botão 3: Turno Anterior
            b3_x = 12 + 2 * (btn_w + 4) + btn_w / 2
            if abs(x - b3_x) <= btn_w / 2:
                self.combat_manager.previous_turn()
                return True

            # Botão 4: Próximo Turno
            b4_x = 12 + 3 * (btn_w + 4) + btn_w / 2
            if abs(x - b4_x) <= btn_w / 2:
                self.combat_manager.next_turn()
                return True

            # Botão 5: Pausar e Salvar Combate
            b5_x = 12 + 4 * (btn_w + 4) + btn_w / 2
            if abs(x - b5_x) <= btn_w / 2:
                self.trigger_save_combat()
                return True

            # Botão 6: Finalizar Combate
            b6_x = 12 + 5 * (btn_w + 4) + btn_w / 2
            if abs(x - b6_x) <= btn_w / 2:
                if self.combat_manager.has_save_state():
                    self.pending_end_combat_modal = True
                    logger.info("Save detectado ao finalizar combate. Abrindo modal de confirmação.")
                else:
                    self.session_manager.end_combat(DisplayState.IDLE)
                return True

        # 2. Cliques no Painel de Feitiços (SpellAoEPanel)
        info_y = bar_y - 24
        if self.spell_aoe_panel.handle_click(x, y, panel_w, info_y - 12):
            return True

        spell_body_h = 82 if not self.spell_aoe_panel.is_collapsed else 0
        spell_next_y = info_y - 12 - (28 + spell_body_h) - 8

        # 3. Cliques no Painel de Névoa de Guerra (FogControlPanel)
        if self.fog_panel.handle_click(x, y, panel_w, spell_next_y):
            return True

        fog_body_h = 68 if not self.fog_panel.is_collapsed else 0
        fog_next_y = spell_next_y - (26 + fog_body_h) - 8

        # 4. Cliques nas Linhas da Tabela de Combatentes (via DiscreteScrollList)
        table_top = fog_next_y
        table_h = 22
        panels_collapsed = (1 if self.spell_aoe_panel.is_collapsed else 0) + (1 if self.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2

        combatants = self.combat_manager.turn_order if self.combat_manager.has_combat_started else self.combat_manager.combatants
        self.__scroll_list.items = combatants
        self.__scroll_list.visible_item_count = max_rows
        list_w = panel_w - 24
        list_h = max_rows * (self.__item_height + self.__spacing)
        list_x = 12
        list_top_y = table_top - table_h
        self.__scroll_list.set_bounds(list_x, list_top_y, list_w, list_h)

        for slot_idx, (actual_idx, combatant) in enumerate(self.__scroll_list.visible_items):
            slot_cx, slot_cy, slot_w, slot_h = self.__scroll_list.get_slot_rect(slot_idx)
            if abs(y - slot_cy) <= slot_h / 2:
                # Clique no ícone de visibilidade (lado direito)
                if abs(x - (panel_w - 40)) <= 20:
                    self.combat_manager.toggle_combatant_visibility(combatant.uid)
                    return True

                # Clique para selecionar o combatente
                if abs(x - slot_cx) <= slot_w / 2:
                    self.selected_combatant_uid = combatant.uid
                    return True

        # 5. Cliques no Despachante de Dano e Cura
        rendered_rows = min(len(combatants), max_rows)
        disp_top = table_top - table_h - rendered_rows * (self.__item_height + self.__spacing) - 8

        sel_combatant = self.combat_manager.get_combatant(self.selected_combatant_uid or "")
        if sel_combatant:
            btn_dmg_y = disp_top - 62
            dmg_vals = [-1, -5, -10, -20]
            dmg_btn_w = (panel_w - 70) / 8

            # Dano Rápido
            if abs(y - btn_dmg_y) <= 11:
                for i, val in enumerate(dmg_vals):
                    bx = 30 + i * (dmg_btn_w + 4) + dmg_btn_w / 2
                    if abs(x - bx) <= dmg_btn_w / 2:
                        self.combat_manager.apply_damage(sel_combatant.uid, abs(val))
                        return True

                # Cura Rápida
                heal_vals = [1, 5, 10, 20]
                for i, val in enumerate(heal_vals):
                    bx = 30 + (i + 4) * (dmg_btn_w + 4) + dmg_btn_w / 2
                    if abs(x - bx) <= dmg_btn_w / 2:
                        self.combat_manager.apply_heal(sel_combatant.uid, val)
                        return True

            custom_y = disp_top - 90
            if abs(y - custom_y) <= 12:
                # Stepper [-]
                if abs(x - 45) <= 13:
                    self.custom_hp_value = max(1, self.custom_hp_value - 1)
                    return True

                # Stepper [+]
                if abs(x - 135) <= 13:
                    self.custom_hp_value = min(999, self.custom_hp_value + 1)
                    return True

                # Dano Customizado
                if abs(x - 215) <= 50:
                    self.combat_manager.apply_damage(sel_combatant.uid, self.custom_hp_value)
                    return True

                # Cura Customizada
                if abs(x - 325) <= 50:
                    self.combat_manager.apply_heal(sel_combatant.uid, self.custom_hp_value)
                    return True

                # Ocultar / Revelar
                if abs(x - (panel_w - 75)) <= 45:
                    self.combat_manager.toggle_combatant_visibility(sel_combatant.uid)
                    return True

            # Cliques nas Condições Táticas D&D 5E (11 Toggles)
            cond_btn_y = disp_top - 140
            cond_btn_h = 24
            if abs(y - cond_btn_y) <= cond_btn_h / 2:
                cond_names = StatusIconAtlas.get_condition_names()
                cond_spacing = 3
                cond_total_w = panel_w - 48
                cond_btn_w = (cond_total_w - (len(cond_names) - 1) * cond_spacing) / len(cond_names)
                for idx, cond_name in enumerate(cond_names):
                    bx = 24 + idx * (cond_btn_w + cond_spacing) + cond_btn_w / 2
                    if abs(x - bx) <= cond_btn_w / 2:
                        self.combat_manager.toggle_condition(sel_combatant.uid, cond_name)
                        return True

        return False

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """Processa a rolagem discreta com a roda do mouse na lista de combatentes."""
        if self.pending_end_combat_modal or self.add_token_modal.is_open:
            return False
        return self.__scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        """Repassa evento de arraste do mouse para o painel de magias."""
        return self.spell_aoe_panel.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def handle_mouse_release(self, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        """Repassa evento de liberação de clique para o painel de magias."""
        self.spell_aoe_panel.handle_mouse_release(x, y, button, modifiers)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        """Repassa teclas para os inputs do modal de token ou painel de magias."""
        if self.add_token_modal.is_open:
            if self.add_token_modal.handle_key_press(symbol, modifiers):
                return True
        return self.spell_aoe_panel.handle_key_press(symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        """Repassa liberação de teclas para o modal de token ou painel de magias."""
        if self.add_token_modal.is_open:
            self.add_token_modal.handle_key_release(symbol, modifiers)
        self.spell_aoe_panel.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        """Repassa texto digitado para os inputs do modal de token ou painel de magias."""
        if self.add_token_modal.is_open:
            if self.add_token_modal.handle_text_input(text):
                return True
        return self.spell_aoe_panel.handle_text_input(text)

    def on_update(self, dt: float) -> None:
        """Atualiza animações e inputs do painel de feitiços, névoa, modal de token e toast de salvamento."""
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
            if self.toast_timer == 0:
                self.toast_message = None

        self.spell_aoe_panel.on_update(dt)
        self.fog_panel.fog_manager = self.combat_manager.fog_manager
        self.fog_panel.on_update(dt)
        self.add_token_modal.on_update(dt)

