# 🎨 Guia de Inclusão de Assets Visuais & Mapas

Este guia define os padrões técnicos, resoluções, especificações de frames e procedimentos de importação para novos recursos gráficos no **Medusa VTT** através da [`SpriteFactory`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/ui/sprites/sprite_factory.py).

---

## 📐 Especificações Técnicas de Sprites

O Medusa VTT utiliza renderização pixel-art com interpolação vizinha mais próxima (`pixelated=True`). Todos os assets devem seguir rigorosamente as dimensões canônicas:

| Tipo de Asset | Dimensão do Quadro | Quantidade de Quadros | Taxa de Reprodução | Diretório Padrão |
| :--- | :--- | :--- | :--- | :--- |
| **Props Animados Padrão** | $32 \times 32\text{px}$ | 6 quadros horizontais | 8 FPS (loop contínuo) | `assets/sprites/` |
| **Props Estáticos** | $32 \times 32\text{px}$ | 1 quadro único | Estático | `assets/sprites/` |
| **Sigil Místico (IDLE - Exceção)** | $48 \times 48\text{px}$ | 5 quadros (escalado para 92px) | 0.20s por frame (5 FPS) | `assets/sprites/medusa_idle_1.png` |
| **Atlas de Ícones de Status** | $16 \times 16\text{px}$ | Grade $11 \times 2$ subtexturas | Estático | `assets/sprites/status_icons.png` |
| **Mapas em Imagem** | Proporção $16:9$ (ex: $1920 \times 1080\text{px}$) | Imagem única | Estático | `assets/images/maps/` |
| **Imagens de Showcase (Projeção)** | Qualquer resolução (Aspect-Fit) | Imagem única | Estático | `assets/images/showcase/` |
| **Atlas de Tilesets (Aseprite)** | Tiles base em $32 \times 32\text{px}$ | Par JSON + PNG | Runtime Tileset | `assets/tilesets/` |

---

## 🔥 1. Criação de Props Animados de Cenário

Um prop animado padrão consiste em uma fita horizontal (*strip*) de **6 quadros de $32 \times 32\text{px}$**, totalizando uma imagem de $192 \times 32\text{px}$ com fundo transparente:

```
┌────────┬────────┬────────┬────────┬────────┬────────┐
│Frame 0 │Frame 1 │Frame 2 │Frame 3 │Frame 4 │Frame 5 │  (Total: 192x32px)
│(32x32) │(32x32) │(32x32) │(32x32) │(32x32) │(32x32) │
└────────┴────────┴────────┴────────┴────────┴────────┘
```

### Exemplo em Código (`SpriteFactory`):
```python
# Instanciação direta de prop animado
firepit = SpriteFactory.create_animated_prop(
    spritesheet_path="assets/sprites/firepit.png",
    scale=1.0,
    frame_count=6,
    fps=8.0,
    frame_width=32,
    frame_height=32,
)
```

---

## 🗺️ 2. Inclusão de Props em Mapas Modulares JSON

Para que um prop estático ou animado seja desenhado automaticamente sobre um mapa modular ([`creations/maps/*.json`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/creations/maps)), adicione a definição ao array `"assets"` do arquivo:

```json
{
    "tileset": "Sprite-007",
    "width": 21,
    "height": 12,
    "data": [ ... ],
    "assets": [
        {
            "sprite": "assets/sprites/firepit.png",
            "type": "spritesheet",
            "position": {
                "x": 5,
                "y": 4
            },
            "scale": 1.0
        },
        {
            "sprite": "assets/sprites/caixa_madeira.png",
            "type": "sprite",
            "position": {
                "x": 8,
                "y": 6
            },
            "scale": 1.0
        }
    ]
}
```

- `"type": "spritesheet"`: Carrega e anima em loop contínuo (6 quadros de 32x32px a 8 FPS).
- `"type": "sprite"`: Carrega como textura estática de quadro único.
- `"position"`: Coordenadas discretas $(\text{col}, \text{row})$ da célula da grade onde o objeto será ancorado.

---

## 🖼️ 3. Importação de Imagens de Showcase (Projeção)

Para disponibilizar ilustrações cinemáticas de locais, cartas de itens, enigmas ou retratos de NPCs na **Aba 1 (Cenários)**:

1. Salve os arquivos de imagem em `assets/images/showcase/` ou subpastas organizadas (ex: `assets/images/showcase/locais/`, `assets/images/showcase/npcs/`).
2. Formatos suportados: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`.
3. O `SessionManager` faz descoberta automática de novos arquivos ao inicializar a interface.
4. Ao clicar em **"Projetar na TV"**, o Medusa calcula o enquadramento *Aspect-Fit (Contain)* sem cortes e projeta a imagem instantaneamente na tela dos jogadores.

---

## 🧩 4. Importação de Atlas do Aseprite para Tilesets

Para adicionar novos conjuntos de terreno modular:
1. No **Aseprite**, exporte o tileset como **Sprite Sheet** selecionando:
   - *Output File:* `assets/tilesets/{nome_tileset}.png`
   - *JSON Data:* `assets/tilesets/{nome_tileset}.json` (formato Hash ou Array)
2. O `TilesetManager` fatia a textura em memória em $O(1)$, disponibilizando os índices de tiles para o criador de mapas e para a engine do `TileMapRenderer`.
