import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from ..models.entity import Entity, DynamicToken
from ..models.fog_manager import FogManager

logger = logging.getLogger(__name__)


class CombatStateSerializer:
    """
    Serviço de persistência e serialização de snapshots de sessão de combate
    em creations/encounters/saves/{uid}_save.json.
    """

    @staticmethod
    def get_save_path(encounter_uid: str) -> Path:
        target_uid = encounter_uid or "unknown_encounter"
        uid_stem = Path(target_uid).stem
        if uid_stem.endswith("_save"):
            uid_stem = uid_stem[:-5]

        saves_dir = Path("creations/encounters/saves")
        saves_dir.mkdir(parents=True, exist_ok=True)
        return saves_dir / f"{uid_stem}_save.json"

    @staticmethod
    def has_save_state(encounter_uid: str) -> bool:
        if not encounter_uid:
            return False
        save_path = CombatStateSerializer.get_save_path(encounter_uid)
        return save_path.is_file()

    @staticmethod
    def build_snapshot(
        encounter_uid: str,
        round_number: int,
        current_turn_index: int,
        turn_order: List[Entity],
        hidden_combatants: Dict[str, Entity],
        combatants: List[Entity],
        fog_manager: FogManager,
    ) -> Dict[str, Any]:
        turn_order_uids = [c.uid for c in turn_order if not c.is_hidden]
        hidden_combatants_uids = list(hidden_combatants.keys())
        combatants_state = []
        for c in combatants:
            etype_str = c.entity_type.value if hasattr(c, "entity_type") else ("player" if getattr(c, "is_player", False) else "monster")
            combatants_state.append({
                "uid": c.uid,
                "name": c.name,
                "is_alive": c.is_alive,
                "current_hp": c.current_hp,
                "max_hp": c.max_hp,
                "armor_class": c.armor_class,
                "entity_type": etype_str,
                "token_sprite": getattr(c, "token_sprite", None),
                "size": getattr(c, "size", "Medium"),
                "conditions": list(c.conditions),
                "position": c.position,
                "hidden": c.is_hidden,
            })

        return {
            "encounter_uid": encounter_uid,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "round": round_number,
            "current_turn_index": current_turn_index,
            "turn_order": turn_order_uids,
            "hidden_combatants": hidden_combatants_uids,
            "fog_of_war": fog_manager.export_state(),
            "combatants_state": combatants_state,
        }

    @staticmethod
    def save_state(
        encounter_uid: str,
        round_number: int,
        current_turn_index: int,
        turn_order: List[Entity],
        hidden_combatants: Dict[str, Entity],
        combatants: List[Entity],
        fog_manager: FogManager,
    ) -> bool:
        if not encounter_uid:
            logger.warning("Nenhum encontro ativo carregado para salvar o estado de combate.")
            return False

        try:
            save_path = CombatStateSerializer.get_save_path(encounter_uid)
            snapshot = CombatStateSerializer.build_snapshot(
                encounter_uid=encounter_uid,
                round_number=round_number,
                current_turn_index=current_turn_index,
                turn_order=turn_order,
                hidden_combatants=hidden_combatants,
                combatants=combatants,
                fog_manager=fog_manager,
            )

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=4, ensure_ascii=False)

            logger.info(
                f"Estado de combate salvo com sucesso em '{save_path}' (Rodada {round_number}, "
                f"Turno {current_turn_index}, {len(combatants)} combatentes, "
                f"{len(hidden_combatants)} ocultos, {fog_manager.count} células de névoa)."
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar estado de combate do encontro '{encounter_uid}': {e}")
            return False

    @staticmethod
    def restore_combatants_state(
        combatants: List[Entity],
        combatants_state_data: List[Dict[str, Any]],
    ) -> Tuple[List[Entity], Dict[str, Entity], Dict[str, Entity]]:
        """
        Restaura o estado individual de cada entidade e instancia tokens dinâmicos.
        Retorna (todos_combatentes, combatentes_por_uid, combatentes_ocultos).
        """
        existing_by_uid = {c.uid: c for c in combatants}
        existing_by_name = {c.name.lower(): c for c in combatants}
        combatants_by_uid: Dict[str, Entity] = {}
        all_combatants = list(combatants)

        for c_state in combatants_state_data:
            uid = c_state.get("uid")
            name = c_state.get("name")
            c: Optional[Entity] = None

            if uid and uid in existing_by_uid:
                c = existing_by_uid[uid]
            elif name and name.lower() in existing_by_name:
                c = existing_by_name[name.lower()]
                if uid:
                    c.set_uid(uid)
            else:
                # Entidade dinâmica spawnada no meio do combate (Mid-Combat Token Spawn)
                etype_val = c_state.get("entity_type", "neutral")
                max_hp_val = int(c_state.get("max_hp", 1))
                ac_val = int(c_state.get("armor_class", 10))
                token_sprite_val = c_state.get("token_sprite")
                c = DynamicToken(
                    name=name or "Token",
                    max_hp=max_hp_val,
                    armor_class=ac_val,
                    uid=uid,
                    entity_type=etype_val,
                    token_sprite=token_sprite_val,
                )
                all_combatants.append(c)
                if uid:
                    existing_by_uid[uid] = c

            if c is not None:
                combatants_by_uid[c.uid] = c

                # HP e Vitalidade
                if "max_hp" in c_state:
                    c.set_max_hp(int(c_state["max_hp"]))
                if "current_hp" in c_state:
                    hp = int(c_state["current_hp"])
                    c.set_current_hp(hp)
                    if hp <= 0 or not c_state.get("is_alive", True):
                        c.die()

                # Condições
                if "conditions" in c_state:
                    for cond in list(c.conditions):
                        c.remove_condition(cond)
                    for cond in c_state["conditions"]:
                        c.add_condition(cond)

                # Posição no Grid
                if "position" in c_state:
                    pos = c_state["position"]
                    if isinstance(pos, dict):
                        px = int(pos.get("x", pos.get("col", 0)))
                        py = int(pos.get("y", pos.get("row", 0)))
                        c.set_position(px, py)

                # Visibilidade Tática
                if "hidden" in c_state:
                    c.set_hidden(bool(c_state["hidden"]))
                elif "is_hidden" in c_state:
                    c.set_hidden(bool(c_state["is_hidden"]))

        hidden_combatants = {c.uid: c for c in all_combatants if c.is_hidden}
        return all_combatants, combatants_by_uid, hidden_combatants

    @staticmethod
    def delete_save_state(encounter_uid: str) -> None:
        if not encounter_uid:
            logger.warning("UID do encontro não fornecido para exclusão do save.")
            return

        try:
            save_path = CombatStateSerializer.get_save_path(encounter_uid)
            if save_path.is_file():
                save_path.unlink(missing_ok=True)
                logger.info(f"Arquivo de save de combate excluído com sucesso: '{save_path}'.")
            else:
                logger.debug(f"Nenhum arquivo de save encontrado para exclusão em '{save_path}'.")
        except Exception as e:
            logger.error(f"Erro ao excluir arquivo de save de combate para '{encounter_uid}': {e}")
