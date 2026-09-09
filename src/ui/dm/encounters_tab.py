import logging
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple
import arcade
from ...manager.session_manager import SessionManager
from ...domain.loaders.encounter_loader import EncounterLoader
from ..components.discrete_scroll_list import DiscreteScrollList
from .renderers.encounters_tab_renderer import EncountersTabRenderer
from .handlers.encounters_tab_input_handler import EncountersTabInputHandler

logger = logging.getLogger(__name__)


class EncountersTabView:
    """
    Componente da Aba de Encontros (Lista de arquivos JSON com DiscreteScrollList,
    detalhes, acionador de combate, edição e exclusão segura Poka-Yoke).
    Orquestra a renderização e eventos delegando para EncountersTabRenderer e EncountersTabInputHandler.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        dm_window: Optional[arcade.Window] = None,
    ) -> None:
        self.session_manager = session_manager
        self.dm_window = dm_window
        self.selected_index: int = 0
        self.encounters_list: List[Dict[str, Any]] = []
        self.text_cache: Dict[str, arcade.Text] = {}

        # Componente OOD de Paginação e Rolagem Discreta
        self.scroll_list: DiscreteScrollList = DiscreteScrollList(
            item_height=52,
            spacing=6,
        )

        # Estado do Modal de Confirmação de Exclusão (Poka-Yoke)
        self.pending_delete_encounter: Optional[Dict[str, Any]] = None

        # Estado do Modal de Retomada de Save (Save State)
        self.pending_resume_encounter: Optional[Dict[str, Any]] = None

        self.refresh()

    def refresh(self) -> None:
        """Recarrega a lista de arquivos de encontro disponíveis no diretório creations/encounters/."""
        self.encounters_list = self.session_manager.list_available_encounters()
        self.scroll_list.items = self.encounters_list
        if self.encounters_list and self.selected_index >= len(self.encounters_list):
            self.selected_index = max(0, len(self.encounters_list) - 1)

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

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        """Processa a rolagem discreta com a roda do mouse na lista de encontros."""
        if self.pending_delete_encounter is not None or self.pending_resume_encounter is not None:
            return True
        return self.scroll_list.on_mouse_scroll(x, y, scroll_x, scroll_y)

    def draw(self, panel_w: float, top_y: float) -> None:
        """Desenha a lista de encontros via EncountersTabRenderer."""
        EncountersTabRenderer.draw(self, panel_w, top_y)

    def handle_click(
        self,
        x: float,
        y: float,
        panel_w: float,
        top_y: float,
        on_start_combat_callback: Callable[[str], None],
        on_edit_encounter_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """Processa cliques na aba de encontros via EncountersTabInputHandler."""
        return EncountersTabInputHandler.handle_click(
            self,
            x,
            y,
            panel_w,
            top_y,
            on_start_combat_callback,
            on_edit_encounter_callback,
        )
