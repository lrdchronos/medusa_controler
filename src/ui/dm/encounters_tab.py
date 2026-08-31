from typing import List, Dict, Any, Callable
import arcade
from ...manager.session_manager import SessionManager


class EncountersTabView:
    """
    Componente da Aba de Encontros (Lista de arquivos JSON, detalhes e acionador de combate).
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.selected_index: int = 0
        self.encounters_list: List[Dict[str, Any]] = []
        self.text_cache: Dict[str, arcade.Text] = {}
        self.refresh()

    def refresh(self) -> None:
        """Recarrega a lista de arquivos de encontro disponíveis no diretório creations/encounters/."""
        self.encounters_list = self.session_manager.list_available_encounters()
        if self.encounters_list and self.selected_index >= len(self.encounters_list):
            self.selected_index = 0

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

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha a lista de encontros e o cartão de detalhes."""
        # Cabeçalho da Seção
        sec_y = top_y - 20
        self._get_text("enc_sec_t", "ARQUIVOS DE ENCONTRO DISPONÍVEIS", 16, sec_y, (241, 196, 15, 255), 11, bold=True).draw()

        # Botão Atualizar
        btn_ref_x = panel_w - 70
        arcade.draw_rect_filled(arcade.XYWH(btn_ref_x, sec_y, 80, 24), (30, 40, 55, 255))
        arcade.draw_rect_outline(arcade.XYWH(btn_ref_x, sec_y, 80, 24), (70, 90, 120, 200), 1)
        self._get_text("enc_btn_ref", "🔄 Atualizar", btn_ref_x, sec_y, (200, 210, 225, 255), 8, bold=True, anchor_x="center").draw()

        # Lista de Encontros
        list_top = sec_y - 22
        item_h = 44
        gap = 6

        if not self.encounters_list:
            self._get_text("enc_empty", "Nenhum arquivo JSON de encontro encontrado em creations/encounters/", 16, list_top - 20, (160, 175, 195, 255), 10, bold=False).draw()
            return

        for idx, enc in enumerate(self.encounters_list[:7]):
            cy = list_top - idx * (item_h + gap) - item_h / 2
            is_selected = (idx == self.selected_index)

            bg_c = (35, 48, 68, 255) if is_selected else (22, 28, 38, 255)
            bd_c = (241, 196, 15, 255) if is_selected else (45, 58, 78, 180)

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, cy, panel_w - 24, item_h), bg_c)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, cy, panel_w - 24, item_h), bd_c, 2 if is_selected else 1)

            title_str = enc.get("title") or enc.get("filename") or enc.get("file_name") or enc.get("uid", "Encontro")
            self._get_text(f"enc_item_t_{idx}", f"⚔️ {title_str}", 24, cy + 8, (241, 196, 15, 255) if is_selected else (220, 225, 235, 255), 10, bold=True).draw()

            filename_str = enc.get("filename") or enc.get("file_name") or enc.get("path", "")
            count = enc.get("combatants_count", 0)
            sub_str = f"Arquivo: {filename_str} • {count} combatentes"
            self._get_text(f"enc_item_s_{idx}", sub_str, 24, cy - 10, (140, 155, 175, 255), 8, bold=False).draw()

        # Cartão de Detalhes e Início de Encontro
        card_top = list_top - min(len(self.encounters_list), 7) * (item_h + gap) - 12
        card_h = 220
        card_cy = card_top - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), (18, 23, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), (50, 65, 90, 200), 1)

        sel_enc = self.encounters_list[self.selected_index] if self.encounters_list else None
        if sel_enc:
            title_str = sel_enc.get("title") or sel_enc.get("filename") or sel_enc.get("file_name", "")
            filename_str = sel_enc.get("filename") or sel_enc.get("file_name") or sel_enc.get("path", "")
            map_str = sel_enc.get("map_path") or sel_enc.get("map_file") or "assets/images/battlemaps/forest_01.png"

            self._get_text("enc_d_t", f"DETALHES DO ENCONTRO SELECIONADO: {title_str}", 24, card_top - 20, (241, 196, 15, 255), 10, bold=True).draw()
            self._get_text("enc_d_f", f"• Arquivo: {filename_str}", 24, card_top - 44, (200, 210, 225, 255), 9, bold=False).draw()
            self._get_text("enc_d_m", f"• Mapa: {map_str}", 24, card_top - 66, (200, 210, 225, 255), 9, bold=False).draw()

            grid_info = sel_enc.get("grid", {})
            cols = grid_info.get("columns", 25) if isinstance(grid_info, dict) else 25
            feet = grid_info.get("feet_per_square", 5) if isinstance(grid_info, dict) else 5
            self._get_text("enc_d_g", f"• Grid Tático: {cols} colunas • {feet} ft/quadrado", 24, card_top - 88, (100, 200, 255, 255), 9, bold=True).draw()

            comb_names = ", ".join(sel_enc.get("combatant_names", [])) if "combatant_names" in sel_enc else f"{sel_enc.get('combatants_count', 0)} combatentes"
            self._get_text("enc_d_c", f"• Combatentes: {comb_names[:65]}...", 24, card_top - 110, (180, 190, 205, 255), 8, bold=False).draw()

            # Botão Iniciar Encontro
            btn_start_y = card_top - 165
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_start_y, panel_w - 60, 38), (192, 57, 43, 255))
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_start_y, panel_w - 60, 38), (231, 76, 60, 255), 2)
            self._get_text("enc_b_start", "▶ INICIAR ENCONTRO TÁTICO", panel_w / 2, btn_start_y, (255, 255, 255, 255), 11, bold=True, anchor_x="center").draw()

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float, on_start_combat_callback: Callable[[str], None]) -> bool:
        """Processa cliques na aba de encontros."""
        sec_y = top_y - 20

        # Botão Atualizar
        btn_ref_x = panel_w - 70
        if abs(y - sec_y) <= 12 and abs(x - btn_ref_x) <= 40:
            self.refresh()
            return True

        # Clique na Lista de Encontros
        list_top = sec_y - 22
        item_h = 44
        gap = 6

        for idx in range(min(len(self.encounters_list), 7)):
            cy = list_top - idx * (item_h + gap) - item_h / 2
            if abs(y - cy) <= item_h / 2 and abs(x - panel_w / 2) <= (panel_w - 24) / 2:
                self.selected_index = idx
                return True

        # Clique no Botão Iniciar Encontro
        card_top = list_top - min(len(self.encounters_list), 7) * (item_h + gap) - 12
        btn_start_y = card_top - 165
        if abs(y - btn_start_y) <= 19 and abs(x - panel_w / 2) <= (panel_w - 60) / 2:
            if self.encounters_list:
                sel_enc = self.encounters_list[self.selected_index]
                enc_id = sel_enc.get("uid") or sel_enc.get("id") or sel_enc.get("filename") or sel_enc.get("path", "")
                on_start_combat_callback(enc_id)
                return True

        return False
