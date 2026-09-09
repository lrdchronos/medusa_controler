# 📚 Documentação Técnica — Medusa VTT

Bem-vindo ao repositório central de documentação técnica no padrão **Docs-as-Code** do **Medusa VTT** (*Virtual Tabletop Local para D&D 5E*).

Este diretório contém as especificações arquiteturais, modelagem de dados, regras de negócio táticas, contratos de subsistemas e guias operacionais para engenheiros de software, mantenedores e agentes de IA/LLMs.

---

## 🗺️ Mapa de Navegação da Documentação

A documentação está modularizada em 3 pilares temáticos:

```text
docs/
├── README.md                      # Índice central e mapa de navegação da documentação
├── architecture/                  # Fundamentos e decisões de arquitetura de sistema
│   ├── state_machine.md           # DisplayState (IDLE, PROJECTION, COMBAT) e Sincronização Observer
│   ├── grid_and_coords.md         # GridManager, pixels_per_foot, aspect-fit/fill e snap-to-grid
│   └── data_schemas.md            # Schemas JSON (presets/ vs creations/, saves/ e mapas)
├── subsystems/                    # Motores de regras e subsistemas especializados
│   ├── combat_engine.md           # CombatManager, fila de turnos, criaturas ocultas e save incremental
│   ├── spell_projections.md       # Formas canônicas (2D/3D), analítica vetorial e GridCellHighlighter
│   ├── fog_of_war.md              # FogManager, pincel contínuo, persistência e visual DM vs Player
│   └── token_badges.md            # SpriteFactory, órbita de status (relógio) e tamanhos D&D 5E
└── guides/                        # Manuais operacionais e diretrizes para criadores
    ├── encounter_workflow.md      # Ciclo de vida: Builder -> Staging -> Batalha -> Save State
    └── adding_assets.md           # Sprites estáticos/animados (32x32 6 frames) e props de mapas
```

---

## 🏛️ Visão Geral da Arquitetura

O Medusa VTT é construído sobre os princípios de **Clean Code**, **Domain-Driven Design (DDD)**, **Object-Oriented Design (OOD)** e **Data-Driven Architecture**, operando em regime de **dupla janela sincronizada**:

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

### Resumo das Camadas em `src/`

| Camada | Diretório | Responsabilidade | Principais Módulos |
| :--- | :--- | :--- | :--- |
| **Domínio** | [`src/domain/`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain) | Modelos de entidade (`Entity`, `PlayableCharacter`, `Monster`), terreno (`TileMap`, `TileProperties`), áreas de feitiços (`SpellTemplate`, `AoEShape`), névoa (`FogManager`), regras (`InitiativeTracker`, `AoECalculator`, `CombatantRules`, `CombatStateSerializer`) e builders fluentes. | [`entity.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/entity.py), [`spell_template.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/spell_template.py), [`aoe_calculator.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/aoe_calculator.py) |
| **Gerenciamento** | [`src/manager/`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager) | Orquestração da sessão (`SessionManager`), controle da fila circular de combate e dano (`CombatManager`) e geometria de projeção do grid (`GridManager`). | [`session_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/session_manager.py), [`combat_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/combat_manager.py), [`grid_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/grid_manager.py) |
| **Apresentação** | [`src/ui/`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui) | Telas (`DMWindow`, `PlayerWindow`), renderizadores gráficos em GPU (`TileMapRenderer`, `PlayerViewRenderer`, `MiniMapRenderer`), HUDs (`InitiativeHUD`), componentes desacoplados (`GridCellHighlighter`, `DiscreteScrollList`, `SmartTextInput`), fábricas (`SpriteFactory`) e painéis do Mestre. | [`dm_window.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm_window.py), [`player_window.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/player_window.py), [`sprite_factory.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/sprite_factory.py) |
| **Infraestrutura** | [`src/utils/`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/utils) | Logger rotativo estruturado UTF-8 sem dependências de `print()`. | [`logger.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/utils/logger.py) |

---

## 📖 Leitura Recomendada por Perfil

### 👨‍💻 Para Desenvolvedores & Contribuidores:
1. Inicie pelas premissas fundamentais em [`PREMISES.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/PREMISES.md).
2. Compreenda a máquina de estados em [`architecture/state_machine.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/architecture/state_machine.md).
3. Estude a matemática de grade e aspect-fit em [`architecture/grid_and_coords.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/architecture/grid_and_coords.md).
4. Consulte os contratos de subsistema em [`subsystems/combat_engine.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/subsystems/combat_engine.md) e [`subsystems/spell_projections.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/subsystems/spell_projections.md).

### 🎲 Para Mestres de RPG (DMs):
1. Siga o fluxo de preparação de sessões em [`guides/encounter_workflow.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/guides/encounter_workflow.md).
2. Aprenda a adicionar artes, mapas e spritesheets em [`guides/adding_assets.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/guides/adding_assets.md).
3. Entenda o uso da névoa de guerra em [`subsystems/fog_of_war.md`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/docs/subsystems/fog_of_war.md).
