import logging
from enum import Enum
from pathlib import Path
import json
from typing import Optional, List, Dict, Any, Callable
from .combat_manager import CombatManager

logger = logging.getLogger(__name__)


class DisplayState(Enum):
    """Estados da Máquina de Exibição da Tela dos Jogadores (PlayerWindow)."""
    IDLE = "IDLE"              # Tela de descanso / espera ("Aguardando o Mestre...")
    PROJECTION = "PROJECTION"  # Projeção de imagens avulsas (NPCs, cenários, itens)
    COMBAT = "COMBAT"          # Modo de combate ativo com mapa e fita de iniciativas


class SessionManager:
    """
    Gerenciador central da sessão do Medusa VTT.
    Atua como Single Source of Truth para o estado de exibição da mesa (DisplayState),
    controla o CombatManager e a projeção de mídias imersivas.
    """

    def __init__(
        self,
        combat_manager: Optional[CombatManager] = None,
        encounters_dir: str = "creations/encounters",
        showcase_dir: str = "assets/images/showcase",
    ) -> None:
        self.__combat_manager: CombatManager = combat_manager or CombatManager()
        self.__display_state: DisplayState = DisplayState.IDLE
        self.__projected_image_path: Optional[str] = None

        self.__encounters_dir: Path = Path(encounters_dir)
        self.__showcase_dir: Path = Path(showcase_dir)

        self.__listeners: List[Callable[[], None]] = []

        # Conecta listener do CombatManager para propagar atualizações de combate
        self.__combat_manager.add_listener(self.notify_listeners)

    # --- Properties ---

    @property
    def display_state(self) -> DisplayState:
        return self.__display_state

    @property
    def combat_manager(self) -> CombatManager:
        return self.__combat_manager

    @property
    def projected_image_path(self) -> Optional[str]:
        return self.__projected_image_path

    @property
    def is_combat_active(self) -> bool:
        return self.__display_state == DisplayState.COMBAT

    @property
    def is_idle(self) -> bool:
        return self.__display_state == DisplayState.IDLE

    @property
    def is_projecting(self) -> bool:
        return self.__display_state == DisplayState.PROJECTION

    # --- Observer / Notificação de Mudanças ---

    def add_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self.__listeners:
            self.__listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        if listener in self.__listeners:
            self.__listeners.remove(listener)

    def notify_listeners(self) -> None:
        for listener in list(self.__listeners):
            try:
                listener()
            except Exception as e:
                logger.error(f"Erro no listener {listener}: {e}")

    # --- Controle de Estados e Projeção ---

    def set_display_state(self, state: DisplayState) -> None:
        """Altera diretamente o estado de exibição e notifica ouvintes."""
        if self.__display_state != state:
            logger.info(f"Transição de estado de exibição: {self.__display_state.value} -> {state.value}")
            self.__display_state = state
            self.notify_listeners()

    def project_image(self, image_path: str) -> bool:
        """
        Envia uma imagem para ser projetada na Tela dos Jogadores (PROJECTION).
        """
        p = Path(image_path)
        if not p.is_file():
            logger.error(f"Arquivo de imagem não encontrado: {image_path}")
            return False

        self.__projected_image_path = str(p.resolve())
        logger.info(f"Projetando imagem: '{p.name}' ({self.__projected_image_path})")
        self.__display_state = DisplayState.PROJECTION
        self.notify_listeners()
        return True

    def start_encounter(self, encounter_id_or_path: str) -> None:
        """
        Carrega o encontro no CombatManager e altera a exibição dos jogadores para COMBAT.
        """
        logger.info(f"Iniciando encontro: {encounter_id_or_path}")
        self.__combat_manager.load_encounter(encounter_id_or_path)
        self.__display_state = DisplayState.COMBAT
        self.notify_listeners()

    def end_combat(self, return_to: DisplayState = DisplayState.IDLE) -> None:
        """
        Encerra o combate ativo, reseta o estado do CombatManager e retorna a tela dos jogadores para IDLE (ou PROJECTION).
        """
        logger.info(f"Encerrando combate e retornando exibição para: {return_to.value}")
        self.__combat_manager.reset_combat()
        self.__display_state = return_to
        self.notify_listeners()

    def clear_display_to_idle(self) -> None:
        """Retorna a Tela dos Jogadores para a tela de espera / descanso (IDLE), descarregando combate e projeções."""
        logger.info("Retornando Tela dos Jogadores para IDLE")
        self.__combat_manager.reset_combat()
        self.__projected_image_path = None
        self.__display_state = DisplayState.IDLE
        self.notify_listeners()

    def return_to_idle(self) -> None:
        """Alias ergonômico para clear_display_to_idle()."""
        self.clear_display_to_idle()

    # --- Descoberta de Arquivos de Encontros e Imagens ---

    def list_available_encounters(self) -> List[Dict[str, Any]]:
        """
        Varre os diretórios de encontros e retorna a lista de metadados dos encontros disponíveis.
        """
        encounters: List[Dict[str, Any]] = []
        search_dirs = [self.__encounters_dir, Path("creations")]

        seen_uids = set()
        for base in search_dirs:
            if not base.exists():
                continue
            for file in base.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    uid = data.get("uid", file.stem)
                    if uid in seen_uids:
                        continue
                    # Checa se possui estrutura de combate
                    if "combatants" in data:
                        seen_uids.add(uid)
                        raw_map_source = data.get("map_source") or data.get("map_file", "Padrão")
                        map_type = data.get("map_type")
                        if not map_type:
                            map_type = "tilemap" if str(raw_map_source).lower().endswith(".json") else "image"
                        else:
                            map_type = str(map_type).strip().lower()

                        encounters.append({
                            "uid": uid,
                            "filename": file.name,
                            "path": str(file),
                            "title": data.get("title", file.stem),
                            "description": data.get("description", "Sem descrição"),
                            "combatants_count": len(data.get("combatants", [])),
                            "map_type": map_type,
                            "map_source": raw_map_source,
                            "map_file": raw_map_source,
                            "grid": data.get("grid", {"columns": 25, "feet_per_square": 5}),
                        })
                except Exception as e:
                    logger.error(f"Falha ao ler encontro '{file}': {e}")

        return encounters

    def list_available_showcase_images(self) -> List[Dict[str, str]]:
        """
        Varre as pastas de showcase e mapas para listar imagens disponíveis para projeção.
        """
        images: List[Dict[str, str]] = []
        search_dirs = [
            self.__showcase_dir,
            Path("assets/images/showcase"),
            Path("assets/images/maps"),
            Path("assets/images"),
        ]

        valid_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        seen_paths = set()

        for base in search_dirs:
            if not base.exists():
                continue
            for file in base.glob("*.*"):
                if file.suffix.lower() in valid_extensions:
                    resolved = str(file.resolve())
                    if resolved in seen_paths:
                        continue
                    seen_paths.add(resolved)
                    category = file.parent.name.capitalize()
                    images.append({
                        "name": file.stem.replace("_", " ").title(),
                        "filename": file.name,
                        "path": str(file),
                        "category": category,
                    })

        return images

    def list_available_image_maps(self) -> List[Dict[str, str]]:
        """Varre as pastas de imagens de mapas estáticos (.png, .jpg)."""
        maps: List[Dict[str, str]] = []
        search_dirs = [
            Path("assets/images/maps"),
            Path("assets/maps"),
            Path("assets/images"),
        ]
        valid_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        seen_paths = set()

        for base in search_dirs:
            if not base.exists():
                continue
            for file in base.glob("*.*"):
                if file.suffix.lower() in valid_extensions:
                    resolved = str(file.resolve())
                    if resolved in seen_paths:
                        continue
                    seen_paths.add(resolved)
                    try:
                        rel_path = str(file.relative_to(Path.cwd())).replace("\\", "/")
                    except Exception:
                        rel_path = str(file).replace("\\", "/")
                    maps.append({
                        "name": file.stem.replace("_", " ").title(),
                        "filename": file.name,
                        "path": rel_path,
                    })
        return maps

    def list_available_maps(self) -> List[Dict[str, str]]:
        """Alias para list_available_image_maps() para compatibilidade retroativa."""
        return self.list_available_image_maps()

    def list_available_tilemaps(self) -> List[Dict[str, Any]]:
        """
        Varre os diretórios de layouts modulares de tilesets (creations/maps/*.json)
        e retorna metadados táticos pré-carregados (largura, altura, tileset, etc.).
        """
        tilemaps: List[Dict[str, Any]] = []
        search_dirs = [
            Path("creations/maps"),
            Path("presets/maps"),
        ]
        seen_paths = set()

        for base in search_dirs:
            if not base.exists():
                continue
            for file in base.glob("*.json"):
                resolved = str(file.resolve())
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)

                try:
                    with open(file, "r", encoding="utf-8") as f:
                        map_data = json.load(f)

                    width = int(map_data.get("width", 25))
                    height = int(map_data.get("height", 14))
                    tileset = str(map_data.get("tileset", "default"))
                    name = file.stem.replace("_", " ").title()

                    try:
                        rel_path = str(file.relative_to(Path.cwd())).replace("\\", "/")
                    except Exception:
                        rel_path = str(file).replace("\\", "/")

                    tilemaps.append({
                        "name": name,
                        "filename": file.name,
                        "path": rel_path,
                        "width": width,
                        "height": height,
                        "tileset": tileset,
                        "tile_count": len(map_data.get("tiles", [])),
                    })
                except Exception as e:
                    logger.warning(f"Falha ao inspecionar layout de tilemap '{file}': {e}")

        return tilemaps

    def list_available_characters(self) -> List[Dict[str, Any]]:
        """Varre as fichas de personagens de jogadores disponíveis."""
        characters: List[Dict[str, Any]] = []
        search_dirs = [
            Path("creations/characters"),
            Path("creations"),
        ]
        seen_uids = set()

        for base in search_dirs:
            if not base.exists():
                continue
            for file in base.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    uid = data.get("uid", file.stem)
                    if uid in seen_uids:
                        continue
                    if "classes" in data or "vitality" in data or "race" in data:
                        seen_uids.add(uid)
                        classes_list = data.get("classes", [])
                        class_names = [c.get("class_id", "") for c in classes_list if isinstance(c, dict)]
                        class_str = "/".join(class_names).title() if class_names else "Aventureiro"
                        characters.append({
                            "uid": uid,
                            "name": data.get("name", file.stem),
                            "level": data.get("level", 1),
                            "class_summary": class_str,
                            "max_hp": data.get("vitality", {}).get("max_hp", 10),
                            "filename": file.name,
                            "path": str(file),
                        })
                except Exception as e:
                    logger.error(f"Falha ao ler personagem '{file}': {e}")
        return characters

    def list_available_monster_presets(self) -> List[Dict[str, Any]]:
        """Varre os presets de monstros disponíveis."""
        monsters: List[Dict[str, Any]] = []
        search_dirs = [
            Path("presets/monsters"),
            Path("presets"),
        ]
        seen_uids = set()

        for base in search_dirs:
            if not base.exists():
                continue
            for file in base.glob("*.json"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    uid = data.get("uid", file.stem)
                    if uid in seen_uids:
                        continue
                    if "hit_points" in data or "challenge_rating" in data or "actions" in data:
                        seen_uids.add(uid)
                        hp_info = data.get("hit_points", {})
                        hp_val = hp_info.get("average", 10) if isinstance(hp_info, dict) else 10
                        ac_info = data.get("armor_class", {})
                        ac_val = ac_info.get("value", 10) if isinstance(ac_info, dict) else 10
                        raw_tags = data.get("tags", [])
                        if isinstance(raw_tags, str):
                            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
                        elif isinstance(raw_tags, list):
                            tags_list = [str(t).strip() for t in raw_tags if str(t).strip()]
                        else:
                            tags_list = []

                        monsters.append({
                            "uid": uid,
                            "name": data.get("name", file.stem.title()),
                            "cr": data.get("challenge_rating", 0),
                            "max_hp": hp_val,
                            "armor_class": ac_val,
                            "type": str(data.get("type", "")),
                            "sub_type": str(data.get("sub_type", "")),
                            "tags": tags_list,
                            "sprite_path": data.get("sprite_path") or data.get("token_path"),
                            "filename": file.name,
                            "path": str(file),
                            "raw_data": data,
                        })
                except Exception as e:
                    logger.error(f"Falha ao ler preset de monstro '{file}': {e}")
        return monsters
