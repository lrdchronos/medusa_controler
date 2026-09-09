from typing import Optional, Dict, Union
from .entity import Entity, EntityType


class DynamicToken(Entity):
    """
    Entidade leve / Token dinâmico criado em tempo de execução
    (ex: feitiços duradouros, invocações mágicas, reforços de monstros ou plebeus).
    """

    def __init__(
        self,
        name: str,
        max_hp: int = 1,
        armor_class: int = 10,
        entity_type: Union[EntityType, str] = EntityType.NEUTRAL,
        token_sprite: Optional[str] = None,
        uid: Optional[str] = None,
        speed: int = 30,
        position: Optional[Dict[str, int]] = None,
        is_hidden: bool = False,
        size: str = "Medium",
    ) -> None:
        super().__init__(
            name=name,
            max_hp=max_hp,
            armor_class=armor_class,
            uid=uid,
            speed=speed,
            position=position,
            is_hidden=is_hidden,
            entity_type=entity_type,
            token_sprite=token_sprite,
            size=size,
        )
