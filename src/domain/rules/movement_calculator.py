import heapq
import logging
from typing import Dict, Tuple, List, Optional, Set, Callable, Any
from ..models.entity import Entity, EntityType

logger = logging.getLogger(__name__)


class MovementResult:
    """
    Objeto de valor imutável contendo o resultado do cálculo de deslocamento ortogonal.
    Encapsula o mapa de células alcançáveis com seus custos acumulados em pés e a árvore de predecessores.
    """

    def __init__(
        self,
        reachable_cells: Dict[Tuple[int, int], float],
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]],
        start_cell: Tuple[int, int],
    ) -> None:
        self.__reachable_cells: Dict[Tuple[int, int], float] = dict(reachable_cells)
        self.__came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = dict(came_from)
        self.__start_cell: Tuple[int, int] = (int(start_cell[0]), int(start_cell[1]))

    @property
    def reachable_cells(self) -> Dict[Tuple[int, int], float]:
        """Retorna uma cópia defensiva do dicionário de células alcançáveis mapeadas ao custo em pés."""
        return self.__reachable_cells.copy()

    @property
    def came_from(self) -> Dict[Tuple[int, int], Optional[Tuple[int, int]]]:
        """Retorna uma cópia defensiva da árvore de predecessores para reconstrução de caminhos."""
        return self.__came_from.copy()

    @property
    def start_cell(self) -> Tuple[int, int]:
        """Coordenada matricial de origem do deslocamento."""
        return self.__start_cell

    def is_reachable(self, cell: Tuple[int, int]) -> bool:
        """Verifica se a célula especificada pode ser alcançada com o saldo de movimento."""
        return (int(cell[0]), int(cell[1])) in self.__reachable_cells

    def get_cost(self, cell: Tuple[int, int]) -> Optional[float]:
        """Retorna o custo em pés para alcançar a célula especificada, ou None se inalcançável."""
        return self.__reachable_cells.get((int(cell[0]), int(cell[1])))

    def get_path(self, target_cell: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Reconstrói o caminho ortogonal mais curto (4-vizinhança) da célula inicial até a célula alvo.
        Retorna uma lista de tuplas (col, row) iniciando em start_cell e terminando em target_cell.
        Retorna lista vazia caso a célula não seja alcançável.
        """
        target = (int(target_cell[0]), int(target_cell[1]))
        if target == self.__start_cell:
            return [self.__start_cell]
        if target not in self.__came_from or target not in self.__reachable_cells:
            return []

        path: List[Tuple[int, int]] = []
        curr: Optional[Tuple[int, int]] = target
        while curr is not None:
            path.append(curr)
            curr = self.__came_from.get(curr)

        path.reverse()
        return path

    def __len__(self) -> int:
        return len(self.__reachable_cells)

    def __repr__(self) -> str:
        return (
            f"<MovementResult start={self.__start_cell} "
            f"reachable_count={len(self.__reachable_cells)}>"
        )


class MovementCalculator:
    """
    Motor desacoplado de cálculo de alcance de deslocamento estritamente ortogonal (4-vizinhança).
    Utiliza algoritmo de Dijkstra para encontrar todos os caminhos mínimos sem movimentos diagonais,
    respeitando custos de terreno difícil (2x) e bloqueios de colisões / tokens hostis vivos.
    """

    # Estritamente 4 vizinhos ortogonais (Norte, Sul, Leste, Oeste) - Zero diagonais
    ORTHOGONAL_NEIGHBORS: List[Tuple[int, int]] = [
        (0, 1),   # Norte
        (0, -1),  # Sul
        (1, 0),   # Leste
        (-1, 0),  # Oeste
    ]

    @classmethod
    def calculate_reachable_cells(
        cls,
        start_cell: Tuple[int, int],
        max_movement_feet: float,
        columns: int,
        rows: int,
        feet_per_square: float = 5.0,
        is_walkable_fn: Optional[Callable[[int, int], bool]] = None,
        is_difficult_fn: Optional[Callable[[int, int], bool]] = None,
        occupied_cells: Optional[Set[Tuple[int, int]]] = None,
        blocking_cells: Optional[Set[Tuple[int, int]]] = None,
    ) -> MovementResult:
        """
        Calcula todas as células acessíveis a partir de start_cell com base no orçamento em pés.

        :param start_cell: Tupla (col, row) da posição de origem.
        :param max_movement_feet: Orçamento máximo de movimento disponível em pés.
        :param columns: Total de colunas na grade tática.
        :param rows: Total de linhas na grade tática.
        :param feet_per_square: Escala de pés por quadrado da grade (padrão 5.0).
        :param is_walkable_fn: Função (col, row) -> bool indicando se a célula é transitável no terreno/mapa.
        :param is_difficult_fn: Função (col, row) -> bool indicando se o terreno é difícil (custo dobrado).
        :param occupied_cells: Conjunto de células ocupadas por tokens (não podem ser destino final).
        :param blocking_cells: Conjunto de células intransponíveis (ex: inimigos hostis vivos / obstáculos).
        :return: Instância de MovementResult com as células acessíveis e grafo de caminhos.
        """
        start = (int(start_cell[0]), int(start_cell[1]))
        occ_set = set(occupied_cells) if occupied_cells else set()
        blk_set = set(blocking_cells) if blocking_cells else set()

        if columns <= 0 or rows <= 0 or max_movement_feet <= 0.0:
            return MovementResult(
                reachable_cells={},
                came_from={start: None},
                start_cell=start,
            )

        if not (0 <= start[0] < columns and 0 <= start[1] < rows):
            logger.warning("Célula inicial %s fora dos limites da grade (%dx%d).", start, columns, rows)
            return MovementResult(
                reachable_cells={},
                came_from={start: None},
                start_cell=start,
            )

        # Fila de prioridade Dijkstra: (custo_acumulado, (col, row))
        pq: List[Tuple[float, Tuple[int, int]]] = [(0.0, start)]
        distances: Dict[Tuple[int, int], float] = {start: 0.0}
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}

        while pq:
            current_dist, (c, r) = heapq.heappop(pq)

            if current_dist > distances.get((c, r), float("inf")):
                continue

            # Avaliação estrita dos 4 vizinhos ortogonais
            for dc, dr in cls.ORTHOGONAL_NEIGHBORS:
                nc, nr = c + dc, r + dr
                neighbor = (nc, nr)

                # Validação de limites da grade
                if not (0 <= nc < columns and 0 <= nr < rows):
                    continue

                # Validação de transitabilidade física do terreno / mapa
                if is_walkable_fn is not None and not is_walkable_fn(nc, nr):
                    continue

                # Validação de bloqueio intransponível (tokens hostis vivos / obstáculos travados)
                if neighbor in blk_set and neighbor != start:
                    continue

                # Cálculo de custo da transição para a célula vizinha
                is_diff = bool(is_difficult_fn(nc, nr)) if is_difficult_fn else False
                step_cost = (feet_per_square * 2.0) if is_diff else feet_per_square
                new_dist = current_dist + step_cost

                # Se o custo acumulado estiver dentro do orçamento de movimento
                if new_dist <= max_movement_feet:
                    if new_dist < distances.get(neighbor, float("inf")):
                        distances[neighbor] = new_dist
                        came_from[neighbor] = (c, r)
                        heapq.heappush(pq, (new_dist, neighbor))

        # Células alcançáveis como destino final (exclui células ocupadas por outros tokens e a origem)
        reachable: Dict[Tuple[int, int], float] = {}
        for cell, dist in distances.items():
            if cell == start or dist <= 0.0:
                continue
            # Destino não compartilhável: dois tokens não devem coexistir
            if cell in occ_set:
                continue
            reachable[cell] = dist

        return MovementResult(
            reachable_cells=reachable,
            came_from=came_from,
            start_cell=start,
        )

    @classmethod
    def calculate_for_entity(
        cls,
        entity: Entity,
        combat_manager: Any,
        movement_override: Optional[float] = None,
    ) -> MovementResult:
        """
        Método de alta conveniência para calcular as células alcançáveis de uma entidade
        dentro do contexto ativo do CombatManager.
        """
        pos = entity.position
        start_cell = (int(pos.get("x", 0)), int(pos.get("y", 0)))

        if movement_override is not None:
            max_movement = max(0.0, float(movement_override))
        else:
            max_movement = getattr(entity, "available_movement", float(entity.speed))

        grid_mgr = getattr(combat_manager, "grid_manager", None)
        columns = grid_mgr.columns if grid_mgr is not None else 25
        rows = grid_mgr.rows if grid_mgr is not None else 14
        feet_per_sq = float(combat_manager.grid_data.get("feet_per_square", 5.0))

        # Mapeamento de ocupação e hostilidade entre combatentes
        occupied_cells: Set[Tuple[int, int]] = set()
        blocking_cells: Set[Tuple[int, int]] = set()

        is_entity_player = getattr(entity, "is_player", False) or getattr(entity, "entity_type", None) == EntityType.PLAYER
        is_entity_monster = getattr(entity, "is_monster", False) or getattr(entity, "entity_type", None) == EntityType.MONSTER

        for c in combat_manager.combatants:
            if not c.is_alive or c.uid == entity.uid:
                continue
            c_pos = (int(c.position.get("x", 0)), int(c.position.get("y", 0)))
            occupied_cells.add(c_pos)

            c_is_player = getattr(c, "is_player", False) or getattr(c, "entity_type", None) == EntityType.PLAYER
            c_is_monster = getattr(c, "is_monster", False) or getattr(c, "entity_type", None) == EntityType.MONSTER

            # Oponentes hostis vivos bloqueiam passagem completamente
            if (is_entity_player and c_is_monster) or (is_entity_monster and c_is_player):
                blocking_cells.add(c_pos)

        def is_walkable(col: int, row: int) -> bool:
            return combat_manager.is_walkable_for_entity(entity, col, row)

        def is_difficult(col: int, row: int) -> bool:
            if hasattr(combat_manager, "is_difficult_terrain"):
                return combat_manager.is_difficult_terrain(col, row)
            return False

        return cls.calculate_reachable_cells(
            start_cell=start_cell,
            max_movement_feet=max_movement,
            columns=columns,
            rows=rows,
            feet_per_square=feet_per_sq,
            is_walkable_fn=is_walkable,
            is_difficult_fn=is_difficult,
            occupied_cells=occupied_cells,
            blocking_cells=blocking_cells,
        )
