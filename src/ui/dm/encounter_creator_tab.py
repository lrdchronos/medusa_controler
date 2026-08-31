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
      - Etapa 2: CreatorTacticalStage (Palco Tático, Drag & Drop, Snap-to-Grid, Visibilidade Oculta).
    """

    def __init__(self, session_manager: SessionManager, dm_window: Optional[arcade.Window] = None) -> None:
        self.session_manager = session_manager
        self.dm_window = dm_window

        self.stage: int = 1  # 1 = Formulário, 2 = Palco Tático

        # Subcomponentes Especializados (OOD)
        available_maps = self.session_manager.list_available_maps()
        available_characters = self.session_manager.list_available_characters()
        available_monsters = self.session_manager.list_available_monster_presets()

        self.form = CreatorConfigForm(
            available_maps=available_maps,
            available_characters=available_characters,
            available_monsters=available_monsters,
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

    # --- Transições de Fluxo ---

    def refresh_sources(self) -> None:
        """Recarrega arquivos de mapas, personagens e monstros."""
        maps = self.session_manager.list_available_maps()
        characters = self.session_manager.list_available_characters()
        monsters = self.session_manager.list_available_monster_presets()
        self.form.update_sources(maps, characters, monsters)

    def proceed_to_stage_2(self) -> bool:
        """Valida o formulário e avança para a etapa do palco tático."""
        is_valid, err = self.form.validate()
        if not is_valid:
            self.form.error_message = err
            return False

        self.form.error_message = None
        config_data = self.form.get_config_data()
        self.tactical_stage.initialize(
            config_data=config_data,
            available_characters=self.form.available_characters,
            available_monsters=self.form.available_monsters,
        )
        self.stage = 2
        return True

    def return_to_stage_1(self) -> None:
        """Retorna ao formulário preservando dados inseridos."""
        self.stage = 1
        self.form.error_message = None

    def save_encounter_file(self) -> Optional[Path]:
        """Gera e persiste o arquivo JSON do encontro e recarrega listas."""
        saved_path = self.tactical_stage.save_encounter(directory="creations/encounters")
        if saved_path and self.dm_window and hasattr(self.dm_window, "refresh_encounter_files"):
            self.dm_window.refresh_encounter_files()
        return saved_path

    def on_update(self, delta_time: float) -> None:
        """Atualiza animações de cursor e backspace repeat nos inputs."""
        if self.stage == 1:
            self.form.update(delta_time)

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
            return True

        elif self.stage == 2:
            action = self.tactical_stage.handle_mouse_press(x, y, split_x, h, button)
            if action == "RETURN_TO_STAGE_1":
                self.return_to_stage_1()
                return True
            elif action == "SAVE_ENCOUNTER":
                self.save_encounter_file()
                return True
            return True

        return False

    def handle_mouse_drag(self, x: float, y: float) -> None:
        if self.stage == 2:
            self.tactical_stage.handle_mouse_drag(x, y)

    def handle_mouse_release(self, x: float, y: float, split_x: float) -> None:
        if self.stage == 2:
            self.tactical_stage.handle_mouse_release(x, y, split_x)

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
