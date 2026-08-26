import logging
from typing import Dict, Any, List, Optional
try:
    from .entity import Entity
except ImportError:
    from entity import Entity

logger = logging.getLogger(__name__)


class PlayableCharacter(Entity):
    """
    Representa um Personagem Jogador (PJ / PC) no Medusa VTT.
    Adiciona controle de nível, classes, raça/espécie, histórico, recursos (ex: Rage)
    e inventário/moedas.
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
        level: Optional[int] = None,
        classes: Optional[List[Dict[str, Any]]] = None,
        race: Optional[Dict[str, Any]] = None,
        background: Optional[Dict[str, Any]] = None,
        alignment: str = "neutral",
        resources: Optional[Dict[str, Any]] = None,
        proficiencies: Optional[Dict[str, Any]] = None,
        coins: Optional[Dict[str, int]] = None,
        active_features: Optional[List[str]] = None,
        equipment: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(
            name=name,
            max_hp=max_hp,
            ability_scores=ability_scores,
            armor_class=armor_class,
            uid=uid,
            speed=speed,
            position=position,
        )

        self.__level: Optional[int] = None
        if level is not None:
            self.starter_level(level)

        self.__classes: List[Dict[str, Any]] = [c.copy() for c in (classes or [])]
        self.__race: Dict[str, Any] = race.copy() if race else {}
        self.__background: Dict[str, Any] = background.copy() if background else {}
        self.__alignment: str = alignment

        default_coins: Dict[str, int] = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
        if coins:
            default_coins.update(coins)
        self.__coins: Dict[str, int] = default_coins

        self.__resources: Dict[str, Dict[str, Any]] = (
            {k: v.copy() if isinstance(v, dict) else v for k, v in resources.items()}
            if resources
            else {}
        )
        self.__proficiencies: Dict[str, Any] = (
            {k: v.copy() if isinstance(v, (dict, list)) else v for k, v in proficiencies.items()}
            if proficiencies
            else {}
        )
        self.__active_features: List[str] = list(active_features) if active_features else []
        self.__equipment: List[Dict[str, Any]] = [e.copy() for e in (equipment or [])]

    # --- Properties ---

    @property
    def level(self) -> int:
        return self.__level if self.__level is not None else 1

    @property
    def classes(self) -> List[Dict[str, Any]]:
        return [c.copy() for c in self.__classes]

    @property
    def char_class(self) -> List[Dict[str, Any]]:
        return [c.copy() for c in self.__classes]

    @property
    def primary_class_name(self) -> str:
        if self.__classes:
            return str(self.__classes[0].get("class_id", "Aventureiro")).capitalize()
        return "Aventureiro"

    @property
    def race(self) -> Dict[str, Any]:
        return self.__race.copy()

    @property
    def species(self) -> Dict[str, Any]:
        return self.__race.copy()

    @property
    def background(self) -> Dict[str, Any]:
        return self.__background.copy()

    @property
    def alignment(self) -> str:
        return self.__alignment

    @property
    def resources(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.copy() if isinstance(v, dict) else v for k, v in self.__resources.items()}

    @property
    def proficiencies(self) -> Dict[str, Any]:
        return {
            k: v.copy() if isinstance(v, (dict, list)) else v
            for k, v in self.__proficiencies.items()
        }

    @property
    def coins(self) -> Dict[str, int]:
        return self.__coins.copy()

    @property
    def treasure(self) -> Dict[str, int]:
        return self.__coins.copy()

    @property
    def active_features(self) -> List[str]:
        return self.__active_features.copy()

    @property
    def equipment(self) -> List[Dict[str, Any]]:
        return [e.copy() for e in self.__equipment]

    # --- Métodos de Negócio e Validação Poka-Yoke ---

    def starter_level(self, level: int) -> bool:
        """
        Define o nível inicial do personagem com validação Poka-Yoke [1, 20].
        """
        if 1 <= level <= 20:
            self.__level = level
            return True
        logger.warning(f"Aviso: Nível {level} inválido para {self.name}. Deve estar entre 1 e 20.")
        return False

    def set_classes(self, classes: List[Dict[str, Any]]) -> None:
        self.__classes = [c.copy() for c in classes]

    def set_race(self, race: Dict[str, Any]) -> None:
        self.__race = race.copy()

    def set_background(self, background: Dict[str, Any]) -> None:
        self.__background = background.copy()

    def set_resources(self, resources: Dict[str, Dict[str, Any]]) -> None:
        self.__resources = {
            k: v.copy() if isinstance(v, dict) else v for k, v in resources.items()
        }

    def set_proficiencies(self, proficiencies: Dict[str, Any]) -> None:
        self.__proficiencies = {
            k: v.copy() if isinstance(v, (dict, list)) else v
            for k, v in proficiencies.items()
        }

    def set_active_features(self, features: List[str]) -> None:
        self.__active_features = list(features)

    def set_equipment(self, equipment: List[Dict[str, Any]]) -> None:
        self.__equipment = [e.copy() for e in equipment]

    def consume_resource(self, resource_name: str, amount: int = 1) -> bool:
        """Consome cargas de um recurso (ex: rage). Retorna True se bem sucedido."""
        key = resource_name.lower()
        if key in self.__resources:
            res = self.__resources[key]
            current = res.get("current_uses", 0)
            if current >= amount:
                res["current_uses"] = current - amount
                return True
            logger.warning(
                f"Tentativa de usar recurso '{resource_name}' esgotado ou sem cargas ({current}/{amount}) para {self.name}."
            )
            return False
        logger.warning(f"Tentativa de consumir recurso inexistente: '{resource_name}' para {self.name}.")
        return False

    def restore_resources(self, recharge_type: Optional[str] = None) -> None:
        """Restaura cargas dos recursos configurados para o tipo de descanso informado."""
        for _, res in self.__resources.items():
            if isinstance(res, dict):
                r_type = res.get("recharge_on", "LONG_REST")
                if recharge_type is None or r_type == recharge_type or recharge_type == "LONG_REST":
                    res["current_uses"] = res.get("max_uses", 0)

