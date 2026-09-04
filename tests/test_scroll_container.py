import unittest
import sys
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.components.discrete_scroll_list import DiscreteScrollList

logger = logging.getLogger(__name__)


class TestDiscreteScrollList(unittest.TestCase):
    """
    Suíte de testes unitários para o componente DiscreteScrollList (PREMISES.md).
    Valida a paginação discreta por índice, cálculo exato de itens visíveis
    sem truncamento/corte de itens e tratamento rigoroso de limites e eventos de mouse.
    """

    def setUp(self) -> None:
        self.sample_items = [f"Item_{i}" for i in range(12)]

    def test_visible_item_count_calculation_exact(self) -> None:
        """Calcula dinamicamente a quantidade de itens inteiros que cabem na altura."""
        # Altura: 160, Item: 38, Spacing: 4 -> Slot Total: 42 -> 160 // 42 = 3 itens
        scroll_list = DiscreteScrollList(
            x=10.0,
            y=200.0,
            width=300.0,
            height=160.0,
            item_height=38,
            spacing=4,
            items=self.sample_items,
        )
        self.assertEqual(scroll_list.visible_item_count, 3)
        self.assertEqual(scroll_list.max_start_index, 12 - 3)  # 9

        # Redimensionamento dinâmico: Altura 280 -> 280 // 42 = 6 itens
        scroll_list.height = 280.0
        self.assertEqual(scroll_list.visible_item_count, 6)
        self.assertEqual(scroll_list.max_start_index, 12 - 6)  # 6

    def test_visible_item_count_tactical_sidebar_dimensions(self) -> None:
        """Calcula itens visíveis para as dimensões da sidebar do palco tático (item_height=28, spacing=4)."""
        # Altura: 320, Item: 28, Spacing: 4 -> Slot Total: 32 -> 320 // 32 = 10 itens
        scroll_list = DiscreteScrollList(
            x=12.0,
            y=400.0,
            width=250.0,
            height=320.0,
            item_height=28,
            spacing=4,
            items=self.sample_items,
        )
        self.assertEqual(scroll_list.visible_item_count, 10)
        self.assertEqual(scroll_list.max_start_index, 12 - 10)  # 2

    def test_scroll_boundaries_clamping(self) -> None:
        """Garante que a rolagem não ultrapasse os limites [0, max_start_index]."""
        scroll_list = DiscreteScrollList(
            x=0.0,
            y=100.0,
            width=100.0,
            height=100.0,
            item_height=20,
            spacing=5,
            items=self.sample_items,  # 12 itens, visíveis: 100 // 25 = 4 -> max_start = 8
        )
        self.assertEqual(scroll_list.start_index, 0)

        # Tentativa de rolar acima do topo (valores negativos)
        changed = scroll_list.scroll_up(5)
        self.assertFalse(changed)
        self.assertEqual(scroll_list.start_index, 0)

        # Rola até o final
        scroll_list.scroll_down(5)
        self.assertEqual(scroll_list.start_index, 5)

        # Rola além do máximo
        scroll_list.scroll_down(100)
        self.assertEqual(scroll_list.start_index, scroll_list.max_start_index)
        self.assertEqual(scroll_list.start_index, 8)

        # scroll_to com clamp
        scroll_list.scroll_to(-99)
        self.assertEqual(scroll_list.start_index, 0)
        scroll_list.scroll_to(999)
        self.assertEqual(scroll_list.start_index, 8)

    def test_mouse_scroll_event_handling(self) -> None:
        """Valida que o evento de scroll consome e rola se dentro dos bounds, e ignora se fora."""
        scroll_list = DiscreteScrollList(
            x=100.0,
            y=400.0,
            width=200.0,
            height=150.0,
            item_height=30,
            spacing=0,
            items=self.sample_items,  # 150 // 30 = 5 visíveis -> max_start = 7
        )

        # Coordenada dentro do contêiner: (x=150, y=350)
        inside_x = 150.0
        inside_y = 350.0

        # Rola para baixo (scroll_y < 0)
        handled = scroll_list.on_mouse_scroll(inside_x, inside_y, 0.0, -1.0)
        self.assertTrue(handled)
        self.assertEqual(scroll_list.start_index, 1)

        # Rola para cima (scroll_y > 0)
        handled = scroll_list.on_mouse_scroll(inside_x, inside_y, 0.0, 1.0)
        self.assertTrue(handled)
        self.assertEqual(scroll_list.start_index, 0)

        # Coordenada fora do contêiner
        outside_x = 50.0
        outside_y = 350.0
        handled_outside = scroll_list.on_mouse_scroll(outside_x, outside_y, 0.0, -1.0)
        self.assertFalse(handled_outside)
        self.assertEqual(scroll_list.start_index, 0)

    def test_visible_items_slice(self) -> None:
        """Garante que visible_items retorne a fatia correta de tuplas (índice_original, item)."""
        scroll_list = DiscreteScrollList(
            x=0.0,
            y=200.0,
            width=100.0,
            height=90.0,
            item_height=30,
            spacing=0,
            items=["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
        )
        # 90 // 30 = 3 visíveis
        self.assertEqual(scroll_list.visible_item_count, 3)

        visible = scroll_list.visible_items
        self.assertEqual(len(visible), 3)
        self.assertEqual(visible[0], (0, "Alpha"))
        self.assertEqual(visible[1], (1, "Beta"))
        self.assertEqual(visible[2], (2, "Gamma"))

        scroll_list.scroll_down(1)
        visible_scrolled = scroll_list.visible_items
        self.assertEqual(visible_scrolled[0], (1, "Beta"))
        self.assertEqual(visible_scrolled[1], (2, "Gamma"))
        self.assertEqual(visible_scrolled[2], (3, "Delta"))

    def test_get_item_at_position(self) -> None:
        """Verifica a identificação de itens clicados por coordenadas de tela."""
        scroll_list = DiscreteScrollList(
            x=10.0,
            y=100.0,
            width=100.0,
            height=60.0,
            item_height=30,
            spacing=0,
            items=["Item 0", "Item 1", "Item 2"],
        )
        # Slot 0: y de 100 a 70 (cy = 85)
        # Slot 1: y de 70 a 40 (cy = 55)
        item_top = scroll_list.get_item_at_position(50.0, 85.0)
        self.assertIsNotNone(item_top)
        self.assertEqual(item_top[0], 0)
        self.assertEqual(item_top[1], "Item 0")

        item_bottom = scroll_list.get_item_at_position(50.0, 55.0)
        self.assertIsNotNone(item_bottom)
        self.assertEqual(item_bottom[0], 1)
        self.assertEqual(item_bottom[1], "Item 1")

        # Clique fora
        item_none = scroll_list.get_item_at_position(200.0, 85.0)
        self.assertIsNone(item_none)


if __name__ == "__main__":
    unittest.main()
