from abc_algorithm import generate_abc_population


def _abc_solution_key(sol: dict):
    return (
        sol.get("total_value", 0),
        -sol.get("total_time", float("inf")),
        -sol.get("movement_time", float("inf")),
        -sol.get("attraction_cost", float("inf")),
    )


def _to_ui_path(abc_path):
    # ABC uses (row, col), UI uses (x, y)
    return [(c, r) for r, c in abc_path]


def _abc_evaluate_path(path, parsed_data):
    move_time = parsed_data["move_time"]
    time_limit = parsed_data["time_limit"]
    budget = parsed_data["budget"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]

    movement_time = 0.0
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
        movement_time += move_time[r1][c1] * (1.4 if diagonal else 1.0)

    for pos in path:
        if pos in attraction_map and pos not in visited_set:
            visited_set.add(pos)
            attr = attraction_map[pos]
            t_id = attr["type"]

            visited_attractions.append(pos)
            attraction_cost += int(attr.get("cost", 0) or 0)
            # UI doesn't model visit time per-type yet.
            attraction_time += 0
            total_value += attr["value"]
            type_counts[t_id] += 1

    total_time = movement_time + attraction_time

    time_ok = movement_time <= time_limit
    budget_ok = attraction_cost <= budget

    return {
        "path": path,
        "visited_attractions": visited_attractions,
        "used_attractions": visited_attractions,
        "movement_time": movement_time,
        "attraction_cost": attraction_cost,
        "total_time": total_time,
        "total_value": total_value,
        "type_counts": type_counts,
        "budget_ok": budget_ok,
        "time_ok": time_ok,
        "type_ok": True,
        "feasible": budget_ok and time_ok,
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
            "cost": int(a.get("cost", 0) or 0),
            "type": type_id,
        }

    return {
        "move_time": map_data["weights"],
        "rows": map_data["height"],
        "cols": map_data["width"],
        "time_limit": int(map_data.get("time_limit", 0) or 0),
        "budget": int(map_data.get("budget", 0) or 0),
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
    *,
    on_iteration=None,
    should_stop=None,
    top_k: int = 3,
):
    parsed_data = _ui_map_to_abc(map_data)

    start = (map_data["start"]["y"], map_data["start"]["x"])
    end = (map_data["end"]["y"], map_data["end"]["x"])

    def _on_iter(it, best, population, history):
        if on_iteration is None:
            return
        top = sorted(population, key=_abc_solution_key, reverse=True)[: max(1, int(top_k))]
        on_iteration(
            {
                "iteration": it,
                "history": history,
                "best": best,
                "best_path": _to_ui_path(best["path"]),
                "top_solutions": top,
                "top_paths": [_to_ui_path(s["path"]) for s in top],
            }
        )

    result = generate_abc_population(
        parsed_data,
        population_size=population_size,
        start=start,
        end=end,
        iterations=iterations,
        limit=limit,
        seed=seed,
        deduplicate=False,
        evaluate_path_fn=_abc_evaluate_path,
        on_iteration=_on_iter if on_iteration is not None else None,
        should_stop=should_stop,
    )

    best = result["best"]
    history = result["history"]

    ui_path = _to_ui_path(best["path"])

    return {
        "path": ui_path,
        "history": history,
        "best": best,
    }