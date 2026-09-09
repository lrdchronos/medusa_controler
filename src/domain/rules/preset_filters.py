import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def filter_monster_presets(monsters: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Filtra presets de monstros aplicando correspondência de substring parcial (estilo SQL LIKE '%query%').
    Verifica se a query sanitizada está contida no 'name', 'uid', 'type', 'sub_type' ou na lista de 'tags'.
    Se a query for vazia, restaura e retorna a listagem completa.
    """
    sanitized = query.strip().lower()
    if not sanitized:
        logger.debug(f"Filtro de busca vazio: restaurando listagem completa ({len(monsters)} monstros).")
        return [m.copy() for m in monsters]

    filtered: List[Dict[str, Any]] = []
    for mon in monsters:
        name = str(mon.get("name", "")).lower()
        uid = str(mon.get("uid", "")).lower()
        m_type = str(mon.get("type", "")).lower()
        sub_type = str(mon.get("sub_type", "")).lower()

        # Checa correspondência em tags
        tags = mon.get("tags", [])
        tag_match = False
        if isinstance(tags, (list, tuple, set)):
            tag_match = any(sanitized in str(t).lower() for t in tags)
        elif isinstance(tags, str):
            tag_match = sanitized in tags.lower()

        # Fallback defensivo em raw_data caso exista
        raw_match = False
        raw = mon.get("raw_data")
        if isinstance(raw, dict):
            raw_type = str(raw.get("type", "")).lower()
            raw_sub = str(raw.get("sub_type", "")).lower()
            raw_tags = raw.get("tags", [])
            if isinstance(raw_tags, (list, tuple, set)):
                raw_match = any(sanitized in str(t).lower() for t in raw_tags) or sanitized in raw_type or sanitized in raw_sub
            elif isinstance(raw_tags, str):
                raw_match = sanitized in raw_tags.lower() or sanitized in raw_type or sanitized in raw_sub

        if (
            sanitized in name
            or sanitized in uid
            or sanitized in m_type
            or sanitized in sub_type
            or tag_match
            or raw_match
        ):
            filtered.append(mon.copy())

    logger.info(
        f"Filtragem de monstros executada | Query: '{sanitized}' | Resultados: {len(filtered)}/{len(monsters)}"
    )
    return filtered
