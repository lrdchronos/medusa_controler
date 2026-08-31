from typing import List, Dict, Any, Callable
import arcade
from ...manager.session_manager import SessionManager


class ShowcaseTabView:
    """
    Componente da Aba Showcase (Lista de mídias/imagens e projetor para a PlayerWindow).
    """

    def __init__(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager
        self.selected_index: int = 0
        self.showcase_list: List[Dict[str, Any]] = []
        self.text_cache: Dict[str, arcade.Text] = {}
        self.refresh()

    def refresh(self) -> None:
        """Recarrega a lista de mídias de showcase disponíveis no diretório assets/images/showcase/."""
        self.showcase_list = self.session_manager.list_available_showcase_images()
        if self.showcase_list and self.selected_index >= len(self.showcase_list):
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
        """Desenha a lista de imagens e o painel de projeção."""
        sec_y = top_y - 20
        self._get_text("shw_sec_t", "MÍDIAS DE CENÁRIO / SHOWCASE", 16, sec_y, (241, 196, 15, 255), 11, bold=True).draw()

        btn_ref_x = panel_w - 70
        arcade.draw_rect_filled(arcade.XYWH(btn_ref_x, sec_y, 80, 24), (30, 40, 55, 255))
        arcade.draw_rect_outline(arcade.XYWH(btn_ref_x, sec_y, 80, 24), (70, 90, 120, 200), 1)
        self._get_text("shw_btn_ref", "🔄 Atualizar", btn_ref_x, sec_y, (200, 210, 225, 255), 8, bold=True, anchor_x="center").draw()

        list_top = sec_y - 22
        item_h = 44
        gap = 6

        if not self.showcase_list:
            self._get_text("shw_empty", "Nenhuma imagem encontrada em assets/images/showcase/", 16, list_top - 20, (160, 175, 195, 255), 10, bold=False).draw()
            return

        for idx, media in enumerate(self.showcase_list[:7]):
            cy = list_top - idx * (item_h + gap) - item_h / 2
            is_selected = (idx == self.selected_index)

            bg_c = (35, 48, 68, 255) if is_selected else (22, 28, 38, 255)
            bd_c = (241, 196, 15, 255) if is_selected else (45, 58, 78, 180)

            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, cy, panel_w - 24, item_h), bg_c)
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, cy, panel_w - 24, item_h), bd_c, 2 if is_selected else 1)

            title_str = media.get("name") or media.get("filename") or media.get("file_name", "Imagem")
            title_str = title_str.replace("_", " ").title()
            self._get_text(f"shw_item_t_{idx}", f"🖼️ {title_str}", 24, cy + 8, (241, 196, 15, 255) if is_selected else (220, 225, 235, 255), 10, bold=True).draw()

            filename_str = media.get("filename") or media.get("file_name") or media.get("path", "")
            sub_str = f"Arquivo: {filename_str}"
            self._get_text(f"shw_item_s_{idx}", sub_str, 24, cy - 10, (140, 155, 175, 255), 8, bold=False).draw()

        # Detalhes da Mídia Selecionada
        card_top = list_top - min(len(self.showcase_list), 7) * (item_h + gap) - 12
        card_h = 180
        card_cy = card_top - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), (18, 23, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, card_cy, panel_w - 24, card_h), (50, 65, 90, 200), 1)

        sel_media = self.showcase_list[self.selected_index] if self.showcase_list else None
        if sel_media:
            title_str = sel_media.get("name") or sel_media.get("filename") or sel_media.get("file_name", "Imagem")
            title_str = title_str.replace("_", " ").title()
            file_path = sel_media.get("path") or sel_media.get("file_path", "")

            self._get_text("shw_d_t", f"MÍDIA SELECIONADA: {title_str}", 24, card_top - 20, (241, 196, 15, 255), 10, bold=True).draw()
            self._get_text("shw_d_p", f"• Caminho: {file_path}", 24, card_top - 48, (200, 210, 225, 255), 9, bold=False).draw()

            btn_proj_y = card_top - 120
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_proj_y, panel_w - 60, 38), (41, 128, 185, 255))
            arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_proj_y, panel_w - 60, 38), (52, 152, 219, 255), 2)
            self._get_text("shw_b_proj", "🖼️ PROJETAR NA TELA DOS JOGADORES", panel_w / 2, btn_proj_y, (255, 255, 255, 255), 11, bold=True, anchor_x="center").draw()

    def handle_click(self, x: float, y: float, panel_w: float, top_y: float) -> bool:
        """Processa cliques na aba de showcase."""
        sec_y = top_y - 20

        btn_ref_x = panel_w - 70
        if abs(y - sec_y) <= 12 and abs(x - btn_ref_x) <= 40:
            self.refresh()
            return True

        list_top = sec_y - 22
        item_h = 44
        gap = 6

        for idx in range(min(len(self.showcase_list), 7)):
            cy = list_top - idx * (item_h + gap) - item_h / 2
            if abs(y - cy) <= item_h / 2 and abs(x - panel_w / 2) <= (panel_w - 24) / 2:
                self.selected_index = idx
                return True

        card_top = list_top - min(len(self.showcase_list), 7) * (item_h + gap) - 12
        btn_proj_y = card_top - 120
        if abs(y - btn_proj_y) <= 19 and abs(x - panel_w / 2) <= (panel_w - 60) / 2:
            if self.showcase_list:
                sel_media = self.showcase_list[self.selected_index]
                file_path = sel_media.get("path") or sel_media.get("file_path", "")
                if file_path:
                    self.session_manager.project_image(file_path)
                return True

        return False
