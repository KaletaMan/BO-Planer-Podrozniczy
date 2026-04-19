def parse_map(weight, time_limit, budget, attractions, attraction_types):
    """
    Przekształca dane z JSON do struktur wygodnych dla algorytmu.

    Zwraca:
    - parsed_data (dict)
    """

    rows = len(weight)
    cols = len(weight[0])

    attraction_map = {}

    for a in attractions:
        r, c, value, cost, typ = a
        attraction_map[(r, c)] = {
            "value": value,
            "cost": cost,
            "type": typ
        }

    parsed_types = []

    for t in attraction_types:
        t_time, t_min, t_max = t
        parsed_types.append({
            "time": t_time,
            "min": t_min,
            "max": t_max
        })

    attraction_positions = list(attraction_map.keys())

    parsed_data = {
        "weight": weight,
        "rows": rows,
        "cols": cols,
        "time_limit": time_limit,
        "budget": budget,
        "attraction_map": attraction_map,
        "attraction_types": parsed_types,
        "attraction_positions": attraction_positions
    }

    return parsed_data