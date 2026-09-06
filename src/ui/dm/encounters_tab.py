import logging
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple
import arcade
from ...manager.session_manager import SessionManager
from ...domain.loaders.encounter_loader import EncounterLoader
from ..components.discrete_scroll_list import DiscreteScrollList

logger = logging.getLogger(__name__)


class EncountersTabView:
    """
    Componente da Aba de Encontros (Lista de arquivos JSON com DiscreteScrollList,
    detalhes, acionador de combate, edição e exclusão segura Poka-Yoke).
    """

    def __init__(
        self,
        session_manager: SessionManager,
        dm_window: Optional[arcade.Window] = None,
    ) -> None:
        self.session_manager = session_manager
        self.dm_window = dm_window
        self.selected_index: int = 0
        self.encounters_list: List[Dict[str, Any]] = []
        self.text_cache: Dict[str, arcade.Text] = {}

        # Componente OOD de Paginação e Rolagem Discreta
        self.scroll_list: DiscreteScrollList = DiscreteScrollList(
            item_height=52,
            spacing=6,
        )

        # Estado do Modal de Confirmação de Exclusão (Poka-Yoke)
        self.pending_delete_encounter: Optional[Dict[str, Any]] = None

        self.refresh()

    def refresh(self) -> None:
        """Recarrega a lista de arquivos de encontro disponíveis no diretório creations/encounters/."""
        self.encounters_list = self.session_manager.list_available_encounters()
        self.scroll_list.items = self.encounters_list
        if self.encounters_list and self.selected_index >= len(self.encounters_list):
            self.selected_index = max(0, len(self.encounters_list) - 1)

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

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """Processa a rolagem discreta com a roda do mouse na lista de encontros."""
        if self.pending_delete_encounter is not None:
            return True
        return self.scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha a lista de encontros via DiscreteScrollList, cartão de detalhes e modal de exclusão."""
        # 1. Cabeçalho da Seção
        sec_y = top_y - 20
        self._get_text("enc_sec_t", "ARQUIVOS DE ENCONTRO DISPONÍVEIS", 16, sec_y, (241, 196, 15, 255), 11, bold=True).draw()

        # Botão Atualizar
        btn_ref_x = panel_w - 70
        arcade.draw_rect_filled(arcade.XYWH(btn_ref_x, sec_y, 80, 24), (30, 40, 55, 255))
        arcade.draw_rect_outline(arcade.XYWH(btn_ref_x, sec_y, 80, 24), (70, 90, 120, 200), 1)
        self._get_text("enc_btn_ref", "🔄 Atualizar", btn_ref_x, sec_y, (200, 210, 225, 255), 8, bold=True, anchor_x="center").draw()

        # 2. Configuração do Espaço da Lista Rolável
        list_top = sec_y - 22
        card_h = 210
        list_h = max(80.0, list_top - card_h - 16.0)

        self.scroll_list.set_bounds(x=12.0, y=list_top, width=panel_w - 24.0, height=list_h)
        self.scroll_list.items = self.encounters_list

        if not self.encounters_list:
            self._get_text("enc_empty", "Nenhum arquivo JSON de encontro encontrado em creations/encounters/", 16, list_top - 20, (160, 175, 195, 255), 10, bold=False).draw()
        else:
            visible_items = self.scroll_list.visible_items
            has_scrollbar = len(self.encounters_list) > self.scroll_list.visible_item_count

            for slot_idx, (idx, enc) in enumerate(visible_items):
                slot_cx, slot_cy, slot_w, slot_h = self.scroll_list.get_slot_rect(slot_idx)
                is_selected = (idx == self.selected_index)

                bg_c = (35, 48, 68, 255) if is_selected else (22, 28, 38, 255)
                bd_c = (241, 196, 15, 255) if is_selected else (45, 58, 78, 180)

                arcade.draw_rect_filled(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), bg_c)
                arcade.draw_rect_outline(arcade.XYWH(slot_cx, slot_cy, slot_w, slot_h), bd_c, 2 if is_selected else 1)

                # Título e Subtítulo
                title_str = enc.get("title") or enc.get("filename") or enc.get("file_name") or enc.get("uid", "Encontro")
                self._get_text(f"enc_item_t_{idx}", f"⚔️ {title_str[:28]}", slot_cx - slot_w / 2 + 12, slot_cy + 9, (241, 196, 15, 255) if is_selected else (220, 225, 235, 255), 9, bold=True).draw()

                filename_str = enc.get("filename") or enc.get("file_name") or enc.get("path", "")
                count = enc.get("combatants_count", 0)
                sub_str = f"Arquivo: {filename_str[:22]} • {count} combatentes"
                self._get_text(f"enc_item_s_{idx}", sub_str, slot_cx - slot_w / 2 + 12, slot_cy - 10, (140, 155, 175, 255), 7.5, bold=False).draw()

                # Botões de Ação no Card
                btn_offset_right = 10 if not has_scrollbar else 16

                # [ 🗑️ Excluir ]
                b_del_w = 48
                b_del_x = slot_cx + slot_w / 2 - btn_offset_right - b_del_w / 2
                arcade.draw_rect_filled(arcade.XYWH(b_del_x, slot_cy, b_del_w, 24), (120, 35, 35, 255))
                arcade.draw_rect_outline(arcade.XYWH(b_del_x, slot_cy, b_del_w, 24), (180, 50, 50, 200), 1)
                self._get_text(f"b_del_{idx}", "🗑️ Excluir", b_del_x, slot_cy, (255, 200, 200, 255), 7, bold=True, anchor_x="center").draw()

                # [ ✏️ Editar ]
                b_edit_w = 48
                b_edit_x = b_del_x - b_del_w / 2 - 4 - b_edit_w / 2
                arcade.draw_rect_filled(arcade.XYWH(b_edit_x, slot_cy, b_edit_w, 24), (35, 55, 80, 255))
                arcade.draw_rect_outline(arcade.XYWH(b_edit_x, slot_cy, b_edit_w, 24), (70, 110, 160, 200), 1)
                self._get_text(f"b_edit_{idx}", "✏️ Editar", b_edit_x, slot_cy, (180, 220, 255, 255), 7, bold=True, anchor_x="center").draw()

            # Indicador de Rolagem Discreta
            if has_scrollbar:
                self.scroll_list._draw_scroll_indicator(self.text_cache)

        # 3. Cartão de Detalhes e Ações do Encontro Selecionado
        card_top = list_top - list_h - 10
        card_cy = card_top - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), (18, 23, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), (50, 65, 90, 200), 1)

        sel_enc = self.encounters_list[self.selected_index] if (self.encounters_list and 0 <= self.selected_index < len(self.encounters_list)) else None
        if sel_enc:
            title_str = sel_enc.get("title") or sel_enc.get("filename") or sel_enc.get("file_name", "")
            filename_str = sel_enc.get("filename") or sel_enc.get("file_name") or sel_enc.get("path", "")
            map_str = sel_enc.get("map_path") or sel_enc.get("map_source") or sel_enc.get("map_file") or "assets/images/battlemaps/forest_01.png"

            self._get_text("enc_d_t", f"DETALHES DO ENCONTRO: {title_str[:32]}", 24, card_top - 18, (241, 196, 15, 255), 10, bold=True).draw()
            self._get_text("enc_d_f", f"• Arquivo: {filename_str}", 24, card_top - 38, (200, 210, 225, 255), 8.5, bold=False).draw()
            self._get_text("enc_d_m", f"• Mapa: {map_str[:42]}", 24, card_top - 56, (200, 210, 225, 255), 8.5, bold=False).draw()

            grid_info = sel_enc.get("grid", {})
            cols = grid_info.get("columns", 25) if isinstance(grid_info, dict) else 25
            feet = grid_info.get("feet_per_square", 5) if isinstance(grid_info, dict) else 5
            self._get_text("enc_d_g", f"• Grid Tático: {cols} colunas • {feet} ft/quadrado", 24, card_top - 74, (100, 200, 255, 255), 8.5, bold=True).draw()

            comb_names = ", ".join(sel_enc.get("combatant_names", [])) if "combatant_names" in sel_enc else f"{sel_enc.get('combatants_count', 0)} combatentes"
            self._get_text("enc_d_c", f"• Combatentes: {comb_names[:58]}...", 24, card_top - 92, (180, 190, 205, 255), 8, bold=False).draw()

            # Botões Secundários no Card de Detalhes
            btn_sub_y = card_top - 122
            btn_sub_w = (panel_w - 36) / 2

            # [ ✏️ Editar Encontro ]
            b_d_edit_x = 12 + btn_sub_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_d_edit_x, btn_sub_y, btn_sub_w - 4, 26), (35, 55, 80, 255))
            arcade.draw_rect_outline(arcade.XYWH(b_d_edit_x, btn_sub_y, btn_sub_w - 4, 26), (70, 110, 160, 200), 1)
            self._get_text("enc_b_d_edit", "✏️ Editar Encontro", b_d_edit_x, btn_sub_y, (180, 220, 255, 255), 8.5, bold=True, anchor_x="center").draw()

            # [ 🗑️ Excluir Encontro ]
            b_d_del_x = 12 + btn_sub_w + btn_sub_w / 2
            arcade.draw_rect_filled(arcade.XYWH(b_d_del_x, btn_sub_y, btn_sub_w - 4, 26), (120, 35, 35, 255))
            arcade.draw_rect_outline(arcade.XYWH(b_d_del_x, btn_sub_y, btn_sub_w - 4, 26), (180, 50, 50, 200), 1)
            self._get_text("enc_b_d_del", "🗑️ Excluir Encontro", b_d_del_x, btn_sub_y, (255, 200, 200, 255), 8.5, bold=True, anchor_x="center").draw()

            # Botão Principal [ ▶ INICIAR ENCONTRO TÁTICO ]
            btn_start_y = card_top - 165
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_start_y, panel_w - 40, 36), (192, 57, 43, 255))
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_start_y, panel_w - 40, 36), (231, 76, 60, 255), 2)
            self._get_text("enc_b_start", "▶ INICIAR ENCONTRO TÁTICO", panel_w / 2, btn_start_y, (255, 255, 255, 255), 10.5, bold=True, anchor_x="center").draw()

        # 4. Modal de Confirmação de Exclusão (Poka-Yoke)
        if self.pending_delete_encounter is not None:
            self._draw_delete_confirmation_modal(panel_w, top_y)

    def _draw_delete_confirmation_modal(self, panel_w: float, top_y: float) -> None:
        """Renderiza o modal de confirmação de exclusão sobreposto."""
        # Backdrop semitransparente
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, top_y / 2, panel_w, top_y), (10, 14, 20, 220))

        enc = self.pending_delete_encounter or {}
        title = enc.get("title") or enc.get("filename") or enc.get("uid", "Encontro")

        modal_w = min(panel_w - 28, 420.0)
        modal_h = 175.0
        modal_cx = panel_w / 2
        modal_cy = top_y / 2

        # Caixa do Diálogo Dark Fantasy
        arcade.draw_rect_filled(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (22, 28, 38, 255))
        arcade.draw_rect_outline(arcade.XYWH(modal_cx, modal_cy, modal_w, modal_h), (192, 57, 43, 255), 2.0)

        # Cabeçalho de Alerta
        self._get_text("del_mod_hdr", "⚠️ CONFIRMAR EXCLUSÃO DE ENCONTRO", modal_cx, modal_cy + modal_h / 2 - 20, (241, 196, 15, 255), 10, bold=True, anchor_x="center").draw()

        # Mensagem Poka-Yoke
        msg_line1 = f"Deseja realmente excluir o encontro '{title[:30]}'?"
        msg_line2 = "Esta ação não pode ser desfeita."
        self._get_text("del_mod_m1", msg_line1, modal_cx, modal_cy + 12, (220, 225, 235, 255), 8.5, bold=False, anchor_x="center").draw()
        self._get_text("del_mod_m2", msg_line2, modal_cx, modal_cy - 8, (255, 140, 140, 255), 8.5, bold=True, anchor_x="center").draw()

        # Botões de Ação do Modal
        btn_y = modal_cy - modal_h / 2 + 30
        btn_w = (modal_w - 36) / 2

        # [ Cancelar ]
        b_can_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_can_x, btn_y, btn_w - 4, 32), (44, 62, 80, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_can_x, btn_y, btn_w - 4, 32), (70, 90, 120, 200), 1)
        self._get_text("del_mod_b_can", "Cancelar", b_can_x, btn_y, (236, 240, 241, 255), 9, bold=True, anchor_x="center").draw()

        # [ Confirmar Exclusão ]
        b_conf_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2
        arcade.draw_rect_filled(arcade.XYWH(b_conf_x, btn_y, btn_w - 4, 32), (192, 57, 43, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_conf_x, btn_y, btn_w - 4, 32), (231, 76, 60, 255), 2)
        self._get_text("del_mod_b_conf", "Confirmar Exclusão", b_conf_x, btn_y, (255, 255, 255, 255), 9, bold=True, anchor_x="center").draw()

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        on_start_combat_callback: Callable[[str], None],
        on_edit_encounter_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """Processa cliques na aba de encontros com suporte a exclusão modal e edição."""
        # Interceptação Modal de Exclusão Poka-Yoke
        if self.pending_delete_encounter is not None:
            modal_w = min(panel_w - 28, 420.0)
            modal_h = 175.0
            modal_cx = panel_w / 2
            modal_cy = top_y / 2
            btn_y = modal_cy - modal_h / 2 + 30
            btn_w = (modal_w - 36) / 2

            b_can_x = modal_cx - modal_w / 2 + 12 + btn_w / 2
            b_conf_x = modal_cx - modal_w / 2 + 12 + btn_w + btn_w / 2

            # Clique em [ Cancelar ]
            if abs(y - btn_y) <= 16 and abs(x - b_can_x) <= (btn_w - 4) / 2:
                logger.info("Exclusão de encontro cancelada pelo usuário.")
                self.pending_delete_encounter = None
                return True

            # Clique em [ Confirmar Exclusão ]
            if abs(y - btn_y) <= 16 and abs(x - b_conf_x) <= (btn_w - 4) / 2:
                enc = self.pending_delete_encounter
                uid = enc.get("uid") or enc.get("filename") or enc.get("path", "")
                success = self.session_manager.delete_encounter(uid)
                if success:
                    logger.info(f"Encontro '{uid}' excluído após confirmação do usuário.")
                self.pending_delete_encounter = None
                self.refresh()
                return True

            # Clique fora do diálogo fecha modal
            if not (abs(x - modal_cx) <= modal_w / 2 and abs(y - modal_cy) <= modal_h / 2):
                self.pending_delete_encounter = None
                return True

            return True

        sec_y = top_y - 20

        # Botão Atualizar
        btn_ref_x = panel_w - 70
        if abs(y - sec_y) <= 12 and abs(x - btn_ref_x) <= 40:
            self.refresh()
            return True

        # Interação com a Lista Rolável Discreta
        visible_items = self.scroll_list.visible_items
        has_scrollbar = len(self.encounters_list) > self.scroll_list.visible_item_count

        for slot_idx, (idx, enc) in enumerate(visible_items):
            slot_cx, slot_cy, slot_w, slot_h = self.scroll_list.get_slot_rect(slot_idx)
            left = slot_cx - slot_w / 2.0
            right = slot_cx + slot_w / 2.0
            top = slot_cy + slot_h / 2.0
            bottom = slot_cy - slot_h / 2.0

            if left <= x <= right and bottom <= y <= top:
                btn_offset_right = 10 if not has_scrollbar else 16

                # Botão Excluir no Card
                b_del_w = 48
                b_del_x = slot_cx + slot_w / 2 - btn_offset_right - b_del_w / 2
                if abs(y - slot_cy) <= 12 and abs(x - b_del_x) <= b_del_w / 2:
                    self.selected_index = idx
                    self.pending_delete_encounter = enc
                    logger.info(f"Aberto modal de confirmação para exclusão de '{enc.get('title')}'")
                    return True

                # Botão Editar no Card
                b_edit_w = 48
                b_edit_x = b_del_x - b_del_w / 2 - 4 - b_edit_w / 2
                if abs(y - slot_cy) <= 12 and abs(x - b_edit_x) <= b_edit_w / 2:
                    self.selected_index = idx
                    if on_edit_encounter_callback is not None:
                        on_edit_encounter_callback(enc)
                    return True

                # Selecionar Card
                self.selected_index = idx
                return True

        # Interação no Cartão de Detalhes
        list_top = sec_y - 22
        card_h = 210
        list_h = max(80.0, list_top - card_h - 16.0)
        card_top = list_top - list_h - 10

        sel_enc = self.encounters_list[self.selected_index] if (self.encounters_list and 0 <= self.selected_index < len(self.encounters_list)) else None
        if sel_enc:
            btn_sub_y = card_top - 122
            btn_sub_w = (panel_w - 36) / 2

            # [ ✏️ Editar Encontro ] no Cartão de Detalhes
            b_d_edit_x = 12 + btn_sub_w / 2
            if abs(y - btn_sub_y) <= 13 and abs(x - b_d_edit_x) <= (btn_sub_w - 4) / 2:
                if on_edit_encounter_callback is not None:
                    on_edit_encounter_callback(sel_enc)
                return True

            # [ 🗑️ Excluir Encontro ] no Cartão de Detalhes
            b_d_del_x = 12 + btn_sub_w + btn_sub_w / 2
            if abs(y - btn_sub_y) <= 13 and abs(x - b_d_del_x) <= (btn_sub_w - 4) / 2:
                self.pending_delete_encounter = sel_enc
                logger.info(f"Aberto modal de confirmação para exclusão de '{sel_enc.get('title')}'")
                return True

            # [ ▶ INICIAR ENCONTRO TÁTICO ]
            btn_start_y = card_top - 165
            if abs(y - btn_start_y) <= 18 and abs(x - panel_w / 2) <= (panel_w - 40) / 2:
                enc_id = sel_enc.get("uid") or sel_enc.get("id") or sel_enc.get("filename") or sel_enc.get("path", "")
                on_start_combat_callback(enc_id)
                return True

        return False
