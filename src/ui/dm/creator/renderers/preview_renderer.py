import logging
import os
from typing import Dict, Any
import arcade
from .....domain.models.tile_map import TileMap
from ....utils.tilemap_renderer import TileMapRenderer
from .....manager.grid_manager import GridManager

logger = logging.getLogger(__name__)

COLOR_TEXT_TITLE = (241, 196, 15, 255)
COLOR_TEXT_MAIN = (200, 210, 225, 255)
COLOR_TEXT_MUTED = (140, 155, 175, 255)
COLOR_TEXT_WHITE = (255, 255, 255, 255)
COLOR_TEXT_CYAN = (100, 200, 255, 255)
COLOR_ACCENT_GOLD = (241, 196, 15, 255)


class PreviewRenderer:
    """
    Renderizador da área de pré-visualização do mapa e resumo de combate
    no Criador de Encontros (Lado direito da Etapa 1).
    """

    @staticmethod
    def render_text(
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
        try:
            cached.draw()
        except Exception:
            pass

    @staticmethod
    def draw_preview(
        form: Any,
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
        PreviewRenderer.render_text("wiz_prev_hdr", "🗺️ PRÉ-VISUALIZAÇÃO DO MAPA & COMBATENTES", vx + 16, vy + vh - 18, COLOR_TEXT_TITLE, 10, True, text_cache)

        cur_map = form.current_map_info
        map_path = cur_map.get("path")
        is_tilemap = (form.map_type == "tilemap")

        preview_h = vh * 0.46
        preview_w = vw - 40
        preview_cx = vx + vw / 2
        preview_cy = vy + vh - 36 - preview_h / 2 - 16

        # Fundo do Preview
        arcade.draw_rect_filled(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (18, 24, 34, 255))

        if is_tilemap and map_path:
            tile_map = None
            if map_path in form.tilemap_cache:
                tile_map = form.tilemap_cache[map_path]
            else:
                try:
                    tile_map = TileMap.from_file(map_path)
                    form.tilemap_cache[map_path] = tile_map
                except Exception as e:
                    logger.warning(f"Erro ao carregar preview do TileMap '{map_path}': {e}")

            if tile_map is not None:
                if map_path not in form.tilemap_renderers:
                    try:
                        form.tilemap_renderers[map_path] = TileMapRenderer(tile_map=tile_map)
                    except Exception as e:
                        logger.warning(f"Erro ao instanciar TileMapRenderer para preview: {e}")

                renderer = form.tilemap_renderers.get(map_path)
                if renderer is not None:
                    native_w = tile_map.width * 32.0
                    native_h = tile_map.height * 32.0
                    scale_factor, rend_w, rend_h, off_x, off_y = GridManager.calculate_aspect_fit(
                        viewport_width=preview_w,
                        viewport_height=preview_h,
                        native_width=native_w,
                        native_height=native_h,
                    )
                    draw_x = preview_cx - preview_w / 2 + off_x
                    draw_y = preview_cy - preview_h / 2 + off_y
                    cell_w = rend_w / tile_map.width
                    cell_h = rend_h / tile_map.height

                    renderer.update_layout(draw_x, draw_y, cell_w, cell_h)
                    renderer.draw(pixelated=True)
                    arcade.draw_rect_outline(arcade.XYWH(draw_x + rend_w / 2, draw_y + rend_h / 2, rend_w, rend_h), (70, 95, 130, 220), 1.5)

                    # Grade tática configurada independente sobreposta ao preview
                    grid_cols = max(1, form.columns)
                    grid_rows = max(1, round(grid_cols * (rend_h / rend_w)))
                    grid_cell_w = rend_w / float(grid_cols)
                    grid_cell_h = rend_h / float(grid_rows)
                    grid_color = (130, 205, 255, 75)
                    for c in range(grid_cols + 1):
                        lx = draw_x + float(c) * grid_cell_w
                        arcade.draw_line(lx, draw_y, lx, draw_y + rend_h, grid_color, 1.0)
                    for r in range(grid_rows + 1):
                        ly = draw_y + float(r) * grid_cell_h
                        arcade.draw_line(draw_x, ly, draw_x + rend_w, ly, grid_color, 1.0)
                else:
                    PreviewRenderer.render_text("wiz_no_tm", f"🧩 Tileset {tile_map.width}x{tile_map.height}", preview_cx, preview_cy, COLOR_TEXT_CYAN, 10, True, text_cache, anchor_x="center")
            else:
                PreviewRenderer.render_text("wiz_no_tex", "Layout JSON do Tilemap", preview_cx, preview_cy, COLOR_TEXT_MUTED, 10, False, text_cache, anchor_x="center")
        else:
            tex = None
            if map_path and not str(map_path).lower().endswith((".json", ".xml", ".txt", ".csv")):
                resolved = str(os.path.abspath(map_path)) if os.path.isfile(map_path) else map_path
                if resolved not in texture_cache:
                    try:
                        if os.path.isfile(resolved):
                            texture_cache[resolved] = arcade.load_texture(resolved)
                        else:
                            texture_cache[resolved] = None
                    except Exception:
                        texture_cache[resolved] = None
                tex = texture_cache.get(resolved)

            if tex is not None:
                arcade.draw_texture_rect(tex, arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h))
                arcade.draw_rect_outline(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (70, 95, 130, 220), 2)
            else:
                arcade.draw_rect_filled(arcade.XYWH(preview_cx, preview_cy, preview_w, preview_h), (25, 35, 45, 255))
                PreviewRenderer.render_text("wiz_no_tex", "Miniatura do Mapa", preview_cx, preview_cy, COLOR_TEXT_MUTED, 11, False, text_cache, anchor_x="center")

        # Cartão de Resumo
        card_y = preview_cy - preview_h / 2 - 16
        card_h = card_y - 20
        card_cy = card_y - card_h / 2

        arcade.draw_rect_filled(arcade.XYWH(preview_cx, card_cy, preview_w, card_h), (16, 22, 32, 255))
        arcade.draw_rect_outline(arcade.XYWH(preview_cx, card_cy, preview_w, card_h), (50, 65, 90, 200), 1)

        PreviewRenderer.render_text("wiz_res_t", "RESUMO DO ENCONTRO EM CRIAÇÃO", vx + 32, card_y - 18, COLOR_TEXT_TITLE, 9, True, text_cache)

        num_pcs = len(form.selected_character_uids)
        num_mons = sum(form.monster_counts.values())
        tot = num_pcs + num_mons

        map_type_label = "🧩 Tileset Modular Dinâmico" if is_tilemap else "🖼️ Imagem Fixa Estática"
        PreviewRenderer.render_text("wiz_res_mtype", f"• Tipo de Mapa: {map_type_label}", vx + 32, card_y - 38, COLOR_ACCENT_GOLD if is_tilemap else COLOR_TEXT_CYAN, 8, True, text_cache)
        PreviewRenderer.render_text("wiz_res_p", f"• Jogadores Selecionados: {num_pcs}", vx + 32, card_y - 56, COLOR_TEXT_CYAN, 8, False, text_cache)
        PreviewRenderer.render_text("wiz_res_m", f"• Monstros Instanciados: {num_mons}", vx + 32, card_y - 74, (255, 138, 128, 255), 8, False, text_cache)
        PreviewRenderer.render_text("wiz_res_g", f"• Grade Tática: {form.columns} colunas • {form.feet_per_square} ft/quadrado", vx + 32, card_y - 92, COLOR_TEXT_MAIN, 8, False, text_cache)
        PreviewRenderer.render_text("wiz_res_tot", f"• Total de Combatentes: {tot}", vx + 32, card_y - 110, (46, 204, 113, 255), 9, True, text_cache)
