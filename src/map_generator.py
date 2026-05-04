from __future__ import annotations

import random
from typing import List, Optional

DEFAULT_TYPES = ["zabytek", "przyroda"]


def generate_map(
    width: int,
    height: int,
    n_attractions: int,
    value_min: int,
    value_max: int,
    cost_min: int,
    cost_max: int,
    weight_distribution: str,
    weight_min: int,
    weight_max: int,
    start: Optional[tuple[int, int]],
    end: Optional[tuple[int, int]],
    time_limit: int,
    budget: int,
    seed: int,
    name: str = "",
    attraction_types: Optional[List[str]] = None,
) -> dict:
    rng = random.Random(seed)
    types = attraction_types if attraction_types else DEFAULT_TYPES

    if start is None:
        start = (0, 0)
    if end is None:
        end = (width - 1, height - 1)

    weights = _generate_weights(rng, width, height, weight_distribution, weight_min, weight_max)

    occupied = {start, end}
    attractions = []
    attempts = 0
    while len(attractions) < n_attractions and attempts < width * height * 4:
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        if (x, y) not in occupied:
            occupied.add((x, y))
            attractions.append({
                "id": f"a{len(attractions) + 1}",
                "x": x,
                "y": y,
                "value": rng.randint(value_min, value_max),
                "cost": rng.randint(cost_min, cost_max),
                "type": types[len(attractions) % len(types)],
            })
        attempts += 1

    return {
        "name": name or f"Mapa {width}x{height}",
        "notes": "",
        "width": width,
        "height": height,
        "weights": weights,
        "attractions": attractions,
        "attraction_types": types,
        "start": {"x": start[0], "y": start[1]},
        "end": {"x": end[0], "y": end[1]},
        "time_limit": int(time_limit),
        "budget": budget,
        "seed": seed,
    }


def _generate_weights(
    rng: random.Random,
    width: int,
    height: int,
    distribution: str,
    w_min: int,
    w_max: int,
) -> list[list[int]]:
    if distribution == "clusters":
        n_clusters = max(2, (width * height) // 25)
        centers = [(rng.randint(0, width - 1), rng.randint(0, height - 1)) for _ in range(n_clusters)]
        weights = []
        for y in range(height):
            row = []
            for x in range(width):
                dist = min(_chebyshev(x, y, cx, cy) for cx, cy in centers)
                base = rng.randint(w_min, w_max)
                bonus = max(0, (w_max - w_min) // 2 - dist)
                row.append(min(w_max, base + bonus))
            weights.append(row)
    else:
        weights = [
            [rng.randint(w_min, w_max) for _ in range(width)]
            for _ in range(height)
        ]
    return weights


def _chebyshev(x1: int, y1: int, x2: int, y2: int) -> int:
    return max(abs(x1 - x2), abs(y1 - y2))
