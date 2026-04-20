import json
import random
from statistics import mean
from collections import deque

from load_json import load_map_from_json
from parser import parse_map


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
    # Wagi jednakowe: generator nie powinien faworyzować konkretnych ruchów.
    candidate_moves = [
        ((-1, 0), 1),  # góra
        ((-1, 1), 1),  # góra-prawo
        ((0, 1), 1),   # prawo
        ((1, 1), 1),   # dół-prawo
        ((1, 0), 1),   # dół
        ((1, -1), 1),  # dół-lewo
        ((0, -1), 1),  # lewo
        ((-1, -1), 1), # góra-lewo
    ]

    allowed = []
    for (dr, dc), weight in candidate_moves:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            allowed.append(((dr, dc), weight))

    return allowed


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


def _direct_simple_path(start, end):
    """Deterministyczna prosta ścieżka.

    Zawsze działa na pustej siatce (bez przeszkód), bo każdy krok przybliża do celu.
    """
    r, c = start
    end_r, end_c = end
    path = [(r, c)]

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


def _bfs_path(rows, cols, start, goal, blocked):
    """Najkrótsza ścieżka w siatce (8-kierunków) z blokadami."""
    if start == goal:
        return [start]

    q = deque([start])
    parent = {start: None}

    while q:
        cur = q.popleft()
        if cur == goal:
            break

        r, c = cur
        # Losowa kolejność sąsiadów => różne (ale nadal najkrótsze) ścieżki.
        allowed_moves = get_allowed_moves(r, c, rows, cols)
        random.shuffle(allowed_moves)
        for (dr, dc), _w in allowed_moves:
            nxt = (r + dr, c + dc)
            if nxt in parent:
                continue
            if nxt in blocked:
                continue
            parent[nxt] = cur
            q.append(nxt)

    if goal not in parent:
        return None

    # rekonstrukcja
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


def _grid_min_weight(weight):
    return min(min(row) for row in weight)


def _optimistic_remaining_move_cost(cur, end, min_weight):
    """Dolne oszacowanie kosztu dojścia do celu (ignoruje atrakcje i wagi pól po drodze).

    Używa odległości Chebysheva: maksymalna liczba kroków po skosie + proste.
    """
    dr = abs(end[0] - cur[0])
    dc = abs(end[1] - cur[1])
    diag = min(dr, dc)
    straight = abs(dr - dc)
    return min_weight * (1.4 * diag + 1.0 * straight)


def _chebyshev_steps(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _weighted_sample_unique(items, weights, k):
    """Losuje do k unikalnych elementów z wagami."""
    if k <= 0:
        return []

    if len(items) != len(weights):
        raise ValueError("items i weights muszą mieć ten sam rozmiar")

    chosen = []
    chosen_set = set()
    tries = 0
    max_tries = 2000
    while len(chosen) < min(k, len(items)) and tries < max_tries:
        tries += 1
        cand = random.choices(items, weights=weights, k=1)[0]
        if cand in chosen_set:
            continue
        chosen_set.add(cand)
        chosen.append(cand)
    return chosen


def generate_attraction_targeted_path(
    parsed_data,
    start,
    end,
    max_tries=300,
    targets_range=(1, 3),
    corridor_factor=1.7,
):
    """Generuje krótką trasę, która celowo zahacza o 1–3 atrakcje..
    """
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]

    if not attraction_map:
        return None

    # Filtr „korytarza”: atrakcje, które nie robią gigantycznego objazdu w krokach.
    min_steps = _chebyshev_steps(start, end)
    max_steps_via = int(min_steps * corridor_factor)

    candidates = []
    cand_weights = []
    for pos, attr in attraction_map.items():
        if pos in (start, end):
            continue
        steps_via = _chebyshev_steps(start, pos) + _chebyshev_steps(pos, end)
        if steps_via > max_steps_via:
            continue

        t_id = attr["type"]
        # prosta heurystyka: wartość / (czas typu + 1)
        w = (attr["value"] + 1.0) / (attraction_types[t_id]["time"] + 1.0)
        candidates.append(pos)
        cand_weights.append(w)

    if not candidates:
        return None

    for _ in range(max_tries):
        k = random.randint(targets_range[0], targets_range[1])
        targets = _weighted_sample_unique(candidates, cand_weights, k)
        if not targets:
            continue
        random.shuffle(targets)

        visited = {start}
        path = [start]
        current = start

        ok = True
        for target in targets:
            blocked = visited - {current}
            segment = _bfs_path(rows, cols, current, target, blocked)
            if segment is None:
                ok = False
                break
            for pos in segment[1:]:
                visited.add(pos)
                path.append(pos)
            current = target

        if not ok:
            continue

        blocked = visited - {current, end}
        segment = _bfs_path(rows, cols, current, end, blocked)
        if segment is None:
            continue
        for pos in segment[1:]:
            path.append(pos)

        return path

    return None


def generate_time_bounded_path(
    parsed_data,
    start,
    end,
    max_restarts=800,
    max_steps_factor=2.2,
):
    """Generuje krótką, losową ścieżkę z cięciem wg limitu czasu.
    """
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]
    weight = parsed_data["weight"]
    time_limit = parsed_data["time_limit"]
    budget = parsed_data["budget"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]

    min_weight = _grid_min_weight(weight)

    dr = abs(end[0] - start[0])
    dc = abs(end[1] - start[1])
    min_steps = min(dr, dc) + abs(dr - dc)
    max_steps = max(1, int(min_steps * max_steps_factor))

    for _ in range(max_restarts):
        path = [start]
        visited = {start}
        used_edges = set()
        visited_attractions = set()
        type_counts = [0 for _ in range(len(attraction_types))]

        attraction_cost_sum = 0
        attraction_time_sum = 0
        move_cost_sum = 0.0

        r, c = start

        for _step in range(max_steps):
            if (r, c) == end:
                return path

            allowed_moves = get_allowed_moves(r, c, rows, cols)
            random.shuffle(allowed_moves)

            candidates = []
            candidate_weights = []

            for (dr_m, dc_m), base_w in allowed_moves:
                nr, nc = r + dr_m, c + dc_m
                nxt = (nr, nc)

                if nxt in visited:
                    continue

                edge = ((r, c), nxt)
                if edge in used_edges:
                    continue

                # koszt kroku
                direction_cost = 1.4 if (abs(dr_m) == 1 and abs(dc_m) == 1) else 1.0
                step_move_cost = weight[r][c] * direction_cost

                # przybliżenie wpływu atrakcji (tylko jeśli pierwszy raz)
                add_cost = 0
                add_time = 0
                if nxt in attraction_map and nxt not in visited_attractions:
                    attr = attraction_map[nxt]
                    t_id = attr["type"]
                    # max-y typów
                    if type_counts[t_id] + 1 > attraction_types[t_id]["max"]:
                        continue
                    add_cost = attr["cost"]
                    add_time = attraction_types[t_id]["time"]

                # budżet
                if attraction_cost_sum + add_cost > budget:
                    continue

                # limit czasu z optymistycznym domknięciem
                optimistic = _optimistic_remaining_move_cost(nxt, end, min_weight)
                next_total_time_lb = (
                    move_cost_sum + step_move_cost + attraction_time_sum + add_time + optimistic
                )
                if next_total_time_lb > time_limit:
                    continue

                # preferuj ruchy zbliżające do celu, ale zostaw losowość
                dist = abs(end[0] - nr) + abs(end[1] - nc)
                w = base_w * (1.0 / (dist + 1.0))
                candidates.append((dr_m, dc_m, step_move_cost, add_cost, add_time, nxt))
                candidate_weights.append(w)

            if not candidates:
                break

            dr_m, dc_m, step_move_cost, add_cost, add_time, nxt = random.choices(
                candidates, weights=candidate_weights, k=1
            )[0]

            used_edges.add(((r, c), nxt))
            visited.add(nxt)
            path.append(nxt)

            move_cost_sum += step_move_cost
            if nxt in attraction_map and nxt not in visited_attractions:
                visited_attractions.add(nxt)
                t_id = attraction_map[nxt]["type"]
                type_counts[t_id] += 1
                attraction_cost_sum += add_cost
                attraction_time_sum += add_time

            r, c = nxt

        # restart

    return None


def generate_feasible_path(parsed_data, start, end, max_tries=200):
    """Generuje ścieżkę, która ma duże szanse być wykonalna wg ograniczeń typów.

    Strategia:
    - omijaj wszystkie atrakcje jako "przeszkody"
    - odblokuj i odwiedź tylko tyle atrakcji każdego typu, ile wynosi wymagane minimum
    Dzięki temu nie przekraczamy limitów max przez przypadkowe "zbieranie" atrakcji.
    """
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]
    attraction_positions = set(parsed_data["attraction_positions"])

    # start/end mogą być atrakcjami – traktujemy je jako dozwolone pola.
    always_allowed = {start, end}

    # grupowanie atrakcji wg typu
    positions_by_type = {t_id: [] for t_id in range(len(attraction_types))}
    for pos in attraction_positions:
        t_id = attraction_map[pos]["type"]
        positions_by_type[t_id].append(pos)

    for _ in range(max_tries):
        visited = {start}
        path = [start]
        current = start

        remaining = []
        for t_id, info in enumerate(attraction_types):
            needed = info["min"]
            for p in (start, end):
                if p in attraction_map and attraction_map[p]["type"] == t_id:
                    needed = max(0, needed - 1)
            if needed > 0:
                remaining.append((t_id, needed))

        random.shuffle(remaining)

        ok = True

        for t_id, needed in remaining:
            candidates = [p for p in positions_by_type[t_id] if p not in visited and p not in always_allowed]
            if len(candidates) < needed:
                ok = False
                break

            chosen = random.sample(candidates, needed)

            for target in chosen:
                blocked = (attraction_positions - {target}) - always_allowed
                blocked |= visited

                segment = _bfs_path(rows, cols, current, target, blocked)
                if segment is None:
                    ok = False
                    break

                for pos in segment[1:]:
                    visited.add(pos)
                    path.append(pos)
                current = target

            if not ok:
                break

        if not ok:
            continue

        blocked = attraction_positions - always_allowed
        blocked |= visited - {end}
        segment = _bfs_path(rows, cols, current, end, blocked)
        if segment is None:
            continue

        for pos in segment[1:]:
            path.append(pos)

        return path

    return None


def generate_single_path(
    rows,
    cols,
    start,
    end,
    max_steps=None,
    max_restarts=200,
):
    """Generuje ścieżkę bez powtórzeń pól i przejść.

    - brak powtórzeń wierzchołków => atrakcja nie może zostać "odwiedzona" ponownie
    - brak powtórzeń przejść (krawędzi) jest spełniony automatycznie
    """
    if max_steps is None:
        # górny limit długości prostej ścieżki w siatce
        max_steps = rows * cols

    for _ in range(max_restarts):
        path = [start]
        visited = {start}
        used_edges = set()
        r, c = start

        for _step in range(max_steps):
            if (r, c) == end:
                return path

            allowed_moves = get_allowed_moves(r, c, rows, cols)

            candidates = []
            candidate_weights = []

            for (dr, dc), base_w in allowed_moves:
                nr, nc = r + dr, c + dc
                nxt = (nr, nc)

                if nxt in visited:
                    continue

                edge = ((r, c), nxt)
                if edge in used_edges:
                    continue


                dist = abs(end[0] - nr) + abs(end[1] - nc)
                w = base_w * (1.0 / (dist + 1.0))

                candidates.append((dr, dc))
                candidate_weights.append(w)

            if not candidates:
                break

            dr, dc = random.choices(candidates, weights=candidate_weights, k=1)[0]
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)

            used_edges.add(((r, c), nxt))
            visited.add(nxt)
            path.append(nxt)
            r, c = nr, nc

        # nie udało się dojść do celu w tej próbie => restart

    # Fallback: zawsze poprawna, prosta ścieżka bez powtórzeń
    return _direct_simple_path(start, end)


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


def generate_initial_population(
    parsed_data,
    population_size=50,
    start=None,
    end=None,
    min_feasible_ratio=1,
    deduplicate=True,
):
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]

    start, end = _default_start_end(rows, cols, start, end)

    population = []
    buffer_infeasible = []
    seen_paths = set()

    if not (0.0 <= min_feasible_ratio <= 1.0):
        raise ValueError("min_feasible_ratio musi być w [0, 1]")

    target_feasible = int(population_size * min_feasible_ratio + 0.999999)

    has_type_mins = any(t_info["min"] > 0 for t_info in parsed_data["attraction_types"])

    feasible_count = 0
    attempts = 0
    max_attempts = max(10_000, population_size * 500)

    while len(population) < population_size and attempts < max_attempts:
        attempts += 1

        if feasible_count < target_feasible:
            path = None
            if not has_type_mins:
                # Najpierw spróbuj „wartościowych” tras zahaczających o atrakcje.
                # Potem fallback do krótkich tras dociętych limitem czasu.
                if random.random() < 0.75:
                    path = generate_attraction_targeted_path(parsed_data, start, end)
                if path is None:
                    path = generate_time_bounded_path(parsed_data, start, end)
            if path is None:
                path = generate_feasible_path(parsed_data, start, end)
            if path is None:
                path = generate_single_path(rows, cols, start, end)
        else:
            path = generate_single_path(rows, cols, start, end)

        if deduplicate:
            key = tuple(path)
            if key in seen_paths:
                continue
            seen_paths.add(key)

        solution = evaluate_path(path, parsed_data)

        if solution["feasible"]:
            feasible_count += 1
            solution["id"] = len(population)
            population.append(solution)
            continue


        buffer_infeasible.append(solution)

        if feasible_count >= target_feasible:

            solution = buffer_infeasible.pop()
            solution["id"] = len(population)
            population.append(solution)

    if feasible_count < target_feasible:
        raise RuntimeError(
            "Nie udało się zbudować populacji startowej z min. "
            f"{min_feasible_ratio:.0%} wykonalnych rozwiązań. "
            f"Uzyskano {feasible_count}/{population_size} po {attempts} próbach. "
            "Rozważ poluzowanie ograniczeń (czas/budżet/min-max typów) "
            "albo zmianę generowania ścieżek." 
        )

    # Jeżeli skończyły się próby wcześniej niż wypełniliśmy populację, dopełnij buforem.
    while len(population) < population_size and buffer_infeasible:
        sol = buffer_infeasible.pop()
        sol["id"] = len(population)
        population.append(sol)

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