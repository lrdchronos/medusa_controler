import sys
from pathlib import Path
import tkinter as tk
import arcade

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.session_manager import SessionManager, DisplayState
from src.ui.dm_window import DMWindow
from src.ui.player_window import PlayerWindow


def main() -> None:
    print("=" * 60)
    print("🐉 MEDUSA VTT - SISTEMA DE COMBATE E MESA DIGITAL D&D 5E")
    print("=" * 60)

    # 1. Inicialização do SessionManager no estado inicial IDLE
    session_manager = SessionManager()
    print("[OK] SessionManager inicializado no estado DisplayState.IDLE.")

    # 2. Inicialização da Tela do Mestre (DMWindow - Tkinter com Abas e Dashboard)
    tk_root = tk.Tk()
    dm_window = DMWindow(root=tk_root, session_manager=session_manager)

    # 3. Inicialização da Tela dos Jogadores (PlayerWindow - Arcade)
    player_window = PlayerWindow(
        session_manager=session_manager,
        dm_window=dm_window,
        width=1024,
        height=768,
        title="Medusa VTT - Tela dos Jogadores",
    )

    # 4. Configuração de Encerramento Limpo Sincronizado
    def on_close_all() -> None:
        try:
            tk_root.destroy()
        except Exception:
            pass
        arcade.exit()

    tk_root.protocol("WM_DELETE_WINDOW", on_close_all)

    # 5. Execução do Loop Principal
    print("\n[OK] Janelas ativas: Tela do Mestre (Dashboard com Abas) e Tela dos Jogadores (PlayerWindow).")
    print("Utilize o painel do Mestre para projetar mídias ou iniciar um encontro!\n")
    arcade.run()


if __name__ == "__main__":
    main()
