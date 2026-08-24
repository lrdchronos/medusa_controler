import sys
import os
from pathlib import Path
import tkinter as tk
import arcade

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.manager.combat_manager import CombatManager
from src.ui.dm_window import DMWindow
from src.ui.player_window import PlayerWindow


def main() -> None:
    print("=" * 60)
    print("🐉 MEDUSA VTT - SISTEMA DE COMBATE E MESA DIGITAL D&D 5E")
    print("=" * 60)

    # 1. Identificação do Encontro a ser Carregado
    encounter_target = sys.argv[1] if len(sys.argv) > 1 else "encounter_240820261511"

    # 2. Inicialização do CombatManager
    combat_manager = CombatManager()
    try:
        combat_manager.load_encounter(encounter_target)
        print(f"[OK] Encontro carregado com sucesso: '{combat_manager.title}'")
        print(f"[OK] Total de combatentes carregados: {len(combat_manager.combatants)}")
        for c in combat_manager.combatants:
            print(f"  • {c.name} ({c.__class__.__name__}) - HP: {c.current_hp}/{c.max_hp}, CA: {c.armor_class}, Mod DEX: {c.initiative_mod:+d}")
    except Exception as e:
        print(f"[AVISO] Falha ao carregar '{encounter_target}': {e}. Tentando 'encounter_01'...")
        combat_manager.load_encounter("encounter_01")

    # 3. Inicialização da Tela do Mestre (DMWindow - Tkinter)
    tk_root = tk.Tk()
    dm_window = DMWindow(root=tk_root, combat_manager=combat_manager)

    # 4. Inicialização da Tela dos Jogadores (PlayerWindow - Arcade)
    player_window = PlayerWindow(
        combat_manager=combat_manager,
        dm_window=dm_window,
        width=1024,
        height=768,
        title="Medusa VTT - Tela dos Jogadores",
    )

    # 5. Configuração de Encerramento Limpo Sincronizado
    def on_close_all() -> None:
        try:
            tk_root.destroy()
        except Exception:
            pass
        arcade.exit()

    tk_root.protocol("WM_DELETE_WINDOW", on_close_all)

    # 6. Execução do Loop Principal
    print("\n[OK] Janelas abertas: Tela do Mestre (DMWindow) e Tela dos Jogadores (PlayerWindow).")
    print("Pressione 'Rolar Iniciativas' no Mestre para ordenar a fila de combate!\n")
    arcade.run()


if __name__ == "__main__":
    main()
