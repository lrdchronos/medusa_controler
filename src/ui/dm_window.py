import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any
from ..manager.combat_manager import CombatManager
from ..domain.models.playablechar import PlayableCharacter
from ..domain.models.monster import Monster
from ..domain.models.entity import Entity


class DMWindow:
    """
    Tela do Mestre (DMWindow) do Medusa VTT.
    Interface rica em Dark Theme para o Dungeon Master com:
      - Roster detalhado de combatentes com HP, CA, Modificador e Iniciativa.
      - Botões centrais para 'Rolar Iniciativas' e 'Passar Turno'.
      - Despachante ágil para aplicar Dano e Cura ao participante selecionado.
      - Sincronização reativa e instantânea com a PlayerWindow.
    """

    def __init__(self, root: tk.Tk, combat_manager: CombatManager) -> None:
        self.root = root
        self.combat_manager = combat_manager
        self.selected_combatant_uid: Optional[str] = None

        self._init_window()
        self._apply_dark_theme()
        self._build_widgets()

        # Inscreve listener para atualização automática quando o modelo mudar
        self.combat_manager.add_listener(self.refresh_ui)
        self.refresh_ui()

    def _init_window(self) -> None:
        self.root.title("Medusa VTT - Painel de Controle do Mestre (DM Screen)")
        self.root.geometry("780x620")
        self.root.minsize(700, 520)
        self.root.configure(bg="#181A20")

    def _apply_dark_theme(self) -> None:
        """Aplica estilo moderno escuro aos componentes ttk."""
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        # Configurações globais de cores
        self.bg_color = "#181A20"
        self.card_bg = "#222630"
        self.accent_gold = "#F1C40F"
        self.accent_blue = "#3498DB"
        self.accent_red = "#E74C3C"
        self.accent_green = "#2ECC71"
        self.fg_color = "#ECEFF4"

        self.style.configure(
            "TFrame",
            background=self.bg_color,
        )
        self.style.configure(
            "Card.TFrame",
            background=self.card_bg,
            relief="flat",
        )
        self.style.configure(
            "TLabel",
            background=self.bg_color,
            foreground=self.fg_color,
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Header.TLabel",
            background=self.bg_color,
            foreground=self.accent_gold,
            font=("Segoe UI", 12, "bold"),
        )
        self.style.configure(
            "SubHeader.TLabel",
            background=self.card_bg,
            foreground=self.fg_color,
            font=("Segoe UI", 10, "bold"),
        )

        # Botões de Ação
        self.style.configure(
            "Action.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=6,
        )
        self.style.configure(
            "Damage.TButton",
            font=("Segoe UI", 9, "bold"),
            foreground="#FFFFFF",
            background="#C0392B",
        )
        self.style.configure(
            "Heal.TButton",
            font=("Segoe UI", 9, "bold"),
            foreground="#FFFFFF",
            background="#27AE60",
        )

        # Treeview (Tabela de Combatentes)
        self.style.configure(
            "Treeview",
            background="#222630",
            foreground="#ECEFF4",
            fieldbackground="#222630",
            rowheight=28,
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Treeview.Heading",
            background="#2B303C",
            foreground=self.accent_gold,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#3A4458")],
            foreground=[("selected", "#FFFFFF")],
        )

    def _build_widgets(self) -> None:
        # Container Principal com padding
        main_container = ttk.Frame(self.root, style="TFrame", padding=12)
        main_container.pack(fill=tk.BOTH, expand=True)

        # --- 1. CABEÇALHO COM TÍTULO E STATUS DO ENCONTRO ---
        header_frame = ttk.Frame(main_container, style="TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        self.title_label = ttk.Label(
            header_frame,
            text=f"⚔️ {self.combat_manager.title}",
            style="Header.TLabel",
        )
        self.title_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(
            header_frame,
            text="Rodada 1 • Aguardando Iniciativas",
            style="TLabel",
            foreground="#A0A8B8",
        )
        self.status_label.pack(side=tk.RIGHT)

        # --- 2. BARRA DE COMANDO DO MESTRE (BOTÕES PRINCIPAIS) ---
        toolbar = ttk.Frame(main_container, style="Card.TFrame", padding=8)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        self.btn_roll_init = tk.Button(
            toolbar,
            text="🎲 Rolar Iniciativas",
            font=("Segoe UI", 10, "bold"),
            bg="#D4AC0D",
            fg="#181A20",
            activebackground="#F1C40F",
            activeforeground="#000000",
            relief="flat",
            padx=12,
            pady=6,
            command=self.on_roll_initiatives,
        )
        self.btn_roll_init.pack(side=tk.LEFT, padx=4)

        self.btn_next_turn = tk.Button(
            toolbar,
            text="⏭️ Passar Turno",
            font=("Segoe UI", 10, "bold"),
            bg="#2980B9",
            fg="#FFFFFF",
            activebackground="#3498DB",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=6,
            command=self.on_next_turn,
        )
        self.btn_next_turn.pack(side=tk.LEFT, padx=4)

        self.btn_prev_turn = tk.Button(
            toolbar,
            text="⏮️ Turno Anterior",
            font=("Segoe UI", 9),
            bg="#34495E",
            fg="#ECEFF4",
            activebackground="#4A6572",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=8,
            pady=6,
            command=self.on_prev_turn,
        )
        self.btn_prev_turn.pack(side=tk.LEFT, padx=4)

        self.active_turn_info = ttk.Label(
            toolbar,
            text="Turno Ativo: -",
            style="SubHeader.TLabel",
            foreground=self.accent_gold,
        )
        self.active_turn_info.pack(side=tk.RIGHT, padx=8)

        # --- 3. ROSTER / TABELA DE PARTICIPANTES ---
        roster_frame = ttk.Frame(main_container, style="TFrame")
        roster_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("turn", "name", "type", "hp", "ac", "init_mod", "init_score", "status")
        self.tree = ttk.Treeview(
            roster_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("turn", text="Turno")
        self.tree.heading("name", text="Nome / Instância")
        self.tree.heading("type", text="Tipo")
        self.tree.heading("hp", text="Vida (HP)")
        self.tree.heading("ac", text="CA")
        self.tree.heading("init_mod", text="Mod. DEX")
        self.tree.heading("init_score", text="Iniciativa")
        self.tree.heading("status", text="Status")

        self.tree.column("turn", width=65, anchor="center")
        self.tree.column("name", width=190, anchor="w")
        self.tree.column("type", width=85, anchor="center")
        self.tree.column("hp", width=110, anchor="center")
        self.tree.column("ac", width=55, anchor="center")
        self.tree.column("init_mod", width=80, anchor="center")
        self.tree.column("init_score", width=85, anchor="center")
        self.tree.column("status", width=95, anchor="center")

        # Scrollbar vertical
        scrollbar = ttk.Scrollbar(roster_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_combatant_selected)

        # --- 4. DESPACHANTE RÁPIDO DE DANO E CURA ---
        dispatch_frame = ttk.Frame(main_container, style="Card.TFrame", padding=10)
        dispatch_frame.pack(fill=tk.X)

        self.selected_label = ttk.Label(
            dispatch_frame,
            text="Combatente Selecionado: (Nenhum)",
            style="SubHeader.TLabel",
        )
        self.selected_label.pack(anchor="w", pady=(0, 6))

        controls_box = ttk.Frame(dispatch_frame, style="Card.TFrame")
        controls_box.pack(fill=tk.X)

        # Seção de Dano
        dmg_label = ttk.Label(controls_box, text="DANO:", style="TLabel", foreground="#E74C3C", font=("Segoe UI", 9, "bold"))
        dmg_label.pack(side=tk.LEFT, padx=(0, 6))

        for val in [1, 5, 10, 20]:
            btn = tk.Button(
                controls_box,
                text=f"-{val}",
                font=("Segoe UI", 9, "bold"),
                bg="#922B21",
                fg="#FFFFFF",
                activebackground="#C0392B",
                relief="flat",
                padx=6,
                pady=3,
                command=lambda v=val: self.apply_damage(v),
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Divisor visual
        ttk.Separator(controls_box, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        # Seção de Cura
        heal_label = ttk.Label(controls_box, text="CURA:", style="TLabel", foreground="#2ECC71", font=("Segoe UI", 9, "bold"))
        heal_label.pack(side=tk.LEFT, padx=(0, 6))

        for val in [1, 5, 10, 20]:
            btn = tk.Button(
                controls_box,
                text=f"+{val}",
                font=("Segoe UI", 9, "bold"),
                bg="#1E8449",
                fg="#FFFFFF",
                activebackground="#27AE60",
                relief="flat",
                padx=6,
                pady=3,
                command=lambda v=val: self.apply_heal(v),
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Divisor visual
        ttk.Separator(controls_box, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        # Entrada Customizada
        ttk.Label(controls_box, text="Valor:", style="TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.custom_val_entry = tk.Entry(controls_box, width=6, bg="#2E3440", fg="#FFFFFF", insertbackground="#FFFFFF", relief="flat")
        self.custom_val_entry.insert(0, "8")
        self.custom_val_entry.pack(side=tk.LEFT, padx=2)

        tk.Button(
            controls_box,
            text="Aplicar Dano",
            font=("Segoe UI", 8, "bold"),
            bg="#C0392B",
            fg="#FFFFFF",
            relief="flat",
            padx=5,
            pady=2,
            command=self.apply_custom_damage,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            controls_box,
            text="Aplicar Cura",
            font=("Segoe UI", 8, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            relief="flat",
            padx=5,
            pady=2,
            command=self.apply_custom_heal,
        ).pack(side=tk.LEFT, padx=2)

    # --- Handlers de Ações do Mestre ---

    def on_roll_initiatives(self) -> None:
        self.combat_manager.roll_initiatives()

    def on_next_turn(self) -> None:
        self.combat_manager.next_turn()

    def on_prev_turn(self) -> None:
        self.combat_manager.previous_turn()

    def on_combatant_selected(self, event: Any) -> None:
        selected_items = self.tree.selection()
        if selected_items:
            item_id = selected_items[0]
            self.selected_combatant_uid = item_id
            combatant = self.combat_manager.get_combatant(item_id)
            if combatant:
                self.selected_label.config(
                    text=f"Combatente Selecionado: {combatant.name} (HP: {combatant.current_hp}/{combatant.max_hp}, CA: {combatant.armor_class})"
                )

    def apply_damage(self, amount: int) -> None:
        if not self.selected_combatant_uid:
            messagebox.showinfo("Medusa DM", "Selecione um combatente na tabela para aplicar dano.")
            return
        self.combat_manager.apply_damage(self.selected_combatant_uid, amount)

    def apply_heal(self, amount: int) -> None:
        if not self.selected_combatant_uid:
            messagebox.showinfo("Medusa DM", "Selecione um combatente na tabela para aplicar cura.")
            return
        self.combat_manager.apply_heal(self.selected_combatant_uid, amount)

    def apply_custom_damage(self) -> None:
        try:
            val = int(self.custom_val_entry.get().strip())
            self.apply_damage(val)
        except ValueError:
            messagebox.showwarning("Medusa DM", "Por favor insira um valor numérico válido.")

    def apply_custom_heal(self) -> None:
        try:
            val = int(self.custom_val_entry.get().strip())
            self.apply_heal(val)
        except ValueError:
            messagebox.showwarning("Medusa DM", "Por favor insira um valor numérico válido.")

    # --- Sincronização e Renderização Reativa ---

    def refresh_ui(self) -> None:
        """Atualiza todos os dados da interface com base no estado do CombatManager."""
        active = self.combat_manager.active_character
        turn_order = self.combat_manager.turn_order
        active_index = self.combat_manager.current_turn_index
        round_num = self.combat_manager.round_number

        # Status text
        if active:
            self.status_label.config(text=f"Rodada {round_num} • Em Combate")
            self.active_turn_info.config(text=f"👉 Turno Ativo: {active.name}")
        else:
            self.status_label.config(text=f"Rodada {round_num} • Pré-Combate")
            self.active_turn_info.config(text="Turno Ativo: (Não Iniciado)")

        # Atualiza a tabela (Treeview)
        # Salva seleção atual
        selected = self.selected_combatant_uid

        self.tree.delete(*self.tree.get_children())

        display_list = turn_order if turn_order else self.combat_manager.combatants

        for idx, combatant in enumerate(display_list):
            is_active = (combatant == active) or (idx == active_index and active is not None)
            turn_mark = "▶ ATIVO" if is_active else f"#{idx + 1}"

            ctype = "Jogador" if isinstance(combatant, PlayableCharacter) else "Monstro"
            hp_str = f"{combatant.current_hp} / {combatant.max_hp}"
            if combatant.temp_hp > 0:
                hp_str += f" (+{combatant.temp_hp})"

            mod_sign = "+" if combatant.initiative_mod >= 0 else ""
            init_mod_str = f"{mod_sign}{combatant.initiative_mod}"
            init_score_str = str(combatant.initiative_score)

            if not combatant.is_alive:
                status_str = "💀 Abatido"
            elif is_active:
                status_str = "⚡ No Turno"
            else:
                status_str = "🟢 Pronto"

            self.tree.insert(
                "",
                tk.END,
                iid=combatant.uid,
                values=(
                    turn_mark,
                    combatant.name,
                    ctype,
                    hp_str,
                    combatant.armor_class,
                    init_mod_str,
                    init_score_str,
                    status_str,
                ),
            )

        # Restaura ou define seleção
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
        elif display_list:
            first_uid = display_list[0].uid
            if self.tree.exists(first_uid):
                self.tree.selection_set(first_uid)
                self.selected_combatant_uid = first_uid
                self.selected_label.config(
                    text=f"Combatente Selecionado: {display_list[0].name} (HP: {display_list[0].current_hp}/{display_list[0].max_hp}, CA: {display_list[0].armor_class})"
                )

    def pump_events(self) -> None:
        """Bombeia os eventos do Tkinter de forma não-bloqueante no loop principal do Arcade."""
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            pass
