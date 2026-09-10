import os
import shutil
import tempfile
import unittest
import logging
from pathlib import Path

from src.utils.logger import setup_logging, get_logger


class TestLogger(unittest.TestCase):
    """Testes unitários para o sistema de logging centralizado do Medusa VTT."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_logs", "medusa.log")

    def tearDown(self):
        # Remove handlers antes de deletar diretório temporário
        root = logging.getLogger()
        for h in list(root.handlers):
            h.close()
            root.removeHandler(h)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_setup_logging_creates_file_and_logs_messages(self):
        setup_logging(level=logging.INFO, log_file=self.log_file)
        logger = get_logger("TestModule")

        msg = "Teste de log com acentuação: Ação e Coração 🐉"
        logger.info(msg)

        self.assertTrue(os.path.isfile(self.log_file))

        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[INFO]", content)
        self.assertIn("[TestModule]", content)
        self.assertIn(msg, content)

    def test_setup_logging_debug_flag(self):
        setup_logging(log_file=self.log_file, debug=True)
        logger = get_logger("DebugModule")

        debug_msg = "Mensagem de depuração DEBUG"
        logger.debug(debug_msg)

        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[DEBUG]", content)
        self.assertIn(debug_msg, content)

    def test_renderers_emit_zero_logs_during_draw_loop(self):
        """
        Regra Pétrea (PREMISES.md - Seção 1):
        Logs NÃO DEVEM ser criados dentro de loops executados no loop principal do Arcade (60FPS).
        Garante que PlayerViewRenderer e MiniMapRenderer não emitam nenhum log durante ciclos de desenho.
        """
        from src.manager.session_manager import SessionManager, DisplayState
        from src.ui.renderers.player_view_renderer import PlayerViewRenderer
        from src.ui.renderers.minimap_renderer import MiniMapRenderer
        from src.ui.components.grid_cell_highlighter import GridCellHighlighter
        from src.ui.initiative_hud import InitiativeHUD
        from src.domain.models.entity import DynamicToken, EntityType
        from src.domain.models.spell_template import SpellTemplate, SpellShape

        setup_logging(level=logging.INFO, log_file=self.log_file)

        sm = SessionManager()
        sm.set_display_state(DisplayState.COMBAT)
        cm = sm.combat_manager
        p = DynamicToken(name="Artemis", max_hp=20, armor_class=14, speed=30, entity_type=EntityType.PLAYER)
        cm.spawn_combatant(p, (3, 3))
        cm.start_combat()

        aoe_hl = GridCellHighlighter(grid_manager=cm.grid_manager)
        mov_hl = GridCellHighlighter(grid_manager=cm.grid_manager)
        hud = InitiativeHUD(cm)

        # Configura um manipulador de captura para inspecionar logs emitidos
        class LogCaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)

        capture_handler = LogCaptureHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(capture_handler)

        import arcade
        window = arcade.Window(width=1280, height=720, visible=False)

        try:
            # Limpa qualquer log de setup prévio
            capture_handler.records.clear()

            # 1. Simula 60 frames de renderização do PlayerViewRenderer com Zona de Movimento Ativa
            for _ in range(60):
                PlayerViewRenderer.draw_combat(
                    window_width=1920,
                    window_height=1080,
                    combat_manager=cm,
                    texture_cache={},
                    text_cache={},
                    tilemap_renderer=None,
                    aoe_highlighter=aoe_hl,
                    token_sprites={},
                    hud=hud,
                    movement_highlighter=mov_hl,
                    selected_target_cell=(3, 4),
                    selected_combatant_uid=p.uid,
                )

            # 2. Simula 60 frames de renderização do PlayerViewRenderer e MiniMapRenderer com Magia AoE Ativa
            tpl = SpellTemplate(shape=SpellShape.CIRCLE, size_feet=15.0, origin_world=(150.0, 150.0), is_active=True)
            cm.set_spell_template(tpl)

            for _ in range(60):
                PlayerViewRenderer.draw_combat(
                    window_width=1920,
                    window_height=1080,
                    combat_manager=cm,
                    texture_cache={},
                    text_cache={},
                    tilemap_renderer=None,
                    aoe_highlighter=aoe_hl,
                    token_sprites={},
                    hud=hud,
                    movement_highlighter=mov_hl,
                )
                MiniMapRenderer.draw_content(
                    window_width=1920,
                    window_height=1080,
                    draw_rect=(0, 0, 960, 1080),
                    session_manager=sm,
                    texture_cache={},
                    text_cache={},
                    tilemap_renderer=None,
                    aoe_highlighter=aoe_hl,
                    movement_highlighter=mov_hl,
                )

            # Validação: Nenhum log deve ter sido emitido durante todos os 180 frames de renderização
            render_logs = [
                r.getMessage()
                for r in capture_handler.records
                if "PlayerViewRenderer" in r.name
                or "MiniMapRenderer" in r.name
                or "PlayerViewRenderer" in r.getMessage()
                or "MiniMapRenderer" in r.getMessage()
            ]
            self.assertEqual(
                render_logs,
                [],
                f"Violação de PREMISES.md: Logs foram emitidos durante o loop de renderização (60FPS): {render_logs}"
            )
        finally:
            root_logger.removeHandler(capture_handler)
            try:
                window.close()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()

