from typing import Dict, Any, List, Optional, Union
try:
    from .entity import Entity
except ImportError:
    from entity import Entity


class Monster(Entity):
    """
    Representa uma criatura/monstro no Medusa VTT.
    Adiciona suporte a nível de desafio (CR), XP, lista de ações e features
    estáticas de combate com condições (self_condition, target_condition).
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
        challenge_rating: float = 0.0,
        xp: Optional[int] = None,
        features: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        size: str = "Medium",
        monster_type: str = "Humanoid",
        sub_type: str = "Any",
        alignment: str = "neutral",
        preset_id: Optional[str] = None,
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

        self.__challenge_rating: float = float(challenge_rating)
        self.__xp: int = int(xp) if xp is not None else int(self.__challenge_rating * 100)
        self.__size: str = size
        self.__monster_type: str = monster_type
        self.__sub_type: str = sub_type
        self.__alignment: str = alignment
        self.__preset_id: Optional[str] = preset_id

        # Normaliza features para lista estruturada
        self.__features: List[Dict[str, Any]] = []
        if isinstance(features, list):
            self.__features = [f.copy() if isinstance(f, dict) else {"name": str(f)} for f in features]
        elif isinstance(features, dict):
            for feat_name, feat_data in features.items():
                if isinstance(feat_data, dict):
                    data = feat_data.copy()
                    data.setdefault("name", feat_name)
                    self.__features.append(data)
                else:
                    self.__features.append({"name": feat_name, "description": str(feat_data)})

        self.__actions: List[Dict[str, Any]] = [
            a.copy() for a in (actions or []) if isinstance(a, dict)
        ]

    # --- Properties ---

    @property
    def challenge_rating(self) -> float:
        return self.__challenge_rating

    @property
    def xp(self) -> int:
        return self.__xp

    @property
    def size(self) -> str:
        return self.__size

    @property
    def monster_type(self) -> str:
        return self.__monster_type

    @property
    def sub_type(self) -> str:
        return self.__sub_type

    @property
    def alignment(self) -> str:
        return self.__alignment

    @property
    def preset_id(self) -> Optional[str]:
        return self.__preset_id

    @property
    def features(self) -> List[Dict[str, Any]]:
        return [f.copy() for f in self.__features]

    @property
    def actions(self) -> List[Dict[str, Any]]:
        return [a.copy() for a in self.__actions]

    # --- Métodos de Condição e Combate ---

    def set_features(self, features: List[Dict[str, Any]]) -> None:
        self.__features = [f.copy() for f in features]

    def set_actions(self, actions: List[Dict[str, Any]]) -> None:
        self.__actions = [a.copy() for a in actions]

    def check_advantage(self, roll_type: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Verifica se a criatura obtém vantagem na jogada indicada (ex: 'attack_roll', 'saving_throw')
        baseada nas suas features e no contexto (ex: {'target_condition': 'has_engaged_ally'}).
        """
        ctx = context or {}
        for feat in self.__features:
            advantages = feat.get("advantages", [])
            for adv in advantages:
                if adv.get("type") == roll_type or adv.get("type") == "all":
                    target_cond = adv.get("target_condition")
                    self_cond = adv.get("self_condition")
                    condition_match = True

                    if target_cond and ctx.get("target_condition") != target_cond:
                        condition_match = False
                    if self_cond and ctx.get("self_condition") != self_cond:
                        condition_match = False

                    if condition_match:
                        return True
        return False

    def check_disadvantage(self, roll_type: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Verifica se a criatura possui desvantagem na jogada indicada
        (ex: 'attack_roll' sob self_condition 'in_sunlight').
        """
        ctx = context or {}
        for feat in self.__features:
            disadvantages = feat.get("disadvantages", [])
            for dis in disadvantages:
                if dis.get("type") == roll_type or dis.get("type") == "all":
                    self_cond = dis.get("self_condition")
                    if self_cond and (ctx.get("self_condition") == self_cond or ctx.get(self_cond) is True):
                        return True
        return False