# 🔄 Máquina de Estados Global & Sincronização Observer

Este documento especifica a **Máquina de Estados de Exibição** (`DisplayState`), a camada de orquestração centralizada no [`SessionManager`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/session_manager.py) e o modelo de **Sincronização Reativa (Observer Pattern)** entre as janelas do Mestre ([`DMWindow`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm_window.py)) e dos Jogadores ([`PlayerWindow`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/player_window.py)).

---

## 1. Responsabilidade do Módulo & Orquestração

O subsistema de estados é a **Single Source of Truth (SSoT)** da sessão do Medusa VTT. Ele governa o modo visual projetado na TV da mesa e sincroniza instantaneamente qualquer comando administrativo ou tático emitido pelo Dungeon Master.

### Mapeamento de Arquivos-Fonte:
- [`src/manager/session_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/session_manager.py): Controlador de sessão, hospedeiro de `DisplayState`, descoberta de arquivos e despachante de eventos.
- [`src/manager/combat_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/combat_manager.py): Motor tático de combate agregado ao `SessionManager`.
- [`src/ui/player_window.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/player_window.py): Janela de visualização limpa na TV, observadora estrita do `DisplayState`.
- [`src/ui/dm_window.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm_window.py): Painel administrativo do Mestre, emissor primário de transições de estado.
- [`src/ui/renderers/player_view_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/renderers/player_view_renderer.py): Rotinas de desenho especializadas por estado.

```
                  ┌─────────────────────────────────────────┐
                  │              DMWindow                   │
                  │   (Dispara Comandos / Altera Estados)   │
                  └────────────────────┬────────────────────┘
                                       │ 1. Invoca ação
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │           SessionManager                │
                  │  - display_state: DisplayState          │
                  │  - combat_manager: CombatManager        │
                  │  - projected_image: Optional[Path]      │
                  └────────────────────┬────────────────────┘
                                       │ 2. Notifica Listeners
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │       DMWindow        │             │     PlayerWindow      │
        │  (Atualiza Mini-Mapa  │             │ (Muda Modo de Desenho │
        │   e Indicadores HUD)  │             │   na Viewport da TV)  │
        └───────────────────────┘             └───────────────────────┘
```

---

## 2. Modelagem de Dados e Schemas

### 2.1. Enumeração `DisplayState`
Define os três estados canônicos de exibição da mesa:

```python
class DisplayState(Enum):
    IDLE = "IDLE"              # Tela de descanso / espera ("Aguardando o Mestre...")
    PROJECTION = "PROJECTION"  # Projeção de imagens avulsas (NPCs, cenários, itens)
    COMBAT = "COMBAT"          # Modo de combate ativo com mapa, tokens e HUD de iniciativa
```

| Estado | Contexto de Uso | Renderização na `PlayerWindow` |
| :--- | :--- | :--- |
| **`IDLE`** | Intervalos entre cenas, pausas, descanso ou início de sessão. | Fundo dark `#0E1218`, Sigil Místico animado (48x48 escalado para 92px, 5 frames a 0.20s/frame) e texto "Aguardando o Mestre...". |
| **`PROJECTION`** | Apresentação imersiva de cartas de itens, retratos de NPCs, enigmas ou ilustrações de ambiente. | Imagem centralizada com enquadramento proporcional *Aspect-Fit (Contain)* sobre fundo grafite escuro `#0A0E14` com moldura luminosa. |
| **`COMBAT`** | Batalhas táticas, exploração de masmorras com grid e encontros táticos. | Viewport em tela cheia com mapa (imagem ou *TileMap* em lote GPU), grid tático de alto contraste, tokens interpolados (*Lerp*), névoa de guerra oclusiva (100% preta) e *InitiativeHUD* flutuante no topo. |

### 2.2. Contrato de Interface do `SessionManager`

```python
class SessionManager:
    # Propriedades de Estado
    @property
    def display_state(self) -> DisplayState: ...
    @property
    def combat_manager(self) -> CombatManager: ...
    @property
    def projected_image_path(self) -> Optional[str]: ...
    @property
    def is_combat_active(self) -> bool: ...
    @property
    def is_idle(self) -> bool: ...
    @property
    def is_projecting(self) -> bool: ...

    # Assinatura de Observer
    def add_listener(self, listener: Callable[[], None]) -> None: ...
    def remove_listener(self, listener: Callable[[], None]) -> None: ...
    def notify_listeners(self) -> None: ...

    # Mutadores de Estado
    def set_display_state(self, state: DisplayState) -> None: ...
    def project_image(self, image_path: str) -> bool: ...
    def start_encounter(self, encounter_id_or_path: str) -> None: ...
    def resume_encounter_save(self, encounter_id_or_path: str) -> bool: ...
    def end_combat(self, return_to: DisplayState = DisplayState.IDLE) -> None: ...
    def clear_display_to_idle(self) -> None: ...
```

---

## 3. Regras de Negócio e Casos de Borda (Edge Cases)

### 3.1. Transições de Estado e Flush Reativo
1. **Transição para fora de `COMBAT`:**
   - Ao transicionar de `COMBAT` para `IDLE` ou `PROJECTION`, a `PlayerWindow` executa imediatamente `token_sprites.clear()` e descarta a instância ativa de `TileMapRenderer` (`self._tilemap_renderer = None`). Isso evita que dados obsoletos de posições ou colisões permaneçam na memória de vídeo.
2. **Execução Condicional da Animação do Sigil:**
   - O temporizador interno de animação (`_idle_anim_timer`) e o incremento de quadros (`_idle_cur_frame = (cur + advance) % 5`) são processados no `on_update()` **exclusivamente** quando `display_state == DisplayState.IDLE`. Nos demais estados, o ciclo de CPU/GPU para cálculo de frames de descanso é zerado.

### 3.2. Ciclo de Vida da Janela Secundária (Soft Close vs. Hard Close)
- **Soft Close (`on_close` pelo SO via botão 'X'):**
  - Quando o usuário clica no botão fechar da `PlayerWindow`, a janela NÃO é destruída no OpenGL (o que invalidaria o contexto do Arcade). Ela invoca `set_visible(False)`, pausa a escuta de listeners (`cleanup_resources(hard=False)`) e notifica a `DMWindow`.
- **Reconexão Transparente (`reconnect_listeners`):**
  - Ao reabrir a janela dos jogadores via botão "Reabrir Tela dos Jogadores" na barra superior da `DMWindow`, os listeners de sessão e combate são reinscritos sem duplicidade e o estado visual correspondente ao `display_state` atual é restabelecido de imediato.
- **Hard Close (`close(hard=True)`):**
  - Executado apenas no encerramento global da aplicação (`main.py`), efetuando desescalonamento do clock do Pyglet (`clock.unschedule`), limpeza total dos caches de textura/texto e destruição definitiva do contexto.

---

## 4. Fluxo de Integração & Eventos

### 4.1. Sincronização Thread-Safe no Loop do Arcade
Como o Python Arcade opera sobre um *Single-Threaded Event Loop* baseado em Pyglet/OpenGL, toda a comunicação entre o `SessionManager`, `DMWindow` e `PlayerWindow` ocorre por **notificações síncronas diretas**:
1. O Mestre clica em uma ação na `DMWindow` (ex: projeta uma imagem na aba Cenários).
2. O método `SessionManager.project_image()` valida a existência física do arquivo, atualiza `__display_state = DisplayState.PROJECTION` e aciona `notify_listeners()`.
3. Todos os observadores registrados executam suas rotinas de invalidação de layout.
4. No próximo ciclo de `on_draw()` da `PlayerWindow`, o despachante lê `current_state` e redireciona para `PlayerViewRenderer.draw_projection()`.
5. Durante o `on_update()` da `PlayerWindow`, é chamado defensivamente `dm_window.pump_events()` para garantir que eventos pendentes da interface do Mestre sejam processados mesmo em cenários de alta carga gráfica.

### 4.2. Tópicos de Logging Semântico
Toda mudança de estado emite registros estruturados em UTF-8:
- `[INFO] [src.manager.session_manager]: Transição de estado de exibição: IDLE -> COMBAT`
- `[INFO] [src.manager.session_manager]: Projetando imagem: 'castelo_nevoa.png' (C:\Medusa\assets\images\showcase\castelo_nevoa.png)`
- `[INFO] [src.ui.player_window]: PlayerWindow redimensionada para 1920x1080 (fullscreen=True). Viewport recalculada.`
