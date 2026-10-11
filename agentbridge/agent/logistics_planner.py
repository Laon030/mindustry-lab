"""Deterministic drill placement, conveyor routing, cost and flow verification."""

from collections import deque
from dataclasses import dataclass


DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))


@dataclass(frozen=True)
class ConveyorStep:
    x: int
    y: int
    rotation: int


@dataclass(frozen=True)
class LogisticsPlan:
    drill_x: int
    drill_y: int
    drill_footprint: tuple[tuple[int, int], ...]
    ore_tiles: int
    conveyors: tuple[ConveyorStep, ...]
    drill_cost: int
    conveyor_cost: int
    safety_margin: int

    @property
    def construction_cost(self):
        return self.drill_cost + len(self.conveyors) * self.conveyor_cost

    @property
    def required_copper(self):
        return self.construction_cost + self.safety_margin


def _point(value):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(v) is not int for v in value)):
        raise ValueError("Expected [tileX, tileY]")
    return tuple(value)


def _direction(source, target):
    delta = target[0] - source[0], target[1] - source[1]
    try:
        return DIRECTIONS.index(delta)
    except ValueError as error:
        raise ValueError("Route tiles must be orthogonally adjacent") from error


def _goal_direction(point, core):
    matches = []
    for rotation, delta in enumerate(DIRECTIONS):
        if (point[0] + delta[0], point[1] + delta[1]) in core:
            matches.append(rotation)
    return min(matches) if matches else None


def find_route(conveyor_cells, drill_footprint, core_footprint):
    """Find a route that exits the drill straight and terminates facing the core."""
    cells = dict(conveyor_cells)
    drill, core = set(drill_footprint), set(core_footprint)
    best = None

    for edge in sorted(drill):
        for outward, delta in enumerate(DIRECTIONS):
            start = edge[0] + delta[0], edge[1] + delta[1]
            if start in drill or start not in cells or not cells[start] & (1 << outward):
                continue
            core_direction = _goal_direction(start, core)
            if core_direction == outward:
                candidate = (ConveyorStep(*start, outward),)
                if best is None or _route_key(candidate) < _route_key(best):
                    best = candidate
                continue

            second = start[0] + delta[0], start[1] + delta[1]
            if second not in cells or second in drill or second in core:
                continue
            queue = deque([(second, (start, second))])
            visited = {start, second}
            while queue:
                current, path = queue.popleft()
                final_rotation = _goal_direction(current, core)
                if final_rotation is not None and cells[current] & (1 << final_rotation):
                    rotations = [outward]
                    rotations.extend(_direction(path[i], path[i + 1]) for i in range(1, len(path) - 1))
                    rotations.append(final_rotation)
                    candidate = tuple(ConveyorStep(*point, rotation)
                                      for point, rotation in zip(path, rotations))
                    if best is None or _route_key(candidate) < _route_key(best):
                        best = candidate
                    break
                for rotation, step in enumerate(DIRECTIONS):
                    following = current[0] + step[0], current[1] + step[1]
                    if (following in visited or following in drill or following in core
                            or following not in cells or not cells[current] & (1 << rotation)):
                        continue
                    visited.add(following)
                    queue.append((following, path + (following,)))
    return best


def _route_key(route):
    return len(route), tuple((step.x, step.y, step.rotation) for step in route)


def choose_plan(logistics, safety_margin=10):
    if type(safety_margin) is not int or safety_margin < 0:
        raise ValueError("Safety margin must be a non-negative integer")
    core = logistics.get("core", {})
    core_footprint = tuple(_point(p) for p in core.get("footprint", []))
    if not core_footprint:
        raise ValueError("Core footprint is unavailable")

    cells = {}
    for value in logistics.get("conveyorCells", []):
        if (not isinstance(value, list) or len(value) != 3
                or any(type(v) is not int for v in value) or not 1 <= value[2] <= 15):
            raise ValueError("Invalid conveyor cell")
        cells[(value[0], value[1])] = value[2]

    content = logistics.get("content", {})
    drill = content.get("drill", {})
    conveyor = content.get("conveyor", {})
    if drill.get("name") != "mechanical-drill" or drill.get("size") != 2:
        raise ValueError("Expected the pinned mechanical drill definition")
    if conveyor.get("name") != "conveyor" or conveyor.get("size") != 1:
        raise ValueError("Expected the pinned conveyor definition")
    drill_cost = drill.get("requirements", {}).get("copper")
    conveyor_cost = conveyor.get("requirements", {}).get("copper")
    if type(drill_cost) is not int or drill_cost <= 0 or type(conveyor_cost) is not int or conveyor_cost <= 0:
        raise ValueError("Copper build requirements are unavailable")

    plans = []
    core_center = core.get("tileX"), core.get("tileY")
    for candidate in logistics.get("drillCandidates", []):
        if candidate.get("oreItem") != "copper" or type(candidate.get("oreTiles")) is not int:
            continue
        footprint = tuple(_point(p) for p in candidate.get("footprint", []))
        if len(footprint) != 4:
            continue
        route = find_route(cells, footprint, core_footprint)
        if not route:
            continue
        plan = LogisticsPlan(candidate["tileX"], candidate["tileY"], footprint,
                             candidate["oreTiles"], route, drill_cost, conveyor_cost, safety_margin)
        distance = abs(plan.drill_x - core_center[0]) + abs(plan.drill_y - core_center[1])
        plans.append(((len(route), -plan.ore_tiles, distance, plan.drill_y, plan.drill_x), plan))
    if not plans:
        raise ValueError("No valid copper drill and conveyor route found in bounded scan")
    return min(plans, key=lambda entry: entry[0])[1]


def resources_sufficient(copper, plan):
    return type(copper) is int and copper >= plan.required_copper


def buildings_by_tile(state):
    return {(b["tileX"], b["tileY"]): b for b in state.get("logistics", {}).get("buildings", [])}


def plan_complete(state, plan):
    buildings = buildings_by_tile(state)
    drill = buildings.get((plan.drill_x, plan.drill_y))
    if not drill or drill.get("block") != "mechanical-drill" or drill.get("team") != state.get("team"):
        return False
    for step in plan.conveyors:
        building = buildings.get((step.x, step.y))
        if (not building or building.get("block") != "conveyor"
                or building.get("team") != state.get("team")
                or building.get("rotation") != step.rotation):
            return False
    return True


class FlowVerifier:
    def __init__(self, state, plan):
        core = state["logistics"]["core"]
        self.plan = plan
        self.baseline_copper = core["copper"]
        self.baseline_received = core["receivedCopper"]
        self.drill_producing = False
        self.conveyor_copper_seen = False
        self.core_copper_increased = False
        self.core_receipt_seen = False

    def update(self, state, mono_resource, mono_mining):
        buildings = buildings_by_tile(state)
        drill = buildings.get((self.plan.drill_x, self.plan.drill_y), {})
        self.drill_producing |= (drill.get("block") == "mechanical-drill"
                                 and drill.get("dominantItem") == "copper"
                                 and drill.get("lastDrillSpeed", 0) > 0)
        self.conveyor_copper_seen |= any(
            buildings.get((step.x, step.y), {}).get("copper", 0) > 0
            for step in self.plan.conveyors)
        core = state["logistics"]["core"]
        self.core_copper_increased |= core["copper"] > self.baseline_copper
        self.core_receipt_seen |= core["receivedCopper"] > self.baseline_received
        isolated = mono_resource == "lead" and mono_mining
        return (isolated and self.drill_producing and self.conveyor_copper_seen
                and self.core_copper_increased and self.core_receipt_seen)

    def evidence(self):
        return {"drillProducing": self.drill_producing,
                "conveyorCopperSeen": self.conveyor_copper_seen,
                "coreCopperIncreased": self.core_copper_increased,
                "coreReceiptSeen": self.core_receipt_seen,
                "baselineCopper": self.baseline_copper,
                "baselineReceived": self.baseline_received}
