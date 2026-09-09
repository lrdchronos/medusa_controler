import unittest
import sys
import math
from pathlib import Path
import arcade

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.utils.status_icon_atlas import StatusIconAtlas
from src.ui.renderers.token_status_renderer import TokenStatusRenderer
from src.domain.models.entity import Entity, EntityType, DynamicToken
from src.domain.models.monster import Monster
from src.domain.models.playablechar import PlayableCharacter
from src.domain.builders.character_builder import CharacterBuilder
from src.domain.builders.monster_builder import MonsterBuilder
from src.manager.grid_manager import GridManager
from src.manager.combat_manager import CombatManager
from src.domain.models.tile_map import TileMap
from src.ui.dm.add_token_modal import AddTokenModal


class TestStatusIconAtlas(unittest.TestCase):
    """Testes unitários para o carregador e atlas de ícones de status (StatusIconAtlas)."""

    def setUp(self):
        StatusIconAtlas.clear_cache()
        self.atlas_path = "assets/sprites/status_icons.png"

    def test_load_atlas_and_crop_dimensions(self):
        """Verifica se o spritesheet é fatiado corretamente em ícones de 16x16px."""
        success = StatusIconAtlas.load_atlas(self.atlas_path)
        self.assertTrue(success, "O carregamento do spritesheet status_icons.png deve ser bem sucedido.")

        # Verifica indicadores de saúde (Linha 0)
        health_icons = ["health_green", "health_yellow", "health_red"]
        for h_name in health_icons:
            tex = StatusIconAtlas.get_health_texture(h_name)
            self.assertIsNotNone(tex, f"Textura '{h_name}' deve existir no atlas.")
            self.assertEqual(tex.width, 16, f"Largura do ícone '{h_name}' deve ser 16px.")
            self.assertEqual(tex.height, 16, f"Altura do ícone '{h_name}' deve ser 16px.")

        # Verifica 11 condições canônicas D&D 5E (Linha 1)
        canonical_conditions = [
            "poisoned", "blinded", "frightened", "charmed", "restrained",
            "deafened", "petrified", "paralyzed", "invisible", "stunned", "prone"
        ]
        self.assertEqual(len(StatusIconAtlas.get_condition_names()), 11)

        for cond_name in canonical_conditions:
            tex = StatusIconAtlas.get_condition_texture(cond_name)
            self.assertIsNotNone(tex, f"Textura da condição '{cond_name}' deve existir no atlas.")
            self.assertEqual(tex.width, 16, f"Largura da condição '{cond_name}' deve ser 16px.")
            self.assertEqual(tex.height, 16, f"Altura da condição '{cond_name}' deve ser 16px.")
            self.assertIn(cond_name, StatusIconAtlas.CONDITION_LABELS)

    def test_atlas_caching_avoids_redundant_io(self):
        """Garante que chamadas subsequentes a get_texture usem o cache em memória."""
        StatusIconAtlas.load_atlas(self.atlas_path)
        tex1 = StatusIconAtlas.get_texture("poisoned")
        tex2 = StatusIconAtlas.get_texture("poisoned")
        self.assertIs(tex1, tex2, "A sub-textura deve ser idêntica em memória graças ao cache.")

    def test_health_bracket_selection(self):
        """Testa o cálculo da regra de seleção dos ícones de saúde com base nas faixas de HP."""
        # > 50% -> health_green
        self.assertEqual(StatusIconAtlas.get_health_icon_name(100, 100), "health_green")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(51, 100), "health_green")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(6, 10), "health_green")

        # 25% <= HP <= 50% -> health_yellow
        self.assertEqual(StatusIconAtlas.get_health_icon_name(50, 100), "health_yellow")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(25, 100), "health_yellow")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(5, 10), "health_yellow")

        # < 25% -> health_red
        self.assertEqual(StatusIconAtlas.get_health_icon_name(24, 100), "health_red")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(1, 100), "health_red")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(0, 100), "health_red")
        self.assertEqual(StatusIconAtlas.get_health_icon_name(0, 0), "health_red")

    def test_condition_labels_portuguese(self):
        """Verifica a internacionalização dos rótulos em português das condições."""
        self.assertEqual(StatusIconAtlas.get_condition_label("poisoned"), "Envenenado")
        self.assertEqual(StatusIconAtlas.get_condition_label("blinded"), "Cego")
        self.assertEqual(StatusIconAtlas.get_condition_label("frightened"), "Amedrontado")
        self.assertEqual(StatusIconAtlas.get_condition_label("charmed"), "Enfeitiçado")
        self.assertEqual(StatusIconAtlas.get_condition_label("restrained"), "Restringido")
        self.assertEqual(StatusIconAtlas.get_condition_label("deafened"), "Surdo")
        self.assertEqual(StatusIconAtlas.get_condition_label("petrified"), "Petrificado")
        self.assertEqual(StatusIconAtlas.get_condition_label("paralyzed"), "Paralisado")
        self.assertEqual(StatusIconAtlas.get_condition_label("invisible"), "Invisível")
        self.assertEqual(StatusIconAtlas.get_condition_label("stunned"), "Atordoado")
        self.assertEqual(StatusIconAtlas.get_condition_label("prone"), "Derrubado / Caído")


class TestOrbitalClockMath(unittest.TestCase):
    """Testes unitários para o Algoritmo Orbital de Relógio (TokenStatusRenderer)."""

    def test_12h_cardinal_clock_coordinates(self):
        """Verifica as 4 posições cardeais do relógio (12h, 3h, 6h, 9h) via trigonometria."""
        center_x = 200.0
        center_y = 200.0
        token_radius = 20.0
        icon_size = 16.0
        expected_orbit_radius = token_radius + (icon_size / 2.0)  # 20 + 8 = 28.0

        # 12h -> Ângulo 90°: Topo puro (x = center_x, y = center_y + orbit_radius)
        x12, y12 = TokenStatusRenderer.calculate_slot_position(center_x, center_y, token_radius, 12, icon_size)
        self.assertAlmostEqual(x12, center_x, places=4)
        self.assertAlmostEqual(y12, center_y + expected_orbit_radius, places=4)

        # 3h -> Ângulo 0°: Direita pura (x = center_x + orbit_radius, y = center_y)
        x3, y3 = TokenStatusRenderer.calculate_slot_position(center_x, center_y, token_radius, 3, icon_size)
        self.assertAlmostEqual(x3, center_x + expected_orbit_radius, places=4)
        self.assertAlmostEqual(y3, center_y, places=4)

        # 6h -> Ângulo -90°: Fundo puro (x = center_x, y = center_y - orbit_radius)
        x6, y6 = TokenStatusRenderer.calculate_slot_position(center_x, center_y, token_radius, 6, icon_size)
        self.assertAlmostEqual(x6, center_x, places=4)
        self.assertAlmostEqual(y6, center_y - expected_orbit_radius, places=4)

        # 9h -> Ângulo -180°: Esquerda pura (x = center_x - orbit_radius, y = center_y)
        x9, y9 = TokenStatusRenderer.calculate_slot_position(center_x, center_y, token_radius, 9, icon_size)
        self.assertAlmostEqual(x9, center_x - expected_orbit_radius, places=4)
        self.assertAlmostEqual(y9, center_y, places=4)

    def test_clockwise_sequential_slots(self):
        """Garante que as horas 1h a 11h avancem estritamente no sentido horário."""
        center_x = 100.0
        center_y = 100.0
        token_radius = 16.0
        icon_size = 16.0

        # 1h: 60° (x > center_x, y > center_y)
        x1, y1 = TokenStatusRenderer.calculate_slot_position(center_x, center_y, token_radius, 1, icon_size)
        self.assertGreater(x1, center_x)
        self.assertGreater(y1, center_y)

        # 2h: 30° (x > x1, 0 < y < y1)
        x2, y2 = TokenStatusRenderer.calculate_slot_position(center_x, center_y, token_radius, 2, icon_size)
        self.assertGreater(x2, x1)
        self.assertLess(y2, y1)
        self.assertGreater(y2, center_y)

    def test_angular_step_progression(self):
        """Valida que o passo angular respeita 40° até 8 condições e atinge exatamente 30° para 11."""
        # N <= 8 -> Fixo em 40°
        self.assertEqual(TokenStatusRenderer.calculate_angular_step(1), 40.0)
        self.assertEqual(TokenStatusRenderer.calculate_angular_step(3), 40.0)
        self.assertEqual(TokenStatusRenderer.calculate_angular_step(5), 40.0)
        self.assertEqual(TokenStatusRenderer.calculate_angular_step(8), 40.0)

        # N = 9 -> 40 - 1*(10/3) = 36.6667°
        step_9 = TokenStatusRenderer.calculate_angular_step(9)
        self.assertAlmostEqual(step_9, 40.0 - (10.0 / 3.0), places=4)
        self.assertAlmostEqual(step_9, 36.6667, places=3)

        # N = 10 -> 40 - 2*(10/3) = 33.3333°
        step_10 = TokenStatusRenderer.calculate_angular_step(10)
        self.assertAlmostEqual(step_10, 40.0 - 2.0 * (10.0 / 3.0), places=4)
        self.assertAlmostEqual(step_10, 33.3333, places=3)

        # N = 11 -> 40 - 3*(10/3) = 30.0°
        step_11 = TokenStatusRenderer.calculate_angular_step(11)
        self.assertAlmostEqual(step_11, 30.0, places=4)

    def test_bilateral_symmetry_of_conditions(self):
        """Valida a simetria bilateral dos ângulos e coordenadas em torno do eixo vertical (270°/Y)."""
        # Teste com N = 3 condições (passo de 40°)
        angles_3 = [TokenStatusRenderer.calculate_condition_angle(i, 3) for i in range(3)]
        self.assertAlmostEqual(angles_3[0], 230.0)  # -40° de 270°
        self.assertAlmostEqual(angles_3[1], 270.0)  # Centro em 270° (6h)
        self.assertAlmostEqual(angles_3[2], 310.0)  # +40° de 270°
        # Soma dos desvios em relação a 270° deve ser exatamente zero (balanceamento perfeito)
        self.assertAlmostEqual(sum(a - 270.0 for a in angles_3), 0.0, places=4)

        # Simetria de coordenadas (X espelhado em relação ao centro)
        cx, cy, r = 200.0, 200.0, 20.0
        x0, y0 = TokenStatusRenderer.calculate_position_by_angle(cx, cy, r, angles_3[0])
        x2, y2 = TokenStatusRenderer.calculate_position_by_angle(cx, cy, r, angles_3[2])
        self.assertAlmostEqual(x0 - cx, -(x2 - cx), places=4)
        self.assertAlmostEqual(y0, y2, places=4)

        # Teste com N = 8 condições (passo de 40°)
        angles_8 = [TokenStatusRenderer.calculate_condition_angle(i, 8) for i in range(8)]
        self.assertAlmostEqual(sum(a - 270.0 for a in angles_8), 0.0, places=4)
        # Primeiro ângulo (i=0): 270 - 3.5 * 40 = 130° (40° de distância do topo 90°)
        self.assertAlmostEqual(angles_8[0], 130.0)
        # Último ângulo (i=7): 270 + 3.5 * 40 = 410° (equivalente a 50°, 40° de distância do topo 90°)
        self.assertAlmostEqual(angles_8[-1], 410.0)

        # Teste com N = 11 condições (passo de 30°)
        angles_11 = [TokenStatusRenderer.calculate_condition_angle(i, 11) for i in range(11)]
        self.assertAlmostEqual(sum(a - 270.0 for a in angles_11), 0.0, places=4)
        # Primeiro ângulo (i=0): 270 - 5 * 30 = 120° (30° de folga para 90°)
        self.assertAlmostEqual(angles_11[0], 120.0)
        # Último ângulo (i=10): 270 + 5 * 30 = 420° (60°, 30° de folga para 90°)
        self.assertAlmostEqual(angles_11[-1], 420.0)

    def test_orbital_slots_generation_for_entity(self):
        """Verifica a montagem dos slots orbitais com saúde em 12h e condições ativas de 1h em diante."""
        StatusIconAtlas.load_atlas("assets/sprites/status_icons.png")

        monster = Monster(name="Ogro Envenenado", max_hp=50, size="Large")
        monster.set_current_hp(20)  # 40% -> health_yellow
        monster.add_condition("poisoned")
        monster.add_condition("blinded")

        slots = TokenStatusRenderer.get_orbital_slots(
            entity=monster,
            center_x=300.0,
            center_y=300.0,
            token_radius=32.0,
            scale_factor=1.0,
        )

        # Deve conter 3 slots: 12h (health_yellow), 1h (poisoned), 2h (blinded)
        self.assertEqual(len(slots), 3)

        # Slot 12h
        slot_12 = next(s for s in slots if s["hour"] == 12)
        self.assertEqual(slot_12["name"], "health_yellow")
        self.assertEqual(slot_12["type"], "health")

        # Slot 1h
        slot_1 = next(s for s in slots if s["hour"] == 1)
        self.assertEqual(slot_1["name"], "poisoned")

        # Slot 2h
        slot_2 = next(s for s in slots if s["hour"] == 2)
        self.assertEqual(slot_2["name"], "blinded")

    def test_neutral_token_without_health_omits_12h_slot(self):
        """Garante que tokens neutros sem vida gerenciada omitam o indicador de saúde 12h."""
        StatusIconAtlas.load_atlas("assets/sprites/status_icons.png")

        spell_token = DynamicToken(name="Muralha de Chamas", entity_type=EntityType.NEUTRAL, max_hp=1)
        spell_token.add_condition("invisible")

        slots = TokenStatusRenderer.get_orbital_slots(
            entity=spell_token,
            center_x=100.0,
            center_y=100.0,
            token_radius=16.0,
            scale_factor=1.0,
        )

        # Deve conter apenas a condição no slot 1h, sem slot 12h
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["hour"], 1)
        self.assertEqual(slots[0]["name"], "invisible")


class TestEntityConditionsAndState(unittest.TestCase):
    """Testes unitários para manipulação do conjunto de condições e integração com o Observer."""

    def test_entity_conditions_set_operations(self):
        """Verifica add_condition, remove_condition, has_condition, toggle_condition e clear_conditions."""
        char = PlayableCharacter(name="Guerreiro")
        self.assertEqual(char.conditions, set())

        # Adiciona condição
        char.add_condition("stunned")
        self.assertTrue(char.has_condition("stunned"))
        self.assertTrue(char.has_condition("STUNNED"))  # Case insensitive
        self.assertIn("stunned", char.conditions)

        # Adição duplicada não cria redundância (comportamento de set)
        char.add_condition("stunned")
        self.assertEqual(len(char.conditions), 1)

        # Alterna condição existente -> deve remover
        res1 = char.toggle_condition("stunned")
        self.assertFalse(res1)
        self.assertFalse(char.has_condition("stunned"))

        # Alterna condição inexistente -> deve adicionar
        res2 = char.toggle_condition("frightened")
        self.assertTrue(res2)
        self.assertTrue(char.has_condition("frightened"))

        # Remove condição
        char.remove_condition("frightened")
        self.assertFalse(char.has_condition("frightened"))

        # Limpa condições
        char.add_condition("prone")
        char.add_condition("restrained")
        self.assertEqual(len(char.conditions), 2)
        char.clear_conditions()
        self.assertEqual(len(char.conditions), 0)

    def test_combat_manager_toggle_condition_and_observer(self):
        """Verifica se CombatManager.toggle_condition altera a entidade e notifica os listeners."""
        cm = CombatManager()
        char = PlayableCharacter(name="Mago", uid="char_123")
        cm.add_combatant(char)

        notified = False
        def on_change():
            nonlocal notified
            notified = True

        cm.add_listener(on_change)

        # Alterna condição via CombatManager
        is_active = cm.toggle_condition("char_123", "poisoned")
        self.assertTrue(is_active)
        self.assertTrue(char.has_condition("poisoned"))
        self.assertTrue(notified)

        # Alterna novamente -> deve desativar e notificar
        notified = False
        is_active_2 = cm.toggle_condition("char_123", "poisoned")
        self.assertFalse(is_active_2)
        self.assertFalse(char.has_condition("poisoned"))
        self.assertTrue(notified)


class TestCreatureSizesAndGrid(unittest.TestCase):
    """Testes unitários para Categorias de Tamanho de Criaturas D&D 5E e Matemática de Grid."""

    def setUp(self):
        # Grid 10x10 com 32px por célula
        self.grid = GridManager(map_width=320.0, map_height=320.0, columns=10, feet_per_square=5.0)

    def test_size_normalization_and_squares_mapping(self):
        """Verifica a conversão canônica de categorias D&D 5E para dimensões em quadrados."""
        # Teste na Entity
        e_tiny = DynamicToken(name="Fada", size="tiny")
        self.assertEqual(e_tiny.size, "Tiny")
        self.assertEqual(e_tiny.size_in_squares, 1)

        e_med = PlayableCharacter(name="Humano", size="Medium")
        self.assertEqual(e_med.size, "Medium")
        self.assertEqual(e_med.size_in_squares, 1)

        e_large = Monster(name="Cavalo", size="Large")
        self.assertEqual(e_large.size, "Large")
        self.assertEqual(e_large.size_in_squares, 2)

        e_huge = Monster(name="Gigante do Gelo", size="huge")
        self.assertEqual(e_huge.size, "Huge")
        self.assertEqual(e_huge.size_in_squares, 3)

        e_garg = Monster(name="Tarrasque", size="gargantuan")
        self.assertEqual(e_garg.size, "Gargantuan")
        self.assertEqual(e_garg.size_in_squares, 4)

        # Fallback para tamanhos inválidos -> Medium / 1
        e_inv = Monster(name="Desconhecido", size="colossal_invalid")
        self.assertEqual(e_inv.size, "Medium")
        self.assertEqual(e_inv.size_in_squares, 1)

    def test_creature_grid_cells_occupancy(self):
        """Verifica a lista de células ocupadas para criaturas 1x1, 2x2 e 3x3."""
        # 1x1 em (2, 3)
        cells_1x1 = self.grid.get_creature_grid_cells(2, 3, "Medium")
        self.assertEqual(cells_1x1, [(2, 3)])

        # 2x2 em (2, 3) -> [(2, 3), (2, 4), (3, 3), (3, 4)]
        cells_2x2 = self.grid.get_creature_grid_cells(2, 3, "Large")
        self.assertEqual(len(cells_2x2), 4)
        self.assertIn((2, 3), cells_2x2)
        self.assertIn((3, 3), cells_2x2)
        self.assertIn((2, 4), cells_2x2)
        self.assertIn((3, 4), cells_2x2)

        # 3x3 em (0, 0) -> 9 células
        cells_3x3 = self.grid.get_creature_grid_cells(0, 0, "Huge")
        self.assertEqual(len(cells_3x3), 9)

    def test_creature_geometric_center(self):
        """Verifica se o ponto central calculado respeita a âncora de cada categoria de tamanho."""
        cell_size = self.grid.cell_size  # 32.0px

        # 1x1 em (0, 0): Centro da célula (0.5 * 32 = 16.0, 16.0)
        cx1, cy1 = self.grid.get_creature_center(0, 0, "Medium")
        self.assertAlmostEqual(cx1, 16.0)
        self.assertAlmostEqual(cy1, 16.0)

        # 2x2 em (0, 0): Interseção das linhas do grid (1.0 * 32 = 32.0, 32.0)
        cx2, cy2 = self.grid.get_creature_center(0, 0, "Large")
        self.assertAlmostEqual(cx2, 32.0)
        self.assertAlmostEqual(cy2, 32.0)

        # 3x3 em (0, 0): Centro da célula central (1.5 * 32 = 48.0, 48.0)
        cx3, cy3 = self.grid.get_creature_center(0, 0, "Huge")
        self.assertAlmostEqual(cx3, 48.0)
        self.assertAlmostEqual(cy3, 48.0)

        # 4x4 em (0, 0): Interseção das linhas (2.0 * 32 = 64.0, 64.0)
        cx4, cy4 = self.grid.get_creature_center(0, 0, "Gargantuan")
        self.assertAlmostEqual(cx4, 64.0)
        self.assertAlmostEqual(cy4, 64.0)

    def test_area_walkability_validation_for_large_creatures(self):
        """Verifica se is_walkable_for_size bloqueia movimento quando qualquer célula do footprint estiver obstruída."""
        cm = CombatManager()
        # Matriz 4x4
        from src.domain.models.tile_map import TileProperties
        tile_map = TileMap(
            width=4,
            height=4,
            tileset_name="test_tileset",
            tactical_grid={(1, 2): TileProperties(blocks_movement=True)},
        )
        cm.set_tile_map(tile_map)

        # Célula (0, 0) sozinha é transitável (1x1)
        self.assertTrue(cm.is_walkable_for_size(0, 0, "Medium"))

        # Criatura 2x2 em (0, 0) ocupa (0,0), (1,0), (0,1), (1,1) -> como (1,1) está bloqueada, DEVE retornar False!
        self.assertFalse(cm.is_walkable_for_size(0, 0, "Large"))

        # Criatura 2x2 em (2, 2) ocupa (2,2), (3,2), (2,3), (3,3) -> livre -> DEVE retornar True!
        self.assertTrue(cm.is_walkable_for_size(2, 2, "Large"))

        # Criatura 2x2 em (3, 3) ultrapassa os limites do grid (4x4) -> DEVE retornar False!
        self.assertFalse(cm.is_walkable_for_size(3, 3, "Large"))

    def test_builders_support_size(self):
        """Verifica se CharacterBuilder e MonsterBuilder preservam o tamanho configurado."""
        char = CharacterBuilder().with_name("Halfling Ladino").with_size("Small").build()
        self.assertEqual(char.size, "Small")
        self.assertEqual(char.size_in_squares, 1)

        monster = MonsterBuilder().with_name("Dragão Vermelho Ancião").with_size("Gargantuan").build()
        self.assertEqual(monster.size, "Gargantuan")
        self.assertEqual(monster.size_in_squares, 4)

    def test_modal_size_selection_and_large_token_instantiation(self):
        """Valida que o AddTokenModal permite seleção de tamanho 'Large' e que a entidade ocupa 4 células."""
        modal = AddTokenModal()
        modal.open()
        modal.name_input.set_text("Ogro Chefe")
        modal.selected_size = "Large"

        captured_data = None
        def on_confirm_cb(data):
            nonlocal captured_data
            captured_data = data

        modal.on_confirm = on_confirm_cb
        modal._handle_confirm()

        self.assertIsNotNone(captured_data)
        self.assertEqual(captured_data["name"], "Ogro Chefe")
        self.assertEqual(captured_data["size"], "Large")

        # Criação da entidade e validação de 4 células
        token = DynamicToken(
            name=captured_data["name"],
            size=captured_data["size"],
            max_hp=captured_data["max_hp"],
            armor_class=captured_data["armor_class"],
            entity_type=captured_data["entity_type"],
        )
        self.assertEqual(token.size, "Large")
        self.assertEqual(token.size_in_squares, 2)

        # Ocupação de 4 células no GridManager em (2, 2)
        cells = self.grid.get_creature_grid_cells(2, 2, token.size)
        self.assertEqual(len(cells), 4)
        self.assertEqual(cells, [(2, 2), (2, 3), (3, 2), (3, 3)])


if __name__ == "__main__":
    unittest.main()

