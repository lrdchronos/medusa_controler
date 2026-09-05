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

    try:
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

        # 3. Inicialização da Tela dos Jogadores (PlayerWindow - Arcade com resizable=True)
        player_window = PlayerWindow(
            session_manager=session_manager,
            dm_window=dm_window,
            width=1024,
            height=768,
            title="Medusa VTT - Tela dos Jogadores",
        )
        dm_window.player_window = player_window

        # 4. Execução do Loop Principal
        logger.info("Janelas ativas: Tela do Mestre (DMWindow) e Tela dos Jogadores (PlayerWindow).")
        logger.info("Utilize o painel do Mestre para projetar mídias, gerenciar iniciativas ou movimentar tokens no Grid!")
        logger.info("Atalhos Globais: F10 = Abrir/Fechar Tela do Jogador | F11 = Alternar Tela Cheia (Fullscreen).")
        arcade.run()
    except Exception as e:
        logger.critical(f"Exceção fatal na execução da aplicação: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
