# 🛡️ Tokens Táticos, Badges Orbitais & Portes de Criaturas

Este documento especifica a renderização de tokens circulares Dark Fantasy ([`SpriteFactory`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/sprite_factory.py), [`token_badge_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/token_badge_renderer.py)), o atlas de ícones em subtexturas 16x16px ([`StatusIconAtlas`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/utils/status_icon_atlas.py)), o algoritmo orbital do relógio de 12 horas ([`TokenStatusRenderer`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/renderers/token_status_renderer.py)) e as regras de ocupação matricial por porte de criatura D&D 5E.

---

## 1. Responsabilidade do Módulo & Orquestração

O subsistema é responsável pela representação visual de personagens, monstros e efeitos mágicos no grid de combate. Ele gera identificadores inteligentes para os badges, posiciona ícones de status ao redor do perímetro circular sem sobreposições e aplica as regras de tamanho e colisão D&D 5E ($1\times1$, $2\times2$, $3\times3$, $4\times4$).

### Mapeamento de Arquivos-Fonte:
- [`src/ui/sprites/sprite_factory.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/sprite_factory.py): Fábrica centralizada de sprites, props estáticos/animados e tokens.
- [`src/ui/sprites/token_badge_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/token_badge_renderer.py): Algoritmo de extração de iniciais inteligentes e renderizador do corpo do token.
- [`src/ui/renderers/token_status_renderer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/renderers/token_status_renderer.py): Motor trigonométrico de posicionamento orbital dos badges de vida e condições.
- [`src/ui/utils/status_icon_atlas.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/utils/status_icon_atlas.py): Carregador e fatiador do atlas `assets/sprites/status_icons.png`.
- [`src/ui/sprites/combat_token.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/combat_token.py): Entidade visual do token com suporte a interpolação suave (*Lerp*).

---

## 2. Modelagem de Dados e Schemas

### 2.1. Atlas de Ícones de Status (`assets/sprites/status_icons.png`)
O spritesheet possui grade de células de $16 \times 16\text{px}$, fatiadas e armazenadas em cache pelo `StatusIconAtlas`:

```
   Coluna:    0            1            2            3            4            5            6            7            8            9           10
 Linha 0: [Verde >50%] [Amarelo 25-50%] [Vermelho <25%]
 Linha 1: [Envenenado] [Cego]       [Amedrontado] [Enfeitiçado] [Restringido] [Surdo]      [Petrificado] [Paralisado] [Invisível]   [Atordoado]  [Caído/Prone]
```

### 2.2. Mapeamento de Coordenadas do Atlas

```python
COORDINATE_MAP = {
    # Linha 0: Vitalidade
    "health_green": (0, 0),
    "health_yellow": (1, 0),
    "health_red": (2, 0),
    # Linha 1: 11 Condições Canônicas D&D 5E
    "poisoned": (0, 1),
    "blinded": (1, 1),
    "frightened": (2, 1),
    "charmed": (3, 1),
    "restrained": (4, 1),
    "deafened": (5, 1),
    "petrified": (6, 1),
    "paralyzed": (7, 1),
    "invisible": (8, 1),
    "stunned": (9, 1),
    "prone": (10, 1),
}
```

---

## 3. Regras de Negócio e Casos de Borda (Edge Cases)

### 3.1. Algoritmo Orbital do Relógio de 12 Horas

```
                         [12h: Badge de Vida]
                             (θ = 90°)
                                 │
                 10h ────────────┼──────────── 2h
                                 │
               9h ───────────────┼─────────────── 3h
                                 │
                 8h ─────────────┼───────────── 4h
                                 │
                         [6h: Simetria Condições]
                             (θ = 270°)
```

1. **Posição 12h ($\theta = 90^\circ$): Indicador de Vitalidade (Health Badge)**
   - Reservada exclusivamente para a faixa de vida calculada:
     - `health_green`: $\text{HP} > 50\%$
     - `health_yellow`: $25\% \le \text{HP} \le 50\%$
     - `health_red`: $\text{HP} < 25\%$ (ou $\text{HP} \le 0$)
   - *Exceção:* Tokens neutros sem vida gerenciada (`EntityType.NEUTRAL` com $\text{max\_hp} \le 1$) omitem o badge de 12h.

2. **Posições de Condições (1h a 11h): Distribuição Progressiva Bilateral**
   - As condições ativas são distribuídas simetricamente em torno do eixo inferior ($270^\circ$ / 6h).
   - **Passo Angular Dinâmico ($\Delta\theta$):**
     - Para $N \le 8$ condições: $\Delta\theta = 40.0^\circ$ (fixo).
     - Para $N \in [9, 11]$ condições: interpolação linear reduzindo até $\Delta\theta = 30.0^\circ$ em $N = 11$:
       $$\Delta\theta = 40.0 - (N - 8) \times \frac{10}{3}$$
   - **Fórmula do Ângulo da $i$-ésima Condição ($i = 0 \dots N-1$):**
     $$\theta_i = 270.0^\circ + \left(i - \frac{N - 1}{2}\right) \times \Delta\theta$$
   - **Coordenadas Cartesianas de Mundo/Tela $(x_i, y_i)$:**
     $$R_{\text{orbita}} = R_{\text{token}} + \frac{\text{icon\_size}}{2}$$
     $$x_i = C_x + R_{\text{orbita}} \times \cos(\text{radians}(\theta_i)), \quad y_i = C_y + R_{\text{orbita}} \times \sin(\text{radians}(\theta_i))$$

---

### 3.2. Categorias de Porte D&D 5E & Ocupação Matricial

| Categoria D&D 5E | Quadrados ($N \times N$) | Diâmetro Físico | Âncora Geométrica de Snap |
| :--- | :--- | :--- | :--- |
| **Tiny / Small / Medium** | $1 \times 1$ | 5ft ($1\text{ célula}$) | **Centro da Célula** $(\text{col} + 0.5, \text{row} + 0.5)$ |
| **Large** | $2 \times 2$ | 10ft ($4\text{ células}$) | **Interseção das Linhas** $(\text{col} + 1.0, \text{row} + 1.0)$ |
| **Huge** | $3 \times 3$ | 15ft ($9\text{ células}$) | **Centro da Célula Central** $(\text{col} + 1.5, \text{row} + 1.5)$ |
| **Gargantuan** | $4 \times 4$ | 20ft ($16\text{ células}$) | **Interseção das Linhas** $(\text{col} + 2.0, \text{row} + 2.0)$ |

- **Validação de Transitabilidade (`is_walkable_for_size`):**
  Uma criatura de porte Large ($2\times2$) ou superior só pode ocupar ou transitar por uma posição se **todas as $N \times N$ células sob seu perímetro** permitirem passagem (`blocks_movement == False` e limites válidos do grid).

---

### 3.3. Algoritmo de Extração de Iniciais (`extract_badge_text`)

O sistema extrai identificadores compactos de 1 a 4 caracteres para exibição no centro do token:
1. **Sufixo Numérico Arábico:** `"Kobold 1"` $\to$ `"K1"`, `"Bandido #3"` $\to$ `"B3"`.
2. **Sufixo Romano:** `"Zumbi IV"` $\to$ `"Z-4"`, `"Esqueleto II"` $\to$ `"E-2"`.
3. **Sufixo de Letra Única:** `"Cultista A"` $\to$ `"C-A"`, `"Lobo B"` $\to$ `"L-B"`.
4. **Nomes Compostos:** `"Bruenor Martelo"` $\to$ `"BM"`, `"Mago Cinzento da Colina"` $\to$ `"MC"`.
5. **Nomes Simples:** `"Ogre"` $\to$ `"OGRE"`, `"Artemis"` $\to$ `"ARTE"`.

---

## 4. Fluxo de Integração & Eventos

1. **Instanciação Padronizada:** A criação de sprites utiliza exclusivamente `SpriteFactory.create_entity_token_sprite()` ou `SpriteFactory.draw_tactical_token()`.
2. **Renderização Pixelated em GPU:** Texturas de status do atlas e artes de tokens são desenhadas com `pixelated=True`, garantindo nitidez sem borrões de interpolação bilinear.
3. **Sombra e Fundo Protetor:** Cada badge orbital é desenhado sobre um disco de fundo escuro `(18, 24, 34, 230)` com contorno `(50, 65, 90, 200)` e sombra projetada, assegurando legibilidade sobre qualquer tipo de terreno.
