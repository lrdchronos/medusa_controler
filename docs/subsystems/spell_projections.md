# 🔮 Projeção Tática de Magias & Áreas de Efeito (Spell AoE)

Este documento especifica a geometria analítica vetorial 2D/3D, cálculo de interseção com terreno e renderização acelerada por GPU do subsistema de **Áreas de Efeito (AoE)** de feitiços de D&D 5E ([`SpellTemplate`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/spell_template.py), [`AoECalculator`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/aoe_calculator.py) e [`GridCellHighlighter`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/components/grid_cell_highlighter.py)).

---

## 1. Responsabilidade do Módulo & Orquestração

O subsistema de magias permite ao Dungeon Master posicionar, rotacionar (yaw horizontal), inclinar (pitch vertical) e dimensionar áreas de efeito táticas canônicas de D&D 5E. O motor calcula em tempo real as células da grade afetadas e as projeta simultaneamente na TV dos jogadores e no mini-mapa do Mestre.

### Mapeamento de Arquivos-Fonte:
- [`src/domain/models/spell_template.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/models/spell_template.py): Objeto de valor imutável para parametrização do template de magia.
- [`src/domain/rules/aoe_calculator.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/aoe_calculator.py): Motor analítico desacoplado de testes de interseção geométrica 2D e 3D.
- [`src/domain/rules/spell_projection_controller.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/spell_projection_controller.py): Controlador de mutações imutáveis e mira.
- [`src/ui/components/grid_cell_highlighter.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/components/grid_cell_highlighter.py): Componente de renderização de destaque em lote via GPU (`ShapeElementList`).
- [`src/ui/dm/spell_aoe_panel.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/dm/spell_aoe_panel.py): Painel de controle na `DMWindow` com campos `SmartTextInput` e seletor de formas.
- [`src/ui/utils/aoe_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/utils/aoe_renderer.py): Desenho dos contornos vetoriais e guias de mira da magia.

---

## 2. Modelagem de Dados e Schemas

### 2.1. Formatos Canônicos D&D 5E (`AoEShape`)

```python
class AoEShape(Enum):
    CIRCLE = "circle"  # Círculo (Projeção plana 2D)
    SQUARE = "square"  # Quadrado (Projeção plana 2D)
    SPHERE = "sphere"  # Esfera (Volumétrica 3D)
    CUBE = "cube"      # Cubo (Volumétrica 3D com rotação yaw/pitch)
    CONE = "cone"      # Cone (Volumétrico 3D com abertura canônica de 53.13°)
    LINE = "line"      # Linha / Cilindro (Volumétrica 3D com comprimento e largura)
```

### 2.2. Estrutura Imutável `SpellTemplate`

```python
class SpellTemplate:
    def __init__(
        self,
        shape: Union[AoEShape, str] = AoEShape.CIRCLE,
        size_feet: float = 20.0,
        width_feet: float = 5.0,
        rotation_degrees: float = 0.0,
        origin_world: Tuple[float, float] = (0.0, 0.0),
        origin_z_feet: float = 0.0,
        pitch_degrees: float = 0.0,
        is_active: bool = False,
        is_visible: bool = True,
    ) -> None: ...
```

---

## 3. Geometria Analítica e Regras de Negócio

O `AoECalculator` opera desacoplado de resoluções de tela fixas, convertendo coordenadas através da métrica dinâmica `pixels_per_foot = cell_size / feet_per_square`.

### 3.1. Interseção Volumétrica 3D contra Coluna da Célula
Para cada célula candidata $(\text{col}, \text{row})$, a coluna vertical no espaço 3D é definida por:

$$z_{\text{solo}} = \text{height}(\text{col}, \text{row}) \times \text{feet\_per\_square}$$

$$z_{\text{teto}} = z_{\text{solo}} + \text{feet\_per\_square}$$

---

### 3.2. As 6 Formas Canônicas de D&D 5E

#### 1. Círculo (2D — Ex: *Área de Silêncio*, *Emanações*)
- **Natureza:** Invariante à altitude Z (opera puramente no plano do grid).
- **Condição de Acerto:** Atinge se a distância 2D do centro da célula à origem for menor ou igual ao raio $R$:
  $$\sqrt{(c_x - o_x)^2 + (c_y - o_y)^2} \le R$$

#### 2. Quadrado (2D — Ex: *Nuvem Incendiária Plana*)
- **Natureza:** Invariante a Z. Rotacionado pelo ângulo de *yaw* ($\theta$).
- **Condição de Acerto:** Projeção no referencial local da forma $|x_{\text{local}}| \le \frac{L}{2}$ e $|y_{\text{local}}| \le \frac{L}{2}$.

#### 3. Esfera (3D — Ex: *Bola de Fogo / Fireball*)
- **Natureza:** Volumétrica 3D com centro em $(o_x, o_y, o_z)$ e raio $R$.
- **Condição de Acerto:** Calcula o raio vertical disponível na coordenada horizontal $(c_x, c_y)$:
  $$R_z = \sqrt{\max\left(0, R^2 - d_{2D}^2\right)}$$
  $$\text{Intervalo da Esfera} = [o_z - R_z, \, o_z + R_z]$$
  Intersecta se houver sobreposição com $[z_{\text{solo}}, z_{\text{teto}}]$:
  $$\max(o_z - R_z, z_{\text{solo}}) \le \min(o_z + R_z, z_{\text{teto}})$$

#### 4. Cubo (3D — Ex: *Cubo de Força*, *Faísca Estática*)
- **Natureza:** Volumétrico 3D rotacionado simultaneamente por *yaw* ($\theta$) e *pitch* ($\phi$).
- **Condição de Acerto:** Projeta as amostras da coluna da célula na base ortonormal tridimensional $(\mathbf{u}_x, \mathbf{u}_y, \mathbf{u}_z)$ e verifica inclusão no prisma $[-L/2, L/2]^3$.

#### 5. Cone (3D — Ex: *Cone de Frio / Cone of Cold*, *Sopro de Dragão*)
- **Natureza:** Vértice na origem, vetor diretor unitário $\mathbf{D} = (\cos\phi\cos\theta, \cos\phi\sin\theta, \sin\phi)$, alcance $L$.
- **Semi-Ângulo Canônico:** $\alpha = \arctan(0.5) \approx 26.565^\circ \implies \cos\alpha = \frac{2}{\sqrt{5}} \approx 0.894427$.
- **Condição de Acerto:**
  $$\text{dist}(\mathbf{P}) \le L \quad \text{e} \quad \frac{\mathbf{P} \cdot \mathbf{D}}{\|\mathbf{P}\|} \ge \cos\alpha$$

#### 6. Linha (3D — Ex: *Relâmpago / Lightning Bolt*)
- **Natureza:** Prisma retangular 3D de comprimento $L$ e largura $W$.
- **Condição de Acerto:** Projeção escalar $t = \mathbf{P} \cdot \mathbf{D} \in [0, L]$ e distância ortogonal $\|\mathbf{P} - t\mathbf{D}\| \le \frac{W}{2}$.

---

### 3.3. Controles de Mira do Dungeon Master & Snap-to-Grid (Meio Quadrado)

O posicionamento da âncora de projeção opera com **Snap-to-Grid discreto de resolução de meio quadrado ($0.5 \times \text{cell\_size}$)** implementado no `GridManager.snap_to_half_grid()`. Ao clicar ou arrastar o cursor, a âncora trava magneticamente no ponto discreto mais próximo, garantindo consistência tática e sincronia total com o grid de D&D 5E.

Para qualquer célula quadrada de lado $S = \text{cell\_size}$, existem exatamente **9 pontos de ancoragem válidos**:
1. **Centro da Célula:** $((\text{col} + 0.5)S, \, (\text{row} + 0.5)S)$
2. **4 Quinas (Vértices da Grade):** Interseções das linhas do grid $((\text{col} + i)S, \, (\text{row} + j)S)$ para $i, j \in \{0, 1\}$.
3. **4 Pontos Médios das Bordas:** Centros das 4 arestas divisórias $((\text{col} + 0.5)S, \, (\text{row} + j)S)$ e $((\text{col} + i)S, \, (\text{row} + 0.5)S)$ para $i, j \in \{0, 1\}$.

#### Fórmula de Discretização:
$$\text{step} = \frac{S}{2} = 0.5 \times \text{cell\_size}$$

$$\text{snap\_x} = \text{round}\left(\frac{x - \text{offset\_x}}{\text{step}}\right) \times \text{step} + \text{offset\_x}$$

$$\text{snap\_y} = \text{round}\left(\frac{y - \text{offset\_y}}{\text{step}}\right) \times \text{step} + \text{offset\_y}$$

| Ação do Mestre | Entrada / Atalho | Efeito Tático |
| :--- | :--- | :--- |
| **Posicionar Âncora (Snap)** | `Clique Esquerdo` no Mini-Mapa | Trava magneticamente a âncora da magia $(o_x, o_y)$ no ponto discreto de meio quadrado mais próximo. |
| **Arrastar Origem em Tempo Real** | `Clique Esquerdo + Arraste` | Desloca a âncora continuamente travando nos 9 pontos de ancoragem das células percorridas. |
| **Mirar Direção (Yaw)** | `Clique Direito` ou `Clique Direito + Arraste` | Rotaciona a orientação horizontal para apontar diretamente para o cursor (`atan2`). |
| **Girar Yaw (Fino)** | `Scroll do Mouse` no Mini-Mapa | Rotaciona a orientação horizontal em passos de $\pm 2^\circ$. |
| **Girar Yaw (Rápido)**| `Ctrl + Scroll` | Rotaciona a orientação horizontal em passos de $\pm 15^\circ$. |
| **Inclinar Pitch (Vertical)**| `Alt + Scroll` | Inclina a elevação vertical da magia em passos de $\pm 15^\circ$. |
| **Ajuste Fino Numérico**| Painel `SpellAoEPanel` | Edição direta de Raio/Lado, Largura, Altitude Z e Pitch via `SmartTextInput`. |

---

## 4. Hierarquia de Modos e Fluxo de Integração

### 4.1. Hierarquia de Modos de Entrada & Renderização
1. **Modo Fog ou Modo Spell Ativo:**
   - Prevalecem sobre comandos de seleção, arrasto livre e movimentação ortogonal de tokens.
   - **Suprimem / ocultam a zona azul de movimento** (`movement_highlighter.clear()`) tanto no Mini-Mapa do Mestre quanto na Tela dos Jogadores.
2. **Exclusividade Mútua (Fog vs Spell):**
   - O Modo Fog e o Modo Spell não podem estar ativos simultaneamente.
   - Ativar uma ferramenta de Fog desativa automaticamente o Modo Spell.
   - Ativar o Modo Spell redefine a ferramenta de Fog para `FogTool.NONE`.
3. **Modo Neutro de Combate:**
   - Quando nem Fog nem Spell estão ativos, os comandos de clique simples (selecionar destino), clique duplo (confirmar passo ortogonal) e drag-and-drop livre operam normalmente com exibição da zona de alcance azul.

### 4.2. Otimização com `GridCellHighlighter`
Para evitar queda de desempenho (*FPS drop*) ao destacar centenas de células no grid:
1. O método `aoe_highlighter.set_cells(aoe_cells)` atualiza o conjunto matricial.
2. Na primeira chamada de desenho, constrói uma `ShapeElementList` contendo os retângulos preenchidos e contornos em uma **única *draw call* na GPU**.
3. O componente possui *fallback* defensivo direto via `arcade.draw_rect_filled()`, garantindo execução plena em ambientes *headless* de testes unitários.
