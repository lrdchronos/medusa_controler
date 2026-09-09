import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import arcade

logger = logging.getLogger(__name__)


def _resolve_asset_path(file_path: str) -> str:
    """Resolve o caminho do arquivo de asset de maneira resiliente."""
    if not file_path:
        return file_path
    if os.path.isabs(file_path) and os.path.isfile(file_path):
        return file_path
    if os.path.isfile(file_path):
        return os.path.abspath(file_path)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = project_root / file_path
    if candidate.is_file():
        return str(candidate)
    return file_path


class StatusIconAtlas:
    """
    Carregador e Atlas Gerenciador de Ícones de Status e Condições do Medusa VTT.
    Fatia e faz cache em memória das sub-texturas (16x16px) do spritesheet 'assets/sprites/status_icons.png'.
    """

    DEFAULT_SPRITESHEET = "assets/sprites/status_icons.png"
    ICON_SIZE = 16

    # Mapeamento Canônico de Coordenadas (col, row) na grade de 16x16px
    # Linha 0: Indicadores de Vitalidade / Saúde
    # Linha 1: Condições Canônicas D&D 5E
    COORDINATE_MAP: Dict[str, Tuple[int, int]] = {
        # Vitalidade (Linha 0)
        "health_green": (0, 0),
        "health_yellow": (1, 0),
        "health_red": (2, 0),
        # Condições D&D 5E (Linha 1)
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

    # Rótulos em Português para UI / Tooltips
    CONDITION_LABELS: Dict[str, str] = {
        "poisoned": "Envenenado",
        "blinded": "Cego",
        "frightened": "Amedrontado",
        "charmed": "Enfeitiçado",
        "restrained": "Restringido",
        "deafened": "Surdo",
        "petrified": "Petrificado",
        "paralyzed": "Paralisado",
        "invisible": "Invisível",
        "stunned": "Atordoado",
        "prone": "Derrubado / Caído",
    }

    # Ordem Canônica de Condições D&D 5E
    CANONICAL_CONDITIONS: List[str] = [
        "poisoned",
        "blinded",
        "frightened",
        "charmed",
        "restrained",
        "deafened",
        "petrified",
        "paralyzed",
        "invisible",
        "stunned",
        "prone",
    ]

    _texture_cache: Dict[str, arcade.Texture] = {}
    _base_texture: Optional[arcade.Texture] = None

    @classmethod
    def load_atlas(cls, sheet_path: Optional[str] = None) -> bool:
        """
        Carrega o spritesheet base e inicializa o cache de todas as sub-texturas.
        Evita I/O redundante em disco se o atlas já estiver carregado.
        """
        path = sheet_path or cls.DEFAULT_SPRITESHEET
        resolved = _resolve_asset_path(path)

        if not os.path.isfile(resolved):
            logger.error(f"Arquivo de spritesheet de status não encontrado: '{path}' (resolvido: '{resolved}')")
            return False

        try:
            cls._base_texture = arcade.load_texture(resolved)
            sz = cls.ICON_SIZE

            for name, (col, row) in cls.COORDINATE_MAP.items():
                x = col * sz
                y = row * sz
                sub_tex = cls._base_texture.crop(x, y, sz, sz)
                cls._texture_cache[name] = sub_tex

            logger.info(
                f"Atlas de ícones de status carregado com sucesso: {len(cls._texture_cache)} ícones "
                f"recortados de '{path}' ({cls._base_texture.width}x{cls._base_texture.height}px)."
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao fatiar atlas de ícones de status '{path}': {e}")
            return False

    @classmethod
    def get_texture(cls, name: str) -> Optional[arcade.Texture]:
        """Recupera uma sub-textura pelo nome (ex: 'health_green', 'poisoned', 'blinded')."""
        key = name.strip().lower()
        if key not in cls._texture_cache:
            if not cls._texture_cache:
                cls.load_atlas()
        return cls._texture_cache.get(key)

    @classmethod
    def get_condition_texture(cls, condition_name: str) -> Optional[arcade.Texture]:
        """Recupera a sub-textura da condição D&D 5E informada."""
        return cls.get_texture(condition_name)

    @classmethod
    def get_health_texture(cls, health_name: str) -> Optional[arcade.Texture]:
        """Recupera a sub-textura de indicador de saúde informada."""
        return cls.get_texture(health_name)

    @classmethod
    def get_health_icon_name(cls, current_hp: int, max_hp: int) -> str:
        """
        Determina o ícone de vitalidade correspondente:
          - 'health_green': HP > 50%
          - 'health_yellow': 25% <= HP <= 50%
          - 'health_red': HP < 25% (ou HP <= 0)
        """
        if max_hp <= 0:
            return "health_red"
        ratio = current_hp / float(max_hp)
        if ratio > 0.50:
            return "health_green"
        elif ratio >= 0.25:
            return "health_yellow"
        else:
            return "health_red"

    @classmethod
    def get_condition_names(cls) -> List[str]:
        """Retorna lista das 11 condições canônicas D&D 5E."""
        return cls.CANONICAL_CONDITIONS.copy()

    @classmethod
    def get_condition_label(cls, condition_name: str) -> str:
        """Retorna o rótulo legível em português da condição."""
        key = condition_name.strip().lower()
        return cls.CONDITION_LABELS.get(key, condition_name.capitalize())

    @classmethod
    def get_icon_coords(cls, icon_name: str) -> Optional[Tuple[int, int]]:
        """Retorna as coordenadas (col, row) do ícone no spritesheet."""
        return cls.COORDINATE_MAP.get(icon_name.strip().lower())

    @classmethod
    def clear_cache(cls) -> None:
        """Limpa o cache em memória (útil para testes unitários)."""
        cls._texture_cache.clear()
        cls._base_texture = None
