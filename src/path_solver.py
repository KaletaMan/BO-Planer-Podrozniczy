from __future__ import annotations

import random
from typing import Optional


# 8-neighbor offsets
_DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def _step_cost(
    weights: list[list[int]],
    from_cell: tuple[int, int],
    to_cell: tuple[int, int],
) -> float:
    """Movement cost consistent with ABC: cost uses the weight of the *from* cell.

    Straight move factor = 1.0, diagonal factor = 1.4.
    """
    fx, fy = from_cell
    tx, ty = to_cell
    diagonal = abs(tx - fx) == 1 and abs(ty - fy) == 1
    return float(weights[fy][fx]) * (1.4 if diagonal else 1.0)


def evaluate_path(map_data: dict, path: list[tuple[int, int]]) -> dict:
    weights = map_data["weights"]
    time_limit = map_data.get("time_limit", float("inf"))
    budget = map_data.get("budget", float("inf"))
    attraction_map = {
        (a["x"], a["y"]): {
            "value": a.get("value", 0),
            "cost": a.get("cost", 0),
            "id": a.get("id"),
        }
        for a in map_data.get("attractions", [])
    }
    w = map_data["width"]
    h = map_data["height"]

    movement_time = 0.0
    value_collected = 0
    attraction_cost = 0.0
    attractions_visited = []
    visited_cells: set[tuple[int, int]] = set()

    prev = path[0] if path else None
    for cell in path[1:]:
        x, y = cell
        if not (0 <= x < w and 0 <= y < h):
            return {"cost": movement_time, "movement_time": movement_time,
                    "attraction_cost": attraction_cost, "value_collected": value_collected,
                    "attractions_visited": attractions_visited, "feasible": False,
                    "reason": f"Komórka {cell} poza mapą."}
        movement_time += _step_cost(weights, prev, cell)
        prev = cell
        if cell not in visited_cells:
            visited_cells.add(cell)
            if cell in attraction_map:
                value_collected += attraction_map[cell]["value"]
                attraction_cost += float(attraction_map[cell].get("cost") or 0)
                attractions_visited.append(cell)

    time_ok = movement_time <= time_limit
    budget_ok = attraction_cost <= budget

    feasible = time_ok and budget_ok
    if feasible:
        reason = "OK"
    elif not time_ok and not budget_ok:
        reason = f"Przekroczono limit czasu ({movement_time:.2f} > {time_limit}) i budżet ({attraction_cost:.2f} > {budget})."
    elif not time_ok:
        reason = f"Czas ruchu {movement_time:.2f} > limit czasu {time_limit}."
    else:
        reason = f"Koszt atrakcji {attraction_cost:.2f} > budżet {budget}."
    return {
        # 'cost' kept for backward compatibility in UI: it is movement time.
        "cost": movement_time,
        "movement_time": movement_time,
        "attraction_cost": attraction_cost,
        "value_collected": value_collected,
        "attractions_visited": attractions_visited,
        "path_length": len(path),
        "feasible": feasible,
        "reason": reason,
    }


def solve_random_walk(
    map_data: dict,
    max_steps: int = 500,
    seed: Optional[int] = None,
) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    w, h = map_data["width"], map_data["height"]
    weights = map_data["weights"]
    time_limit = map_data.get("time_limit", float("inf"))
    start = (map_data["start"]["x"], map_data["start"]["y"])
    end_data = map_data.get("end")
    end = (end_data["x"], end_data["y"]) if end_data else None

    path = [start]
    movement_time = 0.0

    for _ in range(max_steps):
        x, y = path[-1]
        if end and (x, y) == end:
            break
        neighbors = [
            (x + dx, y + dy)
            for dx, dy in _DIRS
            if 0 <= x + dx < w and 0 <= y + dy < h
        ]
        rng.shuffle(neighbors)
        moved = False
        for nx, ny in neighbors:
            step_cost = _step_cost(weights, (x, y), (nx, ny))
            if movement_time + step_cost <= time_limit:
                path.append((nx, ny))
                movement_time += step_cost
                moved = True
                break
        if not moved:
            break

    return path


def solve_greedy_attractions(map_data: dict) -> list[tuple[int, int]]:
    w, h = map_data["width"], map_data["height"]
    weights = map_data["weights"]
    time_limit = map_data.get("time_limit", float("inf"))
    start = (map_data["start"]["x"], map_data["start"]["y"])

    remaining = {
        (a["x"], a["y"]): a["value"]
        for a in map_data.get("attractions", [])
    }

    path = [start]
    movement_time = 0.0
    pos = start

    while remaining:
        target = min(remaining, key=lambda t: _chebyshev(pos[0], pos[1], t[0], t[1]))
        sub_path, sub_cost = _walk_toward(pos, target, weights, w, h, time_limit - movement_time)
        if sub_path is None or len(sub_path) <= 1:
            break
        path.extend(sub_path[1:])
        movement_time += sub_cost
        pos = path[-1]
        remaining.pop(pos, None)

    return path


def _chebyshev(x1: int, y1: int, x2: int, y2: int) -> int:
    return max(abs(x1 - x2), abs(y1 - y2))


def _walk_toward(
    start: tuple[int, int],
    goal: tuple[int, int],
    weights: list[list[int]],
    w: int,
    h: int,
    remaining_budget: float,
) -> tuple[Optional[list[tuple[int, int]]], float]:
    """Greedy step-by-step toward goal (chebyshev direction). Returns (path, cost) or (None, 0) if blocked."""
    path = [start]
    cost = 0.0
    pos = start

    for _ in range(w * h):
        if pos == goal:
            break
        x, y = pos
        gx, gy = goal
        dx = 0 if gx == x else (1 if gx > x else -1)
        dy = 0 if gy == y else (1 if gy > y else -1)
        nx, ny = x + dx, y + dy
        if not (0 <= nx < w and 0 <= ny < h):
            return None, 0
        step = _step_cost(weights, (x, y), (nx, ny))
        if cost + step > remaining_budget:
            return path, cost
        cost += step
        pos = (nx, ny)
        path.append(pos)

    return path, cost
