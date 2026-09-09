import logging
from typing import List, Dict, Tuple, Optional, Union
from ..models.entity import Entity

logger = logging.getLogger(__name__)


class CombatantRules:
    """
    Regras de domínio para manipulação de combatentes em tempo de execução:
    Spawn, visibilidade tática, condições, dano, cura e posicionamento.
    """

    @staticmethod
    def spawn_combatant(
        combatants: List[Entity],
        turn_order: List[Entity],
        hidden_combatants: Dict[str, Entity],
        current_turn_index: int,
        has_combat_started: bool,
        entity: Entity,
        position: Tuple[int, int],
        initiative_slot: str = "next",
    ) -> int:
        """
        Registra um novo combatente na sessão de combate e ajusta a ordem de turnos.
        Retorna o novo current_turn_index.
        """
        entity.set_position(position[0], position[1])
        if entity not in combatants:
            combatants.append(entity)

        new_turn_index = current_turn_index

        if entity.is_hidden:
            hidden_combatants[entity.uid] = entity
            if entity in turn_order:
                old_idx = turn_order.index(entity)
                turn_order.pop(old_idx)
                if old_idx < new_turn_index:
                    new_turn_index -= 1
        else:
            hidden_combatants.pop(entity.uid, None)
            if has_combat_started and turn_order:
                if entity in turn_order:
                    old_idx = turn_order.index(entity)
                    turn_order.pop(old_idx)
                    if old_idx < new_turn_index:
                        new_turn_index -= 1

                if initiative_slot == "next":
                    target_idx = new_turn_index + 1
                    if target_idx > len(turn_order):
                        target_idx = len(turn_order)
                    turn_order.insert(target_idx, entity)
                else:  # "end"
                    turn_order.append(entity)
            else:
                if entity not in turn_order:
                    if initiative_slot == "next" and turn_order:
                        turn_order.insert(0, entity)
                    else:
                        turn_order.append(entity)

        etype_val = entity.entity_type.value if hasattr(entity, "entity_type") else "unknown"
        logger.info(
            "Novo combatente spawnado no combate: '%s' (Tipo: %s) na posição (%d, %d), slot: '%s' (hidden=%s).",
            entity.name,
            etype_val,
            position[0],
            position[1],
            initiative_slot,
            entity.is_hidden,
        )
        return new_turn_index

    @staticmethod
    def reveal_combatant(
        combatant: Entity,
        turn_order: List[Entity],
        hidden_combatants: Dict[str, Entity],
        current_turn_index: int,
        has_combat_started: bool,
    ) -> int:
        """
        Revela um combatente oculto e o insere na fila de turnos após o turno ativo.
        Retorna o novo current_turn_index.
        """
        combatant.set_hidden(False)
        hidden_combatants.pop(combatant.uid, None)
        new_turn_index = current_turn_index

        if has_combat_started and turn_order:
            if combatant in turn_order:
                old_idx = turn_order.index(combatant)
                if old_idx != new_turn_index:
                    turn_order.pop(old_idx)
                    if old_idx < new_turn_index:
                        new_turn_index -= 1
                    target_idx = new_turn_index + 1
                    turn_order.insert(target_idx, combatant)
            else:
                target_idx = new_turn_index + 1
                if target_idx > len(turn_order):
                    target_idx = len(turn_order)
                turn_order.insert(target_idx, combatant)
        elif combatant not in turn_order:
            turn_order.append(combatant)

        logger.info(
            "Combatente '%s' revelado e posicionado como próximo a agir na fila de turnos.",
            combatant.name,
        )
        return new_turn_index

    @staticmethod
    def set_combatant_visibility(
        combatant: Entity,
        turn_order: List[Entity],
        hidden_combatants: Dict[str, Entity],
        current_turn_index: int,
        has_combat_started: bool,
        is_hidden: bool,
    ) -> int:
        """
        Define explicitamente a visibilidade tática do combatente.
        Retorna o novo current_turn_index.
        """
        new_turn_index = current_turn_index
        if not is_hidden and combatant.is_hidden:
            new_turn_index = CombatantRules.reveal_combatant(
                combatant, turn_order, hidden_combatants, current_turn_index, has_combat_started
            )
        else:
            combatant.set_hidden(is_hidden)
            if is_hidden:
                hidden_combatants[combatant.uid] = combatant
                if combatant in turn_order:
                    old_idx = turn_order.index(combatant)
                    turn_order.pop(old_idx)
                    if has_combat_started:
                        if old_idx < new_turn_index:
                            new_turn_index -= 1
                        elif new_turn_index >= len(turn_order):
                            new_turn_index = max(0, len(turn_order) - 1) if turn_order else -1
            else:
                hidden_combatants.pop(combatant.uid, None)

            status_desc = "Oculto" if is_hidden else "Visível"
            logger.info("Visibilidade definida: '%s' is_hidden=%s (%s).", combatant.name, is_hidden, status_desc)

        return new_turn_index
