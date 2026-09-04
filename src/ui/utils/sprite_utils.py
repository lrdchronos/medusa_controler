import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import arcade
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

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


class AnimatedPropSprite(arcade.Sprite):
    """
    Sprite animado baseado em tempo para props e decorações de cenário em loop contínuo.
    Suporta avanço suave de quadros via update_animation(delta_time) ou update(delta_time).
    """

    def __init__(
        self,
        textures: Optional[List[arcade.Texture]] = None,
        fps: float = 8.0,
        scale: float = 1.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.textures: List[arcade.Texture] = list(textures) if textures else []
        if self.textures:
            self.texture = self.textures[0]
        self._fps: float = max(0.001, float(fps))
        self._frame_duration: float = 1.0 / self._fps
        self._time_counter: float = 0.0
        self._cur_frame_idx: int = 0
        self.scale = float(scale)

    @property
    def fps(self) -> float:
        """Taxa de quadros por segundo da animação."""
        return self._fps

    @fps.setter
    def fps(self, value: float) -> None:
        self._fps = max(0.001, float(value))
        self._frame_duration = 1.0 / self._fps

    @property
    def frame_duration(self) -> float:
        """Duração de cada quadro em segundos."""
        return self._frame_duration

    @property
    def cur_frame_idx(self) -> int:
        """Índice do quadro atual exibido."""
        return self._cur_frame_idx

    def update_animation(self, delta_time: float = 1 / 60, *args: Any, **kwargs: Any) -> None:
        """Avança a animação em loop contínuo com base no tempo decorrido."""
        if len(self.textures) <= 1:
            return

        self._time_counter += float(delta_time)
        if self._time_counter >= self._frame_duration:
            advance = int(self._time_counter // self._frame_duration)
            self._time_counter %= self._frame_duration
            self._cur_frame_idx = (self._cur_frame_idx + advance) % len(self.textures)
            self.texture = self.textures[self._cur_frame_idx]

    def on_update(self, delta_time: float = 1 / 60) -> None:
        """Hook de atualização de quadro do Arcade."""
        self.update_animation(delta_time)

    def update(self, delta_time: float = 1 / 60) -> None:
        """Compatibilidade com chamadas genéricas de update."""
        self.update_animation(delta_time)


# Alias para conformidade
AnimatedTimeBasedSprite = AnimatedPropSprite


class SpriteFactory:
    """
    Fábrica utilitária declarativa para criação, escalonamento e posicionamento
    de Sprites, Props de cenário e Tokens Táticos para o Medusa VTT.
    """

    _token_texture_cache: Dict[str, arcade.Texture] = {}
    _text_cache: Dict[str, arcade.Text] = {}

    @staticmethod
    def create_sprite(
        sheet_path: str,
        x: float = 0.0,
        y: float = 0.0,
        width: int = 32,
        height: int = 32,
        target_size: Optional[float] = None,
        frame_count: int = 1,
        scale: float = 1.0,
        frame_width: Optional[int] = None,
        frame_height: Optional[int] = None,
        fps: float = 8.0,
    ) -> arcade.Sprite:
        """
        Instancia, fatia, redimensiona e posiciona um arcade.Sprite em 1 linha.

        Parâmetros:
            sheet_path (str): Caminho para a imagem ou spritesheet.
            x (float): Coordenada central X na tela.
            y (float): Coordenada central Y na tela.
            width (int): Largura de cada célula/quadro na imagem original (em px, padrão 32).
            height (int): Altura de cada célula/quadro na imagem original (em px, padrão 32).
            target_size (Optional[float]): Se informado, calcula scale automaticamente (target_size / width).
            frame_count (int): Quantidade de quadros horizontais (1 para estático, >1 para animado).
            scale (float): Escala manual aplicada caso target_size seja None.
            frame_width (Optional[int]): Alias explícito para width.
            frame_height (Optional[int]): Alias explícito para height.
            fps (float): Taxa de quadros para spritesheets animados (padrão 8.0).

        Retorna:
            arcade.Sprite: Objeto Sprite configurado e pronto para adição em SpriteList.
        """
        eff_width = frame_width if frame_width is not None else width
        eff_height = frame_height if frame_height is not None else height
        resolved_path = _resolve_asset_path(sheet_path)

        if frame_count <= 1:
            sprite = arcade.Sprite()
            try:
                base_tex = arcade.load_texture(resolved_path)
                if eff_width > 0 and eff_height > 0 and (base_tex.width > eff_width or base_tex.height > eff_height):
                    tex = base_tex.crop(0, 0, eff_width, eff_height)
                else:
                    tex = base_tex
                sprite.texture = tex
                sprite.textures = [tex]
            except Exception as e:
                logger.error(f"Erro ao carregar textura do Sprite '{sheet_path}' (resolvido: '{resolved_path}'): {e}")
                sprite.textures = []
        else:
            textures: List[arcade.Texture] = []
            try:
                base_tex = arcade.load_texture(resolved_path)
                textures = [
                    base_tex.crop(i * eff_width, 0, eff_width, eff_height)
                    for i in range(frame_count)
                ]
            except Exception as e:
                logger.error(f"Erro ao carregar spritesheet animado '{sheet_path}' (resolvido: '{resolved_path}'): {e}")

            sprite = AnimatedPropSprite(
                textures=textures,
                fps=fps,
            )

        # Cálculo automático da escala ou uso da escala explícita
        if target_size is not None and eff_width > 0:
            effective_scale = float(target_size) / float(eff_width)
        else:
            effective_scale = float(scale)

        sprite.scale = effective_scale
        sprite.position = (float(x), float(y))

        return sprite

    @classmethod
    def create_static_prop(
        cls,
        image_path: str,
        scale: float = 1.0,
    ) -> arcade.Sprite:
        """
        Carrega e instancia um objeto/prop estático de quadro único (padrão 32x32px) com filtro pixelated.
        """
        return cls.create_sprite(
            sheet_path=image_path,
            width=32,
            height=32,
            frame_count=1,
            scale=scale,
        )

    @classmethod
    def create_animated_prop(
        cls,
        spritesheet_path: str,
        scale: float = 1.0,
        frame_count: int = 6,
        fps: float = 8.0,
        frame_width: int = 32,
        frame_height: int = 32,
    ) -> AnimatedPropSprite:
        """
        Carrega e instancia um objeto/prop animado composto por quadros sequenciais de 32x32px
        (padrão 6 frames a 8.0 FPS) em loop contínuo.
        """
        resolved_path = _resolve_asset_path(spritesheet_path)
        textures: List[arcade.Texture] = []
        try:
            base_tex = arcade.load_texture(resolved_path)
            textures = [
                base_tex.crop(i * frame_width, 0, frame_width, frame_height)
                for i in range(frame_count)
            ]
        except Exception as e:
            logger.error(f"Erro ao carregar prop animado '{spritesheet_path}' (resolvido: '{resolved_path}'): {e}")

        prop_sprite = AnimatedPropSprite(
            textures=textures,
            fps=fps,
            scale=scale,
        )
        return prop_sprite

    @classmethod
    def get_procedural_token_texture(
        cls,
        name: str,
        is_player: bool = False,
        base_size: int = 64,
    ) -> arcade.Texture:
        """Gera ou recupera do cache uma textura procedural de token tático circular Dark Fantasy."""
        short_name = name.strip()[:4].upper()
        cache_key = f"{short_name}_{'PC' if is_player else 'MON'}_{base_size}"

        if cache_key in cls._token_texture_cache:
            return cls._token_texture_cache[cache_key]

        img = PIL.Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)

        # Paleta: Jogador (Azul Escuro / Ciano / Dourado) vs Monstro (Carmim / Vermelho Sangue)
        if is_player:
            fill_color = (25, 42, 86, 255)
            border_color = (74, 189, 255, 255)
            inner_border = (241, 196, 15, 200)
            text_color = (255, 255, 255, 255)
        else:
            fill_color = (120, 20, 20, 255)
            border_color = (235, 77, 75, 255)
            inner_border = (180, 50, 50, 200)
            text_color = (255, 240, 240, 255)

        margin = 3
        draw.ellipse(
            (margin, margin, base_size - margin, base_size - margin),
            fill=fill_color,
            outline=border_color,
            width=3,
        )
        draw.ellipse(
            (margin + 4, margin + 4, base_size - margin - 4, base_size - margin - 4),
            fill=None,
            outline=inner_border,
            width=1,
        )

        try:
            font = PIL.ImageFont.load_default()
        except Exception:
            font = None

        bbox = draw.textbbox((0, 0), short_name, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (base_size - text_w) / 2
        text_y = (base_size - text_h) / 2 - 1

        draw.text((text_x, text_y), short_name, fill=text_color, font=font)

        tex = arcade.Texture(img)
        cls._token_texture_cache[cache_key] = tex
        return tex

    @classmethod
    def create_entity_token_sprite(
        cls,
        name: str,
        is_player: bool,
        x: float = 0.0,
        y: float = 0.0,
        target_size: float = 64.0,
        is_hidden: bool = False,
        asset_path: Optional[str] = None,
    ) -> arcade.Sprite:
        """
        Cria um Sprite de Token de entidade pronto para o Grid Tático,
        dimensionado para target_size (cell_size) e respeitando is_hidden.
        """
        if asset_path and os.path.isfile(_resolve_asset_path(asset_path)):
            sprite = cls.create_sprite(
                sheet_path=asset_path,
                x=x,
                y=y,
                target_size=target_size,
            )
        else:
            base_size = 64
            tex = cls.get_procedural_token_texture(name=name, is_player=is_player, base_size=base_size)
            sprite = arcade.Sprite()
            sprite.texture = tex
            sprite.textures = [tex]
            sprite.scale = float(target_size) / float(base_size)
            sprite.position = (float(x), float(y))

        if is_hidden:
            sprite.alpha = 128
        else:
            sprite.alpha = 255

        return sprite

    @classmethod
    def draw_tactical_token(
        cls,
        name: str,
        is_player: bool,
        x: float,
        y: float,
        radius: float,
        is_alive: bool = True,
        is_hidden: bool = False,
        is_selected: bool = False,
        is_active: bool = False,
        text_cache: Optional[Dict[str, arcade.Text]] = None,
        token_key: Optional[str] = None,
    ) -> None:
        """
        Renderiza diretamente um token circular Dark Fantasy com as iniciais do personagem/monstro,
        estilizado identicamente aos badges da fita de iniciativa (InitiativeHUD).
        """
        alpha = 128 if is_hidden else 255
        alpha_ratio = alpha / 255.0

        # Cores conforme estado e tipo
        if not is_alive:
            fill_color = (55, 60, 68, alpha)
            border_color = (120, 120, 130, alpha)
            text_color = (180, 180, 180, alpha)
        elif is_player:
            fill_color = (25, 118, 210, alpha)    # Azul Vibrante
            border_color = (100, 200, 255, alpha) # Ciano
            text_color = (255, 255, 255, alpha)
        else:
            fill_color = (183, 28, 28, alpha)     # Vermelho Carmim
            border_color = (255, 138, 128, alpha) # Coral
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

        # 6. Texto com as 4 primeiras letras do nome (ex: BOLO, KOB1, CULT)
        short_name = name.strip()[:4].upper()
        font_size = max(7, int(radius * 0.44))

        cache = text_cache if text_cache is not None else cls._text_cache
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

        cached_txt.draw()

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
            eye_txt.draw()


class CombatToken(arcade.Sprite):
    """
    Sprite de Token de combate com suporte a movimentação suave (Smooth Token Interpolation / Lerp).
    Mantém separadas a posição atual de renderização (center_x, center_y) e a posição lógica de destino no grid (target_x, target_y).
    """

    def __init__(
        self,
        uid: str,
        name: str,
        is_player: bool,
        target_x: float = 0.0,
        target_y: float = 0.0,
        lerp_speed: float = 10.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.uid: str = uid
        self.name: str = name
        self.is_player: bool = is_player
        self.target_x: float = float(target_x)
        self.target_y: float = float(target_y)
        self.center_x: float = float(target_x)
        self.center_y: float = float(target_y)
        self.lerp_speed: float = float(lerp_speed)

    @property
    def current_x(self) -> float:
        """Posição de renderização atual no eixo X."""
        return self.center_x

    @current_x.setter
    def current_x(self, value: float) -> None:
        self.center_x = float(value)

    @property
    def current_y(self) -> float:
        """Posição de renderização atual no eixo Y."""
        return self.center_y

    @current_y.setter
    def current_y(self, value: float) -> None:
        self.center_y = float(value)

    def set_target(self, target_x: float, target_y: float, snap_immediately: bool = False) -> None:
        """
        Atualiza as coordenadas de destino (target_x, target_y).
        Se snap_immediately=True, crava a posição de renderização imediatamente no destino.
        """
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        if snap_immediately:
            self.center_x = self.target_x
            self.center_y = self.target_y

    def update_lerp(self, delta_time: float) -> None:
        """
        Interpola a posição atual em direção ao alvo utilizando a fórmula de amortecimento exponencial / Lerp.
        Crava no destino quando a distância for menor que 1.0px para evitar jitter.
        """
        lerp_speed = self.lerp_speed
        diff_x = self.target_x - self.center_x
        diff_y = self.target_y - self.center_y

        # Se estiver muito próximo, crava no destino para evitar jitter
        if abs(diff_x) < 1.0 and abs(diff_y) < 1.0:
            self.center_x = self.target_x
            self.center_y = self.target_y
        else:
            self.center_x += diff_x * min(lerp_speed * delta_time, 1.0)
            self.center_y += diff_y * min(lerp_speed * delta_time, 1.0)

    def on_update(self, delta_time: float = 1 / 60) -> None:
        """Atualização de quadro do sprite."""
        self.update_lerp(delta_time)


# Aliases ergonômicos
UIUtils = SpriteFactory
create_sprite = SpriteFactory.create_sprite
create_static_prop = SpriteFactory.create_static_prop
create_animated_prop = SpriteFactory.create_animated_prop
create_entity_token = SpriteFactory.create_entity_token_sprite
draw_tactical_token = SpriteFactory.draw_tactical_token

