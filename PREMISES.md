# 🏛️ MEDUSA VTT — Premissas Arquiteturais & Regras de Código (Vibe Coding)

Este arquivo define as leis universais e padrões técnicos do projeto Medusa. Toda alteração, refatoração ou novo módulo DEVE respeitar estas regras.

---

## 0. Linha de base do código
- **OOD sempre**: O código deve priorizar a orientação por objetos e o conceito de single responsibility. Em resumo: evitar código procedural espalhado
- **Modularização sempre**: O código deve ser modular e bem organizado. Evitar arquivos monolíticos e código espalhado. Separar responsabilidades.

---

## 1. Regras de Ouro da Arquitetura (Invioláveis)
- **Zero Tkinter:** Toda a UI do sistema (PlayerWindow e DMWindow) usa **Python Arcade e Arcade GUI (`arcade.gui`)**.
- **Zero `print()`:** Todas as saídas de terminal e depuração DEVEM usar o módulo padrão `logging` (`logger = logging.getLogger(__name__)`).
- **Encapsulamento Estrito:**
  - Atributos privados com duplo underscore (`self.__current_hp`).
  - Acesso público exclusivo via `@property` e `@setter` com validação defensiva (Poka-Yoke).
  - Dicionários e listas mutáveis retornam cópias defensivas (`return self.__resources.copy()`).
- **Data-Driven (Normalização de JSONs):**
  - Regras estáticas (dados de dano, fórmulas, descrições) ficam em `presets/`.
  - Estados dinâmicos e saves de entidades/encontros ficam em `creations/`.

---

## 2. Padrões de Renderização & UI (Arcade)
- **Criação de Sprites Obrigatória via `SpriteFactory`:**
  - NUNCA instancie texturas na mão no loop de desenho.
  - Use sempre o utilitário: `create_sprite(path, x, y, width, height, target_size, frame_count)`.
  - Sprites escalonados de pixel art DEVEM ser renderizados com `pixelated=True`.
- **Identidade Visual Dark Fantasy:**
  - Fundo principal: `#0E1218` (Azul escuro grafite).
  - Destaques / Acento: `#F1C40F` (Dourado místico).
  - Jogadores (PCs): Azul `#2980B9`.
  - Monstros (NPCs): Carmim / Vermelho `#C0392B`.
  - Suporte de texto rico: Utilize sempre o componente `SmartTextInput`.

---

## 3. Matemática de Grid e Câmeras (Tático)
- **Grid de Combate:** Baseado em colunas (padrão 25 colunas, 5ft por célula). O `GridManager` calcula `cell_size = W / columns` e `rows = ceil(H / cell_size)`.
- **Posicionamento de Tokens:** Movimentação com *Snap-to-Grid* alinhada no centro do quadrado (`grid_to_world_center(col, row)`).
- **Dupla Câmera:**
  - `PlayerCamera`: Renderização limpa em tela cheia na TV.
  - `DMCamera`: Mini-Mapa tático interativo de meia-tela com suporte a arrastar e soltar (Drag & Drop) e `camera.unproject()`.
- **Visibilidade:** Entidades com `is_hidden = True` aparecem com 50% de opacidade na tela do Mestre e NÃO são desenhadas na tela dos jogadores.

### 3.1. Arquitetura de Mapas & Runtime de Tilesets
- **Desacoplamento Visual vs. Lógico:**
  - Mapas modulares utilizam o padrão **Dual Grid / Runtime de Tilesets**: a arte é fatiada a partir de atlas/JSONs do Aseprite (`assets/tilesets/`), enquanto a matriz de dados define os índices das células.
  - **Dimensão Base dos Tiles:** Células de arte em $32 \times 32\text{px}$.
  - **Alinhamento do Grid D&D (5ft):** O centro do quadrado de combate recebe um deslocamento (*half-tile offset* de $16\text{px}$) via `GridManager.grid_to_world_center()` para garantir que tokens fiquem centralizados em estradas e corredores.
- **Hierarquia de Camadas (Layers):**
  - `Ground`: Renderizada em lote com uma única `arcade.SpriteList(use_spatial_hash=False)` e `pixelated=True`.
  - `Objects / Props`: Sprites com propriedades físicas e táticas indexadas matricialmente por `(col, row)`.
- **Propriedades Táticas do Terreno & Objetos:**
  - `blocks_movement` (`bool`): Impede passagem de entidades e trava o Snap-to-Grid.
  - `blocks_vision` (`bool`): Oclui cálculos de linha de visão (LoS) e Fog of War.
  - `cover_type`: Enum string (`"none"`, `"half"`, `"three_quarters"`, `"total"`) para cálculo automatizado de CA e Salvaguardas.
  - `difficult_terrain` (`bool`): Dobra o custo de deslocamento ($10\text{ft}$ por quadrado).
  - `height`: Altura do objeto em células (padrão 0) para cálculo de alcances lineares e sobreposições.
- **Consistência de Dados:**
  - Presets de tilesets e props estáticos residem em `presets/`.
  - Estruturas completas de mapas customizados e saves de encontro residem em `creations/`.
---

## 4. Testabilidade e Qualidade
- Todo novo loader, manager ou componente matemático DEVE conter testes unitários em `tests/`.
- Antes de concluir qualquer tarefa, a suíte de testes (`unittest`) precisa rodar e passar 100%.