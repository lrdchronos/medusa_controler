from typing import Dict, Any, List, Optional, Union
from ..models.monster import Monster


class MonsterBuilder:
    """
    Builder para montagem de instâncias de Monster.
    Permite construir monstros a partir de presets JSON e instanciá-los
    com nomes únicos (ex: 'Kobold A') e posições específicas no mapa.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> "MonsterBuilder":
        self._uid: Optional[str] = None
        self._preset_id: Optional[str] = None
        self._name: str = "Monstro"
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
        self._challenge_rating: float = 0.0
        self._xp: Optional[int] = None
        self._size: str = "Medium"
        self._monster_type: str = "Humanoid"
        self._sub_type: str = "Any"
        self._alignment: str = "neutral"
        self._features: List[Dict[str, Any]] = []
        self._actions: List[Dict[str, Any]] = []
        self._skills: Dict[str, int] = {}
        self._senses: Dict[str, Any] = {}
        self._languages: List[str] = []
        return self

    def with_uid(self, uid: str) -> "MonsterBuilder":
        self._uid = uid
        return self

    def with_preset_id(self, preset_id: str) -> "MonsterBuilder":
        self._preset_id = preset_id
        return self

    def with_name(self, name: str) -> "MonsterBuilder":
        self._name = name
        return self

    def with_vitality(
        self, max_hp: int, current_hp: Optional[int] = None, temp_hp: int = 0
    ) -> "MonsterBuilder":
        self._max_hp = max(1, max_hp)
        self._current_hp = current_hp if current_hp is not None else self._max_hp
        self._temp_hp = max(0, temp_hp)
        return self

    def with_ability_scores(self, ability_scores: Dict[str, int]) -> "MonsterBuilder":
        self._ability_scores.update(ability_scores)
        return self

    def with_armor_class(self, ac: int) -> "MonsterBuilder":
        self._armor_class = max(0, ac)
        return self

    def with_speed(self, speed: int) -> "MonsterBuilder":
        self._speed = speed
        return self

    def with_position(self, x: int, y: int) -> "MonsterBuilder":
        self._position = {"x": int(x), "y": int(y)}
        return self

    def with_challenge_rating(self, cr: float) -> "MonsterBuilder":
        self._challenge_rating = float(cr)
        return self

    def with_xp(self, xp: int) -> "MonsterBuilder":
        self._xp = int(xp)
        return self

    def with_size(self, size: str) -> "MonsterBuilder":
        self._size = size
        return self

    def with_type(self, monster_type: str, sub_type: str = "Any") -> "MonsterBuilder":
        self._monster_type = monster_type
        self._sub_type = sub_type
        return self

    def with_alignment(self, alignment: str) -> "MonsterBuilder":
        self._alignment = alignment
        return self

    def with_features(
        self, features: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> "MonsterBuilder":
        if isinstance(features, list):
            self._features = [f.copy() if isinstance(f, dict) else {"name": str(f)} for f in features]
        elif isinstance(features, dict):
            self._features = []
            for name, data in features.items():
                if isinstance(data, dict):
                    item = data.copy()
                    item.setdefault("name", name)
                    self._features.append(item)
                else:
                    self._features.append({"name": name, "description": str(data)})
        return self

    def with_actions(self, actions: List[Dict[str, Any]]) -> "MonsterBuilder":
        self._actions = [a.copy() for a in actions if isinstance(a, dict)]
        return self

    def from_preset_dict(
        self, data: Dict[str, Any], instance_name: Optional[str] = None
    ) -> "MonsterBuilder":
        """Popula o builder a partir do JSON de preset de monstro."""
        if "uid" in data:
            self.with_preset_id(data["uid"])

        preset_name = data.get("name", "Monstro")
        self.with_name(instance_name if instance_name else preset_name)

        # HP / Vitality
        hp_info = data.get("hit_points", {})
        if isinstance(hp_info, dict):
            max_hp = hp_info.get("average", 10)
        elif isinstance(hp_info, int):
            max_hp = hp_info
        else:
            max_hp = 10
        self.with_vitality(max_hp)

        # AC
        ac_info = data.get("armor_class", {})
        if isinstance(ac_info, dict):
            ac_val = ac_info.get("value", 10)
        elif isinstance(ac_info, int):
            ac_val = ac_info
        else:
            ac_val = 10
        self.with_armor_class(ac_val)

        # Ability Scores
        if "ability_scores" in data:
            self.with_ability_scores(data["ability_scores"])

        # Speed
        speed_info = data.get("speed", {})
        if isinstance(speed_info, dict):
            self.with_speed(speed_info.get("walk", 30))
        elif isinstance(speed_info, int):
            self.with_speed(speed_info)

        # CR & XP
        if "challenge_rating" in data:
            self.with_challenge_rating(data["challenge_rating"])
        if "xp" in data:
            self.with_xp(data["xp"])

        # Metadados
        if "size" in data:
            self.with_size(data["size"])
        if "type" in data:
            self.with_type(data["type"], data.get("sub_type", "Any"))
        if "alignment" in data:
            self.with_alignment(data["alignment"])

        # Features & Actions
        if "features" in data:
            self.with_features(data["features"])
        if "actions" in data:
            self.with_actions(data["actions"])

        if "skills" in data:
            self._skills = data["skills"].copy()
        if "senses" in data:
            self._senses = data["senses"].copy()
        if "languages" in data:
            self._languages = list(data["languages"])

        return self

    def build(self) -> Monster:
        """Constrói e retorna a instância de Monster configurada."""
        monster = Monster(
            name=self._name,
            max_hp=self._max_hp,
            ability_scores=self._ability_scores,
            armor_class=self._armor_class,
            uid=self._uid,
            speed=self._speed,
            position=self._position,
            challenge_rating=self._challenge_rating,
            xp=self._xp,
            features=self._features,
            actions=self._actions,
            size=self._size,
            monster_type=self._monster_type,
            sub_type=self._sub_type,
            alignment=self._alignment,
            preset_id=self._preset_id,
        )

        if self._current_hp is not None:
            monster.set_current_hp(self._current_hp)
        if self._temp_hp > 0:
            monster.set_temporary_hp(self._temp_hp)

        monster.set_skills(self._skills)
        monster.set_senses(self._senses)
        monster.set_languages(self._languages)

        return monster
