from abc_algorithm import generate_abc_population


def _abc_evaluate_path(path, parsed_data):
    weight = parsed_data["weight"]
    budget = parsed_data["budget"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]

    movement_cost = 0.0
    attraction_cost = 0
    attraction_time = 0
    total_value = 0

    visited_attractions = []
    visited_set = set()
    type_counts = [0 for _ in attraction_types]

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        diagonal = abs(r2 - r1) == 1 and abs(c2 - c1) == 1
        movement_cost += weight[r1][c1] * (1.4 if diagonal else 1.0)

    for pos in path:
        if pos in attraction_map and pos not in visited_set:
            visited_set.add(pos)
            attr = attraction_map[pos]
            t_id = attr["type"]

            visited_attractions.append(pos)
            attraction_cost += attr["cost"]
            attraction_time += attraction_types[t_id]["time"]
            total_value += attr["value"]
            type_counts[t_id] += 1

    total_time = movement_cost + attraction_time

    return {
        "path": path,
        "visited_attractions": visited_attractions,
        "used_attractions": visited_attractions,
        "movement_cost": movement_cost,
        "attraction_cost": attraction_cost,
        "total_time": total_time,
        "total_value": total_value,
        "type_counts": type_counts,
        "budget_ok": attraction_cost <= budget,
        "time_ok": True,
        "type_ok": True,
        "feasible": attraction_cost <= budget,
    }


def _ui_map_to_abc(map_data):
    type_names = map_data.get("attraction_types", [])

    parsed_types = [
        {
            "time": 1,
            "min": 0,
            "max": 999,
        }
        for _ in type_names
    ]

    attraction_map = {}

    for a in map_data.get("attractions", []):
        pos = (a["y"], a["x"])  # ABC używa (row, col), UI używa (x, y)
        type_id = type_names.index(a["type"]) if a.get("type") in type_names else 0

        attraction_map[pos] = {
            "value": a["value"],
            "cost": 1,
            "type": type_id,
        }

    return {
        "weight": map_data["weights"],
        "rows": map_data["height"],
        "cols": map_data["width"],
        "time_limit": 999999,
        "budget": map_data.get("budget", 999999),
        "attraction_map": attraction_map,
        "attraction_types": parsed_types,
        "attraction_positions": list(attraction_map.keys()),
    }


def solve_abc_ui(
    map_data,
    population_size=30,
    iterations=100,
    limit=30,
    seed=None,
):
    parsed_data = _ui_map_to_abc(map_data)

    start = (map_data["start"]["y"], map_data["start"]["x"])
    end = (map_data["end"]["y"], map_data["end"]["x"])

    result = generate_abc_population(
        parsed_data,
        population_size=population_size,
        start=start,
        end=end,
        iterations=iterations,
        limit=limit,
        seed=seed,
        evaluate_path_fn=_abc_evaluate_path,
    )

    best = result["best"]
    history = result["history"]

    # ABC zwraca (row, col), UI rysuje (x, y)
    ui_path = [(c, r) for r, c in best["path"]]

    return {
        "path": ui_path,
        "history": history,
        "best": best,
    }