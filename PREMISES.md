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

---

## 4. Testabilidade e Qualidade
- Todo novo loader, manager ou componente matemático DEVE conter testes unitários em `tests/`.
- Antes de concluir qualquer tarefa, a suíte de testes (`unittest`) precisa rodar e passar 100%.