import unittest
from unittest.mock import MagicMock
import arcade
from src.domain.models.entity import Entity, EntityType
from src.domain.models.playablechar import PlayableCharacter
from src.domain.models.monster import Monster
from src.domain.rules.movement_calculator import MovementCalculator, MovementResult
from src.manager.combat_manager import CombatManager
from src.manager.grid_manager import GridManager


class DummyPlayer(Entity):
    def __init__(self, name: str = "Hero", speed: int = 30, position=None, entity_type=EntityType.PLAYER):
        super().__init__(name=name, speed=speed, position=position or {"x": 5, "y": 5}, entity_type=entity_type)


class DummyMonster(Entity):
    def __init__(self, name: str = "Goblin", speed: int = 30, position=None, entity_type=EntityType.MONSTER):
        super().__init__(name=name, speed=speed, position=position or {"x": 8, "y": 8}, entity_type=entity_type)


class TestMovementOrthogonal(unittest.TestCase):
    """
    Suíte de testes canônicos para o subsistema de deslocamento estritamente ortogonal (4-vizinhança) do Medusa VTT.
    """

    @classmethod
    def setUpClass(cls):
        try:
            cls.window = arcade.get_window()
        except RuntimeError:
            cls.window = arcade.open_window(800, 600, "Test Movement Window", visible=False)

    def setUp(self):
        self.grid_manager = GridManager(
            map_width=1920.0,
            map_height=1080.0,
            columns=25,
            feet_per_square=5.0,
        )

    def test_strict_orthogonal_neighbors_no_diagonals(self):
        """Garante que nenhum passo diagonal direto receba custo de 1 passo ou seja acessível diretamente."""
        start_cell = (5, 5)
        # Com 5.0 pés (1 passo de 5ft), apenas os 4 vizinhos ortogonais devem ser alcançáveis
        res = MovementCalculator.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=5.0,
            columns=25,
            rows=14,
            feet_per_square=5.0,
        )

        expected_neighbors = {(5, 6), (5, 4), (6, 5), (4, 5)}
        self.assertEqual(set(res.reachable_cells.keys()), expected_neighbors)

        # Diagonais imediatas NÃO devem ser alcançáveis com 5 pés
        diagonal_neighbors = {(6, 6), (4, 4), (6, 4), (4, 6)}
        for diag in diagonal_neighbors:
            self.assertNotIn(diag, res.reachable_cells)
            self.assertFalse(res.is_reachable(diag))

        for cell in expected_neighbors:
            self.assertEqual(res.get_cost(cell), 5.0)

    def test_multi_step_orthogonal_path_and_costs(self):
        """Verifica se células a 2 passos (10ft) são atingidas exclusivamente por rotas ortogonais."""
        start_cell = (5, 5)
        res = MovementCalculator.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=10.0,
            columns=25,
            rows=14,
            feet_per_square=5.0,
        )

        # Com 10ft, a célula diagonal (6, 6) custa exatamente 10ft (2 passos ortogonais de 5ft)
        self.assertIn((6, 6), res.reachable_cells)
        self.assertEqual(res.get_cost((6, 6)), 10.0)

        # Reconstrução do caminho deve ter 3 nós: (5,5) -> intermediário -> (6,6)
        path = res.get_path((6, 6))
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0], (5, 5))
        self.assertEqual(path[-1], (6, 6))

        # Valida que todos os passos no caminho são estritamente ortogonais (Manhattan dist = 1)
        for i in range(len(path) - 1):
            c1, r1 = path[i]
            c2, r2 = path[i + 1]
            manhattan = abs(c1 - c2) + abs(r1 - r2)
            self.assertEqual(manhattan, 1, f"Passo diagonal inválido detectado entre {path[i]} e {path[i+1]}")

    def test_difficult_terrain_doubles_cost(self):
        """Verifica se terreno difícil dobra o custo métrico do passo de 5.0ft para 10.0ft."""
        start_cell = (5, 5)
        difficult_cells = {(5, 6)}  # Célula ao Norte é terreno difícil

        def is_diff(c, r):
            return (c, r) in difficult_cells

        res = MovementCalculator.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=10.0,
            columns=25,
            rows=14,
            feet_per_square=5.0,
            is_difficult_fn=is_diff,
        )

        # Norte custa 10ft por ser difícil
        self.assertEqual(res.get_cost((5, 6)), 10.0)
        # Sul custa 5ft por ser terreno normal
        self.assertEqual(res.get_cost((5, 4)), 5.0)

        # Com apenas 5ft disponíveis, o Norte NÃO deve ser alcançável
        res_5ft = MovementCalculator.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=5.0,
            columns=25,
            rows=14,
            feet_per_square=5.0,
            is_difficult_fn=is_diff,
        )
        self.assertNotIn((5, 6), res_5ft.reachable_cells)
        self.assertIn((5, 4), res_5ft.reachable_cells)

    def test_obstacles_and_hostiles_block_movement(self):
        """Garante que células bloqueadas ou ocupadas por inimigos hostis vivos sejam intransponíveis."""
        start_cell = (5, 5)
        blocked_cells = {(6, 5)}   # Parede ao Leste
        hostile_cells = {(5, 6)}   # Goblin hostil ao Norte

        def is_walkable(c, r):
            return (c, r) not in blocked_cells

        res = MovementCalculator.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=10.0,
            columns=25,
            rows=14,
            feet_per_square=5.0,
            is_walkable_fn=is_walkable,
            blocking_cells=hostile_cells,
        )

        # Leste está bloqueado e Norte tem inimigo -> nenhum é alcançável
        self.assertNotIn((6, 5), res.reachable_cells)
        self.assertNotIn((5, 6), res.reachable_cells)
        # Célula além do inimigo (5, 7) também não pode ser acessada através dele
        self.assertNotIn((5, 7), res.reachable_cells)

        # Sul e Oeste continuam livres
        self.assertIn((5, 4), res.reachable_cells)
        self.assertIn((4, 5), res.reachable_cells)

    def test_occupied_cells_cannot_be_destination(self):
        """Garante que células ocupadas por qualquer outro token não sejam destinos finais válidos."""
        start_cell = (5, 5)
        occupied = {(5, 4)}  # Aliado ao Sul

        res = MovementCalculator.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=10.0,
            columns=25,
            rows=14,
            feet_per_square=5.0,
            occupied_cells=occupied,
        )

        # Célula do aliado não é destino válido
        self.assertNotIn((5, 4), res.reachable_cells)
        # Mas a célula além do aliado (5, 3) pode ser acessada se atravessável
        self.assertIn((5, 3), res.reachable_cells)

    def test_entity_movement_tracking_and_reset(self):
        """Valida o estado interno de deslocamento gasto e disponível na classe Entity."""
        player = DummyPlayer(name="Artemis", speed=30)
        self.assertEqual(player.speed, 30)
        self.assertEqual(player.movement_spent_this_turn, 0.0)
        self.assertEqual(player.available_movement, 30.0)

        # Gasta 10 pés
        player.spend_movement(10.0)
        self.assertEqual(player.movement_spent_this_turn, 10.0)
        self.assertEqual(player.available_movement, 20.0)

        # Gasta mais 15 pés
        player.spend_movement(15.0)
        self.assertEqual(player.movement_spent_this_turn, 25.0)
        self.assertEqual(player.available_movement, 5.0)

        # Reseta movimento do turno
        player.reset_movement()
        self.assertEqual(player.movement_spent_this_turn, 0.0)
        self.assertEqual(player.available_movement, 30.0)

    def test_double_click_orthogonal_move_execution(self):
        """Valida o débito exato de movimento e alteração de coordenadas via CombatManager."""
        cm = CombatManager()
        player = DummyPlayer(name="Galahad", speed=30, position={"x": 5, "y": 5})
        cm.add_combatant(player)
        cm.start_combat()

        self.assertEqual(player.position, {"x": 5, "y": 5})
        self.assertEqual(player.movement_spent_this_turn, 0.0)

        # Move 3 quadrados para o Norte (5, 8) -> Custo: 15.0 ft
        success = cm.execute_orthogonal_move(player.uid, target_col=5, target_row=8)
        self.assertTrue(success)
        self.assertEqual(player.position, {"x": 5, "y": 8})
        self.assertEqual(player.movement_spent_this_turn, 15.0)
        self.assertEqual(player.available_movement, 15.0)

        # Move mais 2 quadrados para o Leste (7, 8) -> Custo: 10.0 ft
        success2 = cm.execute_orthogonal_move(player.uid, target_col=7, target_row=8)
        self.assertTrue(success2)
        self.assertEqual(player.position, {"x": 7, "y": 8})
        self.assertEqual(player.movement_spent_this_turn, 25.0)
        self.assertEqual(player.available_movement, 5.0)

    def test_drag_and_drop_free_movement_no_cost(self):
        """Garante que reposicionamento via drag-and-drop (teleporte / ajuste livre) NÃO consuma pontos de movimento."""
        cm = CombatManager()
        player = DummyPlayer(name="Mage", speed=30, position={"x": 2, "y": 2})
        cm.add_combatant(player)
        cm.start_combat()

        # Teleporte / Drag-and-drop para longe (15, 10)
        cm.set_combatant_position(player.uid, 15, 10)
        self.assertEqual(player.position, {"x": 15, "y": 10})

        # Regra de ouro: movement_spent_this_turn permanece intacto em 0.0
        self.assertEqual(player.movement_spent_this_turn, 0.0)
        self.assertEqual(player.available_movement, 30.0)

    def test_movement_exhaustion_clears_reachable_cells(self):
        """Garante que ao zerar o saldo de movimento, o conjunto de células alcançáveis seja vazio."""
        player = DummyPlayer(name="Rogue", speed=30, position={"x": 5, "y": 5})
        cm = CombatManager()
        cm.add_combatant(player)
        cm.start_combat()

        # Esgota todo o movimento
        player.spend_movement(30.0)
        self.assertEqual(player.available_movement, 0.0)

        res = MovementCalculator.calculate_for_entity(player, cm)
        self.assertEqual(len(res.reachable_cells), 0)
        self.assertEqual(res.reachable_cells, {})

    def test_turn_advancement_resets_movement(self):
        """Garante que a troca de turnos em CombatManager restaure o movimento do combatente ativo."""
        p1 = DummyPlayer(name="P1", speed=30, position={"x": 1, "y": 1})
        p2 = DummyPlayer(name="P2", speed=25, position={"x": 2, "y": 2})

        cm = CombatManager()
        cm.add_combatant(p1)
        cm.add_combatant(p2)
        cm.apply_initiatives({p1.uid: 20, p2.uid: 15})

        self.assertEqual(cm.active_character.uid, p1.uid)
        p1.spend_movement(20.0)
        self.assertEqual(p1.movement_spent_this_turn, 20.0)

        # Avança para P2
        cm.next_turn()
        self.assertEqual(cm.active_character.uid, p2.uid)
        self.assertEqual(p2.movement_spent_this_turn, 0.0)

        # Volta a rodada para P1 -> movimento deve ser resetado no início do turno
        cm.next_turn()
        self.assertEqual(cm.active_character.uid, p1.uid)
        self.assertEqual(p1.movement_spent_this_turn, 0.0)
        self.assertEqual(p1.available_movement, 30.0)

    def test_dm_manual_movement_reset(self):
        """Garante que o botão auxiliar do Mestre restaure os pontos do combatente selecionado."""
        p1 = DummyPlayer(name="Fighter", speed=30, position={"x": 3, "y": 3})
        cm = CombatManager()
        cm.add_combatant(p1)
        cm.start_combat()

        p1.spend_movement(25.0)
        self.assertEqual(p1.available_movement, 5.0)

        # Mestre clica no Reset
        success = cm.reset_combatant_movement(p1.uid)
        self.assertTrue(success)
        self.assertEqual(p1.movement_spent_this_turn, 0.0)
        self.assertEqual(p1.available_movement, 30.0)

    def test_minimap_single_click_and_double_click_interaction(self):
        """Valida que clique simples seleciona destino e duplo clique executa o movimento no TacticalMiniMap."""
        import arcade
        from src.manager.session_manager import SessionManager
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        sm = SessionManager()
        cm = sm.combat_manager
        p = DummyPlayer(name="Ranger", speed=30, position={"x": 2, "y": 2})
        cm.add_combatant(p)
        cm.start_combat()

        minimap = TacticalMiniMap(window=self.window, session_manager=sm)
        # Configura draw_rect de 500x500 na origem (0,0) com 25 colunas -> cell_size = 20px
        minimap._last_draw_rect = (0.0, 0.0, 500.0, 500.0)

        # Célula alvo (3, 2) -> 1 quadrado ao Leste (custo: 5ft).
        # Centro da célula (3, 2): x = 3.5 * 20 = 70.0, y = 2.5 * 20 = 50.0
        click_x, click_y = 70.0, 50.0

        # 1. Clique Simples: Seleciona célula alvo
        minimap.handle_mouse_press(click_x, click_y, button=arcade.MOUSE_BUTTON_LEFT)
        self.assertEqual(minimap.selected_target_cell, (3, 2))
        self.assertEqual(p.position, {"x": 2, "y": 2})
        self.assertEqual(p.movement_spent_this_turn, 0.0)

        # 2. Clique Duplo imediato (na mesma célula dentro de 0.4s) -> Confirma e move
        minimap.handle_mouse_press(click_x, click_y, button=arcade.MOUSE_BUTTON_LEFT)
        self.assertEqual(p.position, {"x": 3, "y": 2})
        self.assertEqual(p.movement_spent_this_turn, 5.0)
        self.assertEqual(p.available_movement, 25.0)
        self.assertIsNone(minimap.selected_target_cell)

    def test_minimap_click_outside_reachable_zone_deselects(self):
        """Valida que clicar fora da zona azul alcançável desmarca a célula alvo."""
        import arcade
        from src.manager.session_manager import SessionManager
        from src.ui.dm.tactical_minimap import TacticalMiniMap

        sm = SessionManager()
        cm = sm.combat_manager
        p = DummyPlayer(name="Paladin", speed=30, position={"x": 2, "y": 2})
        cm.add_combatant(p)
        cm.start_combat()

        minimap = TacticalMiniMap(window=self.window, session_manager=sm)
        minimap._last_draw_rect = (0.0, 0.0, 500.0, 500.0)

        # Seleciona célula alcançável (3, 2)
        minimap.handle_mouse_press(70.0, 50.0, button=arcade.MOUSE_BUTTON_LEFT)
        self.assertEqual(minimap.selected_target_cell, (3, 2))

        # Clica em célula muito distante inalcançável (20, 10): x=20.5*20=410, y=10.5*20=210
        minimap.handle_mouse_press(410.0, 210.0, button=arcade.MOUSE_BUTTON_LEFT)
        self.assertIsNone(minimap.selected_target_cell)

    def test_combat_tab_input_handler_reset_movement_button(self):
        """Valida que clicar no botão [ 🔄 Reset Mov ] restaura os pontos do turno."""
        from src.manager.session_manager import SessionManager
        from src.ui.dm.handlers.combat_tab_input_handler import CombatTabInputHandler

        sm = SessionManager()
        cm = sm.combat_manager
        p = DummyPlayer(name="Monk", speed=40, position={"x": 1, "y": 1})
        cm.add_combatant(p)
        cm.start_combat()

        p.spend_movement(30.0)
        self.assertEqual(p.available_movement, 10.0)

        mock_tab = MagicMock()
        mock_tab.combat_manager = cm
        mock_tab.add_token_modal.is_open = False
        mock_tab.pending_end_combat_modal = False
        mock_tab.spell_aoe_panel.handle_click.return_value = False

        panel_w = 600.0
        top_y = 700.0
        bar_y = top_y - 20
        info_y = bar_y - 24

        btn_rst_w = 88.0
        btn_rst_x = panel_w - 16 - btn_rst_w / 2

        # Clica exatamente sobre o botão Reset Mov
        handled = CombatTabInputHandler.handle_click(
            mock_tab, btn_rst_x, info_y, panel_w, top_y, open_initiative_modal_callback=MagicMock()
        )
        self.assertTrue(handled)
        self.assertEqual(p.movement_spent_this_turn, 0.0)
        self.assertEqual(p.available_movement, 40.0)

    def test_minimap_renderer_draw_content_with_movement(self):
        """Valida que MiniMapRenderer.draw_content executa perfeitamente sem erros durante o combate."""
        from src.manager.session_manager import SessionManager, DisplayState
        from src.ui.renderers.minimap_renderer import MiniMapRenderer
        from src.ui.components.grid_cell_highlighter import GridCellHighlighter

        sm = SessionManager()
        sm.set_display_state(DisplayState.COMBAT)
        cm = sm.combat_manager
        p = DummyPlayer(name="Sorcerer", speed=30, position={"x": 5, "y": 5})
        cm.add_combatant(p)
        cm.start_combat()

        texture_cache = {}
        text_cache = {}
        movement_hl = GridCellHighlighter()
        aoe_hl = GridCellHighlighter()

        # Renderiza sem seleção
        MiniMapRenderer.draw_content(
            window_width=1280,
            window_height=720,
            draw_rect=(100.0, 100.0, 500.0, 500.0),
            session_manager=sm,
            texture_cache=texture_cache,
            text_cache=text_cache,
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            movement_highlighter=movement_hl,
            selected_target_cell=None,
        )

        # Renderiza com seleção de célula alvo (5, 6)
        MiniMapRenderer.draw_content(
            window_width=1280,
            window_height=720,
            draw_rect=(100.0, 100.0, 500.0, 500.0),
            session_manager=sm,
            texture_cache=texture_cache,
            text_cache=text_cache,
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            movement_highlighter=movement_hl,
            selected_target_cell=(5, 6),
        )

    def test_character_builder_speed_dict_and_walk_defaults(self):
        """Valida que o CharacterBuilder e os JSONs de personagens suportam speed com walk=30."""
        from src.domain.builders.character_builder import CharacterBuilder

        # Teste 1: Parsing de dicionário {"walk": 30, "fly": 0, "swim": 0}
        builder = CharacterBuilder()
        char = builder.from_dict({
            "uid": "char_test_1",
            "name": "Test Wizard",
            "speed": {"walk": 30, "fly": 0, "swim": 0},
            "vitality": {"max_hp": 20, "current_hp": 20},
        }).build()
        self.assertEqual(char.speed, 30)
        self.assertEqual(char.available_movement, 30.0)

        # Teste 2: Parsing de inteiro direto
        char2 = CharacterBuilder().from_dict({
            "uid": "char_test_2",
            "name": "Barbarian",
            "speed": 40,
        }).build()
        self.assertEqual(char2.speed, 40)

    def test_player_view_renderer_maximized_draw_rect(self):
        """Valida que calculate_draw_rect maximiza o enquadramento na tela inteira sem margens artificiais."""
        from src.ui.renderers.player_view_renderer import PlayerViewRenderer
        from src.manager.grid_manager import GridManager

        # Caso 1: Mapa 16:9 em tela 16:9 (1920x1080) -> Ocupa 100% da tela
        grid_mgr_16_9 = GridManager(map_width=1600.0, map_height=900.0, columns=16)
        rx, ry, rw, rh = PlayerViewRenderer.calculate_draw_rect(1920.0, 1080.0, grid_mgr_16_9)
        self.assertAlmostEqual(rw, 1920.0, places=1)
        self.assertAlmostEqual(rh, 1080.0, places=1)
        self.assertAlmostEqual(rx, 0.0, places=1)
        self.assertAlmostEqual(ry, 0.0, places=1)

        # Caso 2: Mapa 25x15 em tela 1920x1080 -> Aspect 5:3, ocupa altura total (1080px) e largura 1800px centrada
        grid_mgr_25_15 = GridManager(map_width=1920.0, map_height=1080.0, columns=25)
        rx2, ry2, rw2, rh2 = PlayerViewRenderer.calculate_draw_rect(1920.0, 1080.0, grid_mgr_25_15)
        self.assertAlmostEqual(rw2, 1800.0, places=1)
        self.assertAlmostEqual(rh2, 1080.0, places=1)
        self.assertAlmostEqual(rx2, 60.0, places=1)
        self.assertAlmostEqual(ry2, 0.0, places=1)

    def test_minimap_input_handler_fog_panel_and_token_safety(self):
        """Valida compatibilidade com FogControlPanel (FogTool e BrushMode) sem lançar exceções."""
        import arcade
        from src.manager.session_manager import SessionManager
        from src.ui.dm.tactical_minimap import TacticalMiniMap
        from src.ui.dm.fog_control_panel import FogControlPanel, FogTool, BrushMode
        from src.domain.models.fog_manager import FogManager

        sm = SessionManager()
        cm = sm.combat_manager
        p = DummyPlayer(name="Ranger", speed=30, position={"x": 2, "y": 2})
        cm.add_combatant(p)
        cm.start_combat()

        fog_panel = FogControlPanel(fog_manager=cm.fog_manager)
        fog_panel.active_tool = FogTool.ADD
        fog_panel.brush_mode = BrushMode.SINGLE

        minimap = TacticalMiniMap(window=self.window, session_manager=sm, fog_panel=fog_panel)
        minimap._last_draw_rect = (0.0, 0.0, 500.0, 500.0)

        # Clica para adicionar névoa
        handled = minimap.handle_mouse_press(100.0, 100.0, button=arcade.MOUSE_BUTTON_LEFT)
        self.assertTrue(handled)
        self.assertTrue(cm.fog_manager.is_fogged(5, 5))

        # Desativa ferramenta de névoa e testa seleção de token
        fog_panel.active_tool = FogTool.NONE
        handled = minimap.handle_mouse_press(50.0, 50.0, button=arcade.MOUSE_BUTTON_LEFT)
        self.assertTrue(handled)
        self.assertEqual(minimap._dragged_combatant_uid, p.uid)

    def test_player_view_renderer_draw_combat_with_movement_overlay(self):
        """Valida que a zona azul de movimento ortogonal renderiza com sucesso na tela do jogador."""
        from src.manager.session_manager import SessionManager, DisplayState
        from src.ui.renderers.player_view_renderer import PlayerViewRenderer
        from src.ui.components.grid_cell_highlighter import GridCellHighlighter
        from src.ui.initiative_hud import InitiativeHUD

        sm = SessionManager()
        sm.set_display_state(DisplayState.COMBAT)
        cm = sm.combat_manager
        p = DummyPlayer(name="Fighter", speed=30, position={"x": 3, "y": 3})
        cm.add_combatant(p)
        cm.start_combat()

        mov_hl = GridCellHighlighter(grid_manager=cm.grid_manager)
        aoe_hl = GridCellHighlighter(grid_manager=cm.grid_manager)
        hud = InitiativeHUD(cm)

        # 1. Renderiza tela de combate dos jogadores com zona azul de movimento
        PlayerViewRenderer.draw_combat(
            window_width=1920,
            window_height=1080,
            combat_manager=cm,
            texture_cache={},
            text_cache={},
            tilemap_renderer=None,
            aoe_highlighter=aoe_hl,
            token_sprites={},
            hud=hud,
            movement_highlighter=mov_hl,
            selected_target_cell=(3, 4),
            selected_combatant_uid=p.uid,
        )

        # Células alcançáveis devem ter sido calculadas e preenchidas no highlighter
        self.assertTrue(len(mov_hl.highlighted_cells) > 0)
        self.assertIn((3, 4), mov_hl.highlighted_cells)


if __name__ == "__main__":
    unittest.main()



