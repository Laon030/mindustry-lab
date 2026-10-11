"""Bounded strategic intent -> legal team command mapping for the duel demo."""

from .coordinator import CommandRejected
from .ollama_provider import validate_slot_decision
from .provider import validate_decision


def apply_intent(coordinator, agent_id, decision):
    """The model selects an intent; Python handles only its unambiguous mechanics."""
    validate_decision(decision)
    session = coordinator.sessions[agent_id]
    if session.observation is None:
        raise CommandRejected("Observe before applying a duel intent")
    own = session.observation["own"]
    fighters = sorted(unit["id"] for unit in own["units"]
                      if unit["id"] in session.roster and unit["type"] == "dagger")
    if decision["intent"] == "WAIT":
        session.decision_counter += 1
        session.last_decision = dict(decision)
        session.log.append({"tick": session.observation["tick"], "intent": dict(decision)})
        return {"accepted": True, "action": "wait", "team": session.team}
    if not fighters:
        raise CommandRejected("No live Dagger group")
    if decision["intent"] == "DEFEND":
        cores = own["cores"]
        if len(cores) != 1:
            raise CommandRejected("Own core target is ambiguous or absent")
        command = {"team": session.team, "action": "move", "unitIds": fighters,
                   "x": cores[0]["x"] * 8, "y": cores[0]["y"] * 8}
    else:
        enemies = [unit["id"] for unit in session.observation["enemy"]["units"]
                   if unit["type"] == "dagger" and unit["health"] > 0]
        if len(enemies) != 1:
            raise CommandRejected("Enemy-force target is ambiguous or absent")
        command = {"team": session.team, "action": "attack", "unitIds": fighters,
                   "targetUnitId": enemies[0]}
    result = coordinator.command(agent_id, command)
    session.last_decision = dict(decision)
    session.log.append({"tick": session.observation["tick"], "intent": dict(decision)})
    return result


def resolve_slot_intent(coordinator, agent_id, decision):
    """Resolve an LLM-selected enemy slot to live IDs without choosing its target."""
    session = coordinator.sessions[agent_id]
    if session.observation is None:
        raise CommandRejected("Observe before applying a duel intent")
    validate_slot_decision(decision, session.observation)
    if decision["intent"] == "WAIT":
        return None
    own = session.observation["own"]
    fighters = sorted(unit["id"] for unit in own["units"]
                      if unit["id"] in session.roster and unit["type"] == "dagger")
    if not fighters:
        raise CommandRejected("No live Dagger group")
    if decision["intent"] == "DEFEND":
        core = own["cores"][0]
        return {"team": session.team, "action": "move", "unitIds": fighters,
                "x": core["x"] * 8, "y": core["y"] * 8}
    enemies = sorted((unit["id"] for unit in session.observation["enemy"]["units"]
                      if unit["type"] == "dagger" and unit["health"] > 0))
    slot = decision["target_slot"]
    if slot >= len(enemies):
        raise CommandRejected("Selected enemy slot is no longer live")
    return {"team": session.team, "action": "attack", "unitIds": fighters,
            "targetUnitId": enemies[slot]}


def apply_slot_intent(coordinator, agent_id, decision, command):
    """Issue a previously resolved command from the same paused round."""
    session = coordinator.sessions[agent_id]
    if command != resolve_slot_intent(coordinator, agent_id, decision):
        raise CommandRejected("Resolved command changed before dispatch")
    if command is None:
        session.decision_counter += 1
        result = {"accepted": True, "action": "wait", "team": session.team}
    else:
        result = coordinator.command(agent_id, command)
    session.last_decision = dict(decision)
    session.log.append({"tick": session.observation["tick"], "intent": dict(decision)})
    return result
