"""Step 3: choose which dealers to visit today and in what order.

This is a prize-collecting TSP: start and end at the branch office, fit travel + visits
into the working day, respect a maximum number of stops, and skip dealers only when
needed - each skip costs a penalty equal to the dealer's priority score, so low-priority
dealers are dropped first. Must-visit dealers are never skipped.

Node 0 is the branch office; node i (i >= 1) is dealer row i - 1.
"""
from dataclasses import dataclass, field

import numpy as np

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    HAS_ORTOOLS = True
except ImportError:  # pragma: no cover - exercised only without OR-Tools installed
    HAS_ORTOOLS = False

DEPOT = 0


class PlanningError(ValueError):
    """The constraints cannot be met (e.g. too many must-visit dealers for one day)."""


@dataclass
class PlanSettings:
    visit_minutes: float = 30
    day_hours: float = 8.0
    max_stops: int = 10
    # 1 priority point is worth this many km of extra driving.
    km_per_priority_point: float = 1.0
    time_limit_s: int = 3

    @property
    def day_minutes(self) -> float:
        return self.day_hours * 60


@dataclass
class RoutePlan:
    order: list[int]  # dealer row indices in visit order
    skipped: list[int]  # dealer row indices not visited today
    method: str
    total_km: float = 0.0
    travel_minutes: float = 0.0
    total_minutes: float = 0.0  # travel + visits
    notes: list[str] = field(default_factory=list)


def route_metrics(order: list[int], km: np.ndarray, minutes: np.ndarray, visit_minutes: float) -> tuple[float, float, float]:
    """(total km, travel minutes, total day minutes) for office -> order -> office."""
    nodes = [DEPOT] + [i + 1 for i in order] + [DEPOT]
    dist = sum(km[a, b] for a, b in zip(nodes, nodes[1:]))
    drive = sum(minutes[a, b] for a, b in zip(nodes, nodes[1:]))
    return float(dist), float(drive), float(drive + visit_minutes * len(order))


def _finish(order, n_dealers, method, km, minutes, settings, notes=None) -> RoutePlan:
    total_km, drive, total = route_metrics(order, km, minutes, settings.visit_minutes)
    skipped = [i for i in range(n_dealers) if i not in set(order)]
    return RoutePlan(order, skipped, method, total_km, drive, total, notes or [])


def _validate(n_dealers: int, must_visit: set[int], settings: PlanSettings) -> None:
    if any(i < 0 or i >= n_dealers for i in must_visit):
        raise PlanningError("Must-visit list contains an unknown dealer.")
    if len(must_visit) > settings.max_stops:
        raise PlanningError(
            f"{len(must_visit)} must-visit dealers but only {settings.max_stops} stops allowed per day."
        )
    if len(must_visit) * settings.visit_minutes > settings.day_minutes:
        raise PlanningError("Must-visit dealers alone need more time than the working day.")


# ----------------------------------------------------------------------------- OR-Tools
def solve_ortools(km, minutes, priority, must_visit: set[int], settings: PlanSettings) -> RoutePlan:
    n_dealers = len(priority)
    n_nodes = n_dealers + 1
    manager = pywrapcp.RoutingIndexManager(n_nodes, 1, DEPOT)
    routing = pywrapcp.RoutingModel(manager)

    # Cost: road distance in metres.
    dist_m = np.rint(km * 1000).astype(int)

    def distance_cb(from_index, to_index):
        return int(dist_m[manager.IndexToNode(from_index), manager.IndexToNode(to_index)])

    dist_idx = routing.RegisterTransitCallback(distance_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(dist_idx)

    # Time dimension (seconds): drive time + visit time at the dealer we are leaving.
    drive_s = np.rint(minutes * 60).astype(int)
    visit_s = int(round(settings.visit_minutes * 60))

    def time_cb(from_index, to_index):
        a, b = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        return int(drive_s[a, b]) + (visit_s if a != DEPOT else 0)

    time_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(time_idx, 0, int(settings.day_minutes * 60), True, "Time")

    # Stops dimension: each dealer counts as one stop.
    def stop_cb(from_index):
        return 0 if manager.IndexToNode(from_index) == DEPOT else 1

    stop_idx = routing.RegisterUnaryTransitCallback(stop_cb)
    routing.AddDimensionWithVehicleCapacity(stop_idx, 0, [settings.max_stops], True, "Stops")

    # Optional visits: skipping a dealer costs its priority (converted to metres).
    for dealer in range(n_dealers):
        if dealer in must_visit:
            continue  # no disjunction -> the solver must visit it
        penalty = max(1, int(round(priority[dealer] * settings.km_per_priority_point * 1000)))
        routing.AddDisjunction([manager.NodeToIndex(dealer + 1)], penalty)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = settings.time_limit_s

    solution = routing.SolveWithParameters(params)
    if solution is None:
        raise PlanningError("No feasible route: the must-visit dealers cannot fit in the working day.")

    order = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node != DEPOT:
            order.append(node - 1)
        index = solution.Value(routing.NextVar(index))
    return _finish(order, n_dealers, "OR-Tools (Path Cheapest Arc + Guided Local Search)", km, minutes, settings)


# ----------------------------------------------------------------------------- Backup heuristic
def _best_insertion(route: list[int], node: int, km: np.ndarray) -> tuple[float, int]:
    """Cheapest place to insert node into a closed node route; returns (extra km, position)."""
    best = (float("inf"), 1)
    for pos in range(1, len(route)):
        a, b = route[pos - 1], route[pos]
        extra = km[a, node] + km[node, b] - km[a, b]
        if extra < best[0]:
            best = (extra, pos)
    return best


def _route_minutes(route: list[int], minutes: np.ndarray, visit_minutes: float) -> float:
    drive = sum(minutes[a, b] for a, b in zip(route, route[1:]))
    return drive + visit_minutes * (len(route) - 2)


def two_opt(route: list[int], km: np.ndarray, minutes: np.ndarray, visit_minutes: float, day_minutes: float) -> list[int]:
    """Reverse route segments while that shortens the route (removes crossings)."""
    best = route[:]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                a, b, c, d = best[i - 1], best[i], best[j], best[j + 1]
                if km[a, c] + km[b, d] < km[a, b] + km[c, d] - 1e-9:
                    candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                    # Drive times aren't perfectly proportional to km, so re-check the clock.
                    if _route_minutes(candidate, minutes, visit_minutes) <= day_minutes:
                        best = candidate
                        improved = True
    return best


def solve_heuristic(km, minutes, priority, must_visit: set[int], settings: PlanSettings) -> RoutePlan:
    n_dealers = len(priority)
    route = [DEPOT, DEPOT]

    # 1) Must-visit dealers first, each at its cheapest position.
    for dealer in sorted(must_visit, key=lambda d: -priority[d]):
        _, pos = _best_insertion(route, dealer + 1, km)
        route.insert(pos, dealer + 1)
    if _route_minutes(route, minutes, settings.visit_minutes) > settings.day_minutes:
        raise PlanningError("No feasible route: the must-visit dealers cannot fit in the working day.")

    # 2) Repeatedly add the dealer with the best priority per extra minute of the day
    #    (detour drive + the visit itself) that still fits. Counting the visit time stops
    #    a dealer next door with a near-zero detour from always winning on ratio alone.
    candidates = set(range(n_dealers)) - must_visit
    while candidates and len(route) - 2 < settings.max_stops:
        best = None
        current = _route_minutes(route, minutes, settings.visit_minutes)
        for dealer in candidates:
            _, pos = _best_insertion(route, dealer + 1, km)
            trial = route[:pos] + [dealer + 1] + route[pos:]
            trial_minutes = _route_minutes(trial, minutes, settings.visit_minutes)
            if trial_minutes > settings.day_minutes:
                continue
            ratio = priority[dealer] / max(trial_minutes - current, 1.0)
            if best is None or ratio > best[0]:
                best = (ratio, dealer, trial)
        if best is None:
            break
        _, dealer, route = best
        candidates.discard(dealer)

    # 3) Tidy the order with 2-opt.
    route = two_opt(route, km, minutes, settings.visit_minutes, settings.day_minutes)
    order = [node - 1 for node in route[1:-1]]
    return _finish(order, n_dealers, "Greedy insertion + 2-opt (backup)", km, minutes, settings)


# ----------------------------------------------------------------------------- Public API
def plan_route(
    km: np.ndarray,
    minutes: np.ndarray,
    priority: list[float] | np.ndarray,
    must_visit: set[int] | None = None,
    settings: PlanSettings | None = None,
    use_ortools: bool = True,
) -> RoutePlan:
    """Pick and order today's visits. Uses OR-Tools when available, else the backup heuristic."""
    settings = settings or PlanSettings()
    must_visit = set(must_visit or ())
    priority = [float(p) for p in priority]
    _validate(len(priority), must_visit, settings)

    if use_ortools and HAS_ORTOOLS:
        return solve_ortools(km, minutes, priority, must_visit, settings)
    plan = solve_heuristic(km, minutes, priority, must_visit, settings)
    if use_ortools and not HAS_ORTOOLS:
        plan.notes.append("OR-Tools is not installed; used the backup heuristic.")
    return plan


def unplanned_order(order: list[int], priority) -> list[int]:
    """Baseline: the same dealers visited 'most urgent first', with no route planning."""
    return sorted(order, key=lambda d: -priority[d])
