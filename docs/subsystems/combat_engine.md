# ⚔️ Motor de Combate, Iniciativas & Ciclo de Turnos

Este documento especifica a arquitetura do motor tático de regras de combate do Medusa VTT, detalhando o gerenciamento circular de turnos e rodadas ([`CombatManager`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/combat_manager.py)), o rastreador de iniciativas com critérios de desempate D&D 5E ([`InitiativeTracker`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/initiative_tracker.py)), a manipulação de combatentes em runtime ([`CombatantRules`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/combatant_rules.py)) e a persistência de snapshots de sessão ([`CombatStateSerializer`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/combat_serializer.py)).

---

## 1. Responsabilidade do Módulo & Orquestração

O subsistema de combate governa a ordem de ação dos combatentes, validação de danos/curas, aplicação de condições de status, movimentação matricial de tokens no grid, gerenciamento de emboscadas e visibilidade oculta (`hidden: True`), e persistência incremental do estado da mesa.

### Mapeamento de Arquivos-Fonte:
- [`src/manager/combat_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/combat_manager.py): Controlador central do combate, agregador de regras e despachante de eventos.
- [`src/domain/rules/initiative_tracker.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/initiative_tracker.py): Algoritmo de rolagens, desempates canônicos D&D 5E, avanço/retrocesso de turnos e incremento de rodadas.
- [`src/domain/rules/combatant_rules.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/combatant_rules.py): Regras de spawn de entidades em runtime, revelação de emboscadores e alteração de visibilidade tática.
- [`src/domain/rules/combat_serializer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/combat_serializer.py): Serialização e desserialização de snapshots em `creations/encounters/saves/`.
- [`src/ui/initiative_hud.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/initiative_hud.py): Fita flutuante translúcida no topo da tela dos jogadores com realce de turno ativo.

---

## 2. Modelagem de Dados e Schemas

### 2.1. Modelos de Entidades
- **`Entity` ([`entity.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/entity.py)):** Classe base abstrata contendo `uid`, `name`, `current_hp`, `max_hp`, `armor_class`, `position` (x, y), `conditions` (`Set[str]`), `is_hidden` (`bool`), `is_alive` (`bool`), `initiative_score` (`int`) e `initiative_mod` (`int`).
- **`EntityType`:** Enumeração canônica:
  - `PLAYER`: Personagens dos jogadores (borda azul).
  - `MONSTER`: Criaturas e oponentes (borda vermelha carmim).
  - `NEUTRAL`: Efeitos mágicos dinâmicos, summons, NPCs neutros (borda dourada/âmbar).
- **`DynamicToken`:** Especialização leve instanciada dinamicamente para tokens spawnados durante a batalha.

```python
class EntityType(Enum):
    PLAYER = "player"
    MONSTER = "monster"
    NEUTRAL = "neutral"
```

---

## 3. Regras de Negócio e Casos de Borda (Edge Cases)

### 3.1. Algoritmo de Passagem de Turno com Pulo Seguro de Abatidos
O avanço (`advance_turn`) e retrocesso (`rewind_turn`) de turnos operam de forma circular sobre a lista `turn_order`. Para garantir que o jogo nunca entre em *loop infinito* quando todos ou a maioria dos combatentes estiverem mortos/inconscientes ($HP \le 0$ ou `is_alive == False`):

```python
@staticmethod
def advance_turn(
    turn_order: List[Entity],
    current_index: int,
    round_number: int,
) -> Tuple[int, int, Optional[Entity]]:
    if not turn_order:
        return -1, round_number, None

    # Verificação prévia O(N): há pelo menos um combatente vivo?
    has_alive = any(c.is_alive and c.current_hp > 0 for c in turn_order)
    if not has_alive:
        logger.info("Todos os combatentes estão mortos/incapacitados. Turno estático.")
        return current_index, round_number, None

    num_combatants = len(turn_order)
    count = 0
    new_index = current_index
    new_round = round_number

    # Percorre no máximo uma volta completa (count < num_combatants)
    while count < num_combatants:
        new_index = (new_index + 1) % num_combatants
        if new_index == 0:
            new_round += 1  # Incrementa rodada ao completar o ciclo
        candidate = turn_order[new_index]
        if candidate.is_alive and candidate.current_hp > 0:
            break
        count += 1

    active_character = turn_order[new_index] if 0 <= new_index < len(turn_order) else None
    return new_index, new_round, active_character
```

---

### 3.2. Tratamento de Criaturas Ocultas (`hidden: True`)
1. **Isolamento Fora da Fita de Turnos:**
   - Criaturas marcadas com `is_hidden = True` ficam armazenadas no dicionário `hidden_combatants: Dict[str, Entity]` e **NÃO** entram na lista `turn_order` nem recebem rolagem no modal de staging de iniciativas.
   - Na tela do Mestre (`DMWindow`), tokens ocultos são renderizados com 50% de opacidade (`alpha = 128`) e badge de olho (`👁️`). Na tela dos jogadores (`PlayerWindow`), são completamente omitidos.
2. **Revelação Dinâmica em Batalha (`reveal_combatant`):**
   - Ao ser revelado pelo Mestre (via menu de contexto ou clique direito), o combatente é transferido de `hidden_combatants` para `turn_order`.
   - **Regra de Emboscada (Immediate Action):** A criatura revelada é inserida imediatamente na posição seguinte ao combatente do turno ativo (`target_index = current_turn_index + 1`), assumindo a vez logo a seguir sem quebrar a rodada.

---

### 3.3. Inserção de Tokens Dinâmicos em Tempo de Execução (`NEUTRAL`)
O Mestre pode adicionar novos tokens durante a batalha ativa através do modal `AddTokenModal`:
- **Opção "Próximo a Agir" (`initiative_slot == "next"`):** Insere o novo combatente em `current_turn_index + 1`.
- **Opção "Final da Rodada" (`initiative_slot == "end"`):** Insere o novo combatente no fim da lista `turn_order.append(entity)`.

---

### 3.4. Sistema de Save Incremental de Combate
- Os snapshots de sessão são gravados em `creations/encounters/saves/{uid}_save.json`.
- Ao salvar, o arquivo armazena: número da rodada, índice do turno ativo, ordem exata da fita de turnos, HP atual de cada entidade, condições de status ativas, posições $(x, y)$, matriz de células da névoa de guerra e lista de tokens ocultos.
- **Restauração Perfeita:** Ao invocar `resume_encounter_save()`, entidades dinâmicas spawnadas no meio da batalha são reidratadas como `DynamicToken` e o combate recomeça exatamente da vez e rodada em que foi interrompido.

---

## 4. Fluxo de Integração & Eventos

1. **Notificação Reativa (Observer Pattern):**
   - Qualquer mutação em `CombatManager` (`apply_damage`, `apply_heal`, `set_combatant_position`, `toggle_condition`, `next_turn`) invoca `notify_listeners()`.
2. **Sincronização em Tempo Real:**
   - `DMWindow` atualiza o painel lateral de status e a renderização do mini-mapa.
   - `PlayerWindow` atualiza a fita de iniciativas `InitiativeHUD` e calcula a interpolação suave (*Lerp*) de transição de posição dos tokens.
3. **Logs Semânticos:**
   - `[INFO] [src.manager.combat_manager]: Dano aplicado: 12 em Goblin Sentinela (HP: 0/12)`
   - `[INFO] [src.domain.rules.combatant_rules]: Combatente 'Ogro Chefe' revelado e posicionado como próximo a agir na fila de turnos.`
   - `[INFO] [src.domain.rules.initiative_tracker]: Passar Turno: combatente ativo 'Artemis' (Rodada 2).`
