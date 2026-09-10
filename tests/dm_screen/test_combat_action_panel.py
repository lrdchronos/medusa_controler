import unittest
import sys
import arcade
from unittest.mock import MagicMock, patch
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.domain.models.playablechar import PlayableCharacter
from src.ui.dm.combat_tab import CombatTabView
from src.ui.dm.panels.combat_roster_panel import CombatRosterPanel
from src.ui.dm.handlers.combat_tab_input_handler import CombatTabInputHandler
from src.ui.utils.status_icon_atlas import StatusIconAtlas
from src.ui.utils.ui_constants import Colors, Dimensions, Spacing, Typography
from src.ui.utils.ui_layout import PixelIconDrawer, FlowRow
from src.ui.components.discrete_scroll_list import DiscreteScrollList


class TestCombatActionPanel(unittest.TestCase):
    """
    Testes unitários para o painel de ação do combate (draw_hp_dispatcher e input handler),
    validando margens verticais da barra de HP, cores de cura e renderização escalonada dos ícones de condição.
    """

    @classmethod
    def setUpClass(cls):
        try:
            cls.window = arcade.open_window(800, 600, "Test Action Panel", visible=False)
        except Exception:
            cls.window = None

    def setUp(self):
        self.combat_manager = CombatManager()
        self.hero = PlayableCharacter(name="Valeria", max_hp=40, armor_class=17)
        self.hero.take_damage(10)
        self.combat_manager.add_combatant(self.hero)
        self.combat_manager.start_combat([self.hero])

        self.tab = MagicMock()
        self.tab.combat_manager = self.combat_manager
        self.tab.selected_combatant_uid = self.hero.uid
        self.tab.custom_hp_value = 5
        self.tab.text_cache = {}
        self.tab.scroll_list = DiscreteScrollList(visible_item_count=4)
        self.tab._CombatTabView__item_height = 32.0
        self.tab._CombatTabView__spacing = 4.0

        mock_text = MagicMock()
        self.tab._get_text.return_value = mock_text

    @patch.object(PixelIconDrawer, "draw_pixel_icon")
    @patch("arcade.draw_rect_filled")
    @patch("arcade.draw_rect_outline")
    def test_hp_bar_vertical_margins_and_layout(self, mock_outline, mock_filled, mock_draw_icon):
        """Verifica se a barra de vida e botões de ação respeitam a escala de 8pt e alturas canônicas de 28px."""
        panel_w = 600.0
        disp_top = 500.0

        CombatRosterPanel.draw_hp_dispatcher(self.tab, panel_w=panel_w, disp_top=disp_top)

        # 1. Título do alvo em disp_top - 14.0 e info de HP em disp_top - 28.0
        self.tab._get_text.assert_any_call(
            "disp_title",
            f"ALVO SELECIONADO: {self.hero.name.upper()} (Medium)",
            float(Spacing.LG),
            disp_top - 14.0,
            unittest.mock.ANY,
            unittest.mock.ANY,
            bold=True,
            anchor_y="center",
        )

        # 2. Barra de HP: bar_y = (disp_top - 28.0) - margin_top(8.0) - bar_h/2(4.0) = disp_top - 40.0
        expected_bar_y = disp_top - 40.0
        expected_bar_w = panel_w - float(Spacing.LG * 2 + Spacing.SM)
        expected_bar_h = 8.0

        # Verifica se arcade.draw_rect_filled foi chamado com a geometria exata da barra de HP
        found_bar_bg = False
        for call_args in mock_filled.call_args_list:
            rect = call_args[0][0]
            cy = getattr(rect, "center_y", getattr(rect, "y", None))
            h = getattr(rect, "height", getattr(rect, "h", None))
            if cy is not None and h is not None:
                if abs(cy - expected_bar_y) < 0.1 and abs(h - expected_bar_h) < 0.1:
                    found_bar_bg = True
                    break
        self.assertTrue(found_bar_bg, f"Barra de HP não encontrada no centro Y esperado {expected_bar_y}")

        # 3. Botões de Dano e Cura: btn_dmg_y = (bar_y - bar_h/2) - margin_bottom(8.0) - dmg_btn_h/2(14.0) = disp_top - 66.0
        expected_btn_dmg_y = disp_top - 66.0
        expected_dmg_btn_h = Dimensions.BTN_HEIGHT_COMPACT
        found_dmg_btn = False
        found_heal_bg = False
        for call_args in mock_filled.call_args_list:
            rect = call_args[0][0]
            color = call_args[0][1] if len(call_args[0]) > 1 else None
            cy = getattr(rect, "center_y", getattr(rect, "y", None))
            h = getattr(rect, "height", getattr(rect, "h", None))
            if cy is not None and h is not None:
                if abs(cy - expected_btn_dmg_y) < 0.1 and abs(h - expected_dmg_btn_h) < 0.1:
                    found_dmg_btn = True
                    if color == Colors.HEAL_BG:
                        found_heal_bg = True

        self.assertTrue(found_dmg_btn, f"Botões de dano/cura não encontrados no centro Y esperado {expected_btn_dmg_y}")
        self.assertTrue(found_heal_bg, "Botão de cura não utilizou Colors.HEAL_BG")

    @patch.object(PixelIconDrawer, "draw_pixel_icon")
    @patch("arcade.draw_rect_filled")
    @patch("arcade.draw_rect_outline")
    def test_condition_icons_rendered_with_pixel_icon_drawer(self, mock_outline, mock_filled, mock_draw_icon):
        """Verifica se todos os 11 ícones de condição D&D 5E são renderizados via PixelIconDrawer centralizados."""
        panel_w = 600.0
        disp_top = 500.0
        expected_cond_btn_y = disp_top - 152.0

        CombatRosterPanel.draw_hp_dispatcher(self.tab, panel_w=panel_w, disp_top=disp_top)

        cond_names = StatusIconAtlas.get_condition_names()
        self.assertEqual(len(cond_names), 11)

        # Verifica se draw_pixel_icon foi invocado para cada textura com anchor centralizado e target_size=20.0
        self.assertGreaterEqual(mock_draw_icon.call_count, len(cond_names))

        for call_args in mock_draw_icon.call_args_list:
            kwargs = call_args[1]
            self.assertEqual(kwargs.get("center_y"), expected_cond_btn_y)
            self.assertEqual(kwargs.get("target_size"), 20.0)
            self.assertIsNotNone(kwargs.get("texture"))

    def test_condition_click_hitbox_alignment(self):
        """Valida se o input handler detecta cliques nas condições táticas na nova coordenada cond_btn_y."""
        panel_w = 600.0
        top_y = 600.0
        info_y = (top_y - 20) - 24  # 556.0
        table_top = info_y - 12 - 28 - 8 - 26 - 8  # 474.0
        table_h = 22
        rendered_rows = 1
        item_h = 32.0
        spacing = 4.0
        disp_top = table_top - table_h - rendered_rows * (item_h + spacing) - 8  # 408.0

        self.tab.pending_end_combat_modal = False
        self.tab.add_token_modal.is_open = False
        self.tab.spell_aoe_panel.handle_click.return_value = False
        self.tab.spell_aoe_panel.is_collapsed = True
        self.tab.fog_panel.handle_click.return_value = False
        self.tab.fog_panel.is_collapsed = True

        cond_btn_y = disp_top - 152.0
        cond_names = StatusIconAtlas.get_condition_names()
        cond_spacing = float(Spacing.TINY)
        cond_total_w = panel_w - float(Spacing.LG * 2)
        cond_btn_w = (cond_total_w - (len(cond_names) - 1) * cond_spacing) / len(cond_names)
        first_cond_x = float(Spacing.LG) + 0 * (cond_btn_w + cond_spacing) + cond_btn_w / 2.0

        # Simula clique no primeiro botão de condição (ex: 'poisoned')
        first_cond = cond_names[0]
        self.assertFalse(self.hero.has_condition(first_cond))

        handled = CombatTabInputHandler.handle_click(
            tab=self.tab,
            x=first_cond_x,
            y=cond_btn_y,
            panel_w=panel_w,
            top_y=top_y,
            open_initiative_modal_callback=lambda: None,
        )
        self.assertTrue(handled)
        self.assertTrue(self.hero.has_condition(first_cond))

    @patch("arcade.draw_rect_filled")
    @patch("arcade.draw_rect_outline")
    def test_draw_roster_table_rendering(self, mock_outline, mock_filled):
        """Verifica se draw_roster_table popula o DiscreteScrollList e renderiza combatentes sem exceções."""
        self.tab.spell_aoe_panel.is_collapsed = True
        self.tab.fog_panel.is_collapsed = True
        panel_w = 600.0
        table_top = 500.0

        bottom_y, count = CombatRosterPanel.draw_roster_table(self.tab, panel_w=panel_w, fog_next_y=table_top)
        self.assertEqual(count, 1)
        self.assertLess(bottom_y, table_top)
        self.assertEqual(len(self.tab.scroll_list.items), 1)


if __name__ == "__main__":
    unittest.main()
