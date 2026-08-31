import sys
import logging
from pathlib import Path
import arcade

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import setup_logging
from src.manager.session_manager import SessionManager, DisplayState
from src.ui.dm_window import DMWindow
from src.ui.player_window import PlayerWindow

logger = logging.getLogger("MedusaMain")


def main() -> None:
    setup_logging(level=logging.INFO)
    logger.info("🐉 MEDUSA VTT - SISTEMA DE COMBATE E MESA DIGITAL D&D 5E")

    # 1. Inicialização do SessionManager no estado inicial IDLE
    session_manager = SessionManager()
    logger.info("SessionManager inicializado no estado DisplayState.IDLE.")

    # 2. Inicialização da Tela do Mestre (DMWindow - Arcade GUI Nativo)
    dm_window = DMWindow(
        session_manager=session_manager,
        width=1280,
        height=768,
        title="Medusa VTT - Painel do Mestre (DM Screen)",
    )

    # 3. Inicialização da Tela dos Jogadores (PlayerWindow - Arcade)
    player_window = PlayerWindow(
        session_manager=session_manager,
        dm_window=dm_window,
        width=1024,
        height=768,
        title="Medusa VTT - Tela dos Jogadores",
    )

    # 4. Configuração de Encerramento Sincronizado
    def on_dm_close():
        try:
            player_window.close()
        except Exception:
            pass
        arcade.exit()

    def on_player_close():
        try:
            dm_window.close()
        except Exception:
            pass
        arcade.exit()

    dm_window.on_close = on_dm_close
    player_window.on_close = on_player_close

    # 5. Execução do Loop Principal
    logger.info("Janelas ativas: Tela do Mestre (DMWindow - Arcade GUI) e Tela dos Jogadores (PlayerWindow - Arcade).")
    logger.info("Utilize o painel do Mestre para projetar mídias, gerenciar iniciativas ou movimentar tokens no Grid!")
    arcade.run()


if __name__ == "__main__":
    main()
