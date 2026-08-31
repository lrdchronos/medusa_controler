from abc import ABC
from typing import Dict, Any, List, Optional
import uuid


class Entity(ABC):
    """
    Classe base abstrata para todas as criaturas e personagens do Medusa VTT.
    Segue regras rigorosas de encapsulamento com atributos privados (__),
    acessos via @property com cópias defensivas e métodos de manipulação de estado.
    """

    def __init__(
        self,
        name: str,
        max_hp: int = 10,
        ability_scores: Optional[Dict[str, int]] = None,
        armor_class: int = 10,
        uid: Optional[str] = None,
        speed: int = 30,
        position: Optional[Dict[str, int]] = None,
        is_hidden: bool = False,
    ) -> None:
        self.__uid: str = uid if uid is not None else str(uuid.uuid4())
        self.__name: str = name
        self.__max_hp: int = max(1, max_hp)
        self.__current_hp: int = self.__max_hp
        self.__temp_hp: int = 0
        self.__armor_class: int = max(0, armor_class)
        self.__initiative_score: int = 0
        self.__is_alive: bool = True
        self.__is_hidden: bool = bool(is_hidden)
        self.__speed: int = speed
        self.__position: Dict[str, int] = position.copy() if position else {"x": 0, "y": 0}

        # Dicionário padrão de Atributos D&D 5E
        default_abilities: Dict[str, int] = {
            "STR": 10,
            "DEX": 10,
            "CON": 10,
            "INT": 10,
            "WIS": 10,
            "CHA": 10,
        }
        if ability_scores:
            default_abilities.update(ability_scores)
        self.__ability_scores: Dict[str, int] = default_abilities

        self.__conditions: List[str] = []
        self.__damage_resistances: List[str] = []
        self.__damage_immunities: List[str] = []
        self.__condition_immunities: List[str] = []
        self.__senses: Dict[str, Any] = {}
        self.__languages: List[str] = []
        self.__skills: Dict[str, int] = {}

    # --- Properties Básicas ---

    @property
    def uid(self) -> str:
        return self.__uid

    @property
    def name(self) -> str:
        return self.__name

    @property
    def ability_scores(self) -> Dict[str, int]:
        """Retorna uma cópia defensiva dos atributos da entidade."""
        return self.__ability_scores.copy()

    @property
    def initiative_mod(self) -> int:
        """Calcula o modificador de iniciativa via Destreza: (DEX - 10) // 2."""
        dex = self.__ability_scores.get("DEX", 10)
        return (dex - 10) // 2

    @property
    def initiative_score(self) -> int:
        return self.__initiative_score

    @property
    def initiative(self) -> int:
        return self.__initiative_score

    @property
    def armor_class(self) -> int:
        return self.__armor_class

    @property
    def ac(self) -> int:
        return self.__armor_class

    @property
    def current_hp(self) -> int:
        return self.__current_hp

    @property
    def max_hp(self) -> int:
        return self.__max_hp

    @property
    def temp_hp(self) -> int:
        return self.__temp_hp

    @property
    def is_alive(self) -> bool:
        return self.__is_alive

    @property
    def is_hidden(self) -> bool:
        return self.__is_hidden

    @property
    def speed(self) -> int:
        return self.__speed

    @property
    def position(self) -> Dict[str, int]:
        return self.__position.copy()

    @property
    def conditions(self) -> List[str]:
        return self.__conditions.copy()

    @property
    def damage_resistances(self) -> List[str]:
        return self.__damage_resistances.copy()

    @property
    def damage_immunities(self) -> List[str]:
        return self.__damage_immunities.copy()

    @property
    def condition_immunities(self) -> List[str]:
        return self.__condition_immunities.copy()

    @property
    def senses(self) -> Dict[str, Any]:
        return self.__senses.copy()

    @property
    def languages(self) -> List[str]:
        return self.__languages.copy()

    @property
    def skills(self) -> Dict[str, int]:
        return self.__skills.copy()

    @property
    def vitality(self) -> Dict[str, Any]:
        """Retorna resumo do estado de vitalidade da entidade."""
        return {
            "max_hp": self.__max_hp,
            "current_hp": self.__current_hp,
            "temporary_hp": self.__temp_hp,
            "is_alive": self.__is_alive,
        }

    # --- Métodos de Modificação de Estado ---

    def set_name(self, name: str) -> None:
        if name and name.strip():
            self.__name = name.strip()

    def set_current_hp(self, hp: int) -> None:
        self.__current_hp = max(0, min(self.__max_hp, hp))
        self.__is_alive = self.__current_hp > 0

    def set_max_hp(self, max_hp: int) -> None:
        self.__max_hp = max(1, max_hp)
        if self.__current_hp > self.__max_hp:
            self.__current_hp = self.__max_hp

    def set_armor_class(self, ac: int) -> None:
        self.__armor_class = max(0, ac)

    def set_temporary_hp(self, amount: int) -> None:
        self.__temp_hp = max(0, amount)

    def set_ability_scores(self, ability_scores: Dict[str, int]) -> None:
        for k, v in ability_scores.items():
            self.__ability_scores[k.upper()] = int(v)

    def set_position(self, x: int, y: int) -> None:
        self.__position = {"x": int(x), "y": int(y)}

    def set_hidden(self, hidden: bool) -> None:
        self.__is_hidden = bool(hidden)

    def set_skills(self, skills: Dict[str, int]) -> None:
        self.__skills = skills.copy()

    def set_senses(self, senses: Dict[str, Any]) -> None:
        self.__senses = senses.copy()

    def set_languages(self, languages: List[str]) -> None:
        self.__languages = list(languages)

    def set_initiative(self, score: int) -> None:
        """Define o valor rolado/calculado de iniciativa da entidade."""
        self.__initiative_score = int(score)

    def take_damage(self, amount: int) -> int:
        """
        Aplica dano à entidade.
        Primeiro absorve via temporary_hp se existente, depois reduz current_hp.
        Atualiza is_alive se o HP atingir 0.
        Retorna o dano total efetivo absorvido/aplicado.
        """
        if amount <= 0:
            return 0

        damage_remaining = amount

        # Absorção por Temporary HP
        if self.__temp_hp > 0:
            absorbed = min(self.__temp_hp, damage_remaining)
            self.__temp_hp -= absorbed
            damage_remaining -= absorbed

        # Aplicação ao HP principal
        if damage_remaining > 0:
            self.__current_hp = max(0, self.__current_hp - damage_remaining)
            if self.__current_hp == 0:
                self.__is_alive = False

        return amount

    def heal(self, amount: int) -> int:
        """
        Cura a entidade sem ultrapassar o max_hp.
        Se a entidade estava com 0 HP, é revivida (is_alive = True).
        Retorna a quantidade de HP recuperada.
        """
        if amount <= 0:
            return 0

        previous_hp = self.__current_hp
        self.__current_hp = min(self.__max_hp, self.__current_hp + amount)
        if self.__current_hp > 0:
            self.__is_alive = True

        return self.__current_hp - previous_hp

    def fully_heal(self) -> None:
        """Recupera a vida máxima da entidade."""
        self.__current_hp = self.__max_hp
        self.__temp_hp = 0
        self.__is_alive = True

    def die(self) -> None:
        """Força o estado de óbito da entidade."""
        self.__current_hp = 0
        self.__temp_hp = 0
        self.__is_alive = False

    def add_condition(self, condition: str) -> None:
        cond = condition.strip().lower()
        if cond and cond not in self.__conditions:
            self.__conditions.append(cond)

    def remove_condition(self, condition: str) -> None:
        cond = condition.strip().lower()
        if cond in self.__conditions:
            self.__conditions.remove(cond)

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name='{self.__name}' "
            f"hp={self.__current_hp}/{self.__max_hp} ac={self.__armor_class} "
            f"init={self.__initiative_score} alive={self.__is_alive}>"
        )