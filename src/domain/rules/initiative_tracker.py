import logging
import random
from typing import List, Dict, Tuple, Optional
from ..models.entity import Entity

logger = logging.getLogger(__name__)


class InitiativeTracker:
    """
    Motor especializado de regras D&D 5E para cálculo de iniciativas, ordenação com desempates,
    gerenciamento de fila de turnos e rodadas circulares com pulo de combatentes incapacitados.
    """

    @staticmethod
    def generate_draft_initiatives(combatants: List[Entity]) -> Dict[str, int]:
        """
        Rola 1d20 + DEX mod para cada participante revelado (não oculto) e devolve um dicionário temporário
        {combatant_uid: score} sem alterar o estado oficial de combate.
        Nenhum dado de iniciativa é rolado para combatentes ocultos (hidden == True).
        """
        draft: Dict[str, int] = {}
        for combatant in combatants:
            if combatant.is_hidden:
                continue
            d20 = random.randint(1, 20)
            score = d20 + combatant.initiative_mod
            draft[combatant.uid] = score
        logger.debug(f"Draft de iniciativas gerado para {len(draft)} participantes revelados.")
        return draft

    @staticmethod
    def calculate_turn_order(
        combatants: List[Entity],
        final_scores: Dict[str, int],
    ) -> Tuple[List[Entity], Dict[str, Entity]]:
        """
        Aplica os scores de iniciativa aos combatentes, separa entidades ocultas
        e ordena a fila de turnos ativos com critérios de desempate D&D 5E:
        (Iniciativa -> Modificador DEX -> Nome).
        """
        hidden_combatants: Dict[str, Entity] = {}
        revealed_combatants: List[Entity] = []

        for combatant in combatants:
            if combatant.is_hidden:
                hidden_combatants[combatant.uid] = combatant
                continue

            if combatant.uid in final_scores:
                score = final_scores[combatant.uid]
            elif combatant.name in final_scores:
                score = final_scores[combatant.name]
            else:
                d20 = random.randint(1, 20)
                score = d20 + combatant.initiative_mod

            combatant.set_initiative(score)
            revealed_combatants.append(combatant)

        # Ordenação com critérios de desempate D&D 5E
        turn_order = sorted(
            revealed_combatants,
            key=lambda c: (c.initiative_score, c.initiative_mod, c.name),
            reverse=True,
        )

        return turn_order, hidden_combatants

    @staticmethod
    def advance_turn(
        turn_order: List[Entity],
        current_index: int,
        round_number: int,
    ) -> Tuple[int, int, Optional[Entity]]:
        """
        Avança para o próximo participante válido (vivo com HP > 0) na fila de iniciativa de forma circular.
        Ao completar uma volta completa (índice 0), incrementa o número da rodada.
        Pula automaticamente combatentes mortos/incapacitados sem travamentos.
        Retorna (novo_indice, nova_rodada, entidade_ativa).
        """
        if not turn_order:
            return -1, round_number, None

        has_alive = any(c.is_alive and c.current_hp > 0 for c in turn_order)
        if not has_alive:
            logger.info("Todos os combatentes estão mortos/incapacitados. Não há participantes válidos para avançar o turno.")
            return current_index, round_number, None

        num_combatants = len(turn_order)

        if current_index < 0:
            found_idx = -1
            for i, c in enumerate(turn_order):
                if c.is_alive and c.current_hp > 0:
                    found_idx = i
                    break
            new_index = found_idx if found_idx >= 0 else 0
            new_round = 1
        else:
            count = 0
            new_index = current_index
            new_round = round_number
            while count < num_combatants:
                new_index = (new_index + 1) % num_combatants
                if new_index == 0:
                    new_round += 1
                candidate = turn_order[new_index]
                if candidate.is_alive and candidate.current_hp > 0:
                    break
                count += 1

            if count >= num_combatants:
                logger.info("Todos os combatentes estão mortos/incapacitados. Turno não avançado.")
                return current_index, round_number, None

        active_character = turn_order[new_index] if 0 <= new_index < len(turn_order) else None
        return new_index, new_round, active_character

    @staticmethod
    def rewind_turn(
        turn_order: List[Entity],
        current_index: int,
        round_number: int,
    ) -> Tuple[int, int, Optional[Entity]]:
        """
        Retrocede para o participante anterior válido (vivo com HP > 0) na fila de iniciativas.
        Retorna (novo_indice, nova_rodada, entidade_ativa).
        """
        if not turn_order:
            return -1, round_number, None

        has_alive = any(c.is_alive and c.current_hp > 0 for c in turn_order)
        if not has_alive:
            logger.info("Todos os combatentes estão mortos/incapacitados. Turno não retrocedido.")
            return current_index, round_number, None

        num_combatants = len(turn_order)
        count = 0
        new_index = current_index
        new_round = round_number

        while count < num_combatants:
            if new_index <= 0:
                new_index = num_combatants - 1
                if new_round > 1:
                    new_round -= 1
            else:
                new_index -= 1
            candidate = turn_order[new_index]
            if candidate.is_alive and candidate.current_hp > 0:
                break
            count += 1

        active_character = turn_order[new_index] if 0 <= new_index < len(turn_order) else None
        return new_index, new_round, active_character
