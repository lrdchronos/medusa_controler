import logging
from typing import Optional, List, Dict, Any, Tuple
import arcade
from arcade.camera import Camera2D
from ..manager.session_manager import SessionManager, DisplayState
from .dm.dm_header import DMHeader
from .dm.encounters_tab import EncountersTabView
from .dm.showcase_tab import ShowcaseTabView
from .dm.combat_tab import CombatTabView
from .dm.encounter_creator_tab import EncounterCreatorTabView
from .dm.tactical_minimap import TacticalMiniMap
from .dm.initiative_modal import InitiativeStagingModal

logger = logging.getLogger(__name__)


class DMWindow(arcade.Window):
    """
    Tela do Mestre (DMWindow) do Medusa VTT em Arcade nativo.
    Estrutura Arquitetural Modularizada (OOD / Clean Code):
      - Componentes Lado Esquerdo (~50%):
        * DMHeader: Barra superior de status, título, atalho IDLE e barra de 4 abas.
        * EncountersTabView (Aba 0): Lista de arquivos JSON de encontros e acionador de combate.
        * ShowcaseTabView (Aba 1): Lista de imagens de cenário e projetor para a PlayerWindow.
        * CombatTabView (Aba 2): Toolbar de ações de turno, roster de combatentes e despachante ágil de dano/cura.
        * EncounterCreatorTabView (Aba 3): Assistente e Palco Tático para criação e persistência de novos encontros.
        * InitiativeStagingModal: Overlay flutuante para rolagem, edição e confirmação de iniciativas D&D 5E.
      - Componentes Lado Direito (~50%):
        * TacticalMiniMap: Viewport da DMCamera com Grid procedural, renderização de tokens táticos com iniciais,
          drag-and-drop interativo com Snap-to-Grid e espelho das projeções em IDLE/PROJECTION.
        * Palco Tático do Criador (quando Aba 3 ativa).
    """

    def __init__(
        self,
        session_manager: SessionManager,
        root: Optional[Any] = None,
        width: int = 1280,
        height: int = 768,
        title: str = "Medusa VTT - Painel do Mestre (DM Screen)",
    ) -> None:
        super().__init__(width, height, title, resizable=True)
        self.switch_to()
        arcade.set_window(self)

        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager

        # Subcomponentes Especializados (OOD)
        self.header = DMHeader(session_manager=self.session_manager)
        self.encounters_tab = EncountersTabView(session_manager=self.session_manager)
        self.showcase_tab = ShowcaseTabView(session_manager=self.session_manager)
        self.combat_tab = CombatTabView(session_manager=self.session_manager)
        self.creator_tab = EncounterCreatorTabView(session_manager=self.session_manager, dm_window=self)
        self.mini_map = TacticalMiniMap(window=self, session_manager=self.session_manager)
        self.initiative_modal = InitiativeStagingModal(session_manager=self.session_manager)

        # Estado Global da Janela
        self.active_tab: int = 2 if self.session_manager.is_combat_active else 0

        # Listener Reativo de Sessão
        self.session_manager.add_listener(self._on_session_changed)

        logger.info("DMWindow (Arcade GUI Modular) inicializada com sucesso.")

    # --- Propriedades de Compatibilidade ---

    @property
    def dm_camera(self) -> Camera2D:
        return self.mini_map.dm_camera

    @property
    def show_initiative_modal(self) -> bool:
        return self.initiative_modal.is_open

    @show_initiative_modal.setter
    def show_initiative_modal(self, value: bool) -> None:
        self.initiative_modal.is_open = value

    @property
    def draft_initiatives(self) -> Dict[str, int]:
        return self.initiative_modal.draft_initiatives

    @draft_initiatives.setter
    def draft_initiatives(self, value: Dict[str, int]) -> None:
        self.initiative_modal.draft_initiatives = value

    @property
    def selected_encounter_index(self) -> int:
        return self.encounters_tab.selected_index

    @selected_encounter_index.setter
    def selected_encounter_index(self, value: int) -> None:
        self.encounters_tab.selected_index = value

    @property
    def selected_showcase_index(self) -> int:
        return self.showcase_tab.selected_index

    @selected_showcase_index.setter
    def selected_showcase_index(self, value: int) -> None:
        self.showcase_tab.selected_index = value

    @property
    def selected_combatant_uid(self) -> Optional[str]:
        return self.combat_tab.selected_combatant_uid

    @selected_combatant_uid.setter
    def selected_combatant_uid(self, value: Optional[str]) -> None:
        self.combat_tab.selected_combatant_uid = value

    @property
    def encounters_list(self) -> List[Dict[str, Any]]:
        return self.encounters_tab.encounters_list

    @property
    def showcase_list(self) -> List[Dict[str, Any]]:
        return self.showcase_tab.showcase_list

    @property
    def custom_hp_value(self) -> int:
        return self.combat_tab.custom_hp_value

    @custom_hp_value.setter
    def custom_hp_value(self, value: int) -> None:
        self.combat_tab.custom_hp_value = value

    # --- Sincronização de Estado ---

    def refresh_encounter_files(self) -> None:
        self.encounters_tab.refresh()
        self.creator_tab.refresh_sources()

    def refresh_showcase_files(self) -> None:
        self.showcase_tab.refresh()

    def _on_session_changed(self) -> None:
        if self.session_manager.is_combat_active and self.active_tab not in (2, 3):
            self.active_tab = 2
        elif self.session_manager.is_idle and self.active_tab == 2:
            self.active_tab = 0
        self.combat_tab.ensure_valid_selection()

    # --- Ciclo de Vida da Janela (Arcade) ---

    def on_resize(self, width: int, height: int) -> None:
        self.switch_to()
        arcade.set_window(self)
        super().on_resize(width, height)
        self.mini_map.update_viewport()

    def on_draw(self) -> None:
        self.switch_to()
        arcade.set_window(self)
        self.use()
        self.clear()

        w, h = self.width, self.height
        split_x = w * 0.50

        # Fundo Global Dark Fantasy (#0E1218)
        arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), (14, 18, 24, 255))
        arcade.draw_line(split_x, 0, split_x, h, (40, 50, 70, 200), 2)

        # 1. Painel Esquerdo: Cabeçalho, Abas e Conteúdo
        content_top_y = self.header.draw(split_x, h, self.active_tab)

        if self.active_tab == 0:
            self.encounters_tab.draw(split_x, content_top_y)
        elif self.active_tab == 1:
            self.showcase_tab.draw(split_x, content_top_y)
        elif self.active_tab == 2:
            self.combat_tab.draw(split_x, content_top_y)
        elif self.active_tab == 3:
            self.creator_tab.draw_left_panel(split_x, content_top_y)

        # 2. Painel Direito: Mini-Mapa Tático, Showcase Preview, ou Palco do Criador
        if self.active_tab == 3:
            self.creator_tab.draw_right_panel(split_x, h, w)
        else:
            self.mini_map.draw(split_x, h, w, self.combat_tab.selected_combatant_uid)

        # 3. Modal Overlay de Staging de Iniciativas
        if self.initiative_modal.is_open:
            self.initiative_modal.draw(w, h)

    # --- Tratamento de Eventos de Mouse ---

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.switch_to()
        arcade.set_window(self)
        w, h = self.width, self.height
        split_x = w * 0.50

        # 1. Se o modal de iniciativas estiver ativo, direciona exclusivamente para ele
        if self.initiative_modal.is_open:
            self.initiative_modal.handle_click(
                x, y, w, h,
                on_confirmed_callback=lambda: setattr(self, "active_tab", 2)
            )
            return

        # 2. Cliques no Lado Esquerdo (Controles e Abas)
        if x < split_x:
            if self.header.handle_click(x, y, split_x, h, set_tab_callback=lambda idx: setattr(self, "active_tab", idx)):
                return

            header_h = 56
            tab_bar_h = 42
            content_top_y = h - header_h - tab_bar_h

            if self.active_tab == 0:
                self.encounters_tab.handle_click(
                    x, y, split_x, content_top_y,
                    on_start_combat_callback=lambda enc_id: self.session_manager.start_encounter(enc_id)
                )
            elif self.active_tab == 1:
                self.showcase_tab.handle_click(x, y, split_x, content_top_y)
            elif self.active_tab == 2:
                self.combat_tab.handle_click(
                    x, y, split_x, content_top_y,
                    open_initiative_modal_callback=self.initiative_modal.open
                )
            elif self.active_tab == 3:
                self.creator_tab.handle_mouse_press(x, y, split_x, h, button=button)
            return

        # 3. Cliques no Lado Direito
        if x >= split_x:
            if self.active_tab == 3:
                self.creator_tab.handle_mouse_press(x, y, split_x, h, button=button)
            elif self.session_manager.is_combat_active:
                self.mini_map.handle_mouse_press(
                    x, y, split_x, h,
                    on_select_combatant=lambda uid: setattr(self.combat_tab, "selected_combatant_uid", uid)
                )

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int) -> None:
        self.switch_to()
        arcade.set_window(self)
        if self.active_tab == 3:
            self.creator_tab.handle_mouse_drag(x, y)
        else:
            self.mini_map.handle_mouse_drag(x, y)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.switch_to()
        arcade.set_window(self)
        split_x = self.width * 0.50
        if self.active_tab == 3:
            self.creator_tab.handle_mouse_release(x, y, split_x)
        else:
            self.mini_map.handle_mouse_release(x, y, split_x)

    def on_update(self, delta_time: float) -> None:
        """Atualização de quadro e lógica periódica dos componentes."""
        if self.active_tab == 3:
            self.creator_tab.on_update(delta_time)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Trata atalhos de teclado e digitação no Criador de Encontros."""
        self.switch_to()
        arcade.set_window(self)
        if self.active_tab == 3:
            self.creator_tab.handle_key_press(symbol, modifiers)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        """Trata liberação de teclas (como backspace repeat) no Criador de Encontros."""
        self.switch_to()
        arcade.set_window(self)
        if self.active_tab == 3:
            self.creator_tab.handle_key_release(symbol, modifiers)

    def on_text(self, text: str) -> None:
        """Trata entrada de texto digitado no Criador de Encontros."""
        self.switch_to()
        arcade.set_window(self)
        if self.active_tab == 3:
            self.creator_tab.handle_text_input(text)

    def on_text_input(self, text: str) -> None:
        """Compatibilidade para versão do Arcade que usa on_text_input."""
        self.on_text(text)

    def pump_events(self) -> None:
        """Compatibilidade para chamadas externas legadas."""
        pass


