# 🗄️ Schemas JSON & Normalização de Dados

Este documento formaliza os contratos de dados, esquemas JSON e o padrão de normalização entre regras estáticas canônicas ([`presets/`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/presets)) e instâncias mutáveis de campanha ([`creations/`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/creations)).

---

## 1. Responsabilidade do Módulo & Orquestração

O Medusa adota uma **Arquitetura Orientada a Dados (Data-Driven)** com separação rígida de responsabilidades:
- **`presets/` (Imutável / Read-Only):** Regras estáticas, definições do sistema D&D 5E, tabelas de progressão de classes, raças e estatísticas do bestiário.
- **`creations/` (Mutável / State-Driven):** Instâncias dinâmicas de campanha, fichas de personagens com recursos gastos, mapas modulares customizados, definições de encontros e snapshots salvos de combate em andamento.

### Mapeamento de Loaders e Builders:
- [`src/domain/loaders/monster_loader.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/loaders/monster_loader.py): Leitura e instanciação do bestiário de `presets/monsters/`.
- [`src/domain/loaders/character_loader.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/loaders/character_loader.py): Leitura e validação de fichas de `creations/characters/`.
- [`src/domain/loaders/tile_map_loader.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/loaders/tile_map_loader.py): Parser de mapas matriciais de `creations/maps/`.
- [`src/domain/loaders/encounter_loader.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/loaders/encounter_loader.py): Carregador central de encontros de `creations/encounters/`.
- [`src/domain/rules/combat_serializer.py`](file:///c:/Users/aguia/OneDrive/Documentos/Medusa/medusa_controler/src/domain/rules/combat_serializer.py): Persistência de snapshots de combate em `creations/encounters/saves/`.

---

## 2. Modelagem de Dados e Schemas

### 2.1. Preset de Monstro (`presets/monsters/{uid}.json`)

```json
{
    "uid": "kobold",
    "source": "monster_manual",
    "page": 194,
    "name": "Kobold",
    "alignment": "LE",
    "size": "Small",
    "type": "Humanoid",
    "sub_type": "dragonborn",
    "armor_class": {
        "value": 12,
        "type": "natural"
    },
    "hit_points": {
        "average": 5,
        "formula": "2d6-2"
    },
    "speed": {
        "walk": 30,
        "fly": 0,
        "swim": 0
    },
    "ability_scores": {
        "STR": 7,
        "DEX": 15,
        "CON": 9,
        "INT": 8,
        "WIS": 7,
        "CHA": 8
    },
    "skills": {},
    "senses": {
        "darkvision": 60
    },
    "languages": ["Comum", "Dracônico"],
    "challenge_rating": 0.125,
    "xp": 25,
    "features": [
        {
            "name": "Sensibilidade à Luz Solar",
            "description": "Desvantagem em ataques e percepção visual sob luz solar."
        }
    ],
    "actions": [
        {
            "name": "Adaga",
            "type": "melee_attack",
            "attack_bonus": 4,
            "reach": 5,
            "damage_dice": "1d4",
            "damage_bonus": 2,
            "damage_type": "piercing"
        }
    ]
}
```

---

### 2.2. Ficha de Personagem do Jogador (`creations/characters/{uid}.json`)

```json
{
    "uid": "char_artemis",
    "name": "Artemis",
    "level": 3,
    "ability_scores": {
        "STR": 10,
        "DEX": 16,
        "CON": 14,
        "INT": 12,
        "WIS": 15,
        "CHA": 8
    },
    "race": {
        "race_id": "elf",
        "subrace_id": "wood_elf",
        "racial_bonuses_applied": {"DEX": 2, "WIS": 1}
    },
    "classes": [
        {
            "class_id": "ranger",
            "subclass_id": "hunter",
            "level": 3
        }
    ],
    "alignment": "chaotic_good",
    "vitality": {
        "max_hp": 28,
        "current_hp": 28,
        "temporary_hp": 0,
        "hit_die_type": 10,
        "hit_dice_remaining": 3
    },
    "resources": {
        "spell_slots_level_1": {
            "max_uses": 3,
            "current_uses": 3,
            "recharge_on": "REST_LONG"
        }
    }
}
```

---

### 2.3. Mapa Modular / TileMap (`creations/maps/{nome}.json`)

```json
{
    "tileset": "Sprite-007",
    "width": 21,
    "height": 12,
    "data": [
        [48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48],
        [48, 48, 48, 14, 16, 16, 17, 48, 48, 48, 48, 48, 48, 48, 48, 48, 48, 37, 42, 42, 47]
    ],
    "block_movement": [1, 5, 23, 32],
    "block_vision": [23],
    "cover": {
        "half": [16],
        "three_quarters": [17],
        "full": [1]
    },
    "difficult_terrain": [42],
    "heights": {
        "pos": {"x": 6, "y": 6},
        "height": 1
    },
    "assets": [
        {
            "sprite": "assets/sprites/firepit.png",
            "type": "spritesheet",
            "position": {"x": 5, "y": 4},
            "scale": 1.0
        }
    ]
}
```

---

### 2.4. Encontro de Combate (`creations/encounters/{uid}.json`)

```json
{
    "uid": "encounter_emboscada",
    "title": "Emboscada na Trilha do Vale",
    "description": "Goblins e um Ogro emboscam os aventureiros.",
    "map_type": "tilemap",
    "map_source": "creations/maps/acampamento_vale.json",
    "environment": {
        "is_sunlight": false,
        "is_raining": false
    },
    "grid": {
        "columns": 21,
        "feet_per_square": 5
    },
    "combatants": [
        {
            "entity_type": "monster",
            "monster_id": "goblin",
            "instance_name": "Goblin Sentinela",
            "position": {"x": 3, "y": 5},
            "is_hidden": true
        },
        {
            "entity_type": "monster",
            "monster_id": "ogre",
            "instance_name": "Ogro Chefe",
            "size": "Large",
            "position": {"x": 8, "y": 4},
            "is_hidden": false
        },
        {
            "entity_type": "playable_character",
            "character_id": "char_artemis",
            "position": {"x": 2, "y": 2}
        }
    ],
    "fog_of_war": [
        {"x": 3, "y": 5},
        {"x": 4, "y": 5}
    ]
}
```

---

### 2.5. Snapshot de Sessão Salva (`creations/encounters/saves/{uid}_save.json`)

```json
{
    "encounter_uid": "encounter_emboscada",
    "timestamp": "2026-09-09T18:30:00",
    "round": 2,
    "current_turn_index": 1,
    "turn_order": ["char_artemis", "ogre_1"],
    "hidden_combatants": ["goblin_sentinela_uid"],
    "fog_of_war": [
        {"x": 3, "y": 5},
        {"x": 4, "y": 5}
    ],
    "combatants_state": [
        {
            "uid": "char_artemis",
            "name": "Artemis",
            "is_alive": true,
            "current_hp": 22,
            "max_hp": 28,
            "armor_class": 15,
            "entity_type": "player",
            "size": "Medium",
            "conditions": ["poisoned"],
            "position": {"x": 4, "y": 3},
            "hidden": false
        },
        {
            "uid": "ogre_1",
            "name": "Ogro Chefe",
            "is_alive": true,
            "current_hp": 39,
            "max_hp": 59,
            "armor_class": 11,
            "entity_type": "monster",
            "size": "Large",
            "conditions": [],
            "position": {"x": 8, "y": 4},
            "hidden": false
        }
    ]
}
```

---

## 3. Regras de Negócio e Casos de Borda (Edge Cases)

### 3.1. Validações Defensivas (Poka-Yoke)
- **Níveis de Personagem:** Validação estrita entre 1 e 20. Valores fora deste intervalo são logados com aviso e ajustados com segurança.
- **Resolução de Mapas:** O loader inspeciona a extensão do `map_source`. Se terminar com `.json`, o `map_type` é inferido automaticamente como `"tilemap"`; caso contrário, assume `"image"`.
- **Desserialização de Posições:** O sistema aceita indistintamente chaves de coordenadas `{"x": col, "y": row}` ou `{"col": col, "row": row}`.
- **Idempotência do Arquivo Base de Encontro:** O salvamento de progresso tático grava exclusivamente em `creations/encounters/saves/{uid}_save.json`, mantendo o template original de `creations/encounters/{uid}.json` totalmente intacto e reutilizável para novas campanhas.

---

## 4. Fluxo de Integração & Eventos

1. **Leitura e Parsing:** Loaders lêem o arquivo JSON com `encoding="utf-8"`, validam a tipagem e alimentam os respectivos modelos ou Builders.
2. **Construção de Entidades:** Fluent Builders instanciam os modelos encapsulados (`PlayableCharacter`, `Monster`, `TileMap`), garantindo cópias defensivas em coleções mutáveis.
3. **Serialização:** Salvamentos de estado utilizam `json.dump(data, f, indent=4, ensure_ascii=False)`.
