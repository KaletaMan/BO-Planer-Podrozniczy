from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.map_generator import DEFAULT_TYPES, generate_map
from src.path_solver import evaluate_path, solve_greedy_attractions, solve_random_walk
from src.ui_io import ValidationIssue, list_maps, load_map, save_map, validate_map
from src.ui_viz import plot_convergence, plot_map, plot_path_on_map, plot_paths_comparison

st.set_page_config(page_title="Trasy turystyczne — BO", layout="wide")

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
RESULTS_DIR = Path(__file__).parent / "results"


# ── Session state init ────────────────────────────────────────────────────────

def _default_map() -> dict:
    return generate_map(
        width=10, height=10,
        n_attractions=4, value_min=3, value_max=10,
        weight_distribution="uniform", weight_min=1, weight_max=5,
        start=(0, 0), end=(9, 9),
        budget=50, seed=42,
        name="Nowa mapa",
        attraction_types=DEFAULT_TYPES,
    )


if "map_data" not in st.session_state:
    st.session_state.map_data = _default_map()
if "last_path" not in st.session_state:
    st.session_state.last_path = None
if "last_eval" not in st.session_state:
    st.session_state.last_eval = None
if "dirty" not in st.session_state:
    st.session_state.dirty = False


# ── Sidebar mode selector ─────────────────────────────────────────────────────

mode = st.sidebar.radio("Tryb", ["Edytor / Generator", "Wyniki"], label_visibility="collapsed")

st.title("Trasy turystyczne — optymalizacja trasą")


# ══════════════════════════════════════════════════════════════════════════════
# MODE: Edytor / Generator
# ══════════════════════════════════════════════════════════════════════════════

if mode == "Edytor / Generator":
    col_left, col_right = st.columns([1, 1.6])

    # ── Left column: parameters + editor ─────────────────────────────────────
    with col_left:
        st.subheader("Generuj mapę")

        with st.form("gen_form"):
            c1, c2 = st.columns(2)
            width  = c1.slider("Szerokość (W)", 5, 30, 10)
            height = c2.slider("Wysokość (H)",  5, 30, 10)

            c3, c4 = st.columns(2)
            n_attr    = c3.slider("Liczba atrakcji", 1, min(20, width * height // 4 or 1), 4)
            seed      = c4.number_input("Seed", value=42, step=1)

            c5, c6 = st.columns(2)
            val_min = c5.number_input("Wartość min atrakcji", value=3, min_value=1, step=1)
            val_max = c6.number_input("Wartość max atrakcji", value=10, min_value=1, step=1)

            types_raw = st.text_input(
                "Typy atrakcji (przecinki)",
                value=", ".join(st.session_state.map_data.get("attraction_types", DEFAULT_TYPES)),
                help="Np. zabytek, przyroda, restauracja — min. 1 typ",
            )

            dist = st.radio("Rozkład wag", ["uniform", "clusters"], horizontal=True)

            c7, c8 = st.columns(2)
            w_min = c7.number_input("Waga min", value=1, min_value=1, step=1)
            w_max = c8.number_input("Waga max", value=5, min_value=1, step=1)

            st.markdown("**Start / End**")
            c9, c10, c11, c12 = st.columns(4)
            sx = c9.number_input("Start x",  value=0, min_value=0, max_value=width - 1,  step=1)
            sy = c10.number_input("Start y", value=0, min_value=0, max_value=height - 1, step=1)
            ex = c11.number_input("End x",   value=width - 1,  min_value=0, max_value=width - 1,  step=1)
            ey = c12.number_input("End y",   value=height - 1, min_value=0, max_value=height - 1, step=1)

            budget = st.slider("Budżet (maks. łączny koszt)", 10, width * height * 10, 50)

            gen_btn = st.form_submit_button("Wygeneruj", type="primary")

        if gen_btn:
            parsed_types = [t.strip() for t in types_raw.split(",") if t.strip()] or DEFAULT_TYPES
            st.session_state.map_data = generate_map(
                width=int(width), height=int(height),
                n_attractions=int(n_attr),
                value_min=int(val_min), value_max=int(val_max),
                weight_distribution=dist,
                weight_min=int(w_min), weight_max=int(w_max),
                start=(int(sx), int(sy)), end=(int(ex), int(ey)),
                budget=int(budget), seed=int(seed),
                name=st.session_state.map_data.get("name", "Nowa mapa"),
                attraction_types=parsed_types,
            )
            st.session_state.last_path = None
            st.session_state.last_eval = None
            st.session_state.dirty = True
            st.rerun()

        # ── Manual edits ──────────────────────────────────────────────────────
        st.subheader("Edycja")
        inst = st.session_state.map_data

        new_name = st.text_input("Nazwa mapy", value=inst.get("name", ""))
        new_budget = st.number_input("Budżet", value=int(inst.get("budget", 50)), min_value=1, step=1)

        current_types = inst.get("attraction_types", DEFAULT_TYPES) or DEFAULT_TYPES
        st.markdown("**Atrakcje** (id, x, y, wartość, typ)")
        raw_attrs = inst.get("attractions", [])
        attr_df = pd.DataFrame(raw_attrs) if raw_attrs else pd.DataFrame(columns=["id", "x", "y", "value", "type"])
        for col in ["id", "x", "y", "value", "type"]:
            if col not in attr_df.columns:
                attr_df[col] = None
        attr_df = attr_df[["id", "x", "y", "value", "type"]]
        attr_df["type"] = attr_df["type"].fillna(current_types[0])

        edited_attr = st.data_editor(
            attr_df,
            num_rows="dynamic",
            key="attractions_editor",
            column_config={
                "id":    st.column_config.TextColumn("ID"),
                "x":     st.column_config.NumberColumn("x", min_value=0, max_value=inst.get("width", 30) - 1, step=1),
                "y":     st.column_config.NumberColumn("y", min_value=0, max_value=inst.get("height", 30) - 1, step=1),
                "value": st.column_config.NumberColumn("Wartość", min_value=0, step=1),
                "type":  st.column_config.SelectboxColumn("Typ", options=current_types, required=True),
            },
            use_container_width=True,
        )

        st.info("Wagi komórek można edytować bezpośrednio w pliku JSON (upload poniżej).", icon="ℹ️")

        new_attrs = [
            {
                "id":    str(r["id"]) if r.get("id") is not None else f"a{i}",
                "x":     int(r["x"])     if r.get("x")     is not None else 0,
                "y":     int(r["y"])     if r.get("y")     is not None else 0,
                "value": int(r["value"]) if r.get("value") is not None else 1,
                "type":  str(r["type"])  if r.get("type")  is not None and str(r.get("type", "")).strip() not in ("", "nan", "None") else current_types[0],
            }
            for i, r in enumerate(edited_attr.to_dict("records"))
            if r.get("id") is not None and str(r.get("id", "")).strip() not in ("", "nan", "None")
        ]

        updated = {
            **inst,
            "name": new_name,
            "budget": int(new_budget),
            "attractions": new_attrs,
            "attraction_types": current_types,
        }
        if updated != st.session_state.map_data:
            st.session_state.map_data = updated
            st.session_state.dirty = True

        # ── Validation ────────────────────────────────────────────────────────
        issues = validate_map(st.session_state.map_data)
        if issues:
            with st.expander("Walidacja", expanded=any(i.level == "error" for i in issues)):
                for issue in issues:
                    if issue.level == "error":
                        st.error(issue.message)
                    else:
                        st.warning(issue.message)
        else:
            st.success("Dane poprawne.", icon="✅")

        # ── Save / Load ───────────────────────────────────────────────────────
        st.subheader("Zapisz / Wczytaj")
        save_name = st.text_input("Nazwa pliku (bez .json)", value="mapa")
        if st.button("Zapisz", disabled=bool(not save_name.strip())):
            p = SCENARIOS_DIR / f"{save_name.strip()}.json"
            save_map(p, st.session_state.map_data)
            st.success(f"Zapisano: {p.name}")
            st.session_state.dirty = False

        maps = list_maps()
        if maps:
            chosen = st.selectbox("Wczytaj scenariusz", ["— wybierz —"] + [m.name for m in maps])
            if st.button("Wczytaj") and chosen != "— wybierz —":
                p = SCENARIOS_DIR / chosen
                st.session_state.map_data = load_map(p)
                st.session_state.last_path = None
                st.session_state.last_eval = None
                st.session_state.dirty = False
                st.rerun()

        uploaded = st.file_uploader("Upload JSON", type="json")
        if uploaded:
            try:
                data = json.loads(uploaded.read())
                st.session_state.map_data = data
                st.session_state.dirty = True
                st.rerun()
            except Exception as exc:
                st.error(f"Błąd parsowania JSON: {exc}")

    # ── Right column: map preview + algorithm ─────────────────────────────────
    with col_right:
        st.subheader("Podgląd mapy")

        map_title = st.session_state.map_data.get("name", "Mapa")
        if st.session_state.last_path:
            fig = plot_path_on_map(
                st.session_state.map_data,
                st.session_state.last_path,
                title=map_title,
            )
        else:
            fig = plot_map(st.session_state.map_data, title=map_title)
        st.pyplot(fig)
        plt = __import__("matplotlib.pyplot", fromlist=["pyplot"])
        plt.close(fig)

        # ── Algorithm stub ────────────────────────────────────────────────────
        st.subheader("Uruchom algorytm (stub)")
        st.caption(
            "To stub — prawdziwy GA/Bee podłączymy gdy będzie gotowy. "
            "Interfejs `solve(map, params) → path` + `evaluate_path(map, path)` jest stabilny."
        )

        algo = st.radio("Algorytm", ["Greedy (zachłanny)", "Random walk"], horizontal=True)
        run_btn = st.button("Uruchom ▶", type="primary")

        if run_btn:
            errors = [i for i in validate_map(st.session_state.map_data) if i.level == "error"]
            if errors:
                st.error("Napraw błędy walidacji przed uruchomieniem algorytmu.")
            else:
                if algo.startswith("Greedy"):
                    path = solve_greedy_attractions(st.session_state.map_data)
                else:
                    path = solve_random_walk(
                        st.session_state.map_data,
                        seed=int(st.session_state.map_data.get("seed", 0)),
                    )
                ev = evaluate_path(st.session_state.map_data, path)
                st.session_state.last_path = path
                st.session_state.last_eval = ev
                st.rerun()

        if st.session_state.last_eval:
            ev = st.session_state.last_eval
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Koszt", ev["cost"])
            c2.metric("Budżet", st.session_state.map_data.get("budget"))
            c3.metric("Wartość", ev["value_collected"])
            c4.metric("Atrakcje", len(ev["attractions_visited"]))
            if ev["feasible"]:
                st.success("Ścieżka mieści się w budżecie.")
            else:
                st.warning(f"Przekroczono budżet: {ev['reason']}")

            if st.button("Wyczyść ścieżkę"):
                st.session_state.last_path = None
                st.session_state.last_eval = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MODE: Wyniki
# ══════════════════════════════════════════════════════════════════════════════

else:
    st.subheader("Wczytaj wyniki")
    st.caption(
        "Format: `results/*.json` z polami `map_file` (ścieżka do scenarios/…) i `runs[]` "
        "(algo, path, history, fitness)."
    )

    results_files = sorted(RESULTS_DIR.glob("*.json")) if RESULTS_DIR.exists() else []
    uploaded_res = st.file_uploader("Upload wyników JSON", type="json", key="res_upload")

    res_data = None
    if uploaded_res:
        try:
            res_data = json.loads(uploaded_res.read())
        except Exception as exc:
            st.error(f"Błąd parsowania: {exc}")
    elif results_files:
        chosen = st.selectbox("Lub wybierz plik", ["— wybierz —"] + [f.name for f in results_files])
        if chosen != "— wybierz —":
            res_data = json.loads((RESULTS_DIR / chosen).read_text(encoding="utf-8"))

    if res_data is None:
        st.info("Wczytaj plik wyników aby zobaczyć wizualizację.")
        st.stop()

    # Load map referenced in results
    map_file = res_data.get("map_file", "")
    map_data = None
    if map_file:
        p = Path(map_file)
        if not p.is_absolute():
            p = Path(__file__).parent / p
        if p.exists():
            map_data = load_map(p)
        else:
            st.warning(f"Plik mapy '{map_file}' nie znaleziony. Ścieżki rysowane bez tła.")

    if map_data is None:
        map_data = {"width": 10, "height": 10, "weights": [[1]*10 for _ in range(10)],
                    "attractions": [], "start": {"x": 0, "y": 0}, "end": {"x": 9, "y": 9}, "budget": 100}

    runs = res_data.get("runs", [])
    if not runs:
        st.warning("Brak danych w 'runs'.")
        st.stop()

    paths = {r["algo"]: [tuple(p) for p in r["path"]] for r in runs if "path" in r}
    histories = {r["algo"]: r["history"] for r in runs if "history" in r}

    tab_map, tab_conv, tab_table = st.tabs(["Mapa ze ścieżkami", "Konwergencja", "Tabela"])

    with tab_map:
        if paths:
            fig = plot_paths_comparison(map_data, paths, title="Porównanie ścieżek")
            st.pyplot(fig)
            import matplotlib.pyplot as _plt
            _plt.close(fig)
        else:
            st.info("Brak ścieżek w danych.")

    with tab_conv:
        if histories:
            fig = plot_convergence(histories)
            st.pyplot(fig)
            import matplotlib.pyplot as _plt
            _plt.close(fig)
        else:
            st.info("Brak historii fitness w danych.")

    with tab_table:
        rows = []
        for r in runs:
            path = [tuple(p) for p in r.get("path", [])]
            ev = evaluate_path(map_data, path) if path else {}
            rows.append({
                "Algorytm": r.get("algo", "?"),
                "Fitness": r.get("fitness", "—"),
                "Koszt": ev.get("cost", "—"),
                "Wartość": ev.get("value_collected", "—"),
                "Atrakcje": len(ev.get("attractions_visited", [])),
                "Długość ścieżki": len(path),
                "Feasible": ev.get("feasible", "—"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
