# 🌫️ Névoa de Guerra (Fog of War)

Este documento especifica o subsistema de **Névoa de Guerra** ([`FogManager`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/fog_manager.py)), as ferramentas de pincel contínuo do Mestre ([`FogControlPanel`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm/fog_control_panel.py)), a persistência de visibilidade e as rotinas de renderização contrastantes entre a visão do DM e dos Jogadores.

---

## 1. Responsabilidade do Módulo & Orquestração

A Névoa de Guerra oculta áreas inexploradas do mapa de batalha para os jogadores, preservando o elemento de surpresa e exploração tática. O subsistema garante consultas de oclusão em tempo real em $O(1)$, edição contínua via arrasto do mouse na tela do Mestre e persistência idempotente nos arquivos de encontro e saves de combate.

### Mapeamento de Arquivos-Fonte:
- [`src/domain/models/fog_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/fog_manager.py): Modelo de dados do conjunto matricial de névoa e despachante Observer.
- [`src/ui/dm/fog_control_panel.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm/fog_control_panel.py): Painel de ferramentas (Pincel, Revelar, Preencher Tudo, Limpar Tudo, Salvar no Encontro).
- [`src/ui/dm/tactical_minimap.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm/tactical_minimap.py): Captura de eventos de clique e arrasto contínuo do pincel.
- [`src/ui/renderers/player_view_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/renderers/player_view_renderer.py): Renderização 100% oclusiva na tela dos jogadores.
- [`src/ui/renderers/minimap_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/renderers/minimap_renderer.py): Renderização translúcida com alto contraste na tela do Mestre.

---

## 2. Modelagem de Dados e Schemas

### 2.1. Estrutura Canônica em Memória
Internamente, o `FogManager` armazena as células cobertas como um conjunto hash `Set[Tuple[int, int]]`, garantindo inserção, remoção e consulta (`is_fogged(col, row)`) em tempo constante $O(1)$.

```python
class FogManager:
    def __init__(self) -> None:
        self.__fogged_cells: Set[Tuple[int, int]] = set()
        self.__listeners: List[Callable[[], None]] = []
```

### 2.2. Schema de Serialização JSON (`export_state` / `load_state`)
A lista é exportada ordenada deterministicamente por `(row, col)`:

```json
[
    {"x": 2, "y": 5},
    {"x": 3, "y": 5},
    {"x": 4, "y": 5},
    {"x": 2, "y": 6}
]
```

O método `load_state()` aplica validação defensiva *Poka-Yoke*, aceitando tanto chaves `{"x": col, "y": row}` quanto `{"col": col, "row": row}` e descartando entradas corrompidas com log de aviso sem interromper a execução.

---

## 3. Regras de Negócio e Casos de Borda (Edge Cases)

### 3.1. Ferramentas de Pincel e Modos de Operação

| Ferramenta / Ação | Gatilho | Comportamento |
| :--- | :--- | :--- |
| **Pincel de Ocultação** | `Clique / Arrasto Esquerdo` (com modo ADD) | Cobre a célula e o raio de abrangência do pincel com névoa (`set_cell`). |
| **Pincel de Revelação** | `Clique / Arrasto Direito` ou modo CLEAR | Remove a névoa da célula e seu raio de abrangência (`clear_cell`). |
| **Preencher Tudo (`fill_all`)** | Botão "Preencher Tudo" no Painel | Cobre instantaneamente todas as células da grade de $(0, 0)$ até $(\text{cols}-1, \text{rows}-1)$. |
| **Limpar Tudo (`clear_all`)** | Botão "Limpar Tudo" no Painel | Revela 100% do mapa de batalha. |
| **Tamanho do Pincel** | Seletor $1\times1$, $3\times3$, $5\times5$ | Aplica a mutação em uma vizinhança de raio $\Delta = \frac{\text{size} - 1}{2}$. |

---

### 3.2. Diferenciação Visual: DM vs. Jogadores

```
   Visão dos Jogadores (TV da Sala)                Visão do Mestre (DMWindow)
   ┌───────────────────────────────┐               ┌───────────────────────────────┐
   │                               │               │                               │
   │      [100% PRETO OPACO]       │               │      [AZUL TRANSLÚCIDO]       │
   │   Oclui Mapa, Tokens e Props  │               │   Mestre enxerga terreno,     │
   │                               │               │   goblins ocultos e armadilhas│
   │                               │               │                               │
   └───────────────────────────────┘               └───────────────────────────────┘
```

1. **Visão dos Jogadores (`PlayerWindow`):**
   - Retângulos preenchidos com cor preta absoluta oclusiva `(10, 14, 20, 255)` desenhados sobre a camada de mapa e tokens. Qualquer elemento tático sob a névoa fica invisível.
2. **Visão do Mestre (`TacticalMiniMap`):**
   - Overlay translúcido grafite/azul-escuro `(20, 30, 45, 140)` com borda sutil. O Mestre inspeciona livremente o terreno, objetos e tokens inimigos, identificando com clareza quais áreas estão bloqueadas para a visão dos jogadores.

---

### 3.3. Persistência e Sincronização

- **Salvar Névoa no Arquivo do Encontro:** O método `save_fog_to_encounter_file()` grava a matriz atual de névoa no JSON base em `creations/encounters/{uid}.json`.
- **Snapshot de Batalha:** Ao executar `save_combat_state()`, a névoa corrente é preservada no arquivo incremental em `creations/encounters/saves/{uid}_save.json`.

---

## 4. Fluxo de Integração & Eventos

1. **Padrão Observer:** Ao alterar qualquer célula, o `FogManager` executa `notify_listeners()`.
2. **Propagação Reativa:** O `CombatManager` propaga a notificação para o `SessionManager`, que aciona o redesenho imediato na `DMWindow` e na `PlayerWindow`.
3. **Logs Semânticos:**
   - `[INFO] [src.domain.models.fog_manager]: Névoa de guerra aplicada a todas as 300 células (25x12).`
   - `[INFO] [src.manager.combat_manager]: Névoa de guerra (45 células) salva com sucesso em 'encounter_01.json'.`
