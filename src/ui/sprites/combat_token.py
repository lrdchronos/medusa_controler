from typing import Optional, Any
import arcade


class CombatToken(arcade.Sprite):
    """
    Sprite de Token de combate com suporte a movimentação suave (Smooth Token Interpolation / Lerp).
    Mantém separadas a posição atual de renderização (center_x, center_y) e a posição lógica de destino no grid (target_x, target_y).
    """

    def __init__(
        self,
        uid: str,
        name: str,
        is_player: bool = False,
        target_x: float = 0.0,
        target_y: float = 0.0,
        lerp_speed: float = 10.0,
        entity_type: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.uid: str = uid
        self.name: str = name
        self.is_player: bool = is_player
        self.entity_type: Optional[Any] = entity_type
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

        if abs(diff_x) < 1.0 and abs(diff_y) < 1.0:
            self.center_x = self.target_x
            self.center_y = self.target_y
        else:
            self.center_x += diff_x * min(lerp_speed * delta_time, 1.0)
            self.center_y += diff_y * min(lerp_speed * delta_time, 1.0)

    def on_update(self, delta_time: float = 1 / 60) -> None:
        """Atualização de quadro do sprite."""
        self.update_lerp(delta_time)
