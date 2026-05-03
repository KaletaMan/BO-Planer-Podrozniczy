# Examples

## 1) Szybki run (mało iteracji)

```bash
python3 initial_population.py --population-size 20 --iters 50 --limit 30 --seed 1 --out initial_population.json
```

## 2) „Lepsze” wyniki (dłuższy run)

```bash
python3 initial_population.py --population-size 50 --iters 300 --limit 80 --seed 1 --out initial_population.json
```

## 3) Więcej eksploracji (więcej onlookerów)

```bash
python3 initial_population.py --population-size 50 --iters 200 --limit 60 --onlookers 150 --seed 1 --out initial_population.json
```

## 4) Walidacja wygenerowanego JSON

Sprawdza:

- czy wszystkie rozwiązania mają `feasible=true`
- czy żadna krawędź (nieskierowana) nie powtarza się w ścieżce

```bash
python3 examples/validate_population.py initial_population.json
```

## 5) Wizualizacja

Domyślnie wizualizator czyta `initial_population.json`:

```bash
python3 visualize_paths.py
```

Jeśli zapisujesz do innego pliku:

```bash
python3 -c "from visualize_paths import draw_paths; draw_paths(population_file='my_population.json')"
```
