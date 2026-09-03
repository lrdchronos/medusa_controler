# 🐉 Medusa VTT — Virtual Tabletop Local para D&D 5E

O **Medusa VTT** é uma plataforma local de *Virtual Tabletop* (Mesa Digital de RPG) desenvolvida em **Python** e **Python Arcade (3.0+)**, projetada para enriquecer sessões presenciais de **Dungeons & Dragons 5ª Edição (D&D 5E)**.

O sistema opera com uma arquitetura de **dupla janela simultânea** sincronizada em tempo real:
1. **Painel do Mestre (`DMWindow`):** Interface de controle tático e administrativo para o Dungeon Master no notebook ou monitor secundário, contendo gerenciamento de encontros, rolagem/staging de iniciativas, controle de visibilidade (névoa de guerra e tokens ocultos), aplicação ágil de dano e cura, assistente visual de criação de encontros e mini-mapa interativo com *Drag & Drop* e *Snap-to-Grid*.
2. **Tela dos Jogadores (`PlayerWindow`):** Viewport imersiva de alta performance projetada na TV da sala ou mesa digital, com renderização de mapas em tela cheia (*Aspect-Fill* ou engine de *Tilemaps* em lote na GPU), interpolação suave de movimento dos tokens (*Lerp*), fita de iniciativas flutuante em overlay translúcido (*InitiativeHUD*) com realce dourado pulsante e telas cinemáticas de descanso (*IDLE*) e projeção (*PROJECTION*).

---

## 📑 Sumário

- [Destaques e Funcionalidades](#-destaques-e-funcionalidades)
- [Arquitetura & Padrões de Projeto](#-arquitetura--padrões-de-projeto)
- [Estrutura Completa de Diretórios](#-estrutura-completa-de-diretórios)
- [Camadas do Sistema](#-camadas-do-sistema)
- [Normalização de Dados: presets/ vs creations/](#-normalização-de-dados-presets-vs-creations)
- [Engine de Tilemaps & Grade Tática](#-engine-de-tilemaps--grade-tática)
- [Guia de Instalação e Execução](#-guia-de-instalação-e-execução)
- [Suíte de Testes Automatizados](#-suíte-de-testes-automatizados)
- [Premissas e Regras de Código](#-premissas-e-regras-de-código)

---

## ✨ Destaques e Funcionalidades

- **Dupla Janela Sincronizada (Zero Latência):** Comunicação reativa via padrão *Observer*. Qualquer alteração efetuada pelo Mestre reflete instantaneamente na tela dos jogadores.
- **Máquina de Estados de Exibição (`DisplayState`):**
  - **`IDLE`:** Tela de descanso elegante com animação procedural do *Sigil Místico* e estética *Dark Fantasy*.
  - **`PROJECTION`:** Projeção cinemática de artes avulsas (cenários, NPCs, cartas de monstros e itens) com enquadramento proporcional (*Aspect-Fit / Contain*).
  - **`COMBAT`:** Modo de batalha tático em tela cheia com mapas (imagem ou tilemap modular), tokens circulares com badges de iniciais, grid de alto contraste e HUD de iniciativa.
- **Assistente Completo de Criação de Encontros (`EncounterCreatorTab`):**
  - **Etapa 1 (Formulário):** Metadados, seleção de mapas (arquivos de imagem ou tilemaps JSON), dimensões de grade (colunas e pés por quadrado), seleção de heróis e monstros com busca rápida e seletores numéricos.
  - **Etapa 2 (Palco Tático):** Posicionamento visual dos combatentes via arrastar-e-soltar (*Drag & Drop* com *Snap-to-Grid*), alternância de visibilidade oculta (50% de opacidade para o DM, invisível para jogadores) e salvamento automático em formato JSON.
- **Engine de Tilemaps em Runtime:** Suporte a fatiamento de atlas do Aseprite (`.json` + `.png`), batch rendering em lote na GPU (`arcade.SpriteList`), alinhamento tático com *half-tile offset* de 16px e propriedades de terreno D&D 5E (`blocks_movement`, `blocks_vision`, `cover_type`, `difficult_terrain`, `height`).
- **Movimentação Suave dos Tokens (*Lerp Interpolation*):** Deslocamento visual fluido dos tokens na tela dos jogadores ao serem movidos pelo DM, eliminando teleportes abruptos.
- **Componente `SmartTextInput`:** Entrada de texto com cursor interativo piscante, seleção de texto por clique/arrasto ou Shift+Setas, atalhos de produtividade (`Ctrl+A`, `Ctrl+C`, `Ctrl+V`, `Ctrl+X`), *hold-to-repeat* no Backspace e suporte a clipboard do sistema operacional.
- **Gerenciador de Iniciativas & Modal de Staging:** Rolagem automática de iniciativa D&D 5E (1d20 + modificador de Destreza), desempate canônico por atributo e inserção manual/ajuste fino antes do início do combate.
- **Painel Ágil de Dano e Cura:** Aplicação com um clique de valores (+ / -) com validação de HP e condições de status.
- **Logging Estruturado UTF-8:** Gravação de logs simultânea em console e arquivo rotativo (`logs/medusa.log` com limite de 5MB e 3 backups). Zero `print()`.

---

## 🏛️ Arquitetura & Padrões de Projeto

O Medusa foi desenvolvido sob os princípios de **Clean Code**, **Domain-Driven Design (DDD)**, **Object-Oriented Design (OOD)** e alta modularidade.

```
                         ┌────────────────────────┐
                         │     SessionManager     │
                         │   (DisplayState / SM)  │
                         └───────────┬────────────┘
                                     │
                ┌────────────────────┴────────────────────┐
                │                                         │
       [Notifica Listeners]                      [Notifica Listeners]
                ▼                                         ▼
      ┌───────────────────┐                     ┌───────────────────┐
      │     DMWindow      │                     │   PlayerWindow    │
      │ (Arcade GUI / DM) │                     │ (Arcade Viewport) │
      └─────────┬─────────┘                     └─────────┬─────────┘
                │                                         │
                │◄────────── CombatManager ──────────────►│
                │        (Combat State / Grid)            │
```

### 1. Padrão Observer (Sincronização Reativa)
- O `SessionManager` e o `CombatManager` atuam como *Subjects* centrais da sessão.
- As janelas `DMWindow` e `PlayerWindow` se registram como *listeners*.
- Disparos de eventos (início de combate, troca de turno, dano, cura, movimentação de token, projeção de imagem) notificam automaticamente ambas as visualizações.

### 2. Padrão State (Máquina de Estados de Exibição)
O estado global da sessão dita o comportamento da `PlayerWindow`:
- **`DisplayState.IDLE`:** Renderiza tela de espera com sprite animado do sigil em loop de tempo delta.
- **`DisplayState.PROJECTION`:** Renderiza imagem de cenário/NPC centralizada com cálculo de proporção de aspecto.
- **`DisplayState.COMBAT`:** Ativa a câmera de combate (`PlayerCamera`), renderiza a camada de chão e grid, atualiza posições interpoladas de tokens e exibe o `InitiativeHUD`.

### 3. Padrões Builder e Factory
- **`SpriteFactory` (`src/ui/utils/sprite_utils.py`):** Fábrica centralizada que instancia sprites estáticos e animados, fatia spritesheets, calcula escalas com base em `target_size`, gerencia cache interno de texturas e produz badges circulares com iniciais dos combatentes.
- **`CharacterBuilder`, `MonsterBuilder` & `EncounterBuilder` (`src/domain/builders/`):** *Fluent Builders* que validam integridade de regras, calculam modificadores e serializam instâncias de entidades e encontros.

### 4. Padrão Value Object
- **`TileProperties` (`src/domain/models/tile_map.py`):** Objeto de valor imutável encapsulando características físicas e táticas de uma célula de terreno (bloqueio de movimento, bloqueio de linha de visão, cobertura D&D 5E, terreno difícil e elevação).

### 5. Encapsulamento Estrito e Cópias Defensivas (*Poka-Yoke*)
- Atributos privados com duplo underscore (`self.__current_hp`, `self.__resources`).
- Acesso exclusivo via `@property` e métodos semânticos (`damage()`, `heal()`, `add_condition()`).
- Retorno de **cópias defensivas** (`.copy()`, `list(...)`) em todas as coleções internas para evitar mutações colaterais externas.

---

## 📂 Estrutura Completa de Diretórios

```
medusa_controler/
├── assets/                          # Recursos estáticos e gráficos do VTT
│   ├── fonts/                       # Tipografias do sistema
│   ├── images/                      # Mídias visuais e cenários
│   │   ├── maps/                    # Mapas de batalha em arquivo de imagem (JPG/PNG)
│   │   ├── showcase/                # Ilustrações cinemáticas de locais, itens e NPCs
│   │   └── tilemaps/                # Atlas visuais de tilesets
│   ├── sprites/                     # Spritesheets animados (ex: sigil místico de IDLE)
│   └── tilesets/                    # Arquivos de atlas Aseprite (.json) e texturas (.png)
│
├── creations/                       # Dados mutáveis instanciados pelos usuários
│   ├── characters/                  # Fichas JSON de Personagens Jogadores (PJs)
│   ├── encounters/                  # Configurações JSON de encontros de combate
│   └── maps/                        # Layouts JSON de mapas modulares (TileMaps)
│
├── presets/                         # Regras estáticas e definições canônicas de D&D 5E
│   ├── classes/                     # Definições JSON de classes (dados de vida, magias)
│   ├── monsters/                    # Bestiário JSON de monstros e NPCs (atributos, CA, ações)
│   └── species/                     # Traços, bônus raciais e deslocamento
│
├── logs/                            # Histórico e auditoria de execução
│   └── medusa.log                   # Log rotativo contínuo formatado em UTF-8
│
├── src/                             # Código-fonte principal da aplicação
│   ├── domain/                      # Camada de Domínio e Lógica de Negócio
│   │   ├── builders/                # Fluent Builders de entidades e encontros
│   │   │   ├── character_builder.py # Montador de PlayableCharacter
│   │   │   ├── encounter_builder.py # Montador e serializador de Encontros (JSON)
│   │   │   └── monster_builder.py   # Montador de Monster/NPC
│   │   ├── loaders/                 # Carregadores de dados com validação segura
│   │   │   ├── character_loader.py  # Carregador de fichas de personagens
│   │   │   ├── encounter_loader.py  # Carregador de arquivos de encontro
│   │   │   ├── monster_loader.py    # Carregador de presets do bestiário
│   │   │   └── tileset_manager.py   # Loader em runtime de atlas Aseprite e texturas
│   │   └── models/                  # Modelos de Domínio e Entidades
│   │       ├── entity.py            # Classe base Entity (HP, CA, Condições, Visibilidade)
│   │       ├── monster.py           # Especialização Monster (Ações, Traits, CR, XP)
│   │       ├── playablechar.py      # Especialização PlayableCharacter (Classes, Spell Slots)
│   │       └── tile_map.py          # Modelo TileMap e Value Object TileProperties
│   │
│   ├── manager/                     # Camada de Orquestração e Estado
│   │   ├── combat_manager.py        # Gerenciador de turnos, rodadas, iniciativas e dano/cura
│   │   ├── grid_manager.py          # Matemática de grid, coordenadas matriciais e snap-to-grid
│   │   └── session_manager.py       # Single Source of Truth para DisplayState e mídias
│   │
│   ├── ui/                          # Camada de Apresentação (Python Arcade GUI)
│   │   ├── dm/                      # Componentes modulares da Tela do Mestre (DMWindow)
│   │   │   ├── creator/             # Submódulos do Assistente de Criação de Encontros
│   │   │   │   ├── config_form.py   # Formulário de configuração (Metadados, Mapa, Grid, Roster)
│   │   │   │   ├── tactical_stage.py# Palco tático de posicionamento e visibilidade oculta
│   │   │   │   └── text_input.py    # Wrapper de campos de texto
│   │   │   ├── combat_tab.py        # Aba de controle de combate ativo e despachante de dano
│   │   │   ├── dm_header.py         # Barra superior de status e seletor de abas
│   │   │   ├── encounter_creator_tab.py # Controlador principal do criador de encontros
│   │   │   ├── encounters_tab.py    # Aba de seleção e inicialização de encontros
│   │   │   ├── initiative_modal.py  # Modal overlay de rolagem e staging de iniciativas
│   │   │   ├── showcase_tab.py      # Aba de seleção e projeção de mídias de cenário
│   │   │   └── tactical_minimap.py  # Mini-mapa com DMCamera, drag & drop e espelho visual
│   │   ├── utils/                   # Utilitários gráficos e de renderização
│   │   │   ├── sprite_utils.py      # SpriteFactory e gerador de badges circulares
│   │   │   ├── text_input.py        # SmartTextInput (cursor, seleção, atalhos, key-repeat)
│   │   │   └── tilemap_renderer.py  # Renderizador em lote GPU (SpriteList) para TileMaps
│   │   ├── dm_window.py             # Janela principal do Mestre (DM Screen)
│   │   ├── player_window.py         # Janela dos Jogadores (Player Screen com Aspect-Fill e Lerp)
│   │   └── initiative_hud.py        # Fita flutuante de iniciativa translúcida
│   │
│   └── utils/                       # Utilitários de Infraestrutura
│       └── logger.py                # Configuração do Logger (Console + RotatingFileHandler UTF-8)
│
├── tests/                           # Suíte de Testes Automatizados (112 testes)
│   ├── ui/
│   │   └── test_smart_text_input.py # Testes unitários do componente SmartTextInput
│   ├── test_combat_manager.py       # Testes de combate, turnos, condições e dano
│   ├── test_creator_ood.py          # Testes da arquitetura OOD do criador de encontros
│   ├── test_dm_window_arcade.py     # Testes da interface e navegação da DMWindow
│   ├── test_domain_models.py        # Testes de encapsulamento de Entity, PC e Monster
│   ├── test_encounter_builder.py    # Testes do builder e persistência de encontros
│   ├── test_encounter_map_types.py  # Testes de suporte a múltiplos formatos de mapa
│   ├── test_grid_manager.py         # Testes de conversão matricial e Snap-to-Grid
│   ├── test_idle_animation.py       # Testes de animação do sigil místico
│   ├── test_initiative_staging.py   # Testes do modal de staging de iniciativas
│   ├── test_loaders_and_builders.py # Testes de I/O de loaders e validações defensivas
│   ├── test_logger.py               # Testes de formatação, rotação e encoding do logger
│   ├── test_monster_search_and_scroll.py # Testes de busca e paginação de monstros
│   ├── test_session_manager.py      # Testes de transição de DisplayState e Observer
│   ├── test_sprite_utils.py         # Testes da SpriteFactory e tokens circulares
│   ├── test_tilemap_engine.py       # Testes da engine de Tilemaps, atlas e colisões
│   └── test_token_interpolation.py  # Testes de interpolação suave (Lerp) dos tokens
│
├── main.py                          # Ponto de entrada (Entrypoint) da aplicação
├── PREMISES.md                      # Premissas arquiteturais e regras invioláveis de código
├── requirements.txt                 # Dependências do projeto (arcade>=3.0.0)
└── README.md                        # Documentação técnica oficial
```

---

## 🧩 Camadas do Sistema

### 1. Camada de Domínio (`src/domain/`)
- **Entidades de Combate:** `Entity` fornece o núcleo com HP atual/máximo/temporário, CA, iniciativa, condições de status (cegueira, paralisia, etc.), visibilidade (`is_hidden`) e posicionamento no grid `(col, row)`. `PlayableCharacter` e `Monster` estendem a entidade base com especificidades de regras D&D 5E.
- **Modelos de Terreno:** `TileMap` encapsula matrizes de células com indexação rápida em $O(1)$, fornecendo consultas de bloqueio de passagem, oclusão de visão, terreno difícil e cobertura.
- **Builders Fluent:** Construção expressiva e semântica com validações defensivas (*Poka-Yoke*):
  ```python
  encounter = (
      EncounterBuilder()
      .with_metadata(title="Emboscada na Floresta", description="Goblins na trilha")
      .with_map("assets/tilesets/test_map_1.json", map_type="tilemap")
      .with_grid(columns=25, feet_per_square=5)
      .add_character_by_uid("char_artemis", col=3, row=4)
      .add_monster_by_uid("goblin", col=10, row=12, count=3, is_hidden=True)
      .build()
  )
  ```

### 2. Camada de Gerenciamento (`src/manager/`)
- **`SessionManager`:** Administra o ciclo de vida da sessão e atua como despachante de comandos entre a UI e o motor de regras.
- **`CombatManager`:** Controla a fila circular de turnos, incremento de rodadas, ordenação de iniciativas com desempates por modificador e despacho de dano/cura.
- **`GridManager`:** Responsável pela geometria tática do combate, transformando coordenadas de tela (pixels) em coordenadas matriciais da grade de combate (e vice-versa), garantindo *Snap-to-Grid* centralizado com *half-tile offset*.

### 3. Camada de Apresentação (`src/ui/`)
- **`DMWindow`:** Painel de 4 abas estruturado com componentes OOD:
  - **Aba 0 (Encontros):** Carregamento de encontros de `creations/encounters/`.
  - **Aba 1 (Cenários):** Projeção instantânea de artes de `assets/images/showcase/`.
  - **Aba 2 (Combate):** Visão completa do combate com botões táticos, lista de combatentes e controle de HP/condições.
  - **Aba 3 (Criador de Encontros):** Assistente de criação em duas etapas com posicionamento visual.
- **`PlayerWindow`:** Viewport limpa projetada na TV dos jogadores, sem controles de edição, com renderização gráfica acelerada, interpolação *Lerp* de tokens e animações fluidas.

---

## 🗄️ Normalização de Dados: `presets/` vs `creations/`

O Medusa mantém uma separação rígida entre regras estáticas canônicas e dados mutáveis da campanha:

| Diretório | Finalidade | Natureza | Exemplos |
| :--- | :--- | :--- | :--- |
| **`presets/`** | **Regras Estáticas & Canônicas:** Templates base do D&D 5E (classes, raças, monstros). Não sofrem alterações em tempo de execução. | *Imutável (Read-Only)* | `presets/monsters/goblin.json`<br>`presets/classes/wizard.json` |
| **`creations/`** | **Instâncias Vivas de Campanha:** Personagens, mapas e encontros criados para a mesa, contendo estado mutável (HP, posições X/Y, tokens ocultos). | *Mutável (State-Driven)* | `creations/characters/artemis.json`<br>`creations/encounters/emboscada.json`<br>`creations/maps/floresta.json` |

---

## 🗺️ Engine de Tilemaps & Grade Tática

O Medusa suporta tanto mapas tradicionais em imagem única (JPG/PNG) quanto **Mapas Modulares por Tilesets (Dual Grid Runtime)**:

```
                  ┌──────────────────────────────┐
                  │      Aseprite Export         │
                  │ (.json atlas + .png texture) │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │    TilesetManager     │
                     │ (Fatia Texturas O(1)) │
                     └───────────┬───────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       ┌───────────────────┐           ┌───────────────────┐
       │      TileMap      │           │  TileMapRenderer  │
       │ (Matriz Tática)   │           │ (Batch SpriteList)│
       └───────────────────┘           └───────────────────┘
```

- **Fatiamento Dinâmico em Memória:** O `TilesetManager` analisa o JSON exportado pelo Aseprite e fatia a textura PNG correspondente em subtexturas `arcade.Texture` em $O(1)$.
- **Renderização em Lote na GPU:** O `TileMapRenderer` constrói uma única `arcade.SpriteList(use_spatial_hash=False)` com `pixelated=True`, garantindo alta taxa de quadros (60+ FPS).
- **Alinhamento Tático D&D (5ft):** O centro do quadrado recebe um deslocamento (*half-tile offset* de $16\text{px}$) via `GridManager.grid_to_world_center()`, garantindo que tokens fiquem perfeitamente centralizados nas células da grade.

---

## ⚙️ Guia de Instalação e Execução

### 1. Pré-requisitos
- **Python 3.10+** (recomendado Python 3.11 ou superior)
- Placa de vídeo compatível com **OpenGL 3.3+**

### 2. Criação do Ambiente Virtual (`venv`) e Instalação

```powershell
# Criação do ambiente virtual
python -m venv venv

# Ativação do ambiente virtual no Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Ativação no Linux / macOS
# source venv/bin/activate

# Instalação das dependências
pip install -r requirements.txt
```

### 3. Executando o Medusa VTT

Para iniciar simultaneamente as duas janelas sincronizadas (`DMWindow` e `PlayerWindow`):

```powershell
python main.py
```

---

## 🧪 Suíte de Testes Automatizados

O sistema conta com **112 testes unitários e de integração**, cobrindo 100% dos subsistemas críticos:

```powershell
# Execução de todos os testes unitários
python -m unittest discover -s tests -p "test_*.py" -v
```

### Cobertura da Suíte de Testes:
- **Combate & Iniciativa:** Rolagens, desempates D&D 5E, turnos, rodadas, dano e cura.
- **Modelos de Domínio:** Encapsulamento de `Entity`, `PlayableCharacter`, `Monster` e cópias defensivas.
- **Tilemap Engine & Colisão:** Validação de `TileProperties`, `TileMap`, `TilesetManager` e `TileMapRenderer`.
- **Encounter Wizard & Builders:** Criação, edição e serialização de encontros com múltiplos tipos de mapa.
- **Geometria Tática:** Matemática do `GridManager`, conversões matriciais e *Snap-to-Grid*.
- **UI & Interatividade:** Componente `SmartTextInput` (cursor, seleção, atalhos, key-repeat), animações e renderização.
- **Logging & Auditoria:** Gravação UTF-8 e rotação automática de arquivos.

---

## 📜 Premissas e Regras de Código

As regras invioláveis de desenvolvimento do Medusa VTT estão formalizadas em [`PREMISES.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/PREMISES.md):

1. **Zero Tkinter:** 100% da interface utiliza Python Arcade e Arcade GUI nativo.
2. **Zero `print()`:** Todas as mensagens utilizam o módulo padrão `logging` com suporte a caracteres UTF-8.
3. **Encapsulamento Estrito (*Poka-Yoke*):** Atributos internos privados com duplo underscore (`__attr`), validação defensiva em *setters* e retorno de cópias defensivas para coleções mutáveis.
4. **Data-Driven Architecture:** Separação estrita entre regras estáticas (`presets/`) e instâncias dinâmicas (`creations/`).
5. **Criação de Sprites Centralizada:** Uso obrigatório de `SpriteFactory` para instanciar texturas e sprites.
6. **Testabilidade Obrigatória:** Qualquer novo módulo ou refatoração deve conter testes automatizados em `tests/`.
