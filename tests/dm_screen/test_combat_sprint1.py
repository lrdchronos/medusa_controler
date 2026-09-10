import unittest
import sys
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / "src").is_dir():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.manager.session_manager import SessionManager
from src.domain.models.entity import Entity, EntityType, DynamicToken
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster
from src.ui.utils.sprite_utils import SpriteFactory
from src.ui.dm.combat_tab import CombatTabView


class TestCombatSprint1(unittest.TestCase):
    """
    Suíte de testes para validação do Sprint 1 de Estabilidade de Combate:
    1. Pulo automático de combatentes mortos em next_turn / previous_turn.
    2. Reintegração de combatentes revividos por cura.
    3. Diferenciação inteligente de badges procedurais (nomes sequenciais, romanos, letras, compostos).
    4. Rolagem discreta e sem overflow na CombatTabView (DiscreteScrollList).
    """

    def setUp(self):
        self.combat_manager = CombatManager()

        # Criação de entidades de teste
        self.hero = PlayableCharacter(name="Guerreira Valéria", max_hp=30, armor_class=16)
        self.mage = PlayableCharacter(name="Mago Elminster", max_hp=20, armor_class=12)
        self.goblin1 = Monster(name="Kobold 1", max_hp=10, armor_class=12)
        self.goblin2 = Monster(name="Kobold 2", max_hp=10, armor_class=12)
        self.goblin3 = Monster(name="Kobold 3", max_hp=10, armor_class=12)

    # --- 1. Testes de Pulo de Combatentes Mortos no CombatManager ---

    def test_next_turn_skips_single_dead_combatant(self):
        """Verifica se next_turn() pula automaticamente um combatente abatido (is_alive=False / HP=0)."""
        combatants = [self.hero, self.goblin1, self.mage]
        self.combat_manager.start_combat(combatants)

        # Início no turno do Hero
        self.assertEqual(self.combat_manager.active_character, self.hero)
        self.assertEqual(self.combat_manager.round_number, 1)

        # Abate o Goblin 1 (próximo na fila)
        self.goblin1.take_damage(10)
        self.assertFalse(self.goblin1.is_alive)
        self.assertEqual(self.goblin1.current_hp, 0)

        # Avança o turno: deve pular o goblin1 e ir direto para o mage
        next_char = self.combat_manager.next_turn()
        self.assertEqual(next_char, self.mage)
        self.assertEqual(self.combat_manager.active_character, self.mage)
        self.assertEqual(self.combat_manager.round_number, 1)

    def test_next_turn_skips_multiple_consecutive_dead_combatants(self):
        """Verifica se múltiplos combatentes mortos em sequência são pulados corretamente."""
        combatants = [self.hero, self.goblin1, self.goblin2, self.goblin3, self.mage]
        self.combat_manager.start_combat(combatants)

        self.assertEqual(self.combat_manager.active_character, self.hero)

        # Abate todos os três goblins
        self.goblin1.take_damage(10)
        self.goblin2.take_damage(10)
        self.goblin3.take_damage(10)

        # Avança o turno: deve pular goblin1, goblin2 e goblin3, caindo no mage
        next_char = self.combat_manager.next_turn()
        self.assertEqual(next_char, self.mage)
        self.assertEqual(self.combat_manager.active_character, self.mage)

    def test_round_increment_on_wrap_around_with_dead(self):
        """Verifica se a rodada incrementa adequadamente ao dar a volta pulando combatentes mortos."""
        combatants = [self.hero, self.goblin1, self.mage]
        self.combat_manager.start_combat(combatants)

        # Hero (rodada 1) -> Mage (rodada 1) -> Hero (rodada 2, pulando goblin1)
        self.goblin1.take_damage(10)

        self.combat_manager.next_turn()  # Vai para Mage
        self.assertEqual(self.combat_manager.active_character, self.mage)
        self.assertEqual(self.combat_manager.round_number, 1)

        self.combat_manager.next_turn()  # Dá a volta para Hero (rodada 2)
        self.assertEqual(self.combat_manager.active_character, self.hero)
        self.assertEqual(self.combat_manager.round_number, 2)

    def test_all_combatants_dead_safe_termination(self):
        """Garante que se todos os combatentes estiverem mortos, next_turn() não entra em loop infinito."""
        combatants = [self.goblin1, self.goblin2]
        self.combat_manager.start_combat(combatants)

        self.goblin1.take_damage(10)
        self.goblin2.take_damage(10)

        # Executa next_turn - deve terminar graciosamente sem hang ou exceção
        result = self.combat_manager.next_turn()
        self.assertIsNone(result)

    def test_previous_turn_skips_dead_combatants(self):
        """Verifica se previous_turn() também pula combatentes inativos ao retroceder."""
        combatants = [self.hero, self.goblin1, self.mage]
        self.combat_manager.start_combat(combatants)

        # Avança para o Mage
        self.combat_manager.next_turn()
        self.assertEqual(self.combat_manager.active_character, self.goblin1)
        self.combat_manager.next_turn()
        self.assertEqual(self.combat_manager.active_character, self.mage)

        # Abate o goblin1
        self.goblin1.take_damage(10)

        # Retrocede turno: de Mage deve pular goblin1 e voltar para Hero
        prev_char = self.combat_manager.previous_turn()
        self.assertEqual(prev_char, self.hero)
        self.assertEqual(self.combat_manager.active_character, self.hero)

    # --- 2. Teste de Ressurreição / Cura de Combatente Abatido ---

    def test_healed_combatant_regains_turn_eligibility(self):
        """Confirma que um combatente curado após a morte volta a receber turnos normalmente."""
        combatants = [self.hero, self.goblin1, self.mage]
        self.combat_manager.start_combat(combatants)

        # Abate goblin1
        self.goblin1.take_damage(10)
        self.assertFalse(self.goblin1.is_alive)

        # Turno pula goblin1
        self.combat_manager.next_turn()
        self.assertEqual(self.combat_manager.active_character, self.mage)

        # Cura o goblin1
        self.combat_manager.apply_heal(self.goblin1.uid, 5)
        self.assertTrue(self.goblin1.is_alive)
        self.assertEqual(self.goblin1.current_hp, 5)

        # Próximo turno completa a volta e vai para Hero (rodada 2)
        self.combat_manager.next_turn()
        self.assertEqual(self.combat_manager.active_character, self.hero)
        self.assertEqual(self.combat_manager.round_number, 2)

        # Próximo turno agora DEVE cair em goblin1, pois foi curado!
        self.combat_manager.next_turn()
        self.assertEqual(self.combat_manager.active_character, self.goblin1)

    # --- 3. Testes do Algoritmo Inteligente de Badges Circulares (SpriteFactory) ---

    def test_badge_text_extraction_differentiation(self):
        """Testa diferenciação de tokens numerados sequencialmente."""
        k1 = SpriteFactory.extract_badge_text("Kobold 1")
        k2 = SpriteFactory.extract_badge_text("Kobold 2")
        k3 = SpriteFactory.extract_badge_text("Kobold #3")
        k4 = SpriteFactory.extract_badge_text("Kobold_4")

        self.assertEqual(k1, "K1")
        self.assertEqual(k2, "K2")
        self.assertEqual(k3, "K3")
        self.assertEqual(k4, "K4")
        self.assertNotEqual(k1, k2)
        self.assertNotEqual(k2, k3)

    def test_badge_text_letter_suffixes(self):
        """Testa identificadores com sufixo de letra única (ex: Cultista A, Esqueleto B)."""
        ca = SpriteFactory.extract_badge_text("Cultista A")
        cb = SpriteFactory.extract_badge_text("Cultista B")
        eb = SpriteFactory.extract_badge_text("Esqueleto B")

        self.assertEqual(ca, "C-A")
        self.assertEqual(cb, "C-B")
        self.assertEqual(eb, "E-B")
        self.assertNotEqual(ca, cb)

    def test_badge_text_roman_numeral_suffixes(self):
        """Testa identificadores com numerais romanos (ex: Zumbi IV -> Z-4)."""
        z1 = SpriteFactory.extract_badge_text("Zumbi I")
        z2 = SpriteFactory.extract_badge_text("Zumbi II")
        z3 = SpriteFactory.extract_badge_text("Zumbi III")
        z4 = SpriteFactory.extract_badge_text("Zumbi IV")
        z5 = SpriteFactory.extract_badge_text("Zumbi V")

        self.assertEqual(z1, "Z-1")
        self.assertEqual(z2, "Z-2")
        self.assertEqual(z3, "Z-3")
        self.assertEqual(z4, "Z-4")
        self.assertEqual(z5, "Z-5")

    def test_badge_text_compound_names(self):
        """Testa extração de iniciais canônicas em nomes compostos."""
        bm = SpriteFactory.extract_badge_text("Bruenor Martelo")
        mn = SpriteFactory.extract_badge_text("Mago Negro")
        ef = SpriteFactory.extract_badge_text("Elfo da Floresta")

        self.assertEqual(bm, "BM")
        self.assertEqual(mn, "MN")
        self.assertEqual(ef, "EF")

    def test_badge_text_single_word_names(self):
        """Testa extração em nomes simples sem sufixo."""
        self.assertEqual(SpriteFactory.extract_badge_text("Orc"), "ORC")
        self.assertEqual(SpriteFactory.extract_badge_text("Kobold"), "KOBO")
        self.assertEqual(SpriteFactory.extract_badge_text("Bolo"), "BOLO")
        self.assertEqual(SpriteFactory.extract_badge_text("Gandalf"), "GAND")
        self.assertEqual(SpriteFactory.extract_badge_text(""), "")

    # --- 4. Testes de Rolagem Discreta na CombatTabView (DiscreteScrollList) ---

    def test_combat_tab_discrete_scroll_pagination(self):
        """Testa a integração da DiscreteScrollList na CombatTabView com >8 combatentes."""
        session = SessionManager()
        # Cria 10 combatentes
        combatants = [
            DynamicToken(name=f"Monstro {i}", max_hp=10, armor_class=10)
            for i in range(1, 11)
        ]
        session.combat_manager.start_combat(combatants)

        combat_tab = CombatTabView(session_manager=session)
        scroll_list = combat_tab.scroll_list

        # Configura combatentes e limites geométricos
        scroll_list.items = combatants
        scroll_list.visible_item_count = 4
        scroll_list.set_bounds(x=12.0, y=500.0, width=380.0, height=104.0)

        # Verifica configuração inicial da lista
        self.assertEqual(len(scroll_list.items), 10)
        self.assertEqual(scroll_list.start_index, 0)
        self.assertTrue(scroll_list.can_scroll_down)
        self.assertFalse(scroll_list.can_scroll_up)

        # Executa rolagem discreta para baixo (scroll_y < 0)
        list_cx = scroll_list.x + scroll_list.width / 2.0
        list_cy = scroll_list.y - scroll_list.height / 2.0

        scrolled = combat_tab.handle_mouse_scroll(list_cx, list_cy, scroll_x=0.0, scroll_y=-1.0)
        self.assertTrue(scrolled)
        self.assertEqual(scroll_list.start_index, 1)
        self.assertTrue(scroll_list.can_scroll_up)

        # Rola mais 3 passos para baixo
        for _ in range(3):
            combat_tab.handle_mouse_scroll(list_cx, list_cy, scroll_x=0.0, scroll_y=-1.0)
        self.assertEqual(scroll_list.start_index, 4)

        # Executa rolagem discreta para cima (scroll_y > 0)
        scrolled_up = combat_tab.handle_mouse_scroll(list_cx, list_cy, scroll_x=0.0, scroll_y=1.0)
        self.assertTrue(scrolled_up)
        self.assertEqual(scroll_list.start_index, 3)

        # Verifica que visible_items respeita a paginação discreta
        visible = scroll_list.visible_items
        self.assertEqual(len(visible), 4)
        first_visible_idx, first_visible_entity = visible[0]
        self.assertEqual(first_visible_idx, 3)
        self.assertEqual(first_visible_entity.name, "Monstro 4")


if __name__ == "__main__":
    unittest.main()
