import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import arcade
from ....manager.grid_manager import GridManager
from ....domain.builders.encounter_builder import EncounterBuilder
from ....domain.models.tile_map import TileMap
from ....domain.models.fog_manager import FogManager
from ...utils.tilemap_renderer import TileMapRenderer
from ...components.discrete_scroll_list import DiscreteScrollList
from ..fog_control_panel import FogControlPanel
from .renderers.tactical_stage_renderer import TacticalStageRenderer
from .handlers.tactical_stage_input_handler import TacticalStageInputHandler

logger = logging.getLogger(__name__)


class CreatorTacticalStage:
    """
    Componente especializado para a Etapa 2 do Criador de Encontros (Palco Tático e Posicionamento).
    Gerencia:
      - Instanciação de tokens e persistência de encontros.
      - Estado de Staging, GridManager e FogManager.
      - Delegação de renderização para TacticalStageRenderer e eventos para TacticalStageInputHandler.
    """

    def __init__(self) -> None:
        self.config_data: Dict[str, Any] = {}
        self.staging_combatants: List[Dict[str, Any]] = []
        self.grid_manager: Optional[GridManager] = None
        self.tile_map: Optional[TileMap] = None
        self.tilemap_renderer: Optional[TileMapRenderer] = None

        self.scroll_list: DiscreteScrollList = DiscreteScrollList(item_height=28, spacing=4)

        # Gerenciamento de Névoa de Guerra no Palco Tático
        self.fog_manager: FogManager = FogManager()
        self.fog_panel: FogControlPanel = FogControlPanel(
            fog_manager=self.fog_manager,
            dimensions_provider=self._get_grid_dimensions,
            save_callback=self._handle_save_fog,
        )
        self._is_brushing: bool = False
        self._last_fog_cell: Optional[Tuple[int, int]] = None

        self.dragged_combatant_idx: Optional[int] = None
        self.drag_pos: Tuple[float, float] = (0.0, 0.0)

        self._last_map_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
        self._last_reserve_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)

        self._last_click_time: float = 0.0
        self._last_clicked_idx: Optional[int] = None

        self.is_editing: bool = False
        self.editing_uid: Optional[str] = None
        self.editing_filename: Optional[str] = None

        self.error_message: Optional[str] = None
        self.success_message: Optional[str] = None
        self.saved_encounter_path: Optional[str] = None

    def initialize(
        self,
        config_data: Dict[str, Any],
        available_characters: List[Dict[str, Any]],
        available_monsters: List[Dict[str, Any]],
        preset_combatants: Optional[List[Dict[str, Any]]] = None,
        is_editing: bool = False,
        editing_uid: Optional[str] = None,
        editing_filename: Optional[str] = None,
    ) -> None:
        """Configura o palco tático a partir dos dados consolidados do formulário ou de pré-carregamento."""
        self.config_data = config_data.copy()
        self.is_editing = is_editing
        self.editing_uid = editing_uid
        self.editing_filename = editing_filename
        self.error_message = None
        self.success_message = None
        self.saved_encounter_path = None
        self.dragged_combatant_idx = None
        self._is_brushing = False
        self._last_fog_cell = None

        # Carrega estado inicial de névoa se houver
        self.fog_manager.load_state(self.config_data.get("fog_of_war", []))

        map_type = self.config_data.get("map_type", "image")
        map_source = self.config_data.get("map_source") or self.config_data.get("map_path")
        columns = config_data.get("columns", 25)
        feet_per_square = config_data.get("feet_per_square", 5)

        if map_type == "tilemap" and map_source:
            try:
                self.tile_map = TileMap.from_file(map_source)
                self.tilemap_renderer = TileMapRenderer(tile_map=self.tile_map)
                self.grid_manager = GridManager(
                    map_width=self.tile_map.width * 32.0,
                    map_height=self.tile_map.height * 32.0,
                    columns=columns,
                    feet_per_square=feet_per_square,
                )
            except Exception as e:
                logger.error(f"Erro ao instanciar TileMap no CreatorTacticalStage: {e}")
                self.tile_map = None
                self.tilemap_renderer = None
                self.grid_manager = GridManager(
                    map_width=1920.0,
                    map_height=1080.0,
                    columns=columns,
                    feet_per_square=feet_per_square,
                )
        else:
            self.tile_map = None
            self.tilemap_renderer = None
            self.grid_manager = GridManager(
                map_width=1920.0,
                map_height=1080.0,
                columns=columns,
                feet_per_square=feet_per_square,
            )

        if preset_combatants is not None and len(preset_combatants) > 0:
            self.staging_combatants = [c.copy() for c in preset_combatants]
        else:
            self.staging_combatants = []

            # 1. Personagens Jogadores
            selected_uids = config_data.get("selected_character_uids", set())
            for char in available_characters:
                if char["uid"] in selected_uids:
                    self.staging_combatants.append({
                        "entity_type": "playable_character",
                        "character_id": char["uid"],
                        "monster_id": None,
                        "name": char["name"],
                        "is_player": True,
                        "is_hidden": False,
                        "placed": False,
                        "col": 0,
                        "row": 0,
                    })

            # 2. Monstros
            counts = config_data.get("monster_counts", {})
            for mon in available_monsters:
                mid = mon["uid"]
                qty = counts.get(mid, 0)
                base_name = mon["name"]
                for i in range(1, qty + 1):
                    instance_name = f"{base_name} {i}" if qty > 1 else base_name
                    self.staging_combatants.append({
                        "entity_type": "monster",
                        "character_id": None,
                        "monster_id": mid,
                        "name": instance_name,
                        "is_player": False,
                        "is_hidden": False,
                        "placed": False,
                        "col": 0,
                        "row": 0,
                    })

        self.scroll_list.items = self.staging_combatants
        self.scroll_list.reset_scroll()

        logger.info(
            f"CreatorTacticalStage inicializado com {len(self.staging_combatants)} combatentes para o mapa '{config_data.get('map_name')}' (Tipo: {map_type}, Edição: {self.is_editing})."
        )

    def save_encounter(
        self,
        directory: str = "creations/encounters",
        uid: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Optional[Path]:
        """Serializa e grava o encontro no disco (preservando UID se em modo de edição)."""
        self.error_message = None
        self.success_message = None

        if not self.staging_combatants:
            self.error_message = "Nenhum combatente presente para salvar o encontro!"
            return None

        # Posiciona automaticamente no grid tokens que ficaram na reserva
        columns = self.config_data.get("columns", 25)
        rows = self.grid_manager.rows if self.grid_manager else 14

        for idx, item in enumerate(self.staging_combatants):
            if not item.get("placed", False):
                item["col"] = idx % columns
                item["row"] = (idx // columns) if item.get("is_player", False) else (rows - 1 - (idx // columns))
                item["placed"] = True

        target_uid = uid or self.editing_uid or self.config_data.get("uid")

        builder = EncounterBuilder()
        builder.with_metadata(
            title=self.config_data.get("title", "Novo Encontro"),
            description=self.config_data.get("description", ""),
            uid=target_uid,
        )
        map_type = self.config_data.get("map_type", "image")
        map_source = self.config_data.get("map_source") or self.config_data.get("map_path", "assets/images/maps/open_field_grass_trees.jpg")
        builder.with_map(map_source=map_source, map_type=map_type)
        builder.with_grid(
            columns=columns,
            feet_per_square=self.config_data.get("feet_per_square", 5),
        )
        builder.with_environment(is_sunlight=self.config_data.get("is_sunlight", False))
        builder.with_fog_of_war(self.fog_manager.export_state())

        for item in self.staging_combatants:
            if item.get("is_player", False):
                builder.add_character(
                    character_id=item["character_id"],
                    col=item["col"],
                    row=item["row"],
                    is_hidden=item.get("is_hidden", False),
                )
            else:
                builder.add_monster(
                    monster_id=item["monster_id"],
                    instance_name=item["name"],
                    col=item["col"],
                    row=item["row"],
                    is_hidden=item.get("is_hidden", False),
                )

        try:
            target_filename = filename or self.editing_filename or (f"{target_uid}.json" if target_uid else None)
            saved_path = builder.save_to_file(directory=directory, filename=target_filename)
            self.saved_encounter_path = str(saved_path)
            action_desc = "Alterações salvas" if self.is_editing else "Encontro salvo"
            self.success_message = f"{action_desc} com sucesso: {saved_path.name}"
            logger.info(f"Encontro gravado com sucesso em '{saved_path}' (UID: {target_uid}).")
            return saved_path
        except Exception as e:
            self.error_message = f"Erro ao salvar: {e}"
            logger.error(f"Falha ao persistir encontro via EncounterBuilder: {e}")
            return None

    # --- Renderização ---

    def draw_sidebar(self, panel_w: float, top_y: float, text_cache: Dict[str, arcade.Text]) -> None:
        TacticalStageRenderer.draw_sidebar(self, panel_w, top_y, text_cache)

    def draw_canvas(
        self,
        vx: float,
        vy: float,
        vw: float,
        vh: float,
        text_cache: Dict[str, arcade.Text],
        texture_cache: Dict[str, arcade.Texture],
    ) -> None:
        TacticalStageRenderer.draw_canvas(self, vx, vy, vw, vh, text_cache, texture_cache)

    def _render_text(
        self,
        key: str,
        text: str,
        x: float,
        y: float,
        color: tuple,
        font_size: int,
        bold: bool,
        cache: Dict[str, arcade.Text],
        anchor_x: str = "left",
    ) -> None:
        TacticalStageRenderer.render_text(key, text, x, y, color, font_size, bold, cache, anchor_x=anchor_x)

    # --- Eventos ---

    def handle_mouse_press(self, x: float, y: float, split_x: float, h: float, button: int) -> Optional[str]:
        return TacticalStageInputHandler.handle_mouse_press(self, x, y, split_x, h, button)

    def handle_mouse_scroll(self, x: float, y: float, scroll_x: float, scroll_y: float) -> bool:
        return TacticalStageInputHandler.handle_mouse_scroll(self, x, y, scroll_x, scroll_y)

    def handle_mouse_drag(self, x: float, y: float) -> None:
        TacticalStageInputHandler.handle_mouse_drag(self, x, y)

    def handle_mouse_release(self, x: float, y: float, split_x: float) -> None:
        TacticalStageInputHandler.handle_mouse_release(self, x, y, split_x)

    def on_update(self, dt: float) -> None:
        self.fog_panel.on_update(dt)

    def _get_grid_dimensions(self) -> Tuple[int, int]:
        columns = self.config_data.get("columns", 25)
        rows = self.grid_manager.rows if self.grid_manager else 14
        return (columns, rows)

    def _handle_save_fog(self) -> bool:
        path = self.save_encounter()
        return path is not None
