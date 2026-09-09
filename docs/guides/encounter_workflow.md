# 🎲 Guia Operacional: Ciclo de Vida do Encontro de Combate

Este guia descreve o fluxo de ponta a ponta para preparação, configuração tática, rolagem de iniciativas, condução de batalha e persistência de sessões de combate no **Medusa VTT**.

---

## 🗺️ Visão Geral do Ciclo de Vida

```
  ┌─────────────────────────┐
  │  1. Formulário Inicial  │  Definição de metadados, mapa (imagem ou tilemap),
  │   (Encounter Creator)   │  dimensões de grade e seleção do roster de heróis e monstros.
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ 2. Palco Tático Staging │  Posicionamento visual por Drag & Drop, definição de
  │   (Posicionamento)      │  emboscadores ocultos (50% opacidade) e gravação JSON.
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ 3. Staging de Iniciativa│  Rolagem D&D 5E (1d20 + DEX), desempate por modificador,
  │   (InitiativeModal)     │  ajuste manual fino e isolamento de criaturas ocultas.
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │   4. Batalha Ativa      │  Gerenciamento de turnos e rodadas, dano/cura com 1 clique,
  │      (CombatTab)        │  interpolação Lerp, projeção de magias AoE e névoa de guerra.
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ 5. Save State & Retomada│  Gravação de snapshot em creations/encounters/saves/{uid}_save.json
  │   (Sessão Persistente)  │  e retomada instantânea de onde o combate parou.
  └─────────────────────────┘
```

---

## 📝 Etapa 1: Formulário de Configuração do Encontro

Na `DMWindow`, selecione a **Aba 3 (Criador de Encontros)**:

1. **Metadados:**
   - Preencha o **Título do Encontro** (ex: *"Emboscada na Trilha do Vale"*) e a **Descrição**.
2. **Seleção do Mapa:**
   - Escolha entre um mapa em **Imagem Contínua** (`assets/images/maps/*.png`) ou um **Layout Modular de Tileset** (`creations/maps/*.json`).
3. **Parâmetros da Grade Tática:**
   - Defina o número de **Colunas** (padrão: 25 colunas) e a escala de **Pés por Quadrado** (padrão: 5ft).
4. **Composição do Roster:**
   - **Personagens Jogadores (PCs):** Selecione as fichas dos heróis salvas em `creations/characters/`.
   - **Monstros & NPCs:** Utilize o campo de busca com filtro em tempo real para selecionar criaturas do bestiário (`presets/monsters/`) e definir a quantidade de instâncias.
5. Clique no botão **"Avançar para Posicionamento ➡️"**.

---

## 🎯 Etapa 2: Palco Tático & Staging de Posições

No visualizador interativo de posicionamento:

1. **Arrastar e Soltar (Drag & Drop):**
   - Clique e arraste os tokens para posicioná-los estrategicamente sobre o mapa. O sistema realiza *Snap-to-Grid* automático no centro de cada célula (ou interseção para criaturas grandes).
2. **Configuração de Emboscadores (Tokens Ocultos):**
   - Clique com o botão direito sobre um monstro ou ative o botão de visibilidade. Tokens com `is_hidden = True` recebem o ícone `👁️` e 50% de opacidade no painel do Mestre e **NÃO** serão exibidos na TV dos jogadores.
3. **Conclusão:**
   - Clique em **"Salvar Encontro 💾"**. O arquivo JSON canônico será gerado em `creations/encounters/{uid}.json`.

---

## 🎲 Etapa 3: Modal de Staging de Iniciativas

Na **Aba 0 (Encontros)**, localize o encontro salvo e clique em **"Iniciar Combate"**:

1. O modal **`InitiativeModal`** surge em overlay:
   - Os dados são rolados automaticamente: $1d20 + \text{Modificador de DEX}$.
   - O sistema aplica os desempates canônicos D&D 5E ($\text{Score} \to \text{Mod DEX} \to \text{Nome}$).
   - **Importante:** Criaturas ocultas (`is_hidden: True`) são automaticamente omitidas da rolagem inicial.
2. **Ajuste Manual:**
   - O Mestre pode clicar em qualquer valor numérico de iniciativa e digitar o resultado rolado fisicamente pelos jogadores na mesa.
3. Clique em **"Confirmar e Iniciar Combate ⚔️"**:
   - A máquina de estados da sessão muda para `DisplayState.COMBAT`.
   - A TV dos jogadores ativa a visualização em tela cheia com mapa, grade, tokens e a fita de iniciativas (`InitiativeHUD`) no topo.

---

## ⚔️ Etapa 4: Batalha Ativa & Condução Tática

Durante a rodada na **Aba 2 (Combate)**:

1. **Passagem de Turnos (`Passar Turno` / `Retroceder Turno`):**
   - O ponteiro de turno avança circularmente. Combatentes mortos ou inconscientes ($HP \le 0$) são pulados de forma transparente sem travar o ciclo.
   - Ao completar a volta, a fita incrementa automaticamente o contador de **Rodada**.
2. **Despacho Ágil de Dano e Cura:**
   - Clique em um combatente para selecioná-lo.
   - Utilize os botões de ajuste rápido (`-10`, `-5`, `-1`, `+1`, `+5`, `+10`) ou digite um valor no campo de dano/cura.
3. **Condições de Status:**
   - Clique nos ícones da paleta de condições (Envenenado, Cego, Derrubado, etc.) para alternar o status do token. Os badges orbitais aparecem instantaneamente ao redor da borda do token na TV.
4. **Projeção de Magias AoE:**
   - Ative o painel `SpellAoEPanel` para projetar Cones, Esferas, Linhas, Cubos ou Círculos com rotação (*Scroll*) e inclinação 3D (*Alt + Scroll*).
5. **Névoa de Guerra:**
   - Pinte ou revele áreas do mapa em tempo real utilizando o painel `FogControlPanel`.

---

## 💾 Etapa 5: Salvamento Incremental e Retomada

1. **Gravação de Progresso:**
   - A qualquer momento durante a batalha, clique no botão **"Salvar Estado de Combate"** na barra superior.
   - O snapshot do encontro é gravado em `creations/encounters/saves/{uid}_save.json` sem modificar o arquivo de encontro base.
2. **Retomada de Sessão:**
   - Em sessões futuras, ao acessar a Aba 0 (Encontros), encontros com progresso salvo exibirão o botão dourado **"Retomar Sessão Salva 🔄"**.
   - O combate será restaurado na mesma rodada, no turno do mesmo personagem, com os HPs e células de névoa exatamente como foram deixados.
