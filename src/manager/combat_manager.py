import random
from typing import List, Dict, Any, Optional, Callable
from ..domain.models.entity import Entity
from ..domain.loaders.encounter_loader import EncounterLoader


class CombatManager:
    """
    Motor central de gerenciamento de encontros de combate e turnos do Medusa VTT.
    Responsável por carregar o encontro, rolar e ordenar iniciativas com desempates,
    gerenciar o ponteiro de turno ativo, rodadas e despachar dano/cura.
    """

    def __init__(self, encounter_loader: Optional[EncounterLoader] = None) -> None:
        self._encounter_loader = encounter_loader or EncounterLoader()
        self.__encounter_uid: str = ""
        self.__title: str = "Encontro"
        self.__description: str = ""
        self.__map_file: Optional[str] = None
        self.__environment: Dict[str, Any] = {"is_sunlight": False, "is_raining": False}

        self.__combatants: List[Entity] = []
        self.__turn_order: List[Entity] = []
        self.__current_turn_index: int = -1
        self.__round_number: int = 1

        self.__listeners: List[Callable[[], None]] = []

    # --- Properties ---

    @property
    def encounter_uid(self) -> str:
        return self.__encounter_uid

    @property
    def title(self) -> str:
        return self.__title

    @property
    def description(self) -> str:
        return self.__description

    @property
    def map_file(self) -> Optional[str]:
        return self.__map_file

    @property
    def environment(self) -> Dict[str, Any]:
        return self.__environment.copy()

    @property
    def combatants(self) -> List[Entity]:
        """Retorna cópia defensiva da lista de todos os combatentes."""
        return list(self.__combatants)

    @property
    def turn_order(self) -> List[Entity]:
        """Retorna cópia defensiva da lista de turnos ordenados por iniciativa."""
        return list(self.__turn_order)

    @property
    def current_turn_index(self) -> int:
        return self.__current_turn_index

    @property
    def round_number(self) -> int:
        return self.__round_number

    @property
    def active_character(self) -> Optional[Entity]:
        """Retorna o combatente do turno ativo, ou None caso o combate não tenha iniciado."""
        if 0 <= self.__current_turn_index < len(self.__turn_order):
            return self.__turn_order[self.__current_turn_index]
        return None

    @property
    def has_combat_started(self) -> bool:
        return self.__current_turn_index >= 0 and len(self.__turn_order) > 0

    # --- Observer / Notificação de Mudanças ---

    def add_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self.__listeners:
            self.__listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        if listener in self.__listeners:
            self.__listeners.remove(listener)

    def notify_listeners(self) -> None:
        for listener in list(self.__listeners):
            try:
                listener()
            except Exception as e:
                print(f"[CombatManager] Erro no listener {listener}: {e}")

    # --- Carregamento de Encontro ---

    def load_encounter(self, encounter_id_or_path: str) -> None:
        """Carrega dados do encontro e popula os combatentes."""
        data = self._encounter_loader.load_encounter(encounter_id_or_path)
        self.__encounter_uid = data["uid"]
        self.__title = data["title"]
        self.__description = data["description"]
        self.__map_file = data["map_file"]
        self.__environment = data["environment"]

        self.__combatants = list(data["combatants"])
        # Inicialmente, a fila é a lista na ordem de inserção
        self.__turn_order = list(self.__combatants)
        self.__current_turn_index = -1
        self.__round_number = 1

        self.notify_listeners()

    # --- Sistema de Iniciativas e Ordenação ---

    def roll_initiatives(self, manual_rolls: Optional[Dict[str, int]] = None) -> List[Entity]:
        """
        Rola iniciativa para cada combatente (1d20 + DEX mod), permitindo override manual.
        Ordena a lista turn_order por:
          1. Maior valor de iniciativa
          2. Maior modificador de iniciativa (DEX mod)
          3. Ordem alfabética do nome
        Define o índice do turno ativo para 0 e a rodada para 1.
        """
        manual = manual_rolls or {}

        for combatant in self.__combatants:
            # Verifica se foi informada rolagem manual pelo UID ou pelo Nome
            if combatant.uid in manual:
                score = manual[combatant.uid]
            elif combatant.name in manual:
                score = manual[combatant.name]
            else:
                d20 = random.randint(1, 20)
                score = d20 + combatant.initiative_mod

            combatant.set_initiative(score)

        # Ordenação com critérios de desempate D&D 5E
        self.__turn_order = sorted(
            self.__combatants,
            key=lambda c: (c.initiative_score, c.initiative_mod, c.name),
            reverse=True,
        )

        if self.__turn_order:
            self.__current_turn_index = 0
            self.__round_number = 1
        else:
            self.__current_turn_index = -1

        self.notify_listeners()
        return list(self.__turn_order)

    # --- Gerenciamento de Turnos ---

    def next_turn(self) -> Optional[Entity]:
        """
        Avança para o próximo participante na fila de iniciativa de forma circular.
        Ao completar uma volta completa, incrementa o número da rodada.
        """
        if not self.__turn_order:
            return None

        if self.__current_turn_index < 0:
            self.__current_turn_index = 0
            self.__round_number = 1
        else:
            self.__current_turn_index = (self.__current_turn_index + 1) % len(self.__turn_order)
            if self.__current_turn_index == 0:
                self.__round_number += 1

        self.notify_listeners()
        return self.active_character

    def previous_turn(self) -> Optional[Entity]:
        """Retrocede para o participante anterior na fila de iniciativas."""
        if not self.__turn_order:
            return None

        if self.__current_turn_index <= 0:
            self.__current_turn_index = len(self.__turn_order) - 1
            if self.__round_number > 1:
                self.__round_number -= 1
        else:
            self.__current_turn_index -= 1

        self.notify_listeners()
        return self.active_character

    def set_turn_index(self, index: int) -> None:
        """Define o turno ativo diretamente por índice."""
        if 0 <= index < len(self.__turn_order):
            self.__current_turn_index = index
            self.notify_listeners()

    # --- Despachante de Dano e Cura ---

    def get_combatant(self, uid_or_name: str) -> Optional[Entity]:
        """Busca um combatente por UID ou Nome."""
        for c in self.__combatants:
            if c.uid == uid_or_name or c.name.lower() == uid_or_name.lower():
                return c
        return None

    def apply_damage(self, uid_or_name: str, amount: int) -> bool:
        """Aplica dano ao combatente identificado e notifica ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.take_damage(amount)
            self.notify_listeners()
            return True
        return False

    def apply_heal(self, uid_or_name: str, amount: int) -> bool:
        """Aplica cura ao combatente identificado e notifica ouvintes."""
        combatant = self.get_combatant(uid_or_name)
        if combatant is not None:
            combatant.heal(amount)
            self.notify_listeners()
            return True
        return False
