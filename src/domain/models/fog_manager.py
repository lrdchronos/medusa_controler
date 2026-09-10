import logging
from typing import Set, Tuple, List, Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class FogManager:
    """
    Gerenciador do estado de Névoa de Guerra (Fog of War) no Medusa VTT.
    Mantém o conjunto canônico de células ocultas em coordenadas matriciais (col, row)
    com operações e consultas em O(1), suporte a Padrão Observer para sincronização reativa
    em tempo real e serialização/desserialização para o schema de encontros.
    """

    def __init__(self) -> None:
        self.__fogged_cells: Set[Tuple[int, int]] = set()
        self.__listeners: List[Callable[[], None]] = []

    # --- Consultas ---

    def is_fogged(self, col: int, row: int) -> bool:
        """Retorna True se a célula (col, row) estiver coberta pela névoa."""
        return (int(col), int(row)) in self.__fogged_cells

    def get_fogged_cells(self) -> Set[Tuple[int, int]]:
        """Retorna uma cópia defensiva do conjunto de células cobertas pela névoa."""
        return set(self.__fogged_cells)

    def get_fog_cells(self) -> Set[Tuple[int, int]]:
        """Alias para get_fogged_cells."""
        return self.get_fogged_cells()

    @property
    def count(self) -> int:
        """Quantidade total de células atualmente cobertas pela névoa."""
        return len(self.__fogged_cells)

    # --- Mutações de Estado ---

    def add_fog(self, col: int, row: int) -> None:
        """Adiciona uma célula ao conjunto de névoa de forma idempotente."""
        cell = (int(col), int(row))
        if cell not in self.__fogged_cells:
            self.__fogged_cells.add(cell)
            self.notify_listeners()

    def set_cell(self, col: int, row: int) -> None:
        """Alias para add_fog."""
        self.add_fog(col, row)

    def add_cell(self, col: int, row: int) -> None:
        """Alias para add_fog."""
        self.add_fog(col, row)

    def remove_fog(self, col: int, row: int) -> None:
        """Remove uma célula do conjunto de névoa (revelação de área)."""
        cell = (int(col), int(row))
        if cell in self.__fogged_cells:
            self.__fogged_cells.remove(cell)
            self.notify_listeners()

    def clear_cell(self, col: int, row: int) -> None:
        """Alias para remove_fog."""
        self.remove_fog(col, row)

    def remove_cell(self, col: int, row: int) -> None:
        """Alias para remove_fog."""
        self.remove_fog(col, row)

    def fill_all(self, total_cols: int, total_rows: int) -> None:
        """Cobre todas as células da grade tática de 0 até (cols-1, rows-1)."""
        cols = max(0, int(total_cols))
        rows = max(0, int(total_rows))
        new_cells = {(c, r) for c in range(cols) for r in range(rows)}

        if self.__fogged_cells != new_cells:
            self.__fogged_cells = new_cells
            logger.info(f"Névoa de guerra aplicada a todas as {len(self.__fogged_cells)} células ({cols}x{rows}).")
            self.notify_listeners()

    def clear_all(self) -> None:
        """Remove a névoa de todas as células (mapa totalmente revelado)."""
        if self.__fogged_cells:
            self.__fogged_cells.clear()
            logger.info("Névoa de guerra completamente removida do mapa.")
            self.notify_listeners()

    # --- Serialização e Carga ---

    def export_state(self) -> List[Dict[str, int]]:
        """
        Exporta o estado da névoa para o formato JSON canônico:
        [{"x": col, "y": row}, ...]
        Ordenado deterministicamente por (row, col).
        """
        sorted_cells = sorted(self.__fogged_cells, key=lambda cell: (cell[1], cell[0]))
        return [{"x": c[0], "y": c[1]} for c in sorted_cells]

    def load_state(self, data: Optional[List[Dict[str, Any]]]) -> None:
        """
        Carrega o estado da névoa a partir de uma lista serializada do JSON do encontro.
        Aplica validação defensiva Poka-Yoke para ignorar entradas corrompidas.
        """
        new_cells: Set[Tuple[int, int]] = set()

        if data and isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Aceita chaves 'x'/'y' (padrão) ou 'col'/'row'
                    x_val = item.get("x", item.get("col"))
                    y_val = item.get("y", item.get("row"))
                    if x_val is not None and y_val is not None:
                        try:
                            new_cells.add((int(x_val), int(y_val)))
                        except (ValueError, TypeError):
                            logger.warning(f"Coordenada inválida ignorada no carregamento de névoa: {item}")

        self.__fogged_cells = new_cells
        logger.info(f"Estado de névoa carregado: {len(self.__fogged_cells)} células ativas.")
        self.notify_listeners()

    # --- Padrão Observer (Listeners de Notificação) ---

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Inscreve um callback para ser notificado em qualquer alteração de estado."""
        if listener not in self.__listeners:
            self.__listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Remove um callback da lista de ouvintes."""
        if listener in self.__listeners:
            self.__listeners.remove(listener)

    def subscribe(self, listener: Callable[[], None]) -> None:
        """Alias para add_listener."""
        self.add_listener(listener)

    def unsubscribe(self, listener: Callable[[], None]) -> None:
        """Alias para remove_listener."""
        self.remove_listener(listener)

    def notify_listeners(self) -> None:
        """Notifica todos os ouvintes inscritos sobre alterações na névoa."""
        for listener in list(self.__listeners):
            try:
                listener()
            except Exception as e:
                logger.error(f"Erro ao executar listener de FogManager: {e}")
