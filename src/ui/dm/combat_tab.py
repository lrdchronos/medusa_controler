import logging
from typing import Optional, Dict, Any, Callable, Tuple
import arcade
from ...manager.session_manager import SessionManager, DisplayState
from ...domain.models.entity import Entity, EntityType, DynamicToken
from ..components.discrete_scroll_list import DiscreteScrollList
from .spell_aoe_panel import SpellAoEPanel
from .fog_control_panel import FogControlPanel
from .add_token_modal import AddTokenModal
from .panels.combat_actions_panel import CombatActionsPanel
from .panels.combat_roster_panel import CombatRosterPanel
from .handlers.combat_tab_input_handler import CombatTabInputHandler

logger = logging.getLogger(__name__)


class CombatTabView:
    """
    Componente da Aba de Combate Ativo (Barra de Ações de Turno, Inserção Dinâmica de Tokens,
    Painel de Feitiços AoE, Painel de Névoa de Guerra, Roster de Combatentes com DiscreteScrollList,
    Despachante de Dano/Cura e Save State).
    """

    def __init__(self, session_manager: SessionManager, dm_window: Optional[Any] = None) -> None:
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager
        self.dm_window = dm_window
        self.selected_combatant_uid: Optional[str] = None
        self.custom_hp_value: int = 8
        self.text_cache: Dict[str, arcade.Text] = {}
        self.spell_aoe_panel = SpellAoEPanel(session_manager=self.session_manager)
        self.fog_panel = FogControlPanel(
            fog_manager=self.combat_manager.fog_manager,
            dimensions_provider=self._get_grid_dimensions,
            save_callback=self.combat_manager.save_fog_to_encounter_file,
        )
        self.add_token_modal = AddTokenModal(on_confirm=self._handle_add_token_confirm)

        # Componente OOD reutilizável para Paginação e Rolagem Discreta de Combatentes
        self.__item_height: int = 24
        self.__spacing: int = 2
        self.__scroll_list = DiscreteScrollList(
            item_height=self.__item_height,
            spacing=self.__spacing,
            visible_item_count=4,
        )

        # Notificação Toast de Confirmação de Salvamento
        self.toast_message: Optional[str] = None
        self.toast_timer: float = 0.0

        # Modal de Confirmação ao Finalizar Combate (Limpar ou Manter Save)
        self.pending_end_combat_modal: bool = False

    @property
    def scroll_list(self) -> DiscreteScrollList:
        """Referência ao componente OOD de rolagem discreta de combatentes."""
        return self.__scroll_list

    def _handle_add_token_confirm(self, token_data: Dict[str, Any]) -> None:
        """Aciona o modo PLACING_TOKEN no TacticalMiniMap após confirmação do modal."""
        if self.dm_window is not None and hasattr(self.dm_window, "mini_map"):
            self.dm_window.mini_map.start_placing_token(
                token_data=token_data,
                on_spawn=self._on_token_spawned,
            )
            logger.info(f"Modo de posicionamento ativado no TacticalMiniMap para '{token_data.get('name')}'.")
        else:
            etype = token_data.get("entity_type", EntityType.NEUTRAL)
            token_entity = DynamicToken(
                name=token_data.get("name", "Token"),
                max_hp=int(token_data.get("max_hp", 1)),
                armor_class=int(token_data.get("armor_class", 10)),
                entity_type=etype,
                token_sprite=token_data.get("token_sprite"),
                size=token_data.get("size", "Medium"),
            )
            slot = token_data.get("initiative_slot", "next")
            self.combat_manager.spawn_combatant(token_entity, (0, 0), initiative_slot=slot)
            self.ensure_valid_selection()

    def _on_token_spawned(self, entity: Entity, position: Tuple[int, int], slot: str) -> None:
        """Callback invocado após inserção do token no mini-mapa."""
        self.selected_combatant_uid = entity.uid
        self.ensure_valid_selection()
        logger.info(f"Token '{entity.name}' inserido e selecionado com sucesso em {position}.")

    def _get_grid_dimensions(self) -> Tuple[int, int]:
        """Retorna dimensões (colunas, linhas) da grade tática ativa."""
        grid_mgr = self.combat_manager.grid_manager
        if grid_mgr is not None:
            return (grid_mgr.columns, grid_mgr.rows)
        return (25, 14)

    def _get_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool = True,
        anchor_x: str = "left",
        anchor_y: str = "center",
    ) -> arcade.Text:
        cached = self.text_cache.get(key)
        if cached is None or cached.text != text or cached.font_size != font_size:
            cached = arcade.Text(
                text=text,
                x=x,
                y=y,
                color=color,
                font_size=font_size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
            )
            self.text_cache[key] = cached
        else:
            cached.x = x
            cached.y = y
            cached.color = color
            cached.text = text
        return cached

    def ensure_valid_selection(self) -> None:
        """Garante que haja um combatente válido selecionado."""
        combatants = self.combat_manager.combatants
        if combatants:
            if not self.selected_combatant_uid or not any(c.uid == self.selected_combatant_uid for c in combatants):
                self.selected_combatant_uid = combatants[0].uid
        else:
            self.selected_combatant_uid = None

    def trigger_save_combat(self) -> None:
        """Salva o estado atual de combate e dispara toast de confirmação."""
        success = self.combat_manager.save_combat_state()
        if success:
            self.toast_message = "Progresso do combate salvo com sucesso!"
            self.toast_timer = 3.0
            logger.info("Progresso do combate salvo com sucesso pelo usuário.")
        else:
            self.toast_message = "Falha ao salvar progresso do combate!"
            self.toast_timer = 3.0

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha todo o painel de combate ativo."""
        self.ensure_valid_selection()

        if self.toast_timer > 0:
            self.toast_timer -= 1 / 60

        # 1. Barra de Ações Rápidas de Combate
        bar_y = CombatActionsPanel.draw_action_bar(self, panel_w, top_y)

        # 2. Informação de Rodada e Turno Ativo
        info_y = CombatActionsPanel.draw_round_info(self, panel_w, bar_y)

        # 3. Painel de Feitiços (Spell AoE Overlay)
        spell_next_y = self.spell_aoe_panel.draw(panel_w, info_y - 12)

        # 4. Painel de Névoa de Guerra
        fog_next_y = self.fog_panel.draw(panel_w, spell_next_y)

        # 5. Tabela de Combatentes (Roster) com DiscreteScrollList
        table_bottom_y, num_combatants = CombatRosterPanel.draw_roster_table(self, panel_w, fog_next_y)

        # 6. Painel Inferior: Despachante de Dano / Cura do Alvo Selecionado
        panels_collapsed = (1 if self.spell_aoe_panel.is_collapsed else 0) + (1 if self.fog_panel.is_collapsed else 0)
        max_rows = 4 + panels_collapsed * 2
        rendered_rows = min(num_combatants, max_rows)
        disp_top = table_bottom_y - rendered_rows * (self.__item_height + self.__spacing) - 8
        CombatRosterPanel.draw_hp_dispatcher(self, panel_w, disp_top)

        # 7. Modal de Confirmação ao Finalizar Combate
        if self.pending_end_combat_modal:
            CombatActionsPanel.draw_end_combat_modal(self, panel_w, top_y)

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        open_initiative_modal_callback: Callable[[], None],
    ) -> bool:
        return CombatTabInputHandler.handle_click(self, x, y, panel_w, top_y, open_initiative_modal_callback)

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        return CombatTabInputHandler.handle_mouse_scroll(self, x, y, scroll_x, scroll_y)

    def handle_mouse_drag(self, x: float, y: float, dx: float = 0.0, dy: float = 0.0, buttons: int = 1, modifiers: int = 0) -> bool:
        return CombatTabInputHandler.handle_mouse_drag(self, x, y, dx, dy, buttons, modifiers)

    def handle_mouse_release(self, x: float, y: float, button: int = 1, modifiers: int = 0) -> None:
        CombatTabInputHandler.handle_mouse_release(self, x, y, button, modifiers)

    def handle_key_press(self, symbol: int, modifiers: int = 0) -> bool:
        return CombatTabInputHandler.handle_key_press(self, symbol, modifiers)

    def handle_key_release(self, symbol: int, modifiers: int = 0) -> None:
        CombatTabInputHandler.handle_key_release(self, symbol, modifiers)

    def handle_text_input(self, text: str) -> bool:
        return CombatTabInputHandler.handle_text_input(self, text)

    def on_update(self, dt: float) -> None:
        """Atualiza animações e inputs do painel de feitiços, névoa, modal de token e toast de salvamento."""
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
            if self.toast_timer == 0:
                self.toast_message = None

        self.spell_aoe_panel.on_update(dt)
        self.fog_panel.fog_manager = self.combat_manager.fog_manager
        self.fog_panel.on_update(dt)
        self.add_token_modal.on_update(dt)
