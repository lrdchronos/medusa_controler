import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster


class TestInitiativeStagingAndVisibility(unittest.TestCase):
    """Testes unitários para o fluxo de Staging de Iniciativas, Visibilidade e Posicionamento."""

    def setUp(self):
        self.manager = CombatManager()
        self.manager.load_encounter("encounter_01")

    def test_generate_draft_initiatives_does_not_mutate_combat_state(self):
        # 1. Antes de aplicar, o combate não deve estar iniciado
        self.assertFalse(self.manager.has_combat_started)
        self.assertIsNone(self.manager.active_character)

        # 2. Gera rascunho temporário
        draft = self.manager.generate_draft_initiatives()
        self.assertEqual(len(draft), len(self.manager.combatants))

        # 3. O estado do combate continua inalterado (staging puro)
        self.assertFalse(self.manager.has_combat_started)
        self.assertIsNone(self.manager.active_character)
        self.assertEqual(self.manager.current_turn_index, -1)

        # 4. Todos os combatentes têm um score no draft
        for c in self.manager.combatants:
            self.assertIn(c.uid, draft)
            # 1 <= 1d20 <= 20 + initiative_mod
            self.assertGreaterEqual(draft[c.uid], 1 + c.initiative_mod)
            self.assertLessEqual(draft[c.uid], 20 + c.initiative_mod)

    def test_apply_initiatives_with_tiebreaker(self):
        # Cria rascunho com empates controlados
        # Kobold A (DEX mod +2) e Bolo (DEX mod +1) ambos com score 18
        # Kobold B (DEX mod +2) com score 15, Cultista (DEX mod +1) com score 15
        kobold_a = self.manager.get_combatant("Kobold A")
        kobold_b = self.manager.get_combatant("Kobold B")
        kobold_c = self.manager.get_combatant("Kobold C")
        cultist = self.manager.get_combatant("Cultista Líder")
        bolo = self.manager.get_combatant("Bolo de Morango")

        custom_scores = {
            kobold_a.uid: 18,
            bolo.uid: 18,        # Empate com Kobold A, mas DEX mod é +1 (menor que +2 do Kobold)
            kobold_b.uid: 15,
            cultist.uid: 15,     # Empate com Kobold B, mas DEX mod é +1
            kobold_c.uid: 8,
        }

        # Aplica iniciativas consolidadas
        self.manager.apply_initiatives(custom_scores)

        # Estado oficial de combate agora está ativo
        self.assertTrue(self.manager.has_combat_started)
        self.assertEqual(self.manager.current_turn_index, 0)
        self.assertEqual(self.manager.round_number, 1)

        turn_names = [c.name for c in self.manager.turn_order]
        # Ordem esperada:
        # 1. Kobold A (Score 18, Mod +2)
        # 2. Bolo de Morango (Score 18, Mod +1)
        # 3. Kobold B (Score 15, Mod +2)
        # 4. Cultista Líder (Score 15, Mod +1)
        # 5. Kobold C (Score 8, Mod +2)
        self.assertEqual(turn_names[0], "Kobold A")
        self.assertEqual(turn_names[1], "Bolo de Morango")
        self.assertEqual(turn_names[2], "Kobold B")
        self.assertEqual(turn_names[3], "Cultista Líder")
        self.assertEqual(turn_names[4], "Kobold C")

    def test_visibility_toggle_and_set(self):
        kobold = self.manager.get_combatant("Kobold A")
        self.assertFalse(kobold.is_hidden)

        # Alterna para oculto
        new_state = self.manager.toggle_combatant_visibility("Kobold A")
        self.assertTrue(new_state)
        self.assertTrue(kobold.is_hidden)

        # Alterna de volta para visível
        new_state2 = self.manager.toggle_combatant_visibility("Kobold A")
        self.assertFalse(new_state2)
        self.assertFalse(kobold.is_hidden)

        # Define explicitamente
        self.manager.set_combatant_visibility("Kobold A", True)
        self.assertTrue(kobold.is_hidden)

    def test_combatant_position_update(self):
        kobold = self.manager.get_combatant("Kobold A")
        self.manager.set_combatant_position(kobold.uid, 7, 12)
        self.assertEqual(kobold.position, {"x": 7, "y": 12})

    def test_large_combat_group_initiative_integrity_and_staging(self):
        """Valida a integridade de dados e ordenação de iniciativas para combates grandes (15+ entidades)."""
        manager = CombatManager()
        # 5 PJs + 12 Monstros = 17 participantes
        pcs = [
            PlayableCharacter(
                name=f"Heroi_{i}",
                uid=f"pc_{i}",
                level=5,
                max_hp=40,
                armor_class=16,
                ability_scores={"DEX": 10 + i},
            )
            for i in range(5)
        ]
        mobs = [
            Monster(
                name=f"Goblin_{j}",
                uid=f"mob_{j}",
                max_hp=10,
                armor_class=12,
                challenge_rating=0.25,
                ability_scores={"DEX": 14},
            )
            for j in range(12)
        ]

        combatants_data = []
        for pc in pcs:
            combatants_data.append(pc)
        for mob in mobs:
            combatants_data.append(mob)

        manager._CombatManager__combatants = combatants_data
        manager._CombatManager__turn_order = list(combatants_data)

        # 1. Rascunho preliminar para todos os 17 participantes
        draft = manager.generate_draft_initiatives()
        self.assertEqual(len(draft), 17)
        for c in combatants_data:
            self.assertIn(c.uid, draft)

        # 2. Atribui scores com valores decrescentes e alguns empates
        custom_scores = {}
        for idx, c in enumerate(combatants_data):
            custom_scores[c.uid] = 20 - (idx % 10)  # Gera empates controlados

        manager.apply_initiatives(custom_scores)
        self.assertTrue(manager.has_combat_started)
        self.assertEqual(len(manager.turn_order), 17)

        # 3. Verifica ordenação decrescente rigorosa
        scores = [c.initiative_score for c in manager.turn_order]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i + 1], "A ordem de iniciativa deve ser estritamente decrescente.")

        # 4. Percorre todos os 17 turnos garantindo consistência
        for t in range(17):
            self.assertEqual(manager.current_turn_index, t)
            active = manager.active_character
            self.assertIsNotNone(active)
            self.assertEqual(active, manager.turn_order[t])
            manager.next_turn()

        # Volta ao primeiro turno da rodada 2
        self.assertEqual(manager.current_turn_index, 0)
        self.assertEqual(manager.round_number, 2)

    def test_initiative_staging_modal_discrete_scroll_and_interactions(self):
        """Valida que o modal de staging acomoda grupos grandes via DiscreteScrollList com step discreto e cliques nos steppers."""
        from src.manager.session_manager import SessionManager
        from src.ui.dm.initiative_modal import InitiativeStagingModal

        session = SessionManager()
        manager = session.combat_manager

        # Popula com 17 combatentes
        combatants = [
            Monster(name=f"Orc_{i}", uid=f"orc_{i}", max_hp=15, armor_class=13)
            for i in range(17)
        ]
        manager._CombatManager__combatants = combatants
        manager._CombatManager__turn_order = list(combatants)

        modal = InitiativeStagingModal(session_manager=session)
        modal.open()
        self.assertTrue(modal.is_open)

        # Configura dimensões do modal e bounds da lista
        modal_w, modal_h = 540, 440
        modal_cx, modal_cy = 640, 384
        list_y = modal_cy + modal_h / 2 - 70
        list_w = modal_w - 40
        list_x = modal_cx - list_w / 2
        list_h = 6 * 40 - 4
        modal.scroll_list.set_bounds(list_x, list_y, list_w, list_h)

        # 1. Componente de rolagem discreta com 6 slots visíveis
        self.assertEqual(modal.scroll_list.visible_item_count, 6)
        self.assertEqual(modal.scroll_list.max_start_index, 17 - 6)  # 11
        self.assertEqual(modal.scroll_list.start_index, 0)

        # 2. Rolagem com mouse_scroll
        # Rola para baixo (scroll_y = -1.0)
        scrolled = modal.handle_scroll(x=640, y=384, scroll_x=0.0, scroll_y=-1.0)
        self.assertTrue(scrolled)
        self.assertEqual(modal.scroll_list.start_index, 1)

        # 3. Rola para o final (clamp em 11)
        for _ in range(20):
            modal.handle_scroll(x=640, y=384, scroll_x=0.0, scroll_y=-1.0)
        self.assertEqual(modal.scroll_list.start_index, 11)

        # 4. Rola de volta para o topo
        for _ in range(20):
            modal.handle_scroll(x=640, y=384, scroll_x=0.0, scroll_y=1.0)
        self.assertEqual(modal.scroll_list.start_index, 0)

        # 5. Ajuste de iniciativa pelo stepper [+]
        first_mob = combatants[0]
        initial_score = modal.draft_initiatives[first_mob.uid]

        slot_cx, slot_cy, slot_w, slot_h = modal.scroll_list.get_slot_rect(0)
        btn_plus_x = slot_cx + slot_w / 2 - 10
        btn_plus_y = slot_cy

        handled = modal.handle_click(btn_plus_x, btn_plus_y, w=1280, h=768)
        self.assertTrue(handled)
        self.assertEqual(modal.draft_initiatives[first_mob.uid], initial_score + 1)

    def test_initiative_hud_sliding_window_with_large_combat(self):
        """Valida o cálculo da janela deslizante (sliding window) e indicadores de overflow no InitiativeHUD."""
        from src.ui.initiative_hud import InitiativeHUD

        manager = CombatManager()
        combatants = [
            Monster(name=f"Creature_{i}", uid=f"c_{i}", max_hp=20, armor_class=10)
            for i in range(17)
        ]
        manager._CombatManager__combatants = combatants
        manager._CombatManager__turn_order = list(combatants)
        manager.apply_initiatives({c.uid: 20 - i for i, c in enumerate(combatants)})

        hud = InitiativeHUD(combat_manager=manager)

        # Tela de 1024px: max_visible = (1024 - 160) // 80 = 10 itens
        # Caso 1: Turno 0 (início da fila)
        start, end, visible, has_prev, has_next = hud.get_visible_window(screen_width=1024, spacing=80.0)
        self.assertEqual(start, 0)
        self.assertEqual(end, 10)
        self.assertEqual(len(visible), 10)
        self.assertFalse(has_prev)
        self.assertTrue(has_next)

        # Caso 2: Turno no meio da fila (Turno 8)
        for _ in range(8):
            manager.next_turn()
        self.assertEqual(manager.current_turn_index, 8)
        start_m, end_m, visible_m, has_prev_m, has_next_m = hud.get_visible_window(screen_width=1024, spacing=80.0)
        # half = 5 -> start = 8 - 5 = 3, end = 3 + 10 = 13
        self.assertEqual(start_m, 3)
        self.assertEqual(end_m, 13)
        self.assertEqual(len(visible_m), 10)
        self.assertTrue(has_prev_m)
        self.assertTrue(has_next_m)

        # Caso 3: Turno no final da fila (Turno 16)
        for _ in range(8):
            manager.next_turn()
        self.assertEqual(manager.current_turn_index, 16)
        start_e, end_e, visible_e, has_prev_e, has_next_e = hud.get_visible_window(screen_width=1024, spacing=80.0)
        # Final da fila: start = 17 - 10 = 7, end = 17
        self.assertEqual(start_e, 7)
        self.assertEqual(end_e, 17)
        self.assertEqual(len(visible_e), 10)
        self.assertTrue(has_prev_e)
        self.assertFalse(has_next_e)


if __name__ == "__main__":
    unittest.main()
