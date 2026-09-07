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
        player_window: Optional[Any] = None,
        width: int = 1280,
        height: int = 768,
        title: str = "Medusa VTT - Painel do Mestre (DM Screen)",
    ) -> None:
        super().__init__(width, height, title, resizable=True)
        self.switch_to()
        arcade.set_window(self)

        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.player_window = player_window
        if self.player_window is not None:
            self.player_window.dm_window = self

        # Subcomponentes Especializados (OOD)
        self.header = DMHeader(session_manager=self.session_manager, dm_window=self)
        self.encounters_tab = EncountersTabView(session_manager=self.session_manager, dm_window=self)
        self.showcase_tab = ShowcaseTabView(session_manager=self.session_manager)
        self.combat_tab = CombatTabView(session_manager=self.session_manager, dm_window=self)
        self.creator_tab = EncounterCreatorTabView(session_manager=self.session_manager, dm_window=self)
        self.mini_map = TacticalMiniMap(window=self, session_manager=self.session_manager, fog_panel=self.combat_tab.fog_panel)
        self.initiative_modal = InitiativeStagingModal(session_manager=self.session_manager)


        # Estado Global da Janela
        self.active_tab: int = 2 if self.session_manager.is_combat_active else 0
        self.is_ctrl_held: bool = False

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

    # --- Propriedades e Controle de Ciclo de Vida da PlayerWindow ---

    @property
    def is_player_window_open(self) -> bool:
        """Indica se a tela dos jogadores está instanciada e visível."""
        if self.player_window is None:
            return False
        if getattr(self.player_window, "context", None) is None or getattr(self.player_window, "_closed", False):
            return False
        return bool(getattr(self.player_window, "visible", False))

    @property
    def is_player_fullscreen(self) -> bool:
        """Indica se a tela dos jogadores está em modo tela cheia."""
        if self.is_player_window_open and self.player_window is not None:
            return bool(getattr(self.player_window, "fullscreen", False))
        return False

    def open_player_window(self) -> None:
        """Instancia ou reexibe a PlayerWindow conectada aos managers de sessão e combate."""
        if self.is_player_window_open:
            logger.info("PlayerWindow já se encontra aberta.")
            return

        # Se a janela já existe e está apenas oculta (warm reuse), reexibe preservando o contexto OpenGL
        if (
            self.player_window is not None
            and getattr(self.player_window, "context", None) is not None
            and not getattr(self.player_window, "_closed", False)
        ):
            self.player_window.set_visible(True)
            self.player_window.reconnect_listeners()
            self.player_window.switch_to()
            try:
                self.player_window.activate()
            except Exception:
                pass
            self.switch_to()
            arcade.set_window(self)
            logger.info("PlayerWindow reexibida com sucesso.")
            return

        from .player_window import PlayerWindow

        self.player_window = PlayerWindow(
            session_manager=self.session_manager,
            dm_window=self,
            width=1024,
            height=768,
            title="Medusa VTT - Tela dos Jogadores",
        )
        self.switch_to()
        arcade.set_window(self)
        logger.info("PlayerWindow instanciada e conectada ao SessionManager.")

    def close_player_window(self) -> None:
        """Fecha a PlayerWindow graciosamente, pausando observadores e ocultando a janela."""
        if self.player_window is not None:
            try:
                self.player_window.close(hard=False)
            except Exception as e:
                logger.debug(f"Erro ao fechar PlayerWindow: {e}")
            logger.info("PlayerWindow ocultada e desconectada da DMWindow.")

    def toggle_player_window(self) -> None:
        """Alterna a exibição (abre ou fecha) da PlayerWindow."""
        if self.is_player_window_open:
            self.close_player_window()
        else:
            self.open_player_window()

    def toggle_player_fullscreen(self) -> None:
        """Alterna entre tela cheia e modo janela na PlayerWindow se estiver ativa."""
        if self.is_player_window_open and self.player_window is not None:
            self.player_window.toggle_fullscreen()
        else:
            logger.warning("Não é possível alternar tela cheia: PlayerWindow está fechada.")

    def notify_player_window_closed(self) -> None:
        """Callback invocado quando a PlayerWindow é fechada externamente (ex: botão 'X' do SO)."""
        logger.info("DMWindow notificada da ocultação da PlayerWindow.")

    # --- Sincronização de Estado ---

    def refresh_encounter_files(self) -> None:
        self.encounters_tab.refresh()
        self.creator_tab.refresh_sources()

    def refresh_showcase_files(self) -> None:
        self.showcase_tab.refresh()

    def open_encounter_for_editing(self, enc_dict_or_uid: Any) -> None:
        """Carrega o encontro selecionado no Encounter Creator/Builder e transiciona para a Aba 3."""
        if isinstance(enc_dict_or_uid, dict):
            enc_data = enc_dict_or_uid.copy()
        else:
            from ..domain.loaders.encounter_loader import EncounterLoader
            loader = EncounterLoader()
            enc_data = loader.load_encounter(str(enc_dict_or_uid))

        path = enc_data.get("path") or enc_data.get("filename")
        if path:
            from ..domain.loaders.encounter_loader import EncounterLoader
            resolved = EncounterLoader().resolve_encounter_path(path)
            if resolved and resolved.is_file():
                try:
                    import json
                    with open(resolved, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        raw["path"] = str(resolved)
                        enc_data = raw
                except Exception as e:
                    logger.error(f"Erro ao carregar raw JSON do encontro para edição: {e}")

        self.creator_tab.load_for_editing(enc_data)
        self.active_tab = 3
        logger.info(f"DMWindow: transicionado para Encounter Builder para edição de '{enc_data.get('title')}'.")

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
        content_top_y = self.header.draw(
            split_x,
            h,
            self.active_tab,
            player_window_open=self.is_player_window_open,
            is_fullscreen=self.is_player_fullscreen,
        )

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

        # 4. Modal Overlay de Criação e Inserção de Tokens (Mid-Combat Token Spawning)
        if self.combat_tab.add_token_modal.is_open:
            self.combat_tab.add_token_modal.draw(w, h)

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

        # 1.5 Se o modal de criação de token estiver ativo, direciona exclusivamente para ele
        if self.combat_tab.add_token_modal.is_open:
            self.combat_tab.add_token_modal.handle_click(x, y, w, h)
            return

        # 2. Cliques no Lado Esquerdo (Controles e Abas)
        if x < split_x:
            if self.header.handle_click(
                x,
                y,
                split_x,
                h,
                set_tab_callback=lambda idx: setattr(self, "active_tab", idx),
                on_toggle_player_window=self.toggle_player_window,
                on_toggle_fullscreen=self.toggle_player_fullscreen,
            ):
                return

            header_h = 56
            tab_bar_h = 42
            content_top_y = h - header_h - tab_bar_h

            if self.active_tab == 0:
                self.encounters_tab.handle_click(
                    x, y, split_x, content_top_y,
                    on_start_combat_callback=lambda enc_id: self.session_manager.start_encounter(enc_id),
                    on_edit_encounter_callback=self.open_encounter_for_editing,
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

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        """Trata movimento do cursor do mouse, atualizando o overlay de magia em tempo real."""
        self.switch_to()
        arcade.set_window(self)
        split_x = self.width * 0.50
        if x >= split_x and self.session_manager.is_combat_active:
            self.mini_map.handle_mouse_motion(x, y)
        else:
            self.mini_map.handle_mouse_leave()

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int) -> None:
        self.switch_to()
        arcade.set_window(self)
        split_x = self.width * 0.50
        if x < split_x and self.active_tab == 2:
            self.combat_tab.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)
        if self.active_tab == 3:
            self.creator_tab.handle_mouse_drag(x, y)
        elif x >= split_x:
            self.mini_map.handle_mouse_drag(x, y)
            if self.session_manager.is_combat_active:
                self.mini_map.handle_mouse_motion(x, y)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.switch_to()
        arcade.set_window(self)
        split_x = self.width * 0.50
        if x < split_x and self.active_tab == 2:
            self.combat_tab.handle_mouse_release(x, y, button, modifiers)
        if self.active_tab == 3:
            self.creator_tab.handle_mouse_release(x, y, split_x)
        else:
            self.mini_map.handle_mouse_release(x, y, split_x)

    def on_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> None:
        self.switch_to()
        arcade.set_window(self)
        if self.initiative_modal.is_open:
            if self.initiative_modal.handle_scroll(x, y, scroll_x, scroll_y):
                return

        split_x = self.width * 0.50
        if self.active_tab == 0 and x < split_x:
            if self.encounters_tab.handle_mouse_scroll(x, y, scroll_x, scroll_y):
                return
        elif self.active_tab == 2 and x < split_x:
            if self.combat_tab.handle_mouse_scroll(x, y, scroll_x, scroll_y):
                return
        elif self.active_tab == 3:
            self.creator_tab.handle_mouse_scroll(x, y, scroll_x, scroll_y)
        elif x >= split_x and self.session_manager.is_combat_active:
            self.mini_map.handle_mouse_scroll(x, y, scroll_x, scroll_y, is_ctrl=self.is_ctrl_held)

    def on_update(self, delta_time: float) -> None:
        """Atualização de quadro e lógica periódica dos componentes."""
        if self.active_tab == 3:
            self.creator_tab.on_update(delta_time)
        elif self.active_tab == 2:
            self.combat_tab.on_update(delta_time)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """Trata atalhos de teclado e digitação no Criador de Encontros e no Painel de Feitiços."""
        self.switch_to()
        arcade.set_window(self)

        # Rastreia estado da tecla Ctrl
        if symbol in (arcade.key.LCTRL, arcade.key.RCTRL) or bool(modifiers & arcade.key.MOD_CTRL):
            self.is_ctrl_held = True

        # Atalhos Globais da DMWindow para Controle da PlayerWindow
        if symbol == arcade.key.F10:
            self.toggle_player_window()
            return

        if symbol == arcade.key.F11:
            self.toggle_player_fullscreen()
            return

        if symbol == arcade.key.ESCAPE:
            if self.combat_tab.add_token_modal.is_open:
                self.combat_tab.add_token_modal.close()
                return
            if self.mini_map.is_placing_token:
                self.mini_map.cancel_placing_token()
                return
            if self.initiative_modal.is_open:
                self.initiative_modal.close()
                return

        if self.active_tab == 3:
            self.creator_tab.handle_key_press(symbol, modifiers)
        elif self.active_tab == 2:
            self.combat_tab.handle_key_press(symbol, modifiers)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        """Trata liberação de teclas (como backspace repeat) no Criador e no Painel de Feitiços."""
        self.switch_to()
        arcade.set_window(self)

        # Atualiza estado da tecla Ctrl
        if symbol in (arcade.key.LCTRL, arcade.key.RCTRL):
            self.is_ctrl_held = False

        if self.active_tab == 3:
            self.creator_tab.handle_key_release(symbol, modifiers)
        elif self.active_tab == 2:
            self.combat_tab.handle_key_release(symbol, modifiers)

    def on_text(self, text: str) -> None:
        """Trata entrada de texto digitado no Criador e no Painel de Feitiços."""
        self.switch_to()
        arcade.set_window(self)
        if self.active_tab == 3:
            self.creator_tab.handle_text_input(text)
        elif self.active_tab == 2:
            self.combat_tab.handle_text_input(text)

    def on_text_input(self, text: str) -> None:
        """Compatibilidade para versão do Arcade que usa on_text_input."""
        self.on_text(text)

    def pump_events(self) -> None:
        """Compatibilidade para chamadas externas legadas."""
        pass

    def on_close(self) -> None:
        """Encerra a DMWindow, fechando graciosamente a PlayerWindow e finalizando a aplicação."""
        logger.info("DMWindow sendo fechada. Encerrando aplicação...")
        if self.player_window is not None:
            try:
                self.player_window.close(hard=True)
            except Exception as e:
                logger.debug(f"Erro ao fechar PlayerWindow durante encerramento da DMWindow: {e}")
            self.player_window = None
        super().on_close()
        arcade.exit()



