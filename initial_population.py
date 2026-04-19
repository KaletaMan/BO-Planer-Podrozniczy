import json
import random
from statistics import mean

from load_json import load_map_from_json
from parser import parse_map


START = (0, 0)
END = (29, 29)


def weighted_choice(moves):
    total = sum(weight for _, weight in moves)
    x = random.uniform(0, total)
    cumulative = 0.0

    for move, weight in moves:
        cumulative += weight
        if x <= cumulative:
            return move

    return moves[-1][0]


def get_allowed_moves(r, c, rows, cols):
    candidate_moves = [
        ((1, 0), 30),   # dół
        ((0, 1), 30),   # prawo
        ((1, 1), 30),   # prawo-dół
        ((1, -1), 5),   # dół-lewo
        ((-1, 1), 5),   # prawo-góra
    ]

    allowed = []
    for (dr, dc), weight in candidate_moves:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            allowed.append(((dr, dc), weight))

    return allowed


def finish_greedily_to_goal(path, current, end):
    r, c = current
    end_r, end_c = end

    while (r, c) != (end_r, end_c):
        dr = 0
        dc = 0

        if r < end_r:
            dr = 1
        elif r > end_r:
            dr = -1

        if c < end_c:
            dc = 1
        elif c > end_c:
            dc = -1

        r += dr
        c += dc
        path.append((r, c))

    return path


def generate_single_path(rows, cols, start, end, max_steps=500):
    path = [start]
    r, c = start

    for _ in range(max_steps):
        if (r, c) == end:
            return path

        allowed_moves = get_allowed_moves(r, c, rows, cols)
        if not allowed_moves:
            break

        dr, dc = weighted_choice(allowed_moves)
        r += dr
        c += dc
        path.append((r, c))

        if (r, c) == end:
            return path

    return finish_greedily_to_goal(path, (r, c), end)


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
    weight = parsed_data["weight"]
    time_limit = parsed_data["time_limit"]
    budget = parsed_data["budget"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]

    unique_positions = set(path)

    visited_attractions = []
    used_attractions = []

    attraction_cost_sum = 0
    attraction_time_sum = 0
    total_value = 0

    type_counts = [0 for _ in range(len(attraction_types))]

    for pos in unique_positions:
        if pos in attraction_map:
            attr = attraction_map[pos]
            attr_type = attr["type"]

            visited_attractions.append(pos)
            used_attractions.append(pos)

            attraction_cost_sum += attr["cost"]
            attraction_time_sum += attraction_types[attr_type]["time"]
            total_value += attr["value"]
            type_counts[attr_type] += 1

    move_cost = movement_cost(path, weight)
    total_time = move_cost + attraction_time_sum

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
        "movement_cost": move_cost,
        "attraction_cost": attraction_cost_sum,
        "total_time": total_time,
        "total_value": total_value,
        "type_counts": type_counts,
        "budget_ok": budget_ok,
        "time_ok": time_ok,
        "type_ok": type_ok,
        "feasible": feasible,
    }


def generate_initial_population(parsed_data, population_size=50, start=START, end=END):
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]

    population = []

    for idx in range(population_size):
        path = generate_single_path(rows, cols, start, end)
        solution = evaluate_path(path, parsed_data)
        solution["id"] = idx
        population.append(solution)

    return population


def print_population_stats(population, attraction_types):
    feasible_count = sum(1 for sol in population if sol["feasible"])
    budget_ok_count = sum(1 for sol in population if sol["budget_ok"])
    time_ok_count = sum(1 for sol in population if sol["time_ok"])
    type_ok_count = sum(1 for sol in population if sol["type_ok"])

    avg_total_time = mean(sol["total_time"] for sol in population)
    avg_attraction_cost = mean(sol["attraction_cost"] for sol in population)
    avg_attraction_count = mean(len(sol["used_attractions"]) for sol in population)
    avg_movement_cost = mean(sol["movement_cost"] for sol in population)
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
    print(f"Średni koszt ruchu: {avg_movement_cost:.2f}")
    print(f"Średni użyty budżet: {avg_attraction_cost:.2f}")
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
            "movement_cost": sol["movement_cost"],
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
    weight, time_limit, budget, attractions, attraction_types = load_map_from_json("map.json")
    parsed_data = parse_map(weight, time_limit, budget, attractions, attraction_types)

    population = generate_initial_population(parsed_data, population_size=50)

    print_population_stats(population, parsed_data["attraction_types"])
    save_population_to_json(population, "initial_population.json")

    print("\n=== PRZYKŁADOWA PIERWSZA TRASA ===")
    first = population[0]
    print(f"Długość ścieżki: {len(first['path'])}")
    print(f"Koszt ruchu: {first['movement_cost']:.2f}")
    print(f"Koszt atrakcji: {first['attraction_cost']}")
    print(f"Całkowity czas: {first['total_time']:.2f}")
    print(f"Wartość: {first['total_value']}")
    print(f"Liczba atrakcji: {len(first['used_attractions'])}")
    print(f"Liczności typów: {first['type_counts']}")
    print(f"Spełnia wszystko: {first['feasible']}")