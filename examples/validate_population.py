import json
import sys


def _canon_undirected_edge(a, b):
    return (a, b) if a <= b else (b, a)


def check_no_repeated_edges(path):
    used = set()
    for i in range(len(path) - 1):
        e = _canon_undirected_edge(tuple(path[i]), tuple(path[i + 1]))
        if e in used:
            return False
        used.add(e)
    return True


def main(argv):
    if len(argv) != 2:
        print("usage: python3 examples/validate_population.py <population.json>")
        return 2

    fname = argv[1]
    with open(fname, "r", encoding="utf-8") as f:
        pop = json.load(f)

    if not isinstance(pop, list):
        print("ERROR: expected a JSON list")
        return 2

    bad_edges = []
    infeasible = []

    for sol in pop:
        sol_id = sol.get("id")
        path = sol.get("path")
        if not path:
            bad_edges.append(sol_id)
            continue

        if not check_no_repeated_edges(path):
            bad_edges.append(sol_id)

        if not sol.get("feasible", False):
            infeasible.append(sol_id)

    print(f"paths: {len(pop)}")
    print(f"bad_no_repeated_edges: {len(bad_edges)}")
    if bad_edges:
        print("  ids:", bad_edges[:20], "..." if len(bad_edges) > 20 else "")

    print(f"infeasible: {len(infeasible)}")
    if infeasible:
        print("  ids:", infeasible[:20], "..." if len(infeasible) > 20 else "")

    ok = (not bad_edges) and (not infeasible)
    print("OK" if ok else "NOT OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
