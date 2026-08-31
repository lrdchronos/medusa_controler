import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..models.monster import Monster
from ..builders.monster_builder import MonsterBuilder

logger = logging.getLogger(__name__)


class MonsterLoader:
    """
    Responsável por carregar presets de monstros e instanciá-los como
    entidades de combate com nomes de instância e posições no grid.
    """

    def __init__(self, preset_dirs: Optional[List[str]] = None) -> None:
        self._preset_dirs = preset_dirs or [
            "presets/monsters",
            "presets",
            ".",
        ]
        self._cached_presets: Dict[str, Dict[str, Any]] = {}

    def resolve_preset_path(self, monster_id: str) -> Optional[Path]:
        """Resolve o arquivo JSON de preset do monstro."""
        raw_path = Path(monster_id)
        if raw_path.is_file():
            return raw_path

        clean_id = monster_id.replace("mon_", "")
        candidates = [
            monster_id,
            f"{monster_id}.json",
            clean_id,
            f"{clean_id}.json",
            f"mon_{clean_id}.json",
        ]

        # Tratamento especial para variações de grafia conhecidas (ex: culstist / cultist)
        if "cultist" in clean_id:
            candidates.extend(["basic_culstist", "basic_culstist.json", "culstist.json"])
        if "culstist" in clean_id:
            candidates.extend(["basic_cultist", "basic_cultist.json", "cultist.json"])

        for base in self._preset_dirs:
            base_p = Path(base)
            if not base_p.exists():
                continue
            for cand in candidates:
                cand_path = base_p / cand
                if cand_path.is_file():
                    return cand_path

            for file in base_p.glob("*.json"):
                stem_clean = file.stem.replace("mon_", "")
                if clean_id == stem_clean or clean_id in file.stem:
                    return file

        return None

    def load_preset(self, monster_id: str) -> Dict[str, Any]:
        """Carrega e armazena em cache o dicionário bruto do preset de monstro."""
        if monster_id in self._cached_presets:
            return self._cached_presets[monster_id].copy()

        resolved = self.resolve_preset_path(monster_id)
        if resolved is None:
            logger.error(
                f"Preset de monstro '{monster_id}' não foi encontrado em: {self._preset_dirs}"
            )
            raise FileNotFoundError(
                f"Preset de monstro '{monster_id}' não foi encontrado em: {self._preset_dirs}"
            )

        with open(resolved, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)


        self._cached_presets[monster_id] = data
        return data.copy()

    def create_instance(
        self,
        monster_id: str,
        instance_name: Optional[str] = None,
        position: Optional[Dict[str, int]] = None,
    ) -> Monster:
        """Instancia um novo Monster a partir de um preset com nome e posição específicos."""
        preset_data = self.load_preset(monster_id)
        builder = MonsterBuilder()
        builder.from_preset_dict(preset_data, instance_name=instance_name)

        if position:
            pos_x = position.get("col", position.get("x", 0))
            pos_y = position.get("row", position.get("y", 0))
            builder.with_position(pos_x, pos_y)

        return builder.build()

