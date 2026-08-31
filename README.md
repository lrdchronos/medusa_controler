# 🐉 Medusa VTT - Virtual Tabletop Local para D&D 5E

O **Medusa VTT** é uma plataforma local de *Virtual Tabletop* (Mesa Digital) desenvolvida em **Python** e **Python Arcade**, projetada especificamente para enriquecer sessões presenciais de **Dungeons & Dragons 5ª Edição (D&D 5E)**.

O sistema opera com uma arquitetura de **dupla janela simultânea**:
1. **Painel do Mestre (`DMWindow`):** Interface de controle tático para o Dungeon Master no notebook ou monitor principal, com gerenciamento de encontros, rolagem e staging de iniciativas, controle de visibilidade (névoa de guerra / tokens ocultos), aplicação ágil de dano e cura, e mini-mapa interativo com *Drag & Drop* e *Snap-to-Grid*.
2. **Tela dos Jogadores (`PlayerWindow`):** Viewport imersiva de alta definição projetada na TV da sala ou mesa digital, com renderização de mapas em tela cheia (*Aspect-Fill* sem distorção nem barras pretas), fita de iniciativas flutuante em overlay translúcido, indicação de turnos ativos com realce dourado pulsante e telas de descanso/showcase elegantes.

---

## 🏛️ Arquitetura & Padrões de Projeto (Design Patterns)

O Medusa foi concebido seguindo princípios de **Clean Code**, **Object-Oriented Design (OOD)** e alta modularidade:

```
                          ┌────────────────────────┐
                          │     SessionManager     │
                          │   (DisplayState State) │
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
- A `DMWindow` e a `PlayerWindow` registram *listeners* no `SessionManager` e `CombatManager`.
- Qualquer ação executada pelo Mestre (iniciar combate, mudar de turno, projetar imagem de cenário, alternar para estado de espera, mover um token no grid) notifica instantaneamente ambas as janelas, mantendo a experiência do jogador sincronizada em tempo real sem latência.

### 2. Máquina de Estados de Exibição (`DisplayState`)
A `PlayerWindow` adapta sua renderização visual com base no estado global:
- **`DisplayState.IDLE`:** Tela de descanso e espera imersiva (*"Aguardando o Mestre..."*) com sigil místico animado proceduralmente e paleta *Dark Fantasy*.
- **`DisplayState.PROJECTION`:** Projeção cinemática de ilustrações avulsas (cenários, NPCs, itens e cartas de monstros) com enquadramento proporcional (*Aspect Ratio Fit / Contain*).
- **`DisplayState.COMBAT`:** Renderização do mapa de combate em tela cheia (*Aspect-Fill*), grid tático de alto contraste (Luminous Steel Cyan), tokens visíveis dos combatentes e fita de iniciativas flutuante (*InitiativeHUD*).

### 3. Padrões Builder e Factory
- **`SpriteFactory` (`src/ui/utils/sprite_utils.py`):** Fábrica centralizada que cria sprites estáticos e animados em apenas uma linha de código, com corte automático de spritesheets, cálculo de escala com `target_size`, cache interno de texturas e renderização de tokens circulares padronizados.
- **`CharacterBuilder` & `MonsterBuilder` (`src/domain/builders/`):** Implementação de *Fluent Builders* para montagem de entidades ricas de domínio, validando integridade de dados e atributos antes da instanciação.

### 4. Encapsulamento Estrito e Cópias Defensivas
- As entidades de domínio (`Entity`, `PlayableCharacter`, `Monster`) protegem seu estado interno contra mutações indevidas.
- Propriedades de coleções e dicionários (`resources`, `spell_slots`, `conditions`, `attacks`, `actions`, `legendary_actions`, `traits`) retornam **cópias defensivas** (`dict.copy()`, `list.copy()`).
- Mutações de pontos de vida e condições são realizadas exclusivamente através de métodos semânticos (`damage(amount)`, `heal(amount)`, `add_condition(cond)`, `remove_condition(cond)`), com validações defensivas (*Poka-Yoke* de níveis entre 1 e 20 e não-negatividade de dano/cura).

---

## 📂 Estrutura de Diretórios

```
medusa_controler/
├── assets/                  # Recursos visuais e gráficos do VTT
│   ├── fonts/               # Tipografias do sistema
│   ├── images/              # Imagens de mapas e cenários de exibição (showcase)
│   │   ├── maps/            # Mapas táticos de batalha
│   │   └── showcase/        # Ilustrações cinemáticas de locais e NPCs
│   └── sprites/             # Spritesheets animados (sigil místico de IDLE)
│
├── creations/               # Dados mutáveis instanciados pelos usuários
│   ├── characters/          # Fichas JSON dos personagens jogadores (PJ)
│   └── encounters/          # Configuração JSON de encontros de combate tático
│
├── presets/                 # Regras estáticas e definições canônicas de D&D 5E
│   ├── classes/             # Definições JSON de classes (dados de vida, proficiências)
│   ├── monsters/            # Bestiário JSON de monstros e NPCs (atributos, CA, ações)
│   └── species/             # Traços e bônus raciais
│
├── logs/                    # Arquivos de log de execução da aplicação
│   └── medusa.log           # Log central contínuo / rotativo em formato UTF-8
│
├── src/                     # Código-fonte principal da aplicação
│   ├── domain/              # Camada de Domínio e Lógica de Negócio
│   │   ├── builders/        # Fluent Builders de Personagens e Monstros
│   │   ├── loaders/         # Carregadores JSON com tratamento seguro de I/O
│   │   └── models/          # Modelos de Entidade (Entity, PlayableCharacter, Monster)
│   ├── manager/             # Gerenciadores de Estado e Orquestração
│   │   ├── combat_manager.py  # Orquestrador de turnos, dano, cura e visibilidade
│   │   ├── grid_manager.py    # Conversor matricial World-to-Grid e Snap-to-Grid
│   │   └── session_manager.py # Máquina de estados (IDLE, PROJECTION, COMBAT) e Observer
│   ├── ui/                  # Camada de Apresentação (Python Arcade)
│   │   ├── dm/              # Componentes especializados da tela do Mestre (DMWindow)
│   │   │   ├── combat_tab.py         # Aba de combate e despacho de dano/cura
│   │   │   ├── dm_header.py          # Barra superior e seletor de abas
│   │   │   ├── encounters_tab.py     # Lista de encontros e acionador
│   │   │   ├── initiative_modal.py   # Modal de rolagem/staging de iniciativas
│   │   │   ├── showcase_tab.py       # Aba de projeção de imagens
│   │   │   └── tactical_minimap.py   # Mini-mapa com drag-and-drop de tokens
│   │   ├── utils/           # Utilitários de interface gráfica
│   │   │   └── sprite_utils.py       # SpriteFactory e gerador de badges circulares
│   │   ├── dm_window.py     # Janela principal do Mestre (DM Screen)
│   │   ├── player_window.py # Janela dos Jogadores (Player Screen - Aspect-Fill)
│   │   └── initiative_hud.py# Fita de iniciativa flutuante e translúcida
│   └── utils/               # Utilitários de infraestrutura
│       └── logger.py        # Configuração de logging (Console + FileHandler UTF-8)
│
├── tests/                   # Suíte de testes unitários automatizados
│   ├── test_combat_manager.py
│   ├── test_dm_window_arcade.py
│   ├── test_domain_models.py
│   ├── test_grid_manager.py
│   ├── test_idle_animation.py
│   ├── test_initiative_staging.py
│   ├── test_loaders_and_builders.py
│   ├── test_logger.py
│   ├── test_session_manager.py
│   └── test_sprite_utils.py
│
├── main.py                  # Ponto de entrada (Entrypoint) da aplicação
├── requirements.txt         # Dependências do projeto
└── README.md                # Documentação técnica oficial
```

---

## 🗄️ Normalização de Dados: `presets/` vs `creations/`

O Medusa adota uma separação rigorosa entre dados imutáveis de regras e dados dinâmicos de campanha:

| Diretório | Finalidade | Natureza dos Dados | Exemplos |
| :--- | :--- | :--- | :--- |
| **`presets/`** | **Regras Estáticas & Canônicas:** Contém os templates base do sistema D&D 5E. Não devem sofrer mutações durante o combate. | *Imutável / Read-Only* | `presets/monsters/goblin.json`, `presets/classes/wizard.json` |
| **`creations/`** | **Instâncias Vivas de Campanha:** Personagens e encontros criados para a mesa atual, contendo estado dinâmico (HP atual, posições na matriz X/Y, tokens ocultos). | *Mutável / State-Driven* | `creations/characters/bolo.json`, `creations/encounters/encounter_01.json` |

---

## ⚙️ Guia de Instalação, Execução e Testes

### 1. Pré-requisitos
- **Python 3.10+** (recomendado Python 3.11 ou superior)
- Placa de vídeo compatível com **OpenGL 3.3+**

### 2. Criação do Ambiente Virtual (`venv`) e Instalação

```powershell
# Criação do ambiente virtual
python -m venv venv

# Ativação do ambiente virtual (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Ativação no Linux / macOS
# source venv/bin/activate

# Instalação das dependências
pip install -r requirements.txt
```

### 3. Executando o Medusa VTT

Para iniciar as duas janelas sincronizadas (`DMWindow` e `PlayerWindow`):

```powershell
python main.py
```

### 4. Executando a Suíte de Testes Automatizados

O projeto conta com mais de 45 testes unitários abrangendo regras de combate, builders, loaders, snap-to-grid, animações e infraestrutura de logging:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🪵 Sistema de Logging

Todos os eventos de inicialização, transição de estados, rolagens de dados e alterações em combate são registrados simultaneamente:
- **Terminal (Console):** Saída colorida/formatada para acompanhamento rápido.
- **Arquivo (`logs/medusa.log`):** Gravação contínua com rotação automática (`RotatingFileHandler` de até 5 MB e 3 backups) e encoding `UTF-8` para preservação integral de caracteres semânticos e acentuação:
  ```
  [YYYY-MM-DD HH:MM:SS,mmm] [LEVEL] [ModuleName]: Mensagem do evento
  ```
