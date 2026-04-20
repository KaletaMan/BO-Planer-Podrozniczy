import json
import random


def generate_weight(rows, cols, min_val=7, max_val=12):
    """
    Generuje losową mapę wag.

    Parametry:
    - rows: liczba wierszy
    - cols: liczba kolumn
    - min_val: minimalna wartość wagi (domyślnie 7)
    - max_val: maksymalna wartość wagi (domyślnie 12)

    Zwraca:
    - lista list (rows x cols) z intami
    """

    if rows <= 0 or cols <= 0:
        raise ValueError("rows i cols muszą być > 0")

    if min_val > max_val:
        raise ValueError("min_val nie może być większe od max_val")

    weight = [
        [random.randint(min_val, max_val) for _ in range(cols)]
        for _ in range(rows)
    ]

    return weight


def add_attraction_type(
    attractions,
    attraction_types,
    rows,
    cols,
    time_needed,
    min_count,
    max_count,
    number_on_map,
    value_range,
    cost_range,
):
    """
    Dodaje nowy typ atrakcji oraz losowo rozmieszcza atrakcje tego typu na mapie.

    Parametry:
    - attractions: lista istniejących atrakcji w formacie
      [row, col, value, cost, type]
    - attraction_types: lista istniejących typów w formacie
      [time, min, max]
    - rows, cols: rozmiar mapy
    - time_needed: czas potrzebny na zaliczenie atrakcji tego typu
    - min_count: minimalna liczba atrakcji tego typu, które trzeba odwiedzić
    - max_count: maksymalna liczba atrakcji tego typu, które można odwiedzić
    - number_on_map: ile atrakcji tego typu wylosować na mapie
    - value_range: krotka (min_value, max_value)
    - cost_range: krotka (min_cost, max_cost)

    Zwraca:
    - (new_attractions, new_attraction_types)
    """

    if rows <= 0 or cols <= 0:
        raise ValueError("rows i cols muszą być > 0")

    if number_on_map < 0:
        raise ValueError("number_on_map nie może być ujemne")

    if min_count < 0 or max_count < 0:
        raise ValueError("min_count i max_count nie mogą być ujemne")

    if min_count > max_count:
        raise ValueError("min_count nie może być większe od max_count")

    min_value, max_value = value_range
    min_cost, max_cost = cost_range

    if min_value > max_value:
        raise ValueError("value_range ma zły przedział")

    if min_cost > max_cost:
        raise ValueError("cost_range ma zły przedział")

    occupied_positions = {(a[0], a[1]) for a in attractions}
    total_cells = rows * cols
    free_cells = total_cells - len(occupied_positions)

    if number_on_map > free_cells:
        raise ValueError(
            f"Nie ma dość wolnych pól. Wolnych: {free_cells}, "
            f"próbowano dodać: {number_on_map}"
        )

    new_attractions = [a[:] for a in attractions]
    new_attraction_types = [t[:] for t in attraction_types]

    new_type_id = len(new_attraction_types)
    new_attraction_types.append([time_needed, min_count, max_count])

    available_positions = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if (r, c) not in occupied_positions
    ]

    chosen_positions = random.sample(available_positions, number_on_map)

    for r, c in chosen_positions:
        value = random.randint(min_value, max_value)
        cost = random.randint(min_cost, max_cost)
        new_attractions.append([r, c, value, cost, new_type_id])

    return new_attractions, new_attraction_types


def save_map_to_json(
    weight,
    time_limit,
    budget,
    attractions,
    attraction_types,
    filename="map.json"
):
    """
    Zapisuje dane mapy do pliku JSON.

    Parametry:
    - weight: lista list intów (siatka)
    - time_limit: int
    - budget: int
    - attractions: lista [row, col, value, cost, type]
    - attraction_types: lista [time, min, max]
    - filename: nazwa pliku (domyślnie map.json)
    """

    if not weight or not isinstance(weight[0], list):
        raise ValueError("weight musi być listą list")

    for row in weight:
        if not all(isinstance(x, int) for x in row):
            raise ValueError("weight musi zawierać inty")

    for a in attractions:
        if len(a) != 5:
            raise ValueError("atrakcja musi mieć format [row, col, value, cost, type]")

    for t in attraction_types:
        if len(t) != 3:
            raise ValueError("typ atrakcji musi mieć format [time, min, max]")

    data = {
        "weight": weight,
        "time": time_limit,
        "budget": budget,
        "attractions": attractions,
        "attraction_types": attraction_types
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"Zapisano mapę do {filename}")


if __name__ == "__main__":
    rows = 30
    cols = 30

    time_limit = 800
    budget = 300

    weight = generate_weight(rows, cols, min_val=7, max_val=12)

    attractions = []
    attraction_types = []

    # Typ 0
    attractions, attraction_types = add_attraction_type(
        attractions=attractions,
        attraction_types=attraction_types,
        rows=rows,
        cols=cols,
        time_needed=20,
        min_count=0,
        max_count=10,
        number_on_map=15,
        value_range=(20, 70),
        cost_range=(10, 50),
    )

    # Typ 1
    attractions, attraction_types = add_attraction_type(
        attractions=attractions,
        attraction_types=attraction_types,
        rows=rows,
        cols=cols,
        time_needed=35,
        min_count=0,
        max_count=7,
        number_on_map=20,
        value_range=(10, 120),
        cost_range=(25, 120),
    )

    # Typ 2
    attractions, attraction_types = add_attraction_type(
        attractions=attractions,
        attraction_types=attraction_types,
        rows=rows,
        cols=cols,
        time_needed=8,
        min_count=0,
        max_count=20,
        number_on_map=30,
        value_range=(2, 25),
        cost_range=(2, 25),
    )

    save_map_to_json(
        weight=weight,
        time_limit=time_limit,
        budget=budget,
        attractions=attractions,
        attraction_types=attraction_types,
        filename="map.json",
    )

    print(f"Rozmiar mapy: {rows}x{cols}")
    print(f"Liczba atrakcji: {len(attractions)}")
    print(f"Liczba typów atrakcji: {len(attraction_types)}")