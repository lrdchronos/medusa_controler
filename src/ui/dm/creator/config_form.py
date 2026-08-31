import os
from typing import Optional, List, Dict, Any, Set, Tuple
import arcade
from .text_input import TextInputWidget, SmartTextInput




class CreatorConfigForm:
    """
    Componente especializado para a Etapa 1 do Criador de Encontros (Formulário e Configuração).
    Gerencia:
      - Entradas de texto inteligentes para Título e Descrição via TextInputWidget.
      - Seletor de Mapa com miniaturas e navegação fluida.
      - Ajustes da grade tática (colunas e pés por quadrado).
      - Seleção de personagens jogadores (checkboxes).
      - Instanciação de monstros presets (steppers de quantidade).
      - Pré-visualização do mapa e resumo dos combatentes.
    """

    def __init__(
        self,
        available_maps: List[Dict[str, str]],
        available_characters: List[Dict[str, Any]],
        available_monsters: List[Dict[str, Any]],
    ) -> None:
        self.available_maps = available_maps
        self.available_characters = available_characters
        self.available_monsters = available_monsters

        # Widgets de Texto com suporte a backspace hold e navegação
        self.title_input = TextInputWidget(
            widget_id="wiz_title",
            placeholder="Digite o título do encontro...",
            initial_text="Emboscada na Floresta",
            max_length=60,
            font_size=9,
        )
        self.description_input = TextInputWidget(
            widget_id="wiz_desc",
            placeholder="Digite a descrição da batalha...",
            initial_text="Grupo de monstros surpreende os heróis em uma clareira.",
            max_length=140,
            font_size=8,
        )

        self.columns: int = 25
        self.feet_per_square: int = 5
        self.selected_map_index: int = 0
        self.is_sunlight: bool = False

        self.selected_character_uids: Set[str] = set()
        self.monster_counts: Dict[str, int] = {}
        self.error_message: Optional[str] = None

        self._init_defaults()

    def _init_defaults(self) -> None:
        if self.available_characters and not self.selected_character_uids:
            for char in self.available_characters:
                self.selected_character_uids.add(char["uid"])

        for mon in self.available_monsters:
            mid = mon["uid"]
            if mid not in self.monster_counts:
                self.monster_counts[mid] = 2 if "kobold" in mid.lower() else 0

    def update_sources(
        self,
        available_maps: List[Dict[str, str]],
        available_characters: List[Dict[str, Any]],
        available_monsters: List[Dict[str, Any]],
    ) -> None:
        self.available_maps = available_maps
        self.available_characters = available_characters
        self.available_monsters = available_monsters
        if self.selected_map_index >= len(self.available_maps):
            self.selected_map_index = 0
        self._init_defaults()

    def update(self, delta_time: float) -> None:
        self.title_input.update(delta_time)
        self.description_input.update(delta_time)

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida o formulário antes de prosseguir para o palco tático."""
        if not self.title_input.text.strip():
            return False, "O título do encontro é obrigatório!"

        if not self.available_maps:
            return False, "Nenhum mapa disponível encontrado!"

        has_combatants = bool(self.selected_character_uids) or any(q > 0 for q in self.monster_counts.values())
        if not has_combatants:
            return False, "Selecione ao menos um personagem ou monstro!"

        if self.columns <= 0:
            return False, "A grade deve ter pelo menos 1 coluna!"

        if self.feet_per_square <= 0:
            return False, "Pés por quadrado deve ser maior que 0!"

        return True, None

    def get_config_data(self) -> Dict[str, Any]:
        """Retorna os dados consolidados do formulário para o palco de staging."""
        cur_map = self.available_maps[self.selected_map_index] if self.available_maps else {"path": "assets/images/maps/open_field_grass_trees.jpg"}
        return {
            "title": self.title_input.text.strip(),
            "description": self.description_input.text.strip(),
            "map_path": cur_map["path"],
            "map_name": cur_map.get("name", "Mapa"),
            "columns": self.columns,
            "feet_per_square": self.feet_per_square,
            "is_sunlight": self.is_sunlight,
            "selected_character_uids": set(self.selected_character_uids),
            "monster_counts": dict(self.monster_counts),
        }

    # --- Renderização ---

    def draw_form(self, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        """Desenha todo o painel esquerdo da Etapa 1."""
        sec_y = top_y - 18
        self._render_text("wiz_sec_t", "🛠️ CRIADOR DE ENCONTROS (ETAPA 1: CONFIGURAÇÃO)", 16, sec_y, (241, 196, 15, 255), 10, True, text_cache)

        # 1. Campo Título
        lbl_t_y = sec_y - 24
        self._render_text("lbl_title", "• Título do Encontro:", 16, lbl_t_y, (200, 210, 225, 255), 9, True, text_cache)
        box_t_y = lbl_t_y - 18
        self.title_input.draw(panel_w / 2, box_t_y, panel_w - 32, 26, text_cache)

        # Campo Descrição
        lbl_d_y = box_t_y - 22
        self._render_text("lbl_desc", "• Descrição do Encontro:", 16, lbl_d_y, (200, 210, 225, 255), 9, True, text_cache)
        box_d_y = lbl_d_y - 18
        self.description_input.draw(panel_w / 2, box_d_y, panel_w - 32, 26, text_cache)

        # 2. Seletor de Mapa
        map_sec_y = box_d_y - 24
        self._render_text("lbl_map_sec", "• Mapa & Grade Tática:", 16, map_sec_y, (200, 210, 225, 255), 9, True, text_cache)

        map_row_y = map_sec_y - 20
        cur_map = self.available_maps[self.selected_map_index] if self.available_maps else {"name": "Nenhum", "filename": ""}

        # [◀]
        b_prev_m_x = 30
        arcade.draw_rect_filled(arcade.XYWH(b_prev_m_x, map_row_y, 26, 24), (35, 45, 60, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_prev_m_x, map_row_y, 26, 24), (70, 90, 120, 200), 1)
        self._render_text("b_map_prev", "◀", b_prev_m_x, map_row_y, (241, 196, 15, 255), 10, True, text_cache, anchor_x="center")

        # Caixa do Nome do Mapa
        map_box_w = panel_w - 180
        map_box_x = 30 + 13 + map_box_w / 2 + 4
        arcade.draw_rect_filled(arcade.XYWH(map_box_x, map_row_y, map_box_w, 24), (20, 26, 36, 255))
        arcade.draw_rect_outline(arcade.XYWH(map_box_x, map_row_y, map_box_w, 24), (50, 65, 90, 200), 1)
        self._render_text("map_name_t", f"🗺️ {cur_map['name'][:24]}", map_box_x, map_row_y, (100, 200, 255, 255), 8, True, text_cache, anchor_x="center")

        # [▶]
        b_next_m_x = map_box_x + map_box_w / 2 + 17
        arcade.draw_rect_filled(arcade.XYWH(b_next_m_x, map_row_y, 26, 24), (35, 45, 60, 255))
        arcade.draw_rect_outline(arcade.XYWH(b_next_m_x, map_row_y, 26, 24), (70, 90, 120, 200), 1)
        self._render_text("b_map_next", "▶", b_next_m_x, map_row_y, (241, 196, 15, 255), 10, True, text_cache, anchor_x="center")

        # Steppers de Colunas e Pés
        grid_y = map_row_y - 28
        self._render_text("lbl_cols", "Cols:", 16, grid_y, (160, 175, 195, 255), 8, True, text_cache)

        b_c_min_x = 65
        arcade.draw_rect_filled(arcade.XYWH(b_c_min_x, grid_y, 22, 22), (35, 45, 60, 255))
        self._render_text("b_c_min", "-", b_c_min_x, grid_y, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

        arcade.draw_rect_filled(arcade.XYWH(b_c_min_x + 24, grid_y, 30, 22), (18, 24, 34, 255))
        self._render_text("val_cols", str(self.columns), b_c_min_x + 24, grid_y, (255, 255, 255, 255), 9, True, text_cache, anchor_x="center")

        b_c_plus_x = b_c_min_x + 48
        arcade.draw_rect_filled(arcade.XYWH(b_c_plus_x, grid_y, 22, 22), (35, 45, 60, 255))
        self._render_text("b_c_plus", "+", b_c_plus_x, grid_y, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

        feet_lbl_x = b_c_plus_x + 30
        self._render_text("lbl_feet", "Ft/sq:", feet_lbl_x, grid_y, (160, 175, 195, 255), 8, True, text_cache)

        b_f_min_x = feet_lbl_x + 45
        arcade.draw_rect_filled(arcade.XYWH(b_f_min_x, grid_y, 22, 22), (35, 45, 60, 255))
        self._render_text("b_f_min", "-", b_f_min_x, grid_y, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

        arcade.draw_rect_filled(arcade.XYWH(b_f_min_x + 24, grid_y, 26, 22), (18, 24, 34, 255))
        self._render_text("val_feet", str(self.feet_per_square), b_f_min_x + 24, grid_y, (255, 255, 255, 255), 9, True, text_cache, anchor_x="center")

        b_f_plus_x = b_f_min_x + 48
        arcade.draw_rect_filled(arcade.XYWH(b_f_plus_x, grid_y, 22, 22), (35, 45, 60, 255))
        self._render_text("b_f_plus", "+", b_f_plus_x, grid_y, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

        # 3. Personagens Jogadores (Checkboxes)
        pc_sec_y = grid_y - 28
        self._render_text("lbl_pcs", "• Personagens dos Jogadores (PJs):", 16, pc_sec_y, (200, 210, 225, 255), 9, True, text_cache)

        pc_list_top = pc_sec_y - 16
        for idx, char in enumerate(self.available_characters[:3]):
            cy = pc_list_top - idx * 24
            is_checked = char["uid"] in self.selected_character_uids

            cb_x = 26
            arcade.draw_rect_filled(arcade.XYWH(cb_x, cy, 16, 16), (30, 42, 58, 255) if is_checked else (18, 24, 34, 255))
            arcade.draw_rect_outline(arcade.XYWH(cb_x, cy, 16, 16), (241, 196, 15, 255) if is_checked else (60, 75, 100, 200), 1.5)
            if is_checked:
                self._render_text(f"cb_check_{idx}", "✓", cb_x, cy, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

            char_desc = f"{char['name']} (Nv {char['level']} {char['class_summary']})"
            self._render_text(f"char_lbl_{idx}", char_desc[:38], 44, cy, (100, 200, 255, 255) if is_checked else (140, 155, 175, 255), 8, is_checked, text_cache)

        # 4. Monstros (Steppers de Quantidade)
        mon_sec_y = pc_list_top - min(len(self.available_characters), 3) * 24 - 10
        self._render_text("lbl_mons", "• Presets de Monstros (Inimigos):", 16, mon_sec_y, (200, 210, 225, 255), 9, True, text_cache)

        mon_list_top = mon_sec_y - 18
        for idx, mon in enumerate(self.available_monsters[:3]):
            my = mon_list_top - idx * 28
            mid = mon["uid"]
            qty = self.monster_counts.get(mid, 0)

            bm_x = panel_w - 90
            arcade.draw_rect_filled(arcade.XYWH(bm_x, my, 20, 20), (35, 45, 60, 255))
            self._render_text(f"b_m_min_{idx}", "-", bm_x, my, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

            arcade.draw_rect_filled(arcade.XYWH(bm_x + 22, my, 22, 20), (18, 24, 34, 255))
            self._render_text(f"val_mqty_{idx}", str(qty), bm_x + 22, my, (255, 255, 255, 255), 9, True, text_cache, anchor_x="center")

            bp_x = bm_x + 44
            arcade.draw_rect_filled(arcade.XYWH(bp_x, my, 20, 20), (35, 45, 60, 255))
            self._render_text(f"b_m_plus_{idx}", "+", bp_x, my, (241, 196, 15, 255), 9, True, text_cache, anchor_x="center")

            mon_desc = f"{mon['name']} (CR {mon['cr']} • HP {mon['max_hp']})"
            self._render_text(f"mon_lbl_{idx}", mon_desc[:30], 24, my, (255, 138, 128, 255) if qty > 0 else (140, 155, 175, 255), 8, qty > 0, text_cache)

        # Mensagem de Erro
        if self.error_message:
            err_y = mon_list_top - min(len(self.available_monsters), 3) * 28 - 14
            arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, err_y, panel_w - 32, 22), (120, 40, 31, 255))
            self._render_text("wiz_err", f"⚠️ {self.error_message}", panel_w / 2, err_y, (255, 215, 0, 255), 8, True, text_cache, anchor_x="center")

        # Botão "➡️ Posicionar no Mapa"
        btn_next_y = 36
        arcade.draw_rect_filled(arcade.XYWH(panel_w / 2, btn_next_y, panel_w - 40, 36), (39, 174, 96, 255))
        arcade.draw_rect_outline(arcade.XYWH(panel_w / 2, btn_next_y, panel_w - 40, 36), (46, 204, 113, 255), 2)
        self._render_text("b_go_stage2", "➡️ POSICIONAR NO MAPA (ETAPA 2)", panel_w / 2, btn_next_y, (255, 255, 255, 255), 10, True, text_cache, anchor_x="center")

    def draw_preview(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        text_cache: Dict[str, arcade.Text],
        texture_cache: Dict[str, arcade.Texture],
    ) -> None:
        """Desenha a área de pré-visualização do lado direito na Etapa 1."""
        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh / 2, vw, vh), (12, 16, 22, 255))

        arcade.draw_rect_filled(arcade.XYWH(vx + vw / 2, vy + vh - 18, vw, 36), (18, 24, 34, 255))
        arcade.draw_line(vx, vy + vh - 36, vx + vw, vy + vh - 36, (50, 65, 90, 200), 1)
        self._render_text("wiz_prev_hdr", "🗺️ PRÉ-VISUALIZAÇÃO DO MAPA & COMBATENTES", vx + 16, vy + vh - 18, (241, 196, 15, 255), 10, True, text_cache)

        cur_map = self.available_maps[self.selected_map_index] if self.available_maps else None
        map_path = cur_map["path"] if cur_map else None

        preview_h = vh * 0.46
        preview_w = vw - 40
        preview_cx = vx + vw / 2
        preview_cy = vy + vh - 36 - preview_h / 2 - 16

        tex = None
        if map_path:
            resolved = str(os.path.abspath(map_path)) if os.path.isfile(map_path) else map_path
            if resolved not in texture_cache:
                try:
                    if os.path.isfile(resolved):
                        texture_cache[resolved] = arcade.load_texture(resolved)
                except Exception:
                    pass
            tex = texture_cache.get(resolved)

        if tex is not None:
            arcade.draw_texture_rect(tex, arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h))
            arcade.draw_rect_outline(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (70, 95, 130, 220), 2)
        else:
            arcade.draw_rect_filled(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (25, 35, 45, 255))
            self._render_text("wiz_no_tex", "Miniatura do Mapa", preview_cx, preview_cy, (160, 175, 195, 255), 11, False, text_cache, anchor_x="center")

        # Cartão de Resumo
        card_y = preview_cy - preview_h / 2 - 16
        card_h = card_y - 20
        card_cy = card_y - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(preview_cx, card_cy, preview_w, card_h), (16, 22, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(preview_cx, card_cy, preview_w, card_h), (50, 65, 90, 200), 1)

        self._render_text("wiz_res_t", "RESUMO DO ENCONTRO EM CRIAÇÃO", vx + 32, card_y - 18, (241, 196, 15, 255), 9, True, text_cache)

        num_pcs = len(self.selected_character_uids)
        num_mons = sum(self.monster_counts.values())
        tot = num_pcs + num_mons

        self._render_text("wiz_res_p", f"• Jogadores Selecionados: {num_pcs}", vx + 32, card_y - 40, (100, 200, 255, 255), 8, False, text_cache)
        self._render_text("wiz_res_m", f"• Monstros Instanciados: {num_mons}", vx + 32, card_y - 60, (255, 138, 128, 255), 8, False, text_cache)
        self._render_text("wiz_res_g", f"• Grade Tática: {self.columns} colunas • {self.feet_per_square} ft/quadrado", vx + 32, card_y - 80, (200, 210, 225, 255), 8, False, text_cache)
        self._render_text("wiz_res_tot", f"• Total de Combatentes: {tot}", vx + 32, card_y - 100, (46, 204, 113, 255), 9, True, text_cache)

    def _render_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool,
        cache: Dict[str, arcade.Text],
        anchor_x: str = "left",
    ) -> None:
        cached = cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y="center",
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        cached.draw()

    # --- Tratamento de Eventos ---

    def handle_mouse_press(self, x: float, y: float, panel_w: float, top_y: float) -> Optional[str]:
        """
        Processa cliques no formulário.
        Retorna "PROCEED_TO_STAGE_2" se o botão avançar for clicado e passar na validação.
        """
        # 1. Widgets de Texto
        if self.title_input.handle_mouse_press(x, y):
            self.description_input.blur()
            return None

        if self.description_input.handle_mouse_press(x, y):
            self.title_input.blur()
            return None

        # Se clicou em outra área, remove foco dos inputs
        self.title_input.blur()
        self.description_input.blur()

        sec_y = top_y - 18
        lbl_t_y = sec_y - 24
        box_t_y = lbl_t_y - 18
        lbl_d_y = box_t_y - 22
        box_d_y = lbl_d_y - 18

        # 2. Seletor de Mapa
        map_sec_y = box_d_y - 24
        map_row_y = map_sec_y - 20
        b_prev_m_x = 30
        if abs(y - map_row_y) <= 12 and abs(x - b_prev_m_x) <= 13:
            if self.available_maps:
                self.selected_map_index = (self.selected_map_index - 1) % len(self.available_maps)
            return None

        map_box_w = panel_w - 180
        map_box_x = 30 + 13 + map_box_w / 2 + 4
        b_next_m_x = map_box_x + map_box_w / 2 + 17
        if abs(y - map_row_y) <= 12 and abs(x - b_next_m_x) <= 13:
            if self.available_maps:
                self.selected_map_index = (self.selected_map_index + 1) % len(self.available_maps)
            return None

        # 3. Steppers de Grade
        grid_y = map_row_y - 28
        b_c_min_x = 65
        if abs(y - grid_y) <= 11 and abs(x - b_c_min_x) <= 11:
            self.columns = max(5, self.columns - 1)
            return None

        b_c_plus_x = b_c_min_x + 48
        if abs(y - grid_y) <= 11 and abs(x - b_c_plus_x) <= 11:
            self.columns = min(60, self.columns + 1)
            return None

        feet_lbl_x = b_c_plus_x + 30
        b_f_min_x = feet_lbl_x + 45
        if abs(y - grid_y) <= 11 and abs(x - b_f_min_x) <= 11:
            self.feet_per_square = max(1, self.feet_per_square - 5) if self.feet_per_square > 5 else max(1, self.feet_per_square - 1)
            return None

        b_f_plus_x = b_f_min_x + 48
        if abs(y - grid_y) <= 11 and abs(x - b_f_plus_x) <= 11:
            self.feet_per_square = self.feet_per_square + 5 if self.feet_per_square >= 5 else 5
            return None

        # 4. Checkboxes de Personagens
        pc_sec_y = grid_y - 28
        pc_list_top = pc_sec_y - 16
        for idx, char in enumerate(self.available_characters[:3]):
            cy = pc_list_top - idx * 24
            if abs(y - cy) <= 12 and abs(x - panel_w / 2) <= (panel_w - 32) / 2:
                cid = char["uid"]
                if cid in self.selected_character_uids:
                    self.selected_character_uids.remove(cid)
                else:
                    self.selected_character_uids.add(cid)
                return None

        # 5. Steppers de Monstros
        mon_sec_y = pc_list_top - min(len(self.available_characters), 3) * 24 - 10
        mon_list_top = mon_sec_y - 18
        for idx, mon in enumerate(self.available_monsters[:3]):
            my = mon_list_top - idx * 28
            mid = mon["uid"]
            bm_x = panel_w - 90
            bp_x = bm_x + 44

            if abs(y - my) <= 10 and abs(x - bm_x) <= 10:
                self.monster_counts[mid] = max(0, self.monster_counts.get(mid, 0) - 1)
                return None

            if abs(y - my) <= 10 and abs(x - bp_x) <= 10:
                self.monster_counts[mid] = min(20, self.monster_counts.get(mid, 0) + 1)
                return None

        # 6. Botão Avançar "➡️ Posicionar no Mapa"
        btn_next_y = 36
        if abs(y - btn_next_y) <= 18 and abs(x - panel_w / 2) <= (panel_w - 40) / 2:
            is_valid, err = self.validate()
            if is_valid:
                self.error_message = None
                return "PROCEED_TO_STAGE_2"
            else:
                self.error_message = err
                return None

        return None

    def handle_mouse_drag(self, x: float, y: float) -> bool:
        if self.title_input.is_focused:
            return self.title_input.handle_mouse_drag(x, y)
        if self.description_input.is_focused:
            return self.description_input.handle_mouse_drag(x, y)
        return False

    def handle_mouse_release(self, x: float, y: float) -> None:
        self.title_input.handle_mouse_release(x, y)
        self.description_input.handle_mouse_release(x, y)

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        if self.title_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.TAB):
                self.title_input.blur()
                self.description_input.focus()
                return True
            return self.title_input.handle_key_press(symbol, modifiers)

        if self.description_input.is_focused:
            if symbol in (arcade.key.ENTER, arcade.key.TAB):
                self.description_input.blur()
                return True
            return self.description_input.handle_key_press(symbol, modifiers)

        return False

    def handle_key_release(self, symbol: int, modifiers: int) -> None:
        self.title_input.handle_key_release(symbol, modifiers)
        self.description_input.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        if self.title_input.is_focused:
            return self.title_input.handle_text_input(text)
        if self.description_input.is_focused:
            return self.description_input.handle_text_input(text)
        return False

