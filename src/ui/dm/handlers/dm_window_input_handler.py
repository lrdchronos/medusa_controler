import logging
from typing import Any
import arcade

logger = logging.getLogger(__name__)


class DMWindowInputHandler:
    """
    Controlador de eventos de entrada da tela do Mestre (DMWindow),
    direcionando eventos de mouse e teclado para o modal ativo,
    cabeçalho, abas ou mini-mapa tático.
    """

    @staticmethod
    def on_mouse_press(window: Any, x: float, y: float, button: int, modifiers: int) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)
            w, h = window.width, window.height
            split_x = w * 0.50

            # 1. Se o modal de iniciativas estiver ativo, direciona exclusivamente para ele
            if window.initiative_modal.is_open:
                window.initiative_modal.handle_click(
                    x, y, w, h,
                    on_confirmed_callback=lambda: setattr(window, "active_tab", 2)
                )
                return

            # 1.5 Se o modal de criação de token estiver ativo, direciona exclusivamente para ele
            if window.combat_tab.add_token_modal.is_open:
                window.combat_tab.add_token_modal.handle_click(x, y, w, h)
                return

            # 2. Cliques no Lado Esquerdo (Controles e Abas)
            if x < split_x:
                if window.header.handle_click(
                    x,
                    y,
                    split_x,
                    h,
                    set_tab_callback=lambda idx: setattr(window, "active_tab", idx),
                    on_toggle_player_window=window.toggle_player_window,
                    on_toggle_fullscreen=window.toggle_player_fullscreen,
                ):
                    return

                header_h = 56
                tab_bar_h = 42
                content_top_y = h - header_h - tab_bar_h

                if window.active_tab == 0:
                    window.encounters_tab.handle_click(
                        x, y, split_x, content_top_y,
                        on_start_combat_callback=lambda enc_id: window.session_manager.start_encounter(enc_id),
                        on_edit_encounter_callback=window.open_encounter_for_editing,
                    )
                elif window.active_tab == 1:
                    window.showcase_tab.handle_click(x, y, split_x, content_top_y)
                elif window.active_tab == 2:
                    window.combat_tab.handle_click(
                        x, y, split_x, content_top_y,
                        open_initiative_modal_callback=window.initiative_modal.open
                    )
                elif window.active_tab == 3:
                    window.creator_tab.handle_mouse_press(x, y, split_x, h, button=button)
                return

            # 3. Cliques no Lado Direito
            if x >= split_x:
                if window.active_tab == 3:
                    window.creator_tab.handle_mouse_press(x, y, split_x, h, button=button)
                elif window.session_manager.is_combat_active:
                    window.mini_map.handle_mouse_press(
                        x, y, button=button, modifiers=modifiers, split_x=split_x
                    )
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_mouse_press: %s", e, exc_info=True)

    @staticmethod
    def on_mouse_motion(window: Any, x: float, y: float, dx: float, dy: float) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)
            split_x = window.width * 0.50
            if x >= split_x and window.session_manager.is_combat_active:
                window.mini_map.handle_mouse_motion(x, y, dx, dy, split_x=split_x)
            else:
                window.mini_map.handle_mouse_leave()
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_mouse_motion: %s", e, exc_info=True)

    @staticmethod
    def on_mouse_drag(window: Any, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)
            split_x = window.width * 0.50

            # Se há um token sendo arrastado no minimapa, continua o arrasto diretamente no minimapa
            if getattr(window.mini_map, "_dragged_combatant_uid", None) is not None:
                window.mini_map.handle_mouse_drag(x, y, dx, dy, buttons, modifiers, split_x=split_x)
                return

            if x < split_x and window.active_tab == 2:
                window.combat_tab.handle_mouse_drag(x, y, dx, dy, buttons, modifiers)
            elif window.active_tab == 3:
                window.creator_tab.handle_mouse_drag(x, y)
            elif x >= split_x:
                window.mini_map.handle_mouse_drag(x, y, dx, dy, buttons, modifiers, split_x=split_x)
                if window.session_manager.is_combat_active:
                    window.mini_map.handle_mouse_motion(x, y, dx, dy, split_x=split_x)
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_mouse_drag: %s", e, exc_info=True)

    @staticmethod
    def on_mouse_release(window: Any, x: float, y: float, button: int, modifiers: int) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)
            split_x = window.width * 0.50

            # Se havia um token sendo arrastado no minimapa, conclui a soltura diretamente no minimapa
            if getattr(window.mini_map, "_dragged_combatant_uid", None) is not None:
                window.mini_map.handle_mouse_release(x, y, button, modifiers, split_x=split_x)
                return

            if x < split_x and window.active_tab == 2:
                window.combat_tab.handle_mouse_release(x, y, button, modifiers)
            elif window.active_tab == 3:
                window.creator_tab.handle_mouse_release(x, y, split_x)
            else:
                window.mini_map.handle_mouse_release(x, y, button, modifiers, split_x=split_x)
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_mouse_release: %s", e, exc_info=True)

    @staticmethod
    def on_mouse_scroll(window: Any, x: float, y: float, scroll_x: float, scroll_y: float) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)
            if window.initiative_modal.is_open:
                if window.initiative_modal.handle_scroll(x, y, scroll_x, scroll_y):
                    return

            split_x = window.width * 0.50
            if window.active_tab == 0 and x < split_x:
                if window.encounters_tab.handle_mouse_scroll(x, y, scroll_x, scroll_y):
                    return
            elif window.active_tab == 2 and x < split_x:
                if window.combat_tab.handle_mouse_scroll(x, y, scroll_x, scroll_y):
                    return
            elif window.active_tab == 3:
                window.creator_tab.handle_mouse_scroll(x, y, scroll_x, scroll_y)
            elif x >= split_x and window.session_manager.is_combat_active:
                window.mini_map.handle_mouse_scroll(x, y, scroll_x, scroll_y, is_ctrl=window.is_ctrl_held, is_alt=window.is_alt_held)
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_mouse_scroll: %s", e, exc_info=True)

    @staticmethod
    def on_key_press(window: Any, symbol: int, modifiers: int) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)

            if symbol in (arcade.key.LCTRL, arcade.key.RCTRL) or bool(modifiers & arcade.key.MOD_CTRL):
                window.is_ctrl_held = True
            if symbol in (arcade.key.LALT, arcade.key.RALT) or bool(modifiers & arcade.key.MOD_ALT):
                window.is_alt_held = True

            if symbol == arcade.key.F10:
                window.toggle_player_window()
                return

            if symbol == arcade.key.F11:
                window.toggle_player_fullscreen()
                return

            if symbol == arcade.key.ESCAPE:
                if window.combat_tab.add_token_modal.is_open:
                    window.combat_tab.add_token_modal.close()
                    return
                if window.mini_map.is_placing_token:
                    window.mini_map.cancel_placing_token()
                    return
                if window.initiative_modal.is_open:
                    window.initiative_modal.close()
                    return

            if window.active_tab == 3:
                window.creator_tab.handle_key_press(symbol, modifiers)
            elif window.active_tab == 2:
                window.combat_tab.handle_key_press(symbol, modifiers)
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_key_press: %s", e, exc_info=True)

    @staticmethod
    def on_key_release(window: Any, symbol: int, modifiers: int) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)

            if symbol in (arcade.key.LCTRL, arcade.key.RCTRL):
                window.is_ctrl_held = False
            if symbol in (arcade.key.LALT, arcade.key.RALT):
                window.is_alt_held = False

            if window.active_tab == 3:
                window.creator_tab.handle_key_release(symbol, modifiers)
            elif window.active_tab == 2:
                window.combat_tab.handle_key_release(symbol, modifiers)
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_key_release: %s", e, exc_info=True)

    @staticmethod
    def on_text(window: Any, text: str) -> None:
        try:
            window.switch_to()
            arcade.set_window(window)
            if window.active_tab == 3:
                window.creator_tab.handle_text_input(text)
            elif window.active_tab == 2:
                window.combat_tab.handle_text_input(text)
        except Exception as e:
            logger.error("Erro inesperado em DMWindowInputHandler.on_text: %s", e, exc_info=True)
