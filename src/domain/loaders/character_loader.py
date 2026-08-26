import logging
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..models.playablechar import PlayableCharacter
from ..builders.character_builder import CharacterBuilder

logger = logging.getLogger(__name__)


class CharacterLoader:
    """
    Responsável por carregar e desserializar fichas de personagens de jogadores
    a partir de arquivos JSON no padrão Medusa.
    """

    def __init__(self, base_dirs: Optional[List[str]] = None) -> None:
        self._base_dirs = base_dirs or [
            "creations/characters",
            "creations",
            ".",
        ]

    def resolve_path(self, character_id_or_path: str) -> Optional[Path]:
        """Resolve o caminho de um arquivo de personagem por ID, nome ou caminho relativo."""
        raw_path = Path(character_id_or_path)
        if raw_path.is_file():
            return raw_path

        candidates = [
            character_id_or_path,
            f"{character_id_or_path}.json",
            f"char_{character_id_or_path}.json",
            character_id_or_path.replace("char_", "char"),
            f"{character_id_or_path.replace('char_', 'char')}.json",
        ]

        for base in self._base_dirs:
            base_p = Path(base)
            if not base_p.exists():
                continue
            for cand in candidates:
                cand_path = base_p / cand
                if cand_path.is_file():
                    return cand_path

            # Busca por varredura se houver match parcial de ID
            for file in base_p.glob("*.json"):
                if character_id_or_path in file.stem or file.stem in character_id_or_path:
                    return file

        return None

    def load_from_file(self, file_path: Path) -> PlayableCharacter:
        """Lê o arquivo JSON e constrói o PlayableCharacter via CharacterBuilder."""
        with open(file_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)

        builder = CharacterBuilder()
        builder.from_dict(data)
        return builder.build()

    def load_by_id(self, character_id: str) -> PlayableCharacter:
        """Busca um personagem por seu UID ou nome de arquivo e o instancia."""
        resolved = self.resolve_path(character_id)
        if resolved is None:
            logger.error(
                f"Ficha de personagem '{character_id}' não foi encontrada nos diretórios: {self._base_dirs}"
            )
            raise FileNotFoundError(
                f"Ficha de personagem '{character_id}' não foi encontrada nos diretórios: {self._base_dirs}"
            )
        return self.load_from_file(resolved)

