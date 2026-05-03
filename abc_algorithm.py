import heapq
import random


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


def _grid_min_weight(weight):
    return min(min(row) for row in weight)


def _optimistic_remaining_move_cost(cur, end, min_weight):
    dr = abs(end[0] - cur[0])
    dc = abs(end[1] - cur[1])
    diag = min(dr, dc)
    straight = abs(dr - dc)
    return min_weight * (1.4 * diag + 1.0 * straight)


def get_allowed_moves(r, c, rows, cols):
    candidate_moves = [
        ((-1, 0), 1),  # góra
        ((-1, 1), 1),  # góra-prawo
        ((0, 1), 1),  # prawo
        ((1, 1), 1),  # dół-prawo
        ((1, 0), 1),  # dół
        ((1, -1), 1),  # dół-lewo
        ((0, -1), 1),  # lewo
        ((-1, -1), 1),  # góra-lewo
    ]

    allowed = []
    for (dr, dc), weight in candidate_moves:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            allowed.append(((dr, dc), weight))

    return allowed


def _canon_undirected_edge(a, b):
    return (a, b) if a <= b else (b, a)


def check_no_repeated_edges(path):
    """Zwraca True jeśli żadna krawędź (nieskierowana) nie występuje 2 razy."""
    used = set()
    for i in range(len(path) - 1):
        e = _canon_undirected_edge(path[i], path[i + 1])
        if e in used:
            return False
        used.add(e)
    return True


def _a_star_path(rows, cols, weight, start, goal, blocked_cells, forbidden_edges, min_weight=None):
    """Najtańsza ścieżka wg kosztu ruchu (jak w movement_cost) w siatce 8-kierunkowej."""
    if start == goal:
        return [start]

    if min_weight is None:
        min_weight = _grid_min_weight(weight)

    open_heap = []
    g = {start: 0.0}
    parent = {start: None}

    h0 = _optimistic_remaining_move_cost(start, goal, min_weight)
    heapq.heappush(open_heap, (h0, 0.0, start))
    closed = set()

    while open_heap:
        _f, g_cur, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        if cur == goal:
            break
        closed.add(cur)

        r, c = cur
        allowed_moves = get_allowed_moves(r, c, rows, cols)
        for (dr, dc), _w in allowed_moves:
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)
            if nxt in blocked_cells:
                continue

            e = _canon_undirected_edge(cur, nxt)
            if e in forbidden_edges:
                continue

            direction_cost = 1.4 if (abs(dr) == 1 and abs(dc) == 1) else 1.0
            step_cost = weight[r][c] * direction_cost
            tentative = g_cur + step_cost

            if tentative < g.get(nxt, float("inf")):
                g[nxt] = tentative
                parent[nxt] = cur
                h = _optimistic_remaining_move_cost(nxt, goal, min_weight)
                heapq.heappush(open_heap, (tentative + h, tentative, nxt))

    if goal not in parent:
        return None

    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


def build_path_from_waypoints(parsed_data, waypoints, start=None, end=None):
    """Buduje ścieżkę po siatce łącząc waypointy, bez powtórzeń pól i krawędzi."""
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]
    weight = parsed_data["weight"]
    attraction_positions = set(parsed_data["attraction_positions"])

    start, end = _default_start_end(rows, cols, start, end)

    if not waypoints or waypoints[0] != start or waypoints[-1] != end:
        raise ValueError("waypoints muszą zaczynać się w start i kończyć w end")

    mid = waypoints[1:-1]
    if len(mid) != len(set(mid)):
        return None

    min_weight = _grid_min_weight(weight)
    visited_cells = {start}
    used_edges = set()
    full_path = [start]

    always_allowed = {start, end}

    for a, b in zip(waypoints, waypoints[1:]):
        allowed_attractions = always_allowed | {a, b}
        blocked_attractions = attraction_positions - allowed_attractions
        blocked_cells = blocked_attractions | (visited_cells - {a, b})

        segment = _a_star_path(
            rows,
            cols,
            weight,
            a,
            b,
            blocked_cells=blocked_cells,
            forbidden_edges=used_edges,
            min_weight=min_weight,
        )
        if segment is None:
            return None

        for i in range(len(segment) - 1):
            used_edges.add(_canon_undirected_edge(segment[i], segment[i + 1]))

        for pos in segment[1:]:
            if pos in visited_cells:
                return None
            visited_cells.add(pos)
            full_path.append(pos)

    if not check_no_repeated_edges(full_path):
        return None
    return full_path


def _solution_is_better(a, b):
    if b is None:
        return True
    ka = (a["total_value"], -a["total_time"], -a["movement_cost"], -a["attraction_cost"])
    kb = (b["total_value"], -b["total_time"], -b["movement_cost"], -b["attraction_cost"])
    return ka > kb


def _rank_weights(population):
    order = sorted(
        range(len(population)),
        key=lambda i: (
            population[i]["total_value"],
            -population[i]["total_time"],
            -population[i]["movement_cost"],
            -population[i]["attraction_cost"],
        ),
        reverse=True,
    )

    n = len(population)
    weights = [0] * n
    for rank, idx in enumerate(order):
        weights[idx] = n - rank
    return weights


def _extract_waypoints_from_solution(solution, start, end):
    attractions_in_order = list(solution["visited_attractions"])
    return [start] + attractions_in_order + [end]


def _try_build_solution_from_waypoints(parsed_data, waypoints, start, end, evaluate_path_fn):
    path = build_path_from_waypoints(parsed_data, waypoints, start=start, end=end)
    if path is None:
        return None

    sol = evaluate_path_fn(path, parsed_data)
    if not sol.get("feasible", False):
        return None
    if not check_no_repeated_edges(sol["path"]):
        return None

    sol["waypoints"] = waypoints
    sol["trial"] = 0
    return sol


def _score_attraction(parsed_data, pos):
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]
    a = attraction_map[pos]
    t = attraction_types[a["type"]]["time"]
    return (a["value"] + 1.0) / (t + 1.0)


def _random_waypoints(parsed_data, start, end, max_extra_total=8):
    attraction_map = parsed_data["attraction_map"]
    attraction_types = parsed_data["attraction_types"]
    attraction_positions = list(parsed_data["attraction_positions"])

    if not attraction_positions:
        return [start, end]

    t_count = len(attraction_types)
    base_counts = [0 for _ in range(t_count)]
    seen_base = set()
    for p in (start, end):
        if p in attraction_map and p not in seen_base:
            seen_base.add(p)
            base_counts[attraction_map[p]["type"]] += 1

    positions_by_type = {t_id: [] for t_id in range(t_count)}
    for pos in attraction_positions:
        if pos == start or pos == end:
            continue
        positions_by_type[attraction_map[pos]["type"]].append(pos)

    chosen = []
    chosen_set = set()
    counts = list(base_counts)

    # twardo realizuj minima
    for t_id, info in enumerate(attraction_types):
        needed = max(0, info["min"] - counts[t_id])
        if needed <= 0:
            continue

        candidates = [p for p in positions_by_type[t_id] if p not in chosen_set]
        if len(candidates) < needed:
            return None
        picked = random.sample(candidates, needed)
        for p in picked:
            chosen.append(p)
            chosen_set.add(p)
            counts[t_id] += 1

    # dodaj trochę ekstra (ale nie musisz)
    remaining = [p for p in attraction_positions if p not in chosen_set and p not in (start, end)]
    if remaining:
        extra_cap = min(max_extra_total, len(remaining))
        extra_target = random.randint(0, extra_cap)
        base_len = len(chosen)
        weights = [_score_attraction(parsed_data, p) for p in remaining]

        tries = 0
        max_tries = 2000
        while len(chosen) < base_len + extra_target and tries < max_tries:
            tries += 1
            p = random.choices(remaining, weights=weights, k=1)[0]
            if p in chosen_set:
                continue
            t_id = attraction_map[p]["type"]
            if counts[t_id] + 1 > attraction_types[t_id]["max"]:
                continue
            chosen.append(p)
            chosen_set.add(p)
            counts[t_id] += 1

    random.shuffle(chosen)
    return [start] + chosen + [end]


def _random_feasible_solution(parsed_data, start, end, evaluate_path_fn, max_tries=800):
    for _ in range(max_tries):
        waypoints = _random_waypoints(parsed_data, start, end)
        if waypoints is None:
            continue
        sol = _try_build_solution_from_waypoints(parsed_data, waypoints, start, end, evaluate_path_fn)
        if sol is not None:
            return sol
    return None


def _mutate_waypoints(parsed_data, solution, start, end, evaluate_path_fn, max_attempts=30):
    attraction_map = parsed_data["attraction_map"]
    attraction_positions = list(parsed_data["attraction_positions"])
    attraction_types = parsed_data["attraction_types"]

    cur_waypoints = solution["waypoints"]
    cur_attrs = list(cur_waypoints[1:-1])

    def attr_type(pos):
        return attraction_map[pos]["type"]

    for _ in range(max_attempts):
        attrs = list(cur_attrs)

        op = random.random()
        if op < 0.30:
            in_set = set(attrs)
            candidates = [p for p in attraction_positions if p not in in_set and p not in (start, end)]
            if not candidates:
                continue
            random.shuffle(candidates)

            def score(p):
                a = attraction_map[p]
                t = attraction_types[a["type"]]["time"]
                return (a["value"] + 1.0) / (t + 1.0)

            candidates.sort(key=score, reverse=True)
            cand_pool = candidates[: min(20, len(candidates))]
            p = random.choice(cand_pool)
            t_id = attr_type(p)
            if solution["type_counts"][t_id] + 1 > attraction_types[t_id]["max"]:
                continue
            insert_at = random.randint(0, len(attrs))
            attrs.insert(insert_at, p)

        elif op < 0.55:
            if not attrs:
                continue
            removable = []
            for i, p in enumerate(attrs):
                t_id = attr_type(p)
                if solution["type_counts"][t_id] - 1 >= attraction_types[t_id]["min"]:
                    removable.append(i)
            if not removable:
                continue
            idx = random.choice(removable)
            attrs.pop(idx)

        elif op < 0.75:
            if len(attrs) < 2:
                continue
            i, j = random.sample(range(len(attrs)), 2)
            attrs[i], attrs[j] = attrs[j], attrs[i]

        elif op < 0.95:
            if len(attrs) < 4:
                continue
            i, j = sorted(random.sample(range(len(attrs)), 2))
            if i == j:
                continue
            attrs[i : j + 1] = reversed(attrs[i : j + 1])

        else:
            if len(attrs) < 2:
                continue
            i = random.randrange(len(attrs))
            p = attrs.pop(i)
            j = random.randint(0, len(attrs))
            attrs.insert(j, p)

        waypoints = [start] + attrs + [end]
        cand = _try_build_solution_from_waypoints(parsed_data, waypoints, start, end, evaluate_path_fn)
        if cand is not None:
            return cand

    return None


def generate_abc_population(
    parsed_data,
    population_size=50,
    start=None,
    end=None,
    iterations=200,
    limit=60,
    onlookers=None,
    seed=None,
    deduplicate=True,
    *,
    evaluate_path_fn,
):
    """Generuje populację rozwiązań metodą ABC.

    Wymaga przekazania:
    - evaluate_path_fn(path, parsed_data) -> dict
    """
    rows = parsed_data["rows"]
    cols = parsed_data["cols"]
    start, end = _default_start_end(rows, cols, start, end)

    if seed is not None:
        random.seed(seed)

    if onlookers is None:
        onlookers = population_size

    population = []
    seen = set()
    attempts = 0
    max_attempts = max(10_000, population_size * 800)

    while len(population) < population_size and attempts < max_attempts:
        attempts += 1
        sol = _random_feasible_solution(parsed_data, start, end, evaluate_path_fn)
        if sol is None:
            continue

        if deduplicate:
            key = tuple(sol["path"])
            if key in seen:
                continue
            seen.add(key)

        sol["id"] = len(population)
        population.append(sol)

    if len(population) < population_size:
        raise RuntimeError(
            "ABC: nie udało się zainicjalizować populacji dopuszczalnych rozwiązań. "
            "Rozważ poluzowanie ograniczeń albo zmniejszenie population_size."
        )

    for _it in range(iterations):
        for i in range(population_size):
            cand = _mutate_waypoints(parsed_data, population[i], start, end, evaluate_path_fn)
            if cand is not None and _solution_is_better(cand, population[i]):
                cand["id"] = population[i]["id"]
                population[i] = cand
            else:
                population[i]["trial"] = population[i].get("trial", 0) + 1

        weights = _rank_weights(population)
        indices = list(range(population_size))
        for _k in range(onlookers):
            i = random.choices(indices, weights=weights, k=1)[0]
            cand = _mutate_waypoints(parsed_data, population[i], start, end, evaluate_path_fn)
            if cand is not None and _solution_is_better(cand, population[i]):
                cand["id"] = population[i]["id"]
                population[i] = cand
            else:
                population[i]["trial"] = population[i].get("trial", 0) + 1

        for i in range(population_size):
            if population[i].get("trial", 0) < limit:
                continue
            repl = _random_feasible_solution(parsed_data, start, end, evaluate_path_fn)
            if repl is None:
                population[i]["trial"] = 0
                continue
            repl["id"] = population[i]["id"]
            population[i] = repl

    for i, sol in enumerate(population):
        sol["id"] = sol.get("id", i)
    return population
