from typing import Dict, Any, List, Optional
from ..models.playablechar import PlayableCharacter


class CharacterBuilder:
    """
    Builder para montagem expressiva e segura de instâncias de PlayableCharacter.
    Permite construir um personagem a partir de dados programáticos ou de um dicionário JSON.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> "CharacterBuilder":
        self._uid: Optional[str] = None
        self._name: str = "Aventureiro"
        self._max_hp: int = 10
        self._current_hp: Optional[int] = None
        self._temp_hp: int = 0
        self._ability_scores: Dict[str, int] = {
            "STR": 10,
            "DEX": 10,
            "CON": 10,
            "INT": 10,
            "WIS": 10,
            "CHA": 10,
        }
        self._armor_class: int = 10
        self._speed: int = 30
        self._position: Dict[str, int] = {"x": 0, "y": 0}
        self._level: int = 1
        self._classes: List[Dict[str, Any]] = []
        self._race: Dict[str, Any] = {}
        self._background: Dict[str, Any] = {}
        self._alignment: str = "neutral"
        self._resources: Dict[str, Any] = {}
        self._proficiencies: Dict[str, Any] = {}
        self._coins: Dict[str, int] = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}
        self._active_features: List[str] = []
        self._equipment: List[Dict[str, Any]] = []
        return self

    def with_uid(self, uid: str) -> "CharacterBuilder":
        self._uid = uid
        return self

    def with_name(self, name: str) -> "CharacterBuilder":
        self._name = name
        return self

    def with_vitality(
        self, max_hp: int, current_hp: Optional[int] = None, temp_hp: int = 0
    ) -> "CharacterBuilder":
        self._max_hp = max(1, max_hp)
        self._current_hp = current_hp if current_hp is not None else self._max_hp
        self._temp_hp = max(0, temp_hp)
        return self

    def with_ability_scores(self, ability_scores: Dict[str, int]) -> "CharacterBuilder":
        self._ability_scores.update(ability_scores)
        return self

    def with_armor_class(self, ac: int) -> "CharacterBuilder":
        self._armor_class = max(0, ac)
        return self

    def with_speed(self, speed: int) -> "CharacterBuilder":
        self._speed = speed
        return self

    def with_position(self, x: int, y: int) -> "CharacterBuilder":
        self._position = {"x": int(x), "y": int(y)}
        return self

    def with_level(self, level: int) -> "CharacterBuilder":
        self._level = level
        return self

    def with_classes(self, classes: List[Dict[str, Any]]) -> "CharacterBuilder":
        self._classes = [c.copy() for c in classes]
        return self

    def with_race(self, race: Dict[str, Any]) -> "CharacterBuilder":
        self._race = race.copy()
        return self

    def with_background(self, background: Dict[str, Any]) -> "CharacterBuilder":
        self._background = background.copy()
        return self

    def with_alignment(self, alignment: str) -> "CharacterBuilder":
        self._alignment = alignment
        return self

    def with_resources(self, resources: Dict[str, Any]) -> "CharacterBuilder":
        self._resources = resources.copy()
        return self

    def with_proficiencies(self, proficiencies: Dict[str, Any]) -> "CharacterBuilder":
        self._proficiencies = proficiencies.copy()
        return self

    def with_coins(self, coins: Dict[str, int]) -> "CharacterBuilder":
        self._coins.update(coins)
        return self

    def with_active_features(self, features: List[str]) -> "CharacterBuilder":
        self._active_features = list(features)
        return self

    def with_equipment(self, equipment: List[Dict[str, Any]]) -> "CharacterBuilder":
        self._equipment = [e.copy() for e in equipment]
        return self

    def from_dict(self, data: Dict[str, Any]) -> "CharacterBuilder":
        """Popula o builder a partir do formato JSON padronizado de personagem."""
        if "uid" in data:
            self.with_uid(data["uid"])
        if "name" in data:
            self.with_name(data["name"])
        if "level" in data:
            self.with_level(int(data["level"]))
        if "ability_scores" in data:
            self.with_ability_scores(data["ability_scores"])

        vitality = data.get("vitality", {})
        max_hp = vitality.get("max_hp", 10)
        curr_hp = vitality.get("current_hp", max_hp)
        temp_hp = vitality.get("temporary_hp", 0)
        self.with_vitality(max_hp, curr_hp, temp_hp)

        # Cálculo de CA base se não fornecida explicitamente: 10 + DEX mod (ou 10 + DEX + CON se Bárbaro com unarmored defense)
        dex_mod = (self._ability_scores.get("DEX", 10) - 10) // 2
        con_mod = (self._ability_scores.get("CON", 10) - 10) // 2
        base_ac = 10 + dex_mod
        if "unarmored_defense" in data.get("active_features", []):
            base_ac += con_mod
        self.with_armor_class(data.get("armor_class", base_ac))

        if "race" in data:
            self.with_race(data["race"])
        if "classes" in data:
            self.with_classes(data["classes"])
        if "background" in data:
            self.with_background(data["background"])
        if "alignment" in data:
            self.with_alignment(data["alignment"])
        if "resources" in data:
            self.with_resources(data["resources"])
        if "proficiencies" in data:
            self.with_proficiencies(data["proficiencies"])
        if "coins" in data:
            self.with_coins(data["coins"])
        if "active_features" in data:
            self.with_active_features(data["active_features"])
        if "equipment" in data:
            self.with_equipment(data["equipment"])
        if "position" in data:
            pos = data["position"]
            self.with_position(pos.get("x", 0), pos.get("y", 0))

        return self

    def build(self) -> PlayableCharacter:
        """Constrói e retorna a instância de PlayableCharacter configurada."""
        char = PlayableCharacter(
            name=self._name,
            max_hp=self._max_hp,
            ability_scores=self._ability_scores,
            armor_class=self._armor_class,
            uid=self._uid,
            speed=self._speed,
            position=self._position,
            level=self._level,
            classes=self._classes,
            race=self._race,
            background=self._background,
            alignment=self._alignment,
            resources=self._resources,
            proficiencies=self._proficiencies,
            coins=self._coins,
            active_features=self._active_features,
            equipment=self._equipment,
        )

        if self._current_hp is not None:
            char.set_current_hp(self._current_hp)
        if self._temp_hp > 0:
            char.set_temporary_hp(self._temp_hp)

        return char