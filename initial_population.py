import json
import random
import argparse
from statistics import mean

from load_json import load_map_from_json
from parser import parse_map
from abc_algorithm import generate_abc_population, check_no_repeated_edges


def _default_start_end(rows, cols, start, end):
    if start is None:
        start = (5, 5)
    if end is None:
        end = (rows - 10, cols - 1)

    sr, sc = start
    er, ec = end

    if not (0 <= sr < rows and 0 <= sc < cols):
        raise ValueError(f"start poza planszą: {start} przy {rows}x{cols}")
    if not (0 <= er < rows and 0 <= ec < cols):
        raise ValueError(f"end poza planszą: {end} przy {rows}x{cols}")
    return start, end


def movement_cost(path, weight):
    total = 0.0

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]

        dr = abs(r2 - r1)
        dc = abs(c2 - c1)

        if dr == 1 and dc == 1:
            direction_cost = 1.4
        else:
            direction_cost = 1.0

        total += weight[r1][c1] * direction_cost

    return total


def evaluate_path(path, parsed_data):
    move_time = parsed_data["move_time"]
    time_limit = parsed_data["time_limit"]
    budget = parsed_data["budget"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]

    visited_attractions = []
    used_attractions = []
    visited_attractions_set = set()

    attraction_cost_sum = 0
    attraction_time_sum = 0
    total_value = 0

    type_counts = [0 for _ in range(len(attraction_types))]

    for pos in path:
        if pos in attraction_map and pos not in visited_attractions_set:
            visited_attractions_set.add(pos)

            attr = attraction_map[pos]
            attr_type = attr["type"]

            visited_attractions.append(pos)
            used_attractions.append(pos)

            attraction_cost_sum += attr["cost"]
            attraction_time_sum += attraction_types[attr_type]["time"]
            total_value += attr["value"]
            type_counts[attr_type] += 1

    movement_time = movement_cost(path, move_time)
    total_time = movement_time + attraction_time_sum

    budget_ok = attraction_cost_sum <= budget
    time_ok = total_time <= time_limit

    type_ok = True
    for t_id, t_info in enumerate(attraction_types):
        count = type_counts[t_id]
        if count < t_info["min"] or count > t_info["max"]:
            type_ok = False
            break

    feasible = budget_ok and time_ok and type_ok

    return {
        "path": path,
        "visited_attractions": visited_attractions,
        "used_attractions": used_attractions,
        "movement_time": movement_time,
        "attraction_cost": attraction_cost_sum,
        "total_time": total_time,
        "total_value": total_value,
        "type_counts": type_counts,
        "budget_ok": budget_ok,
        "time_ok": time_ok,
        "type_ok": type_ok,
        "feasible": feasible,
    }


def print_population_stats(population, attraction_types):
    feasible_count = sum(1 for sol in population if sol["feasible"])
    budget_ok_count = sum(1 for sol in population if sol["budget_ok"])
    time_ok_count = sum(1 for sol in population if sol["time_ok"])
    type_ok_count = sum(1 for sol in population if sol["type_ok"])

    avg_total_time = mean(sol["total_time"] for sol in population)
    avg_attraction_cost = mean(sol["attraction_cost"] for sol in population)
    avg_attraction_count = mean(len(sol["used_attractions"]) for sol in population)
    avg_movement_time = mean(sol["movement_time"] for sol in population)
    avg_total_value = mean(sol["total_value"] for sol in population)
    avg_path_length = mean(len(sol["path"]) for sol in population)

    print("=== STATYSTYKI POPULACJI POCZĄTKOWEJ ===")
    print(f"Liczba tras: {len(population)}")
    print(f"Spełnia wszystko: {feasible_count}/{len(population)}")
    print(f"Spełnia budżet: {budget_ok_count}/{len(population)}")
    print(f"Spełnia limit czasu: {time_ok_count}/{len(population)}")
    print(f"Spełnia ograniczenia typów: {type_ok_count}/{len(population)}")
    print()
    print(f"Średni całkowity czas: {avg_total_time:.2f}")
    print(f"Średni czas ruchu: {avg_movement_time:.2f}")
    print(f"Średnio wydany budżet (ceny atrakcji): {avg_attraction_cost:.2f}")
    print(f"Średnia liczba atrakcji: {avg_attraction_count:.2f}")
    print(f"Średnia wartość atrakcji: {avg_total_value:.2f}")
    print(f"Średnia długość ścieżki (liczba pól): {avg_path_length:.2f}")
    print()

    print("Średnia liczba atrakcji każdego typu:")
    for t_id in range(len(attraction_types)):
        avg_count = mean(sol["type_counts"][t_id] for sol in population)
        t_info = attraction_types[t_id]
        print(
            f"  Typ {t_id}: {avg_count:.2f} "
            f"(min={t_info['min']}, max={t_info['max']}, time={t_info['time']})"
        )


def save_population_to_json(population, filename="initial_population.json"):
    serializable_population = []

    for sol in population:
        serializable_solution = {
            "id": sol["id"],
            "path": [[r, c] for r, c in sol["path"]],
            "visited_attractions": [[r, c] for r, c in sol["visited_attractions"]],
            "used_attractions": [[r, c] for r, c in sol["used_attractions"]],
            "movement_time": sol["movement_time"],
            "attraction_cost": sol["attraction_cost"],
            "total_time": sol["total_time"],
            "total_value": sol["total_value"],
            "type_counts": sol["type_counts"],
            "budget_ok": sol["budget_ok"],
            "time_ok": sol["time_ok"],
            "type_ok": sol["type_ok"],
            "feasible": sol["feasible"],
        }
        serializable_population.append(serializable_solution)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(serializable_population, f, indent=4)

    print(f"Zapisano populację do {filename}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generator populacji tras (ABC – Artificial Bee Colony)")
    ap.add_argument("--map", default="map.json", help="Plik mapy JSON")
    ap.add_argument("--out", default="initial_population.json", help="Plik wyjściowy populacji")
    ap.add_argument("--population-size", type=int, default=50)
    ap.add_argument("--seed", type=int, default=None)

    # ABC params
    ap.add_argument("--iters", type=int, default=200, help="Liczba iteracji ABC")
    ap.add_argument("--limit", type=int, default=60, help="Limit stagnacji (scout)")
    ap.add_argument("--onlookers", type=int, default=None, help="Liczba prób onlookerów na iterację")

    args = ap.parse_args()

    move_time, time_limit, budget, attractions, attraction_types = load_map_from_json(args.map)
    parsed_data = parse_map(move_time, time_limit, budget, attractions, attraction_types)

    start, end = _default_start_end(parsed_data["rows"], parsed_data["cols"], None, None)

    if args.seed is not None:
        random.seed(args.seed)

    abc_result = generate_abc_population(
        parsed_data,
        population_size=args.population_size,
        start=start,
        end=end,
        iterations=args.iters,
        limit=args.limit,
        onlookers=args.onlookers,
        seed=args.seed,
        evaluate_path_fn=evaluate_path,
    )

    population = abc_result["population"]

    print_population_stats(population, parsed_data["attraction_types"])
    save_population_to_json(population, args.out)

    # pokaż najlepszą trasę wg metryki porównania
    best = max(
        population,
        key=lambda s: (s["total_value"], -s["total_time"], -s["movement_time"], -s["attraction_cost"]),
    )

    print("\n=== PRZYKŁADOWA (NAJLEPSZA) TRASA ===")
    print(f"Długość ścieżki: {len(best['path'])}")
    print(f"Czas ruchu: {best['movement_time']:.2f} min")
    print(f"Koszt atrakcji (ceny): {best['attraction_cost']}")
    print(f"Całkowity czas: {best['total_time']:.2f}")
    print(f"Wartość: {best['total_value']}")
    print(f"Liczba atrakcji: {len(best['used_attractions'])}")
    print(f"Liczności typów: {best['type_counts']}")
    print(f"Spełnia wszystko: {best['feasible']}")
    print(f"Bez powtórzeń krawędzi: {check_no_repeated_edges(best['path'])}")