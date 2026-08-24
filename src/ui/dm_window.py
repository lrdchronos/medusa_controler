import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List, Dict, Any
from pathlib import Path
from ..manager.session_manager import SessionManager, DisplayState
from ..domain.models.playablechar import PlayableCharacter
from ..domain.models.monster import Monster
from ..domain.models.entity import Entity


class DMWindow:
    """
    Tela do Mestre (DMWindow) do Medusa VTT.
    Dashboard central de controle com suporte a 3 abas principais:
      1. '📋 Preparações / Encontros': Seleção e inicialização de encontros.
      2. '🖼️ Projetor de Imagens (Showcase)': Projeção de mídias e controle de espera.
      3. '⚔️ Combate Ativo': Roster, iniciativas, turnos e despachante de dano/cura.
    """

    def __init__(self, root: tk.Tk, session_manager: SessionManager) -> None:
        self.root = root
        self.session_manager = session_manager
        self.combat_manager = session_manager.combat_manager

        self.selected_combatant_uid: Optional[str] = None
        self.selected_encounter_path: Optional[str] = None
        self.selected_showcase_path: Optional[str] = None

        self._init_window()
        self._apply_dark_theme()
        self._build_widgets()

        # Inscreve listener para reatividade total
        self.session_manager.add_listener(self.refresh_ui)
        self.refresh_ui()

    def _init_window(self) -> None:
        self.root.title("Medusa VTT - Painel de Controle do Mestre (DM Screen)")
        self.root.geometry("860x680")
        self.root.minsize(780, 580)
        self.root.configure(bg="#181A20")

    def _apply_dark_theme(self) -> None:
        """Aplica estilo escuro aos componentes ttk."""
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

        self.bg_color = "#181A20"
        self.card_bg = "#222630"
        self.accent_gold = "#F1C40F"
        self.accent_blue = "#3498DB"
        self.accent_red = "#E74C3C"
        self.accent_green = "#2ECC71"
        self.fg_color = "#ECEFF4"

        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=self.card_bg, foreground=self.fg_color, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=self.bg_color, foreground=self.accent_gold, font=("Segoe UI", 12, "bold"))
        self.style.configure("SubHeader.TLabel", background=self.card_bg, foreground=self.fg_color, font=("Segoe UI", 10, "bold"))

        # Notebook / Abas
        self.style.configure(
            "TNotebook",
            background=self.bg_color,
            borderwidth=0,
        )
        self.style.configure(
            "TNotebook.Tab",
            background="#252A36",
            foreground="#B0BAC8",
            font=("Segoe UI", 10, "bold"),
            padding=[16, 8],
            borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#2F3646"), ("active", "#3A4458")],
            foreground=[("selected", self.accent_gold), ("active", "#FFFFFF")],
        )

        # Treeviews
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
        main_container = ttk.Frame(self.root, style="TFrame", padding=12)
        main_container.pack(fill=tk.BOTH, expand=True)

        # --- 1. CABEÇALHO GLOBAL COM STATUS DA PLAYER WINDOW ---
        header_frame = ttk.Frame(main_container, style="TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_lbl = ttk.Label(
            header_frame,
            text="🐉 MEDUSA VTT  •  PAINEL DO MESTRE",
            style="Header.TLabel",
        )
        title_lbl.pack(side=tk.LEFT)

        # Badge de Estado Atual da PlayerWindow
        self.state_badge = tk.Label(
            header_frame,
            text="[ IDLE: Espera ]",
            font=("Segoe UI", 9, "bold"),
            bg="#2C3E50",
            fg="#F1C40F",
            padx=10,
            pady=4,
            relief="flat",
        )
        self.state_badge.pack(side=tk.RIGHT, padx=4)

        # Botão de retorno rápido a IDLE no topo
        btn_quick_idle = tk.Button(
            header_frame,
            text="🏠 Tela de Espera",
            font=("Segoe UI", 8, "bold"),
            bg="#34495E",
            fg="#FFFFFF",
            relief="flat",
            padx=8,
            pady=3,
            command=self.session_manager.clear_display_to_idle,
        )
        btn_quick_idle.pack(side=tk.RIGHT, padx=4)

        # --- 2. NOTEBOOK / ABAS DE NAVEGAÇÃO ---
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Aba 1: Preparações / Seletor de Encontros
        self.tab_encounters = ttk.Frame(self.notebook, style="TFrame", padding=8)
        self.notebook.add(self.tab_encounters, text="📋 Preparações / Encontros")
        self._build_encounters_tab(self.tab_encounters)

        # Aba 2: Projetor de Imagens (Showcase)
        self.tab_showcase = ttk.Frame(self.notebook, style="TFrame", padding=8)
        self.notebook.add(self.tab_showcase, text="🖼️ Projetor de Imagens (Showcase)")
        self._build_showcase_tab(self.tab_showcase)

        # Aba 3: Combate Ativo
        self.tab_combat = ttk.Frame(self.notebook, style="TFrame", padding=8)
        self.notebook.add(self.tab_combat, text="⚔️ Combate Ativo")
        self._build_combat_tab(self.tab_combat)

    # --- ABA 1: PREPARAÇÕES / SELETOR DE ENCONTROS ---

    def _build_encounters_tab(self, parent: ttk.Frame) -> None:
        top_bar = ttk.Frame(parent, style="Card.TFrame", padding=8)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        lbl = ttk.Label(
            top_bar,
            text="Selecione um Encontro salvo na pasta creations/encounters/ para carregar na mesa:",
            style="Card.TLabel",
        )
        lbl.pack(side=tk.LEFT)

        btn_reload = tk.Button(
            top_bar,
            text="🔄 Atualizar Lista",
            font=("Segoe UI", 9),
            bg="#2F3646",
            fg="#ECEFF4",
            relief="flat",
            padx=8,
            pady=4,
            command=self.populate_encounters_list,
        )
        btn_reload.pack(side=tk.RIGHT)

        # Split: Lista à esquerda e Detalhes à direita
        split_frame = ttk.Frame(parent, style="TFrame")
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Tabela de Encontros
        enc_cols = ("title", "combatants", "map", "file")
        self.tree_encounters = ttk.Treeview(
            split_frame,
            columns=enc_cols,
            show="headings",
            selectmode="browse",
            height=8,
        )
        self.tree_encounters.heading("title", text="Título do Encontro")
        self.tree_encounters.heading("combatants", text="Combatentes")
        self.tree_encounters.heading("map", text="Mapa")
        self.tree_encounters.heading("file", text="Arquivo")

        self.tree_encounters.column("title", width=220, anchor="w")
        self.tree_encounters.column("combatants", width=90, anchor="center")
        self.tree_encounters.column("map", width=180, anchor="w")
        self.tree_encounters.column("file", width=140, anchor="w")

        self.tree_encounters.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_encounters.bind("<<TreeviewSelect>>", self.on_encounter_selected)

        # Painel de Detalhes e Ação
        details_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        details_frame.pack(fill=tk.X)

        self.enc_detail_title = ttk.Label(
            details_frame,
            text="Encontro Selecionado: (Nenhum)",
            style="SubHeader.TLabel",
            foreground=self.accent_gold,
        )
        self.enc_detail_title.pack(anchor="w")

        self.enc_detail_desc = ttk.Label(
            details_frame,
            text="Selecione um encontro acima para visualizar os detalhes.",
            style="Card.TLabel",
            wraplength=700,
        )
        self.enc_detail_desc.pack(anchor="w", pady=(4, 8))

        self.btn_start_encounter = tk.Button(
            details_frame,
            text="🚀 Iniciar Encontro na Tela dos Jogadores",
            font=("Segoe UI", 11, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            activebackground="#2ECC71",
            relief="flat",
            padx=16,
            pady=8,
            command=self.on_start_encounter_clicked,
        )
        self.btn_start_encounter.pack(side=tk.LEFT)

    # --- ABA 2: PROJETOR DE IMAGENS (SHOWCASE) ---

    def _build_showcase_tab(self, parent: ttk.Frame) -> None:
        top_bar = ttk.Frame(parent, style="Card.TFrame", padding=8)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        lbl = ttk.Label(
            top_bar,
            text="Projete artes de NPCs, mapas regionais, paisagens ou itens na tela dos jogadores:",
            style="Card.TLabel",
        )
        lbl.pack(side=tk.LEFT)

        btn_browse = tk.Button(
            top_bar,
            text="📁 Procurar Imagem no Computador...",
            font=("Segoe UI", 9, "bold"),
            bg="#3498DB",
            fg="#FFFFFF",
            relief="flat",
            padx=10,
            pady=4,
            command=self.on_browse_custom_image,
        )
        btn_browse.pack(side=tk.RIGHT, padx=4)

        btn_reload_showcase = tk.Button(
            top_bar,
            text="🔄 Atualizar",
            font=("Segoe UI", 9),
            bg="#2F3646",
            fg="#ECEFF4",
            relief="flat",
            padx=8,
            pady=4,
            command=self.populate_showcase_list,
        )
        btn_reload_showcase.pack(side=tk.RIGHT, padx=4)

        # Tabela de Imagens
        img_cols = ("name", "category", "file")
        self.tree_showcase = ttk.Treeview(
            parent,
            columns=img_cols,
            show="headings",
            selectmode="browse",
            height=10,
        )
        self.tree_showcase.heading("name", text="Nome da Mídia")
        self.tree_showcase.heading("category", text="Categoria / Pasta")
        self.tree_showcase.heading("file", text="Arquivo")

        self.tree_showcase.column("name", width=250, anchor="w")
        self.tree_showcase.column("category", width=140, anchor="center")
        self.tree_showcase.column("file", width=250, anchor="w")

        self.tree_showcase.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.tree_showcase.bind("<<TreeviewSelect>>", self.on_showcase_selected)

        # Controles de Projeção
        action_box = ttk.Frame(parent, style="Card.TFrame", padding=10)
        action_box.pack(fill=tk.X)

        self.showcase_selected_lbl = ttk.Label(
            action_box,
            text="Imagem Selecionada: (Nenhuma)",
            style="SubHeader.TLabel",
        )
        self.showcase_selected_lbl.pack(anchor="w", pady=(0, 8))

        btn_project = tk.Button(
            action_box,
            text="🖼️ Projetar na Tela dos Jogadores",
            font=("Segoe UI", 11, "bold"),
            bg="#8E44AD",
            fg="#FFFFFF",
            activebackground="#9B59B6",
            relief="flat",
            padx=14,
            pady=7,
            command=self.on_project_image_clicked,
        )
        btn_project.pack(side=tk.LEFT, padx=(0, 8))

        btn_idle = tk.Button(
            action_box,
            text="🏠 Voltar para Tela de Espera (IDLE)",
            font=("Segoe UI", 10),
            bg="#34495E",
            fg="#ECEFF4",
            relief="flat",
            padx=12,
            pady=7,
            command=self.session_manager.clear_display_to_idle,
        )
        btn_idle.pack(side=tk.LEFT)

    # --- ABA 3: COMBATE ATIVO ---

    def _build_combat_tab(self, parent: ttk.Frame) -> None:
        # 1. Barra de Ação Superior
        toolbar = ttk.Frame(parent, style="Card.TFrame", padding=8)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        self.btn_roll_init = tk.Button(
            toolbar,
            text="🎲 Rolar Iniciativas",
            font=("Segoe UI", 10, "bold"),
            bg="#D4AC0D",
            fg="#181A20",
            activebackground="#F1C40F",
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
            relief="flat",
            padx=8,
            pady=6,
            command=self.on_prev_turn,
        )
        self.btn_prev_turn.pack(side=tk.LEFT, padx=4)

        # Botão de Finalizar Combate
        self.btn_end_combat = tk.Button(
            toolbar,
            text="🏁 Finalizar Combate",
            font=("Segoe UI", 9, "bold"),
            bg="#7B1FA2",
            fg="#FFFFFF",
            activebackground="#9C27B0",
            relief="flat",
            padx=10,
            pady=6,
            command=self.on_end_combat_clicked,
        )
        self.btn_end_combat.pack(side=tk.RIGHT, padx=4)

        self.active_turn_info = ttk.Label(
            toolbar,
            text="Turno Ativo: -",
            style="SubHeader.TLabel",
            foreground=self.accent_gold,
        )
        self.active_turn_info.pack(side=tk.RIGHT, padx=8)

        # 2. Tabela de Combatentes
        roster_frame = ttk.Frame(parent, style="TFrame")
        roster_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        columns = ("turn", "name", "type", "hp", "ac", "init_mod", "init_score", "status")
        self.tree_combatants = ttk.Treeview(
            roster_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree_combatants.heading("turn", text="Turno")
        self.tree_combatants.heading("name", text="Nome / Instância")
        self.tree_combatants.heading("type", text="Tipo")
        self.tree_combatants.heading("hp", text="Vida (HP)")
        self.tree_combatants.heading("ac", text="CA")
        self.tree_combatants.heading("init_mod", text="Mod. DEX")
        self.tree_combatants.heading("init_score", text="Iniciativa")
        self.tree_combatants.heading("status", text="Status")

        self.tree_combatants.column("turn", width=65, anchor="center")
        self.tree_combatants.column("name", width=190, anchor="w")
        self.tree_combatants.column("type", width=85, anchor="center")
        self.tree_combatants.column("hp", width=110, anchor="center")
        self.tree_combatants.column("ac", width=55, anchor="center")
        self.tree_combatants.column("init_mod", width=80, anchor="center")
        self.tree_combatants.column("init_score", width=85, anchor="center")
        self.tree_combatants.column("status", width=95, anchor="center")

        scrollbar = ttk.Scrollbar(roster_frame, orient=tk.VERTICAL, command=self.tree_combatants.yview)
        self.tree_combatants.configure(yscrollcommand=scrollbar.set)

        self.tree_combatants.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_combatants.bind("<<TreeviewSelect>>", self.on_combatant_selected)

        # 3. Despachante Rápido de Dano e Cura
        dispatch_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        dispatch_frame.pack(fill=tk.X)

        self.selected_combatant_label = ttk.Label(
            dispatch_frame,
            text="Combatente Selecionado: (Nenhum)",
            style="SubHeader.TLabel",
        )
        self.selected_combatant_label.pack(anchor="w", pady=(0, 6))

        controls_box = ttk.Frame(dispatch_frame, style="Card.TFrame")
        controls_box.pack(fill=tk.X)

        # Dano
        ttk.Label(controls_box, text="DANO:", style="TLabel", foreground="#E74C3C", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        for val in [1, 5, 10, 20]:
            tk.Button(
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
            ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(controls_box, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Cura
        ttk.Label(controls_box, text="CURA:", style="TLabel", foreground="#2ECC71", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        for val in [1, 5, 10, 20]:
            tk.Button(
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
            ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(controls_box, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Custom
        ttk.Label(controls_box, text="Valor:", style="TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.custom_val_entry = tk.Entry(controls_box, width=6, bg="#2E3440", fg="#FFFFFF", insertbackground="#FFFFFF", relief="flat")
        self.custom_val_entry.insert(0, "8")
        self.custom_val_entry.pack(side=tk.LEFT, padx=2)

        tk.Button(
            controls_box,
            text="Dano",
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
            text="Cura",
            font=("Segoe UI", 8, "bold"),
            bg="#27AE60",
            fg="#FFFFFF",
            relief="flat",
            padx=5,
            pady=2,
            command=self.apply_custom_heal,
        ).pack(side=tk.LEFT, padx=2)

    # --- POPULADORES DE LISTAS ---

    def populate_encounters_list(self) -> None:
        self.tree_encounters.delete(*self.tree_encounters.get_children())
        encounters = self.session_manager.list_available_encounters()
        for enc in encounters:
            self.tree_encounters.insert(
                "",
                tk.END,
                iid=enc["path"],
                values=(
                    enc["title"],
                    f"{enc['combatants_count']} criaturas",
                    Path(enc["map_file"]).name,
                    enc["filename"],
                ),
            )
        if encounters and not self.selected_encounter_path:
            first = encounters[0]["path"]
            self.tree_encounters.selection_set(first)
            self.selected_encounter_path = first
            self.enc_detail_title.config(text=f"Encontro: {encounters[0]['title']}")
            self.enc_detail_desc.config(text=encounters[0]["description"])

    def populate_showcase_list(self) -> None:
        self.tree_showcase.delete(*self.tree_showcase.get_children())
        images = self.session_manager.list_available_showcase_images()
        for img in images:
            self.tree_showcase.insert(
                "",
                tk.END,
                iid=img["path"],
                values=(
                    img["name"],
                    img["category"],
                    img["filename"],
                ),
            )
        if images and not self.selected_showcase_path:
            first = images[0]["path"]
            self.tree_showcase.selection_set(first)
            self.selected_showcase_path = first
            self.showcase_selected_lbl.config(text=f"Imagem Selecionada: {images[0]['name']}")

    # --- HANDLERS DE EVENTOS ---

    def on_encounter_selected(self, event: Any) -> None:
        selected = self.tree_encounters.selection()
        if selected:
            path = selected[0]
            self.selected_encounter_path = path
            for enc in self.session_manager.list_available_encounters():
                if enc["path"] == path:
                    self.enc_detail_title.config(text=f"Encontro: {enc['title']} ({enc['combatants_count']} combatentes)")
                    self.enc_detail_desc.config(text=f"Descrição: {enc['description']}\nMapa: {enc['map_file']}")
                    break

    def on_start_encounter_clicked(self) -> None:
        if not self.selected_encounter_path:
            messagebox.showinfo("Medusa DM", "Selecione um encontro na lista antes de iniciar.")
            return
        self.session_manager.start_encounter(self.selected_encounter_path)
        # Alterna para a aba de combate ativo
        self.notebook.select(self.tab_combat)

    def on_showcase_selected(self, event: Any) -> None:
        selected = self.tree_showcase.selection()
        if selected:
            path = selected[0]
            self.selected_showcase_path = path
            self.showcase_selected_lbl.config(text=f"Imagem Selecionada: {Path(path).name}")

    def on_browse_custom_image(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecione uma Imagem para Projetar",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp"), ("Todos os Arquivos", "*.*")],
        )
        if file_path:
            self.selected_showcase_path = file_path
            self.showcase_selected_lbl.config(text=f"Imagem Selecionada: {Path(file_path).name}")
            self.on_project_image_clicked()

    def on_project_image_clicked(self) -> None:
        if not self.selected_showcase_path:
            messagebox.showinfo("Medusa DM", "Selecione uma imagem na lista ou procure um arquivo no computador.")
            return
        self.session_manager.project_image(self.selected_showcase_path)

    def on_end_combat_clicked(self) -> None:
        if messagebox.askyesno("Medusa DM", "Deseja encerrar o combate e retornar a tela dos jogadores para IDLE?"):
            self.session_manager.end_combat(DisplayState.IDLE)
            self.notebook.select(self.tab_encounters)

    def on_roll_initiatives(self) -> None:
        self.combat_manager.roll_initiatives()

    def on_next_turn(self) -> None:
        self.combat_manager.next_turn()

    def on_prev_turn(self) -> None:
        self.combat_manager.previous_turn()

    def on_combatant_selected(self, event: Any) -> None:
        selected_items = self.tree_combatants.selection()
        if selected_items:
            item_id = selected_items[0]
            self.selected_combatant_uid = item_id
            combatant = self.combat_manager.get_combatant(item_id)
            if combatant:
                self.selected_combatant_label.config(
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
            messagebox.showwarning("Medusa DM", "Insira um número válido.")

    def apply_custom_heal(self) -> None:
        try:
            val = int(self.custom_val_entry.get().strip())
            self.apply_heal(val)
        except ValueError:
            messagebox.showwarning("Medusa DM", "Insira um número válido.")

    # --- REFRESH E ATUALIZAÇÃO REATIVA ---

    def refresh_ui(self) -> None:
        """Atualiza estado global e tabelas."""
        state = self.session_manager.display_state

        # 1. Badge de Estado Global
        if state == DisplayState.IDLE:
            self.state_badge.config(text="[ 🟢 IDLE: Tela de Espera ]", bg="#1B4D3E", fg="#A3E4D7")
        elif state == DisplayState.PROJECTION:
            proj_name = Path(self.session_manager.projected_image_path or "").stem
            self.state_badge.config(text=f"[ 🖼️ PROJEÇÃO: {proj_name[:16]} ]", bg="#4A235A", fg="#E8DAEF")
        elif state == DisplayState.COMBAT:
            enc_name = self.combat_manager.title[:16]
            self.state_badge.config(text=f"[ ⚔️ COMBATE: {enc_name} ]", bg="#78281F", fg="#F5B7B1")

        # 2. Atualiza Tabela de Combate Ativo
        active = self.combat_manager.active_character
        turn_order = self.combat_manager.turn_order
        active_index = self.combat_manager.current_turn_index
        round_num = self.combat_manager.round_number

        if active:
            self.active_turn_info.config(text=f"👉 Turno Ativo: {active.name} (R{round_num})")
        else:
            self.active_turn_info.config(text="Turno Ativo: (Não Iniciado)")

        selected = self.selected_combatant_uid
        self.tree_combatants.delete(*self.tree_combatants.get_children())
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

            self.tree_combatants.insert(
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

        if selected and self.tree_combatants.exists(selected):
            self.tree_combatants.selection_set(selected)
        elif display_list:
            first_uid = display_list[0].uid
            if self.tree_combatants.exists(first_uid):
                self.tree_combatants.selection_set(first_uid)
                self.selected_combatant_uid = first_uid
                self.selected_combatant_label.config(
                    text=f"Combatente Selecionado: {display_list[0].name} (HP: {display_list[0].current_hp}/{display_list[0].max_hp}, CA: {display_list[0].armor_class})"
                )

        # Popula listas de encontros e showcase se estiverem vazias
        if not self.tree_encounters.get_children():
            self.populate_encounters_list()
        if not self.tree_showcase.get_children():
            self.populate_showcase_list()

    def pump_events(self) -> None:
        """Bombeia os eventos do Tkinter de forma não-bloqueante no loop principal do Arcade."""
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            pass
