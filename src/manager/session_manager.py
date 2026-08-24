from enum import Enum
from pathlib import Path
import json
from typing import Optional, List, Dict, Any, Callable
from .combat_manager import CombatManager


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
                print(f"[SessionManager] Erro no listener {listener}: {e}")

    # --- Controle de Estados e Projeção ---

    def set_display_state(self, state: DisplayState) -> None:
        """Altera diretamente o estado de exibição e notifica ouvintes."""
        if self.__display_state != state:
            self.__display_state = state
            self.notify_listeners()

    def project_image(self, image_path: str) -> bool:
        """
        Envia uma imagem para ser projetada na Tela dos Jogadores (PROJECTION).
        """
        p = Path(image_path)
        if not p.is_file():
            print(f"[SessionManager] Arquivo de imagem não encontrado: {image_path}")
            return False

        self.__projected_image_path = str(p.resolve())
        self.__display_state = DisplayState.PROJECTION
        self.notify_listeners()
        return True

    def start_encounter(self, encounter_id_or_path: str) -> None:
        """
        Carrega o encontro no CombatManager e altera a exibição dos jogadores para COMBAT.
        """
        self.__combat_manager.load_encounter(encounter_id_or_path)
        self.__display_state = DisplayState.COMBAT
        self.notify_listeners()

    def end_combat(self, return_to: DisplayState = DisplayState.IDLE) -> None:
        """
        Encerra o combate ativo e retorna a tela dos jogadores para IDLE (ou PROJECTION).
        """
        self.__display_state = return_to
        self.notify_listeners()

    def clear_display_to_idle(self) -> None:
        """Retorna a Tela dos Jogadores para a tela de espera / descanso (IDLE)."""
        self.__projected_image_path = None
        self.__display_state = DisplayState.IDLE
        self.notify_listeners()

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
                        encounters.append({
                            "uid": uid,
                            "filename": file.name,
                            "path": str(file),
                            "title": data.get("title", file.stem),
                            "description": data.get("description", "Sem descrição"),
                            "combatants_count": len(data.get("combatants", [])),
                            "map_file": data.get("map_file", "Padrão"),
                        })
                except Exception as e:
                    print(f"[SessionManager] Falha ao ler encontro '{file}': {e}")

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
