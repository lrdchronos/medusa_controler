import logging
from typing import Optional, List, Any
import arcade

logger = logging.getLogger(__name__)


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
