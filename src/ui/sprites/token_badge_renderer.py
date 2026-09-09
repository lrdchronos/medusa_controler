import re
from typing import Optional, Dict, Any
import arcade


def extract_badge_text(name: str) -> str:
    """
    Algoritmo heurístico inteligente para extração de identificadores/iniciais sucintos (1 a 4 caracteres)
    com base no nome da criatura, monstro ou efeito.
    """
    if not name:
        return ""

    cleaned = str(name).strip()
    if not cleaned:
        return ""

    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
        "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
        "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
        "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20
    }
    stop_words = {"de", "da", "do", "dos", "das", "e", "of", "the", "and", "del", "di"}

    def get_base_radical(base_str: str) -> str:
        b_words = [w for w in re.split(r"[\s_#-]+", base_str.strip()) if w and w.lower() not in stop_words]
        if not b_words:
            b_words = [w for w in re.split(r"[\s_#-]+", base_str.strip()) if w]
        if len(b_words) >= 2:
            return "".join(w[0].upper() for w in b_words[:3])
        elif len(b_words) == 1:
            return b_words[0][0].upper()
        return base_str[:1].upper()

    # 1. Padrão: Sufixo numérico arábico (ex: "Kobold 1", "Kobold #2", "Orc_3", "Goblin-4")
    m_num = re.search(r"^(?P<base>.+?)(?:[\s_#-]+|\s*#\s*)(?P<suffix>\d+)$", cleaned)
    if m_num:
        base_part = m_num.group("base").strip()
        suffix_num = int(m_num.group("suffix"))
        radical = get_base_radical(base_part)
        return f"{radical}{suffix_num}"

    # 2. Padrão: Sufixo com numeral romano (ex: "Zumbi IV", "Esqueleto II", "Cultista I")
    m_rom = re.search(r"^(?P<base>.+?)[\s_#-]+(?P<suffix>[IVXLCDMivxlcdm]+)$", cleaned)
    if m_rom:
        suf_upper = m_rom.group("suffix").upper()
        if suf_upper in roman_map:
            base_part = m_rom.group("base").strip()
            radical = get_base_radical(base_part)
            arabic_val = roman_map[suf_upper]
            return f"{radical}-{arabic_val}"

    # 3. Padrão: Sufixo com letra única isolada (ex: "Cultista A", "Esqueleto B", "Bandido - C")
    m_letter = re.search(r"^(?P<base>.+?)[\s_#-]+(?P<suffix>[A-Za-z])$", cleaned)
    if m_letter:
        base_part = m_letter.group("base").strip()
        suf_char = m_letter.group("suffix").upper()
        radical = get_base_radical(base_part)
        return f"{radical}-{suf_char}"

    # 4. Padrão: Nomes compostos comuns (ex: "Bruenor Martelo", "Mago Cinzento da Colina")
    words = [w for w in re.split(r"[\s_#-]+", cleaned) if w]
    meaningful_words = [w for w in words if w.lower() not in stop_words]
    if len(meaningful_words) >= 2:
        return "".join(w[0].upper() for w in meaningful_words[:3])
    elif len(words) >= 2:
        return "".join(w[0].upper() for w in words[:3])

    # 5. Padrão: Nome simples sem sufixo (ex: "Kobold", "Orc", "Bolo")
    return cleaned[:4].upper()


def draw_tactical_token(
    name: str,
    is_player: bool = False,
    x: float = 0.0,
    y: float = 0.0,
    radius: float = 16.0,
    is_alive: bool = True,
    is_hidden: bool = False,
    is_selected: bool = False,
    is_active: bool = False,
    text_cache: Optional[Dict[str, arcade.Text]] = None,
    token_key: Optional[str] = None,
    entity_type: Optional[Any] = None,
) -> None:
    """
    Renderiza diretamente um token circular Dark Fantasy com as iniciais do personagem/monstro/efeito,
    estilizado identicamente aos badges da fita de iniciativa (InitiativeHUD).
    """
    alpha = 128 if is_hidden else 255
    alpha_ratio = alpha / 255.0

    if entity_type is not None:
        etype_str = str(entity_type.value if hasattr(entity_type, "value") else entity_type).lower()
    else:
        etype_str = "player" if is_player else "monster"

    # Cores conforme estado e tipo
    if not is_alive:
        fill_color = (55, 60, 68, alpha)
        border_color = (120, 120, 130, alpha)
        text_color = (180, 180, 180, alpha)
    elif etype_str == "neutral":
        fill_color = (243, 156, 18, int(60 * alpha_ratio))   # Amarelo translúcido suave
        border_color = (241, 196, 15, alpha)                 # Dourado / Âmbar radiante
        text_color = (255, 255, 255, alpha)
    elif etype_str == "player" or is_player:
        fill_color = (25, 118, 210, alpha)                   # Azul Vibrante
        border_color = (100, 200, 255, alpha)                # Ciano
        text_color = (255, 255, 255, alpha)
    else:
        fill_color = (183, 28, 28, alpha)                    # Vermelho Carmim
        border_color = (255, 138, 128, alpha)                # Coral
        text_color = (255, 255, 255, alpha)

    # 1. Sombra suave sob o token
    arcade.draw_circle_filled(x, y - 2, radius + 1, (0, 0, 0, int(110 * alpha_ratio)))

    # 2. Destaque de Seleção (Mestre)
    if is_selected:
        arcade.draw_circle_filled(x, y, radius + 5, (241, 196, 15, int(90 * alpha_ratio)))
        arcade.draw_circle_outline(x, y, radius + 5, (241, 196, 15, alpha), 2)

    # 3. Destaque de Turno Ativo
    elif is_active and is_alive:
        arcade.draw_circle_filled(x, y, radius + 5, (46, 204, 113, int(80 * alpha_ratio)))
        arcade.draw_circle_outline(x, y, radius + 4, (255, 215, 0, alpha), 2)

    # 4. Preenchimento do Token
    arcade.draw_circle_filled(x, y, radius, fill_color)

    # 5. Borda do Token
    border_width = 3 if (is_selected or is_active) else 2
    arcade.draw_circle_outline(x, y, radius, border_color, border_width)

    # 6. Texto com o identificador/iniciais inteligentes do badge
    short_name = extract_badge_text(name)
    font_size = max(7, int(radius * (0.44 if len(short_name) <= 3 else 0.38)))

    cache = text_cache if text_cache is not None else {}
    cache_key = f"tkn_txt_{token_key or short_name}_{font_size}"

    cached_txt = cache.get(cache_key)
    if cached_txt is None or cached_txt.text != short_name or cached_txt.font_size != font_size:
        cached_txt = arcade.Text(
            text=short_name,
            x=x,
            y=y + 1,
            color=text_color,
            font_size=font_size,
            bold=True,
            anchor_x="center",
            anchor_y="center",
            font_name=("Consolas", "Calibri", "Segoe UI", "Arial"),
        )
        cache[cache_key] = cached_txt
    else:
        cached_txt.x = x
        cached_txt.y = y + 1
        cached_txt.color = text_color

    try:
        cached_txt.draw()
    except Exception:
        pass

    # 7. Marcador de Morte se abatido
    if not is_alive:
        cross_r = radius * 0.5
        arcade.draw_line(x - cross_r, y - cross_r, x + cross_r, y + cross_r, (244, 67, 54, alpha), 3)
        arcade.draw_line(x - cross_r, y + cross_r, x + cross_r, y - cross_r, (244, 67, 54, alpha), 3)

    # 8. Marcador de Criatura Oculta (is_hidden)
    if is_hidden:
        eye_key = f"tkn_eye_{token_key or short_name}_{font_size}"
        eye_txt = cache.get(eye_key)
        if eye_txt is None:
            eye_txt = arcade.Text(
                text="👁️",
                x=x,
                y=y + radius * 0.75,
                color=(255, 255, 255, 240),
                font_size=max(8, int(radius * 0.38)),
                bold=True,
                anchor_x="center",
                anchor_y="center",
            )
            cache[eye_key] = eye_txt
        else:
            eye_txt.x = x
            eye_txt.y = y + radius * 0.75
        try:
            eye_txt.draw()
        except Exception:
            pass
