import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..models.entity import Entity
from .character_loader import CharacterLoader
from .monster_loader import MonsterLoader


class EncounterLoader:
    """
    Responsável por carregar encontros a partir de arquivos JSON,
    instanciar os combatentes (PJs e Monstros) via seus respectivos loaders
    e normalizar caminhos de mapas e ambiente.
    """

    def __init__(
        self,
        encounter_dirs: Optional[List[str]] = None,
        character_loader: Optional[CharacterLoader] = None,
        monster_loader: Optional[MonsterLoader] = None,
    ) -> None:
        self._encounter_dirs = encounter_dirs or [
            "creations/encounters",
            "creations",
            ".",
        ]
        self._character_loader = character_loader or CharacterLoader()
        self._monster_loader = monster_loader or MonsterLoader()

    def resolve_encounter_path(self, encounter_id_or_path: str) -> Optional[Path]:
        """Resolve o arquivo JSON de encontro."""
        raw_path = Path(encounter_id_or_path)
        if raw_path.is_file():
            return raw_path

        candidates = [
            encounter_id_or_path,
            f"{encounter_id_or_path}.json",
            f"encounter_{encounter_id_or_path}.json",
        ]

        for base in self._encounter_dirs:
            base_p = Path(base)
            if not base_p.exists():
                continue
            for cand in candidates:
                cand_path = base_p / cand
                if cand_path.is_file():
                    return cand_path

            # Busca por varredura
            for file in base_p.glob("*.json"):
                if encounter_id_or_path in file.stem or file.stem in encounter_id_or_path:
                    return file

        return None

    def resolve_map_path(self, map_file: Optional[str]) -> Optional[str]:
        """Resolve o caminho de imagem do mapa de batalha com fallbacks."""
        if not map_file:
            return None

        map_p = Path(map_file)
        if map_p.is_file():
            return str(map_p)

        search_locations = [
            Path("assets/images/maps") / map_p.name,
            Path("assets/maps") / map_p.name,
            Path("assets/images") / map_p.name,
            Path("assets") / map_p.name,
            Path(map_file),
        ]

        for loc in search_locations:
            if loc.is_file():
                return str(loc)

        return map_file

    def load_encounter(self, encounter_id_or_path: str) -> Dict[str, Any]:
        """
        Carrega o arquivo de encontro, instancia todos os combatentes e retorna
        um dicionário estruturado com as entidades vivas.
        """
        resolved = self.resolve_encounter_path(encounter_id_or_path)
        if resolved is None:
            raise FileNotFoundError(
                f"Encontro '{encounter_id_or_path}' não foi encontrado em: {self._encounter_dirs}"
            )

        with open(resolved, "r", encoding="utf-8") as f:
            raw_data: Dict[str, Any] = json.load(f)

        title = raw_data.get("title", resolved.stem)
        description = raw_data.get("description", "")
        uid = raw_data.get("uid", resolved.stem)
        map_file = self.resolve_map_path(raw_data.get("map_file"))
        environment = raw_data.get("environment", {"is_sunlight": False, "is_raining": False})

        combatants: List[Entity] = []
        raw_combatants = raw_data.get("combatants", [])

        for item in raw_combatants:
            entity_type = item.get("entity_type", "monster")
            position = item.get("position", {"x": 0, "y": 0})

            if entity_type == "monster":
                monster_id = item.get("monster_id", "kobold")
                instance_name = item.get("instance_name")
                monster = self._monster_loader.create_instance(
                    monster_id=monster_id,
                    instance_name=instance_name,
                    position=position,
                )
                combatants.append(monster)

            elif entity_type in ("playable_character", "character", "pc"):
                char_id = item.get("character_id", item.get("uid", "char"))
                char = self._character_loader.load_by_id(char_id)
                char.set_position(position.get("x", 0), position.get("y", 0))
                combatants.append(char)

        return {
            "uid": uid,
            "title": title,
            "description": description,
            "map_file": map_file,
            "environment": environment,
            "combatants": combatants,
        }
