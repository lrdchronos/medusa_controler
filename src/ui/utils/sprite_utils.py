import logging
import os
from pathlib import Path
from typing import Optional
import arcade

logger = logging.getLogger(__name__)


def _resolve_asset_path(file_path: str) -> str:
    """
    Resolve o caminho do arquivo de asset de maneira resiliente,
    tentando caminhos relativos ao diretório de trabalho ou à raiz do projeto.
    """
    if not file_path:
        return file_path

    if os.path.isabs(file_path) and os.path.isfile(file_path):
        return file_path

    if os.path.isfile(file_path):
        return os.path.abspath(file_path)

    # Tenta resolver relativo à raiz do repositório (3 níveis acima deste arquivo)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = project_root / file_path
    if candidate.is_file():
        return str(candidate)

    return file_path


class SpriteFactory:
    """
    Fábrica utilitária declarativa para criação, escalonamento e posicionamento
    de Sprites (estáticos ou animados) em uma única linha de código.
    """

    @staticmethod
    def create_sprite(
        sheet_path: str,
        x: float = 0.0,
        y: float = 0.0,
        width: int = 48,
        height: int = 48,
        target_size: Optional[float] = None,
        frame_count: int = 1,
        scale: float = 1.0,
    ) -> arcade.Sprite:
        """
        Instancia, fatia, redimensiona e posiciona um arcade.Sprite em 1 linha.

        Parâmetros:
            sheet_path (str): Caminho para a imagem ou spritesheet.
            x (float): Coordenada central X na tela.
            y (float): Coordenada central Y na tela.
            width (int): Largura de cada célula/quadro na imagem original (em px).
            height (int): Altura de cada célula/quadro na imagem original (em px).
            target_size (Optional[float]): Se informado, calcula scale automaticamente (target_size / width).
            frame_count (int): Quantidade de quadros horizontais (1 para estático, >1 para animado).
            scale (float): Escala manual aplicada caso target_size seja None.

        Retorna:
            arcade.Sprite: Objeto Sprite configurado e pronto para adição em SpriteList.
        """
        sprite = arcade.Sprite()
        resolved_path = _resolve_asset_path(sheet_path)

        if frame_count <= 1:
            try:
                base_tex = arcade.load_texture(resolved_path)
                if width > 0 and height > 0 and (base_tex.width > width or base_tex.height > height):
                    tex = base_tex.crop(0, 0, width, height)
                else:
                    tex = base_tex
                sprite.texture = tex
                sprite.textures = [tex]
            except Exception as e:
                logger.error(f"Erro ao carregar textura do Sprite '{sheet_path}' (resolvido: '{resolved_path}'): {e}")
                sprite.textures = []
        else:
            try:
                base_tex = arcade.load_texture(resolved_path)
                sprite.textures = [
                    base_tex.crop(i * width, 0, width, height)
                    for i in range(frame_count)
                ]
                if sprite.textures:
                    sprite.texture = sprite.textures[0]
            except Exception as e:
                logger.error(f"Erro ao carregar spritesheet animado '{sheet_path}' (resolvido: '{resolved_path}'): {e}")
                sprite.textures = []

        # Cálculo automático da escala ou uso da escala explícita
        if target_size is not None and width > 0:
            effective_scale = float(target_size) / float(width)
        else:
            effective_scale = float(scale)

        sprite.scale = effective_scale
        sprite.position = (float(x), float(y))

        return sprite


# Aliases ergonômicos
UIUtils = SpriteFactory
create_sprite = SpriteFactory.create_sprite
