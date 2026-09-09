# 📐 Matemática de Grid, Projeção & Coordenadas Táticas

Este documento detalha o sistema de geometria matricial, conversão espacial contínua/discreta, escala métrica de combate (D&D 5E) e algoritmos de enquadramento proporcional ([`GridManager`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/grid_manager.py)).

---

## 1. Responsabilidade do Módulo & Orquestração

O subsistema de grid é responsável por transformar pontos contínuos de tela e mundo em coordenadas matriciais discretas da grade de combate e vice-versa. Ele garante alinhamento pixel-perfect (*Snap-to-Grid*), centralização com compensação de *half-tile offset* e enquadramento visual consistente entre monitores de resoluções e proporções distintas.

### Mapeamento de Arquivos-Fonte:
- [`src/manager/grid_manager.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/manager/grid_manager.py): Núcleo matemático de projeção, enquadramento *Aspect-Fit* e conversões matriciais.
- [`src/ui/player_window.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/player_window.py): Aplicação do enquadramento de combate em tela cheia na TV.
- [`src/ui/dm/tactical_minimap.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm/tactical_minimap.py): Mini-mapa com projeção de meia-tela e desprojeção de câmera (`dm_camera.unproject()`).
- [`src/domain/models/tile_map.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/tile_map.py): Matriz lógica de propriedades de terreno e colisões indexada por célula.

---

## 2. Modelagem de Dados e Schemas

### 2.1. Estrutura de Estado do `GridManager`

```python
class GridManager:
    def __init__(
        self,
        map_width: float,
        map_height: float,
        columns: int = 25,
        feet_per_square: Union[float, int] = 5.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        scale_factor: float = 1.0,
    ) -> None: ...
```

### 2.2. Dicionário de Metadados (`to_dict()`)

```json
{
    "map_width": 1920.0,
    "map_height": 1080.0,
    "columns": 25,
    "rows": 14,
    "cell_size": 76.8,
    "feet_per_square": 5.0,
    "offset_x": 0.0,
    "offset_y": 2.4,
    "scale_factor": 1.0
}
```

### 2.3. Métricas e Propriedades Computadas

| Propriedade | Tipo | Fórmula Matemática | Descrição |
| :--- | :--- | :--- | :--- |
| `cell_size` | `float` | $\text{cell\_size} = \frac{\text{map\_width}}{\text{columns}}$ | Dimensão em pixels do lado do quadrado da grade. |
| `rows` | `int` | $\text{rows} = \max\left(1, \left\lceil \frac{\text{map\_height}}{\text{cell\_size}} \right\rceil\right)$ | Quantidade de linhas calculada proporcionalmente à altura do mapa. |
| `feet_per_square` | `float` | $\text{feet\_per\_square}$ (padrão $5.0$) | Escala tática de pés por quadrado da grade no sistema D&D 5E. |
| `pixels_per_foot` | `float` | $\text{pixels\_per\_foot} = \frac{\text{cell\_size}}{\text{feet\_per\_square}}$ | Fator de conversão métrica contínua utilizado para raios e alcances de magias. |

---

## 3. Regras de Negócio e Casos de Borda (Edge Cases)

### 3.1. Fórmulas de Conversão e Snap-to-Grid

#### A. Mundo Contínuo para Grade Discreta (`world_to_grid`)
Converte uma coordenada de tela/mundo $(x, y)$ em índices de coluna e linha $(\text{col}, \text{row})$ aplicando *clamping* defensivo para evitar estouro de matriz:

$$\text{col} = \max\left(0, \min\left(\text{columns} - 1, \left\lfloor \frac{x - \text{offset\_x}}{\text{cell\_size}} \right\rfloor \right)\right)$$

$$\text{row} = \max\left(0, \min\left(\text{rows} - 1, \left\lfloor \frac{y - \text{offset\_y}}{\text{cell\_size}} \right\rfloor \right)\right)$$

#### B. Grade Discreta para Centro de Mundo (`grid_to_world_center`)
Calcula o centro geométrico $(C_x, C_y)$ em pixels para posicionamento de tokens de tamanho médio ($1\times1$):

$$C_x = \text{offset\_x} + (\text{col} + 0.5) \times \text{cell\_size}$$

$$C_y = \text{offset\_y} + (\text{row} + 0.5) \times \text{cell\_size}$$

#### C. Limites da Célula em Coordenadas de Mundo (`grid_to_world_bounds`)
Retorna $(\min_x, \min_y, \max_x, \max_y)$ do retângulo da célula:

$$\min_x = \text{offset\_x} + \text{col} \times \text{cell\_size}, \quad \max_x = \min_x + \text{cell\_size}$$

$$\min_y = \text{offset\_y} + \text{row} \times \text{cell\_size}, \quad \max_y = \min_y + \text{cell\_size}$$

---

### 3.2. Âncoras Geométricas por Porte de Criatura (D&D 5E)

O ponto central de renderização de um token depende da sua ocupação matricial ($N \times N$ quadrados), calculada por `get_creature_center(col, row, size)`:

$$C_x = \text{offset\_x} + \left(\text{col} + \frac{N}{2}\right) \times \text{cell\_size}$$

$$C_y = \text{offset\_y} + \left(\text{row} + \frac{N}{2}\right) \times \text{cell\_size}$$

```
    Porte 1x1 (Medium)            Porte 2x2 (Large)             Porte 3x3 (Huge)
    ┌───────────┐                 ┌─────┬─────┐                 ┌─────┬─────┬─────┐
    │           │                 │     │     │                 │     │     │     │
    │     ●     │                 ├─────┼─────┤                 ├─────┼─────┼─────┤
    │           │                 │     │  ●  │                 │     │  ●  │     │
    └───────────┘                 └─────┴─────┘                 ├─────┼─────┼─────┤
  Âncora: Centro Célula        Âncora: Interseção Linhas        │     │     │     │
  (col + 0.5, row + 0.5)         (col + 1.0, row + 1.0)         └─────┴─────┴─────┘
                                                              Âncora: Centro Célula Central
                                                                  (col + 1.5, row + 1.5)
```

- **Criaturas $1\times1$ (Tiny, Small, Medium):** $N = 1 \implies$ Âncora no centro da célula $(\text{col} + 0.5, \text{row} + 0.5)$.
- **Criaturas $2\times2$ (Large):** $N = 2 \implies$ Âncora na **interseção das linhas da grade** $(\text{col} + 1.0, \text{row} + 1.0)$.
- **Criaturas $3\times3$ (Huge):** $N = 3 \implies$ Âncora no centro da célula central $(\text{col} + 1.5, \text{row} + 1.5)$.
- **Criaturas $4\times4$ (Gargantuan):** $N = 4 \implies$ Âncora na **interseção das linhas da grade** $(\text{col} + 2.0, \text{row} + 2.0)$.

---

### 3.3. Algoritmo de Enquadramento Proporcional (`Aspect-Fit`)

Para exibir o mapa na TV dos jogadores e no mini-mapa do Mestre sem distorção de aspecto (*aspect ratio*) nem estiramento de texturas, o `GridManager` calcula a escala uniforme máxima e offsets de centralização:

```python
@staticmethod
def calculate_aspect_fit(
    viewport_width: float,
    viewport_height: float,
    native_width: float,
    native_height: float,
) -> Tuple[float, float, float, float, float]:
    scale_x = viewport_width / native_width
    scale_y = viewport_height / native_height
    scale_factor = min(scale_x, scale_y)

    rendered_width = native_width * scale_factor
    rendered_height = native_height * scale_factor

    offset_x = (viewport_width - rendered_width) / 2.0
    offset_y = (viewport_height - rendered_height) / 2.0

    return scale_factor, rendered_width, rendered_height, offset_x, offset_y
```

---

## 4. Fluxo de Integração & Eventos

### 4.1. Ciclo de Redimensionamento (`on_resize`)
1. A janela dos jogadores ou do Mestre é redimensionada (`PlayerWindow.on_resize()`).
2. O método `player_camera.match_window()` atualiza a matriz de visualização da câmera.
3. O método interno `_calculate_combat_layout()` recalcula `draw_x, draw_y, cell_w, cell_h` chamando `GridManager.calculate_aspect_fit()`.
4. Os renderizadores em lote (`TileMapRenderer`, `GridCellHighlighter`) têm suas dimensões atualizadas antes da emissão de *draw calls*.

### 4.2. Desprojeção de Câmera no Mini-Mapa (`TacticalMiniMap`)
Quando o Mestre interage com o mini-mapa na metade direita da `DMWindow`:
1. Coordenadas brutas de tela $(S_x, S_y)$ são convertidas via `dm_camera.unproject((screen_x, screen_y))`.
2. As coordenadas resultantes são normalizadas em relação ao retângulo de desenho `_last_draw_rect`.
3. A conversão `world_to_grid()` identifica imediatamente a célula sob o cursor para arrasto de tokens, pintura de névoa ou mira de magias.
