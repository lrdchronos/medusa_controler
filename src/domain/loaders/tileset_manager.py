import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import arcade

logger = logging.getLogger(__name__)


def _resolve_project_path(path_str: str) -> Optional[Path]:
    """Resolve caminho relativo ao diretório de trabalho ou raiz do projeto."""
    if not path_str:
        return None
    p = Path(path_str)
    if p.is_file():
        return p.resolve()

    # Tenta relativo à raiz do repositório
    root = Path(__file__).resolve().parent.parent.parent.parent
    cand = root / path_str
    if cand.is_file():
        return cand.resolve()
    return None


class TilesetManager:
    """
    Gerenciador e Loader de Tilesets em Runtime para o Medusa VTT.
    Carrega o arquivo de atlas do Aseprite (.json) e a respectiva textura PNG (.png),
    fatia as subtexturas em memória e as armazena em lista indexada list[arcade.Texture],
    permitindo acesso em O(1) via get_tile_texture(tile_id).
    """

    _global_cache: Dict[str, "TilesetManager"] = {}

    def __init__(
        self,
        tileset_name: str,
        atlas_path: Optional[Union[str, Path]] = None,
        image_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.__tileset_name: str = str(tileset_name).strip() if tileset_name else "default"
        self.__textures: List[arcade.Texture] = []
        self.__atlas_metadata: Dict[str, Any] = {}
        self.__atlas_file: Optional[Path] = None
        self.__image_file: Optional[Path] = None

        self._load(atlas_path=atlas_path, image_path=image_path)

    # --- Properties ---

    @property
    def tileset_name(self) -> str:
        """Nome identificador do tileset."""
        return self.__tileset_name

    @property
    def tile_count(self) -> int:
        """Quantidade de subtexturas de tiles carregadas."""
        return len(self.__textures)

    @property
    def textures(self) -> List[arcade.Texture]:
        """Retorna cópia defensiva da lista de subtexturas."""
        return list(self.__textures)

    @property
    def atlas_metadata(self) -> Dict[str, Any]:
        """Cópia defensiva dos metadados do atlas do Aseprite."""
        return dict(self.__atlas_metadata)

    @property
    def atlas_file(self) -> Optional[str]:
        """Caminho absoluto do arquivo de atlas carregado."""
        return str(self.__atlas_file) if self.__atlas_file else None

    @property
    def image_file(self) -> Optional[str]:
        """Caminho absoluto do arquivo de textura carregado."""
        return str(self.__image_file) if self.__image_file else None

    # --- Resolução de Caminhos ---

    @classmethod
    def _generate_name_variants(cls, name: str) -> List[str]:
        """Gera variações comuns de formatação de nome (ex: Sprite-007 -> Sprite-0007)."""
        variants = [name]
        match = re.search(r"(\D+)(\d+)", name)
        if match:
            prefix, digits = match.groups()
            try:
                num = int(digits)
                for fmt in (f"{prefix}{num:04d}", f"{prefix}{num:03d}", f"{prefix}{num:02d}", f"{prefix}{num}"):
                    if fmt not in variants:
                        variants.append(fmt)
            except ValueError:
                pass
        return variants

    @classmethod
    def resolve_atlas_path(cls, tileset_name: str, explicit_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """Resolve o arquivo JSON de atlas do Aseprite."""
        if explicit_path:
            res = _resolve_project_path(str(explicit_path))
            if res:
                return res

        variants = cls._generate_name_variants(tileset_name)
        search_dirs = [
            "assets/tilesets",
            "assets/images/tilemaps",
            "assets/images/maps",
            "assets/images",
            "assets",
            "presets/tilesets",
            ".",
        ]

        for variant in variants:
            for d in search_dirs:
                for suffix in ("_atlas.json", ".json"):
                    cand = f"{d}/{variant}{suffix}"
                    res = _resolve_project_path(cand)
                    if res:
                        return res

        # Varredura por aproximação de stem
        root = Path(__file__).resolve().parent.parent.parent.parent
        for d in search_dirs:
            dir_path = (root / d).resolve()
            if not dir_path.is_dir():
                continue
            for f in dir_path.glob("*.json"):
                if f.name.endswith("_map.json"):
                    continue
                f_stem_clean = f.stem.replace("_atlas", "").lower()
                for v in variants:
                    if v.lower() == f_stem_clean or v.lower() in f.stem.lower():
                        return f.resolve()

        return None

    @classmethod
    def resolve_image_path(
        cls,
        tileset_name: str,
        explicit_path: Optional[Union[str, Path]] = None,
        atlas_meta_image: Optional[str] = None,
        atlas_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Resolve o arquivo de imagem PNG do tileset."""
        if explicit_path:
            res = _resolve_project_path(str(explicit_path))
            if res:
                return res

        if atlas_meta_image and atlas_dir:
            meta_cand = atlas_dir / atlas_meta_image
            if meta_cand.is_file():
                return meta_cand.resolve()

        variants = cls._generate_name_variants(tileset_name)
        search_dirs = [
            "assets/tilesets",
            "assets/images/tilemaps",
            "assets/images/maps",
            "assets/images",
            "assets/sprites",
            "assets",
            "presets/tilesets",
            ".",
        ]

        for variant in variants:
            for d in search_dirs:
                for suffix in (".png", ".jpg", ".jpeg"):
                    cand = f"{d}/{variant}{suffix}"
                    res = _resolve_project_path(cand)
                    if res:
                        return res

        # Varredura por aproximação de stem
        root = Path(__file__).resolve().parent.parent.parent.parent
        for d in search_dirs:
            dir_path = (root / d).resolve()
            if not dir_path.is_dir():
                continue
            for f in dir_path.glob("*.png"):
                f_stem_clean = f.stem.lower()
                for v in variants:
                    if v.lower() == f_stem_clean or v.lower() in f.stem.lower():
                        return f.resolve()

        return None

    # --- Carregamento e Fatiamento de Texturas ---

    def _load(
        self,
        atlas_path: Optional[Union[str, Path]] = None,
        image_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """Carrega e fatia o atlas e textura em subtexturas arcade.Texture indexadas."""
        self.__atlas_file = self.resolve_atlas_path(self.__tileset_name, atlas_path)
        if not self.__atlas_file:
            logger.warning(
                f"Atlas JSON do tileset '{self.__tileset_name}' não foi encontrado. "
                f"Nenhum tile fatiado carregado."
            )
            return

        try:
            with open(self.__atlas_file, "r", encoding="utf-8") as f:
                self.__atlas_metadata = json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler arquivo de atlas '{self.__atlas_file}': {e}")
            return

        meta = self.__atlas_metadata.get("meta", {})
        meta_image = meta.get("image")
        atlas_dir = self.__atlas_file.parent

        self.__image_file = self.resolve_image_path(
            tileset_name=self.__tileset_name,
            explicit_path=image_path,
            atlas_meta_image=meta_image,
            atlas_dir=atlas_dir,
        )

        if not self.__image_file:
            logger.warning(
                f"Imagem do tileset '{self.__tileset_name}' não foi encontrada para o atlas '{self.__atlas_file}'."
            )
            return

        try:
            base_texture = arcade.load_texture(str(self.__image_file))
        except Exception as e:
            logger.error(f"Erro ao carregar textura base '{self.__image_file}': {e}")
            return

        frames = self.__atlas_metadata.get("frames", [])
        self.__textures = []

        for idx, frame_entry in enumerate(frames):
            frame_rect = frame_entry.get("frame", {})
            fx = int(frame_rect.get("x", 0))
            fy = int(frame_rect.get("y", 0))
            fw = int(frame_rect.get("w", 32))
            fh = int(frame_rect.get("h", 32))

            try:
                sub_tex = base_texture.crop(fx, fy, fw, fh)
                self.__textures.append(sub_tex)
            except Exception as e:
                logger.error(
                    f"Erro ao recortar frame {idx} (x={fx}, y={fy}, w={fw}, h={fh}) "
                    f"do tileset '{self.__tileset_name}': {e}"
                )

        logger.info(
            f"TilesetManager '{self.__tileset_name}' inicializado: "
            f"{len(self.__textures)} tiles fatiados a partir de '{self.__image_file.name}'."
        )

    # --- Consulta em O(1) ---

    def has_tile(self, tile_id: int) -> bool:
        """Verifica se o tile_id é válido na lista de texturas."""
        return 0 <= int(tile_id) < len(self.__textures)

    def get_tile_texture(self, tile_id: int) -> Optional[arcade.Texture]:
        """
        Retorna a subtextura correspondente em O(1).
        Se o tile_id for inválido, emite log e retorna None defensivamente.
        """
        idx = int(tile_id)
        if 0 <= idx < len(self.__textures):
            return self.__textures[idx]

        logger.warning(
            f"tile_id {idx} fora dos limites para tileset '{self.__tileset_name}' "
            f"(total de tiles: {len(self.__textures)})."
        )
        return None

    # --- Cache e Acesso Global ---

    @classmethod
    def get_tileset(
        cls,
        tileset_name: str,
        atlas_path: Optional[Union[str, Path]] = None,
        image_path: Optional[Union[str, Path]] = None,
        force_reload: bool = False,
    ) -> "TilesetManager":
        """
        Retorna uma instância de TilesetManager com cache em memória
        para evitar recarregamentos e recortes duplicados de texturas.
        """
        key = str(tileset_name).strip()
        if force_reload or key not in cls._global_cache:
            instance = cls(tileset_name=key, atlas_path=atlas_path, image_path=image_path)
            cls._global_cache[key] = instance
        return cls._global_cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        """Limpa o cache global de tilesets."""
        cls._global_cache.clear()

    def __repr__(self) -> str:
        return f"<TilesetManager '{self.__tileset_name}' tiles={len(self.__textures)}>"
