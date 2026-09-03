import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EncounterBuilder:
    """
    Builder e Serializador para criação, validação e persistência de encontros no Medusa VTT.
    Produz arquivos JSON no schema padrão do Medusa com suporte a múltiplos combatentes,
    metadados, configurações de grid e ambiente.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> "EncounterBuilder":
        """Reinicia o builder para o estado padrão."""
        self._uid: Optional[str] = None
        self._title: str = "Novo Encontro"
        self._description: str = ""
        self._map_type: str = "image"
        self._map_source: str = "assets/images/maps/open_field_grass_trees.jpg"
        self._map_file: str = "assets/images/maps/open_field_grass_trees.jpg"
        self._environment: Dict[str, Any] = {"is_sunlight": False}
        self._grid: Dict[str, Any] = {"columns": 25, "feet_per_square": 5}
        self._combatants: List[Dict[str, Any]] = []
        return self

    @property
    def map_type(self) -> str:
        """Tipo de mapa ('image' ou 'tilemap')."""
        return self._map_type

    @property
    def map_source(self) -> str:
        """Caminho de origem do mapa (arquivo de imagem ou JSON de tilemap)."""
        return self._map_source

    @property
    def map_file(self) -> str:
        """Alias retrocompatível para map_source."""
        return self._map_source

    def with_metadata(
        self,
        title: str,
        description: str = "",
        uid: Optional[str] = None,
    ) -> "EncounterBuilder":
        """Define os metadados do encontro."""
        if title and title.strip():
            self._title = title.strip()
        self._description = description.strip() if description else ""
        if uid:
            self._uid = uid.strip()
        return self

    def with_map(self, map_source: str, map_type: Optional[str] = None) -> "EncounterBuilder":
        """
        Define o mapa de batalha e seu tipo ('image' ou 'tilemap').
        Se map_type não for explicitado, deduz automaticamente:
        'tilemap' se map_source terminar com .json, senão 'image'.
        """
        if map_source and map_source.strip():
            clean_source = map_source.strip().replace("\\", "/")
            self._map_source = clean_source
            self._map_file = clean_source

            if map_type and str(map_type).strip().lower() in ("image", "tilemap"):
                self._map_type = str(map_type).strip().lower()
            else:
                self._map_type = "tilemap" if clean_source.lower().endswith(".json") else "image"
        return self

    def with_grid(self, columns: int = 25, feet_per_square: int = 5) -> "EncounterBuilder":
        """Define os parâmetros da grade tática."""
        self._grid = {
            "columns": int(columns),
            "feet_per_square": int(feet_per_square),
        }
        return self


    def with_environment(
        self, is_sunlight: bool = False, is_raining: bool = False, **kwargs: Any
    ) -> "EncounterBuilder":
        """Define as configurações ambientais."""
        self._environment = {
            "is_sunlight": bool(is_sunlight),
            "is_raining": bool(is_raining),
            **kwargs,
        }
        return self

    def add_monster(
        self,
        monster_id: str,
        instance_name: Optional[str] = None,
        col: int = 0,
        row: int = 0,
        is_hidden: bool = False,
    ) -> "EncounterBuilder":
        """Adiciona uma instância de monstro ao encontro."""
        clean_id = monster_id.strip()
        self._combatants.append({
            "entity_type": "monster",
            "monster_id": clean_id,
            "instance_name": instance_name or clean_id,
            "is_hidden": bool(is_hidden),
            "position": {
                "col": max(0, int(col)),
                "row": max(0, int(row)),
            },
        })
        return self

    def add_character(
        self,
        character_id: str,
        col: int = 0,
        row: int = 0,
        is_hidden: bool = False,
    ) -> "EncounterBuilder":
        """Adiciona um personagem jogador ao encontro."""
        clean_id = character_id.strip()
        self._combatants.append({
            "entity_type": "playable_character",
            "character_id": clean_id,
            "is_hidden": bool(is_hidden),
            "position": {
                "col": max(0, int(col)),
                "row": max(0, int(row)),
            },
        })
        return self

    def set_combatants(self, combatants: List[Dict[str, Any]]) -> "EncounterBuilder":
        """Define diretamente a lista completa de combatentes estruturados."""
        self._combatants = [c.copy() for c in combatants]
        return self

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Valida a consistência dos dados do encontro.
        Retorna (is_valid, error_messages).
        """
        errors: List[str] = []

        if not self._title or not self._title.strip():
            errors.append("O título do encontro não pode ser vazio.")

        map_path = self._map_source or self._map_file
        if not map_path or not map_path.strip():
            errors.append("O caminho do mapa não pode ser vazio.")

        if self._map_type not in ("image", "tilemap"):
            errors.append(f"Tipo de mapa inválido: '{self._map_type}'. Válidos: 'image', 'tilemap'.")

        if not self._combatants:
            errors.append("O encontro deve conter pelo menos um combatente.")

        cols = self._grid.get("columns", 0)
        feet = self._grid.get("feet_per_square", 0)
        if cols <= 0:
            errors.append(f"Número de colunas do grid deve ser maior que 0 (atual: {cols}).")
        if feet <= 0:
            errors.append(f"Pés por quadrado deve ser maior que 0 (atual: {feet}).")

        for idx, combatant in enumerate(self._combatants):
            etype = combatant.get("entity_type")
            if etype not in ("monster", "playable_character", "character", "pc"):
                errors.append(f"Combatente #{idx + 1} possui tipo inválido: '{etype}'.")
            if etype == "monster" and not combatant.get("monster_id"):
                errors.append(f"Monstro #{idx + 1} não possui monster_id especificado.")
            elif etype in ("playable_character", "character", "pc") and not combatant.get("character_id"):
                errors.append(f"Personagem #{idx + 1} não possui character_id especificado.")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Gera o dicionário no formato JSON padrão do Medusa VTT."""
        timestamp = datetime.now().strftime("%d%m%Y%H%M%S")
        uid = self._uid or f"encounter_{timestamp}"

        return {
            "uid": uid,
            "title": self._title,
            "description": self._description,
            "map_type": self._map_type,
            "map_source": self._map_source,
            "map_file": self._map_source,  # Retrocompatibilidade
            "environment": self._environment.copy(),
            "grid": self._grid.copy(),
            "combatants": [c.copy() for c in self._combatants],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serializa o encontro para uma string JSON formatada."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_to_file(
        self,
        directory: str = "creations/encounters",
        filename: Optional[str] = None,
    ) -> Path:
        """
        Valida, serializa e grava o arquivo de encontro no disco.
        Retorna o Path do arquivo gerado.
        """
        is_valid, errors = self.validate()
        if not is_valid:
            error_str = " | ".join(errors)
            logger.error(f"Erro de validação ao salvar encontro: {error_str}")
            raise ValueError(f"Encontro inválido: {error_str}")

        data = self.to_dict()
        uid = data["uid"]

        dest_dir = Path(directory)
        dest_dir.mkdir(parents=True, exist_ok=True)

        if filename:
            target_name = filename if filename.endswith(".json") else f"{filename}.json"
        else:
            target_name = f"{uid}.json"

        target_path = dest_dir / target_name

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info(f"Encontro salvo com sucesso em: '{target_path}' (UID: {uid}, {len(self._combatants)} combatentes).")
        return target_path


# Aliases
EncounterSerializer = EncounterBuilder
EncounterWriter = EncounterBuilder
