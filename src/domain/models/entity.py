from abc import ABC
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Set
import uuid


class EntityType(str, Enum):
    """
    Categorização do alinhamento tático e tipo da entidade no Medusa VTT:
      - PLAYER: Personagem Jogador (PC/PJ) com moldura azul/ciano canônica.
      - MONSTER: Criatura/Monstro/Inimigo com moldura carmim/vermelha canônica.
      - NEUTRAL: Token neutro, feitiço duradouro, invocação ou objeto interativo com moldura âmbar/dourada.
    """
    PLAYER = "player"
    MONSTER = "monster"
    NEUTRAL = "neutral"


class Entity(ABC):
    """
    Classe base abstrata para todas as criaturas, personagens e tokens do Medusa VTT.
    Segue regras rigorosas de encapsulamento com atributos privados (__),
    acessos via @property com cópias defensivas e métodos de manipulação de estado.
    """

    VALID_SIZES: Set[str] = {"tiny", "small", "medium", "large", "huge", "gargantuan"}
    SIZE_SQUARES: Dict[str, int] = {
        "tiny": 1,
        "small": 1,
        "medium": 1,
        "large": 2,
        "huge": 3,
        "gargantuan": 4,
    }

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
        entity_type: Union[EntityType, str] = EntityType.NEUTRAL,
        token_sprite: Optional[str] = None,
        size: str = "Medium",
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
        self.__token_sprite: Optional[str] = str(token_sprite) if token_sprite else None
        self.__size: str = self._normalize_size(size)

        # Alinhamento tático / Tipo da entidade
        if isinstance(entity_type, EntityType):
            self.__entity_type: EntityType = entity_type
        elif isinstance(entity_type, str):
            val = entity_type.strip().lower()
            if val in ("player", "pj", "pc"):
                self.__entity_type = EntityType.PLAYER
            elif val in ("monster", "npc", "mon"):
                self.__entity_type = EntityType.MONSTER
            else:
                self.__entity_type = EntityType.NEUTRAL
        else:
            self.__entity_type = EntityType.NEUTRAL

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

        self.__conditions: Set[str] = set()
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
    def entity_type(self) -> EntityType:
        """Retorna o alinhamento tático / tipo da entidade (PLAYER, MONSTER, NEUTRAL)."""
        return self.__entity_type

    @property
    def is_player(self) -> bool:
        """Indica se a entidade pertence à categoria de Personagem Jogador."""
        return self.__entity_type == EntityType.PLAYER

    @property
    def is_monster(self) -> bool:
        """Indica se a entidade pertence à categoria de Monstro / Criatura."""
        return self.__entity_type == EntityType.MONSTER

    @property
    def is_neutral(self) -> bool:
        """Indica se a entidade pertence à categoria Neutra / Feitiço / Invocação / Objeto."""
        return self.__entity_type == EntityType.NEUTRAL

    @property
    def token_sprite(self) -> Optional[str]:
        """Caminho opcional do arquivo de textura de token personalizado."""
        return self.__token_sprite

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
    def hidden(self) -> bool:
        """Alias canônico para is_hidden."""
        return self.__is_hidden

    @hidden.setter
    def hidden(self, value: bool) -> None:
        self.set_hidden(bool(value))

    @property
    def is_visible(self) -> bool:
        """Indica se a entidade está visível no mapa e na iniciativa."""
        return not self.__is_hidden

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self.set_hidden(not bool(value))

    @property
    def speed(self) -> int:
        return self.__speed

    @property
    def size(self) -> str:
        """Categoria canônica de tamanho D&D 5E (Tiny, Small, Medium, Large, Huge, Gargantuan)."""
        return self.__size

    @property
    def size_in_squares(self) -> int:
        """Número de células/quadrados ocupados por lado na grade tática."""
        return self.SIZE_SQUARES.get(self.__size.lower(), 1)

    @property
    def position(self) -> Dict[str, int]:
        return self.__position.copy()

    @property
    def conditions(self) -> Set[str]:
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
            "hp_percentage": self.hp_percentage,
            "vitality_status": self.vitality_status,
        }

    @property
    def hp_percentage(self) -> float:
        """Retorna a porcentagem atual de vida da entidade [0.0, 100.0]."""
        if self.__max_hp <= 0:
            return 0.0
        return (self.__current_hp / self.__max_hp) * 100.0

    @property
    def health_percentage(self) -> float:
        """Alias para hp_percentage."""
        return self.hp_percentage

    @property
    def health_ratio(self) -> float:
        """Retorna a fração atual de vida da entidade [0.0, 1.0]."""
        if self.__max_hp <= 0:
            return 0.0
        return self.__current_hp / self.__max_hp

    @property
    def vitality_status(self) -> str:
        """
        Retorna a classificação semântica da faixa de vitalidade:
          - "HEALTHY": HP > 80% (Intacto / Saudável)
          - "WOUNDED": 30% < HP <= 80% (Ferido / Sangrando)
          - "CRITICAL": 0% < HP <= 30% (Crítico / Quase abatido)
          - "DEAD": HP <= 0 (Abatido)
        """
        if not self.__is_alive or self.__current_hp <= 0:
            return "DEAD"
        pct = self.hp_percentage
        if pct > 80.0:
            return "HEALTHY"
        elif pct > 30.0:
            return "WOUNDED"
        else:
            return "CRITICAL"

    @property
    def vitality_color(self) -> tuple:
        """
        Retorna a cor RGBA correspondente à faixa semântica de vitalidade:
          - Verde (HP > 80%): (46, 204, 113, 255)
          - Amarelo (30% < HP <= 80%): (241, 196, 15, 255)
          - Vermelho (0% < HP <= 30%): (231, 76, 60, 255)
          - Cinza / Abatido (HP <= 0): (120, 120, 120, 255)
        """
        status = self.vitality_status
        if status == "HEALTHY":
            return (46, 204, 113, 255)
        elif status == "WOUNDED":
            return (241, 196, 15, 255)
        elif status == "CRITICAL":
            return (231, 76, 60, 255)
        else:
            return (120, 120, 120, 255)

    # --- Métodos de Modificação de Estado ---

    def set_uid(self, uid: str) -> None:
        """Define o UID da entidade de forma controlada."""
        if uid and str(uid).strip():
            self.__uid = str(uid).strip()

    def set_name(self, name: str) -> None:
        if name and name.strip():
            self.__name = name.strip()

    def set_entity_type(self, entity_type: Union[EntityType, str]) -> None:
        """Define a categoria tática da entidade com validação defensiva."""
        if isinstance(entity_type, EntityType):
            self.__entity_type = entity_type
        elif isinstance(entity_type, str):
            val = entity_type.strip().lower()
            if val in ("player", "pj", "pc"):
                self.__entity_type = EntityType.PLAYER
            elif val in ("monster", "npc", "mon"):
                self.__entity_type = EntityType.MONSTER
            else:
                self.__entity_type = EntityType.NEUTRAL

    def set_token_sprite(self, token_sprite: Optional[str]) -> None:
        """Define o asset de textura do token."""
        self.__token_sprite = str(token_sprite).strip() if token_sprite and str(token_sprite).strip() else None

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

    def set_size(self, size: str) -> None:
        """Define e valida a categoria de tamanho da entidade."""
        self.__size = self._normalize_size(size)

    @classmethod
    def _normalize_size(cls, size: Union[str, Any]) -> str:
        """Normaliza e valida defensivamente a categoria de tamanho D&D 5E."""
        if not size:
            return "Medium"
        s = str(size).strip().lower()
        if s in cls.VALID_SIZES:
            return s.capitalize()
        return "Medium"

    def add_condition(self, condition: str) -> None:
        """Adiciona uma condição ao conjunto da entidade."""
        cond = str(condition).strip().lower()
        if cond:
            self.__conditions.add(cond)

    def remove_condition(self, condition: str) -> None:
        """Remove uma condição do conjunto da entidade."""
        cond = str(condition).strip().lower()
        self.__conditions.discard(cond)

    def has_condition(self, condition: str) -> bool:
        """Verifica se a entidade possui a condição informada ativa."""
        return str(condition).strip().lower() in self.__conditions

    def clear_conditions(self) -> None:
        """Limpa todas as condições ativas na entidade."""
        self.__conditions.clear()

    def toggle_condition(self, condition: str) -> bool:
        """
        Alterna o estado de uma condição (adiciona se ausente, remove se presente).
        Retorna True se a condição foi ativada, False se foi removida.
        """
        cond = str(condition).strip().lower()
        if not cond:
            return False
        if cond in self.__conditions:
            self.__conditions.remove(cond)
            return False
        else:
            self.__conditions.add(cond)
            return True

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name='{self.__name}' "
            f"type='{self.__entity_type.value}' size='{self.__size}' "
            f"hp={self.__current_hp}/{self.__max_hp} ac={self.__armor_class} "
            f"init={self.__initiative_score} alive={self.__is_alive}>"
        )


class DynamicToken(Entity):
    """
    Entidade leve / Token dinâmico criado em tempo de execução
    (ex: feitiços duradouros, invocações mágicas, reforços de monstros ou plebeus).
    """

    def __init__(
        self,
        name: str,
        max_hp: int = 1,
        armor_class: int = 10,
        entity_type: Union[EntityType, str] = EntityType.NEUTRAL,
        token_sprite: Optional[str] = None,
        uid: Optional[str] = None,
        speed: int = 30,
        position: Optional[Dict[str, int]] = None,
        is_hidden: bool = False,
        size: str = "Medium",
    ) -> None:
        super().__init__(
            name=name,
            max_hp=max_hp,
            armor_class=armor_class,
            uid=uid,
            speed=speed,
            position=position,
            is_hidden=is_hidden,
            entity_type=entity_type,
            token_sprite=token_sprite,
            size=size,
        )