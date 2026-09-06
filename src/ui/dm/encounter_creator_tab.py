import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set
import arcade
from ...manager.session_manager import SessionManager
from .creator.config_form import CreatorConfigForm
from .creator.tactical_stage import CreatorTacticalStage

logger = logging.getLogger(__name__)


class EncounterCreatorTabView:
    """
    Controlador / Facade de Criação e Edição de Encontros (Encounter Wizard).
    Orquestra a transição de estados e delega responsabilidades a subcomponentes OOD:
      - Etapa 1: CreatorConfigForm (Metadados, Mapa, Grade, Combatentes).
      - Etapa 2: CreatorTacticalStage (Palco Tático, Drag & Drop, Snap-to-Grid, Visibilidade Oculta, Névoa).
    """

    def __init__(self, session_manager: SessionManager, dm_window: Optional[arcade.Window] = None) -> None:
        self.session_manager = session_manager
        self.dm_window = dm_window

        self.stage: int = 1  # 1 = Formulário, 2 = Palco Tático

        # Estado de Edição de Encontro
        self.is_editing: bool = False
        self.editing_encounter_uid: Optional[str] = None
        self.editing_encounter_path: Optional[str] = None
        self.editing_encounter_data: Optional[Dict[str, Any]] = None

        # Subcomponentes Especializados (OOD)
        available_maps = self.session_manager.list_available_image_maps()
        available_tilemaps = self.session_manager.list_available_tilemaps()
        available_characters = self.session_manager.list_available_characters()
        available_monsters = self.session_manager.list_available_monster_presets()

        self.form = CreatorConfigForm(
            available_maps=available_maps,
            available_characters=available_characters,
            available_monsters=available_monsters,
            available_tilemaps=available_tilemaps,
        )
        self.tactical_stage = CreatorTacticalStage()

        # Caches de Textura e Texto
        self._text_cache: Dict[str, arcade.Text] = {}
        self._texture_cache: Dict[str, arcade.Texture] = {}

    # --- Propriedades de Compatibilidade e Acesso ---

    @property
    def title(self) -> str:
        return self.form.title_input.text

    @title.setter
    def title(self, value: str) -> None:
        self.form.title_input.set_text(value)

    @property
    def description(self) -> str:
        return self.form.description_input.text

    @description.setter
    def description(self, value: str) -> None:
        self.form.description_input.set_text(value)

    @property
    def columns(self) -> int:
        return self.form.columns

    @columns.setter
    def columns(self, value: int) -> None:
        self.form.columns = value

    @property
    def feet_per_square(self) -> int:
        return self.form.feet_per_square

    @feet_per_square.setter
    def feet_per_square(self, value: int) -> None:
        self.form.feet_per_square = value

    @property
    def selected_character_uids(self) -> Set[str]:
        return self.form.selected_character_uids

    @property
    def monster_counts(self) -> Dict[str, int]:
        return self.form.monster_counts

    @property
    def staging_combatants(self) -> List[Dict[str, Any]]:
        return self.tactical_stage.staging_combatants

    @property
    def error_message(self) -> Optional[str]:
        return self.form.error_message or self.tactical_stage.error_message

    @error_message.setter
    def error_message(self, val: Optional[str]) -> None:
        self.form.error_message = val
        self.tactical_stage.error_message = val

    @property
    def success_message(self) -> Optional[str]:
        return self.tactical_stage.success_message

    # --- Transições de Fluxo e Edição ---

    def refresh_sources(self) -> None:
        """Recarrega arquivos de mapas, personagens e monstros."""
        maps = self.session_manager.list_available_image_maps()
        tilemaps = self.session_manager.list_available_tilemaps()
        characters = self.session_manager.list_available_characters()
        monsters = self.session_manager.list_available_monster_presets()
        self.form.update_sources(maps, characters, monsters, available_tilemaps=tilemaps)

    def load_for_editing(self, encounter_data: Dict[str, Any]) -> None:
        """
        Pré-carrega o encontro completo no builder para o ciclo de edição sem duplicação de dados.
        Restaura metadados, mapa, grade, combatentes com posições e névoa de guerra.
        """
        self.is_editing = True
        self.editing_encounter_uid = encounter_data.get("uid")
        self.editing_encounter_path = encounter_data.get("path")
        self.editing_encounter_data = encounter_data.copy()

        # 1. Configura a Etapa 1 (Formulário)
        self.form.is_editing = True
        self.form.load_configuration(encounter_data)

        # 2. Extrai combatentes salvos para pre-posicionar na Etapa 2
        raw_combatants = encounter_data.get("combatants", [])
        preset_combatants: List[Dict[str, Any]] = []

        for c in raw_combatants:
            if isinstance(c, dict):
                etype = c.get("entity_type", "monster")
                is_player = etype in ("playable_character", "character", "pc")
                pos = c.get("position", {})
                col = pos.get("col", pos.get("x", 0))
                row = pos.get("row", pos.get("y", 0))
                is_hidden = bool(c.get("is_hidden", c.get("hidden", False)))
                name = c.get("instance_name") or c.get("name") or c.get("monster_id") or c.get("character_id", "Combatente")
                preset_combatants.append({
                    "entity_type": etype,
                    "character_id": c.get("character_id") if is_player else None,
                    "monster_id": c.get("monster_id") if not is_player else None,
                    "name": name,
                    "is_player": is_player,
                    "is_hidden": is_hidden,
                    "placed": True,
                    "col": int(col),
                    "row": int(row),
                })
            else:
                # Instância de Entity / Monster / PlayableCharacter
                is_player = getattr(c, "is_player", False)
                pos = getattr(c, "position", {"x": 0, "y": 0})
                col = pos.get("x", 0) if isinstance(pos, dict) else getattr(pos, "x", 0)
                row = pos.get("y", 0) if isinstance(pos, dict) else getattr(pos, "y", 0)
                is_hidden = getattr(c, "is_hidden", False)
                name = getattr(c, "name", "Combatente")
                preset_combatants.append({
                    "entity_type": "playable_character" if is_player else "monster",
                    "character_id": getattr(c, "character_id", getattr(c, "uid", None)) if is_player else None,
                    "monster_id": getattr(c, "monster_id", getattr(c, "uid", None)) if not is_player else None,
                    "name": name,
                    "is_player": is_player,
                    "is_hidden": is_hidden,
                    "placed": True,
                    "col": int(col),
                    "row": int(row),
                })

        # 3. Inicializa o Palco Tático com os dados carregados
        config_data = self.form.get_config_data()
        config_data["fog_of_war"] = encounter_data.get("fog_of_war", [])

        editing_filename = Path(self.editing_encounter_path).name if self.editing_encounter_path else None
        self.tactical_stage.initialize(
            config_data=config_data,
            available_characters=self.form.available_characters,
            available_monsters=self.form.available_monsters,
            preset_combatants=preset_combatants,
            is_editing=True,
            editing_uid=self.editing_encounter_uid,
            editing_filename=editing_filename,
        )

        self.stage = 1
        logger.info(
            f"EncounterCreatorTabView transicionado para edição do encontro '{self.editing_encounter_uid}' ({len(preset_combatants)} combatentes restaurados)."
        )

    def cancel_editing(self) -> None:
        """Descarta as alterações e retorna à aba de encontros sem modificar o disco."""
        self.is_editing = False
        self.editing_encounter_uid = None
        self.editing_encounter_path = None
        self.editing_encounter_data = None

        self.form.is_editing = False
        self.form.title_input.set_text("Novo Encontro")
        self.form.description_input.set_text("")
        self.form.error_message = None
        self.form._init_defaults()

        self.stage = 1

        if self.dm_window is not None and hasattr(self.dm_window, "active_tab"):
            self.dm_window.active_tab = 0

        logger.info("Edição de encontro cancelada. Alterações descartadas e retornado à aba de Encontros.")

    def proceed_to_stage_2(self) -> bool:
        """Valida o formulário e avança para a etapa do palco tático."""
        is_valid, err = self.form.validate()
        if not is_valid:
            self.form.error_message = err
            return False

        self.form.error_message = None
        config_data = self.form.get_config_data()

        # Preserva combatentes já posicionados no palco se as contagens coincidirem
        preset = None
        if self.is_editing and self.tactical_stage.staging_combatants:
            preset = self.tactical_stage.staging_combatants

        editing_filename = Path(self.editing_encounter_path).name if self.editing_encounter_path else None
        self.tactical_stage.initialize(
            config_data=config_data,
            available_characters=self.form.available_characters,
            available_monsters=self.form.available_monsters,
            preset_combatants=preset,
            is_editing=self.is_editing,
            editing_uid=self.editing_encounter_uid,
            editing_filename=editing_filename,
        )
        self.stage = 2
        return True

    def return_to_stage_1(self) -> None:
        """Retorna ao formulário preservando dados inseridos."""
        self.stage = 1
        self.form.error_message = None

    def save_encounter_file(self, directory: Optional[str] = None) -> Optional[Path]:
        """Gera e persiste o arquivo JSON do encontro (sobrescrevendo se em edição) e recarrega listas."""
        dest_dir = directory or "creations/encounters"
        target_uid = self.editing_encounter_uid if self.is_editing else None
        target_filename = Path(self.editing_encounter_path).name if (self.is_editing and self.editing_encounter_path) else None

        # Sincroniza config_data atual do formulário com o tactical_stage
        config_data = self.form.get_config_data()
        config_data["fog_of_war"] = self.tactical_stage.fog_manager.export_state()
        self.tactical_stage.config_data.update(config_data)

        saved_path = self.tactical_stage.save_encounter(
            directory=dest_dir,
            uid=target_uid,
            filename=target_filename,
        )

        if saved_path and self.dm_window and hasattr(self.dm_window, "refresh_encounter_files"):
            self.dm_window.refresh_encounter_files()

        return saved_path

    def on_update(self, delta_time: float) -> None:
        """Atualiza animações de cursor e inputs nos componentes."""
        if self.stage == 1:
            self.form.update(delta_time)
        elif self.stage == 2:
            self.tactical_stage.on_update(delta_time)

    # --- Renderização ---

    def draw_left_panel(self, panel_w: float, top_y: float) -> None:
        if self.stage == 1:
            self.form.draw_form(panel_w, top_y, self._text_cache)
        else:
            self.tactical_stage.draw_sidebar(panel_w, top_y, self._text_cache)

    def draw_right_panel(self, split_x: float, h: float, w: float) -> None:
        right_w = w - split_x
        if self.stage == 1:
            self.form.draw_preview(split_x, 0, right_w, h, self._text_cache, self._texture_cache)
        else:
            self.tactical_stage.draw_canvas(split_x, 0, right_w, h, self._text_cache, self._texture_cache)

    # --- Eventos de Mouse e Teclado ---

    def handle_mouse_press(self, x: float, y: float, split_x: float, h: float, button: int = arcade.MOUSE_BUTTON_LEFT) -> bool:
        if self.stage == 1:
            action = self.form.handle_mouse_press(x, y, split_x, h - 98)
            if action == "PROCEED_TO_STAGE_2":
                return self.proceed_to_stage_2()
            elif action == "CANCEL_EDITING":
                self.cancel_editing()
                return True
            return True

        elif self.stage == 2:
            action = self.tactical_stage.handle_mouse_press(x, y, split_x, h, button)
            if action == "RETURN_TO_STAGE_1":
                self.return_to_stage_1()
                return True
            elif action == "CANCEL_EDITING":
                self.cancel_editing()
                return True
            elif action == "SAVE_ENCOUNTER":
                self.save_encounter_file()
                return True
            return True

        return False

    def handle_mouse_drag(self, x: float, y: float) -> None:
        if self.stage == 1:
            self.form.handle_mouse_drag(x, y)
        elif self.stage == 2:
            self.tactical_stage.handle_mouse_drag(x, y)

    def handle_mouse_release(self, x: float, y: float, split_x: float) -> None:
        if self.stage == 1:
            self.form.handle_mouse_release(x, y)
        elif self.stage == 2:
            self.tactical_stage.handle_mouse_release(x, y, split_x)

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        if self.stage == 1:
            return self.form.handle_mouse_scroll(x, y, scroll_x, scroll_y)
        elif self.stage == 2:
            return self.tactical_stage.handle_mouse_scroll(x, y, scroll_x, scroll_y)
        return False

    def handle_key_press(self, symbol: int, modifiers: int) -> bool:
        if self.stage == 1:
            return self.form.handle_key_press(symbol, modifiers)
        return False

    def handle_key_release(self, symbol: int, modifiers: int) -> None:
        if self.stage == 1:
            self.form.handle_key_release(symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        if self.stage == 1:
            return self.form.handle_text_input(text)
        return False


# Aliases semânticos OOD
EncounterBuilderView = EncounterCreatorTabView
