"""Smart Visit Route Planner - Streamlit web app.

Run:  streamlit run app.py
"""
from datetime import date, time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import ui
from planner import BRANCH_OFFICE, REQUIRED_COLUMNS
from planner.distance import build_matrix, route_geometry
from planner.optimizer import HAS_ORTOOLS, PlanningError, PlanSettings, plan_route
from planner.priority import DEFAULT_WEIGHTS, HIGH_THRESHOLD, MEDIUM_THRESHOLD, score_dealers
from planner.report import (
    SKIPPED_COLOUR,
    TIER_COLOURS,
    build_map,
    build_schedule,
    compute_kpis,
    not_visited,
    summary_table,
    to_excel,
)

SAMPLE_CSV = Path(__file__).resolve().parent / "data" / "dealers.csv"
MAP_HEIGHT = 600

st.set_page_config(page_title="Smart Visit Route Planner", page_icon="🗺️", layout="wide")
ui.inject_css()


# ----------------------------------------------------------------------------- cached helpers
@st.cache_data(show_spinner=False)
def load_sample() -> pd.DataFrame:
    if not SAMPLE_CSV.exists():
        from data.generate_dealers import generate

        generate().to_csv(SAMPLE_CSV, index=False)
    return pd.read_csv(SAMPLE_CSV)


@st.cache_data(show_spinner="Fetching road distances...")
def get_matrix(points: tuple, use_osrm: bool, traffic_factor: float):
    return build_matrix(list(points), use_osrm=use_osrm, traffic_factor=traffic_factor)


@st.cache_data(show_spinner=False)
def get_geometry(points: tuple, use_osrm: bool):
    return route_geometry(list(points), use_osrm=use_osrm)


@st.cache_data(show_spinner="Optimising route...")
def get_plan(km, minutes, priority: tuple, must: tuple, settings: PlanSettings, use_ortools: bool):
    return plan_route(km, minutes, list(priority), set(must), settings, use_ortools=use_ortools)


def validate(df: pd.DataFrame) -> list[str]:
    problems = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return [f"Missing columns: {', '.join(missing)}"]
    numeric = REQUIRED_COLUMNS[3:]
    bad = [c for c in numeric if not pd.api.types.is_numeric_dtype(df[c])]
    if bad:
        problems.append(f"Non-numeric values in: {', '.join(bad)}")
    if df["dealer_id"].duplicated().any():
        problems.append("dealer_id values must be unique")
    if df[["latitude", "longitude"]].isna().any().any():
        problems.append("Every dealer needs latitude and longitude")
    if len(df) < 2:
        problems.append("Need at least 2 dealers")
    return problems


def short_source(source: str) -> str:
    return "OSRM road network" if source.startswith("OSRM") else "Offline estimate"


# ----------------------------------------------------------------------------- sidebar
with st.sidebar:
    ui.sidebar_brand()

    ui.side_label("Working day")
    start_time = st.time_input("Day starts at", value=time(9, 30), step=900)
    day_hours = st.slider("Working hours", 4.0, 11.0, 8.0, 0.5, format="%.1f h")
    visit_minutes = st.slider("Minutes per visit", 10, 90, 30, 5, format="%d min")
    max_stops = st.slider("Maximum stops", 1, 20, 10)

    ui.side_label("Priority weights")
    st.caption("How much each signal counts. Rescaled to add up to 100%.")
    weights = {
        "target_gap": st.slider("Target gap", 0, 100, int(DEFAULT_WEIGHTS["target_gap"] * 100), 5, format="%d%%"),
        "pending_issues": st.slider("Pending issues", 0, 100, int(DEFAULT_WEIGHTS["pending_issues"] * 100), 5, format="%d%%"),
        "days_since_visit": st.slider("Days since visit", 0, 100, int(DEFAULT_WEIGHTS["days_since_visit"] * 100), 5, format="%d%%"),
        "dealer_size": st.slider("Dealer size", 0, 100, int(DEFAULT_WEIGHTS["dealer_size"] * 100), 5, format="%d%%"),
    }

    ui.side_label("Dealer data")
    upload = st.file_uploader("Upload your own CSV", type="csv", help="Columns: " + ", ".join(REQUIRED_COLUMNS))
    st.download_button("Download sample CSV", SAMPLE_CSV.read_bytes() if SAMPLE_CSV.exists() else b"",
                       "dealers.csv", "text/csv", width="stretch")

    ui.side_label("Advanced")
    use_osrm = st.toggle("Real road distances (OSRM)", value=True,
                         help="Off = straight-line distance x 1.35 at 20 km/h. Works offline.")
    traffic = st.slider("Traffic factor on drive times", 1.0, 2.5, 1.5, 0.1, disabled=not use_osrm,
                        format="x%.1f", help="OSRM returns free-flow times; city traffic is slower.")
    km_per_point = st.slider("Detour worth 1 priority point", 0.1, 3.0, 1.0, 0.1, format="%.1f km",
                             help="Higher = willing to drive further to reach important dealers.")
    use_ortools = st.toggle("Use OR-Tools solver", value=HAS_ORTOOLS, disabled=not HAS_ORTOOLS,
                            help="Off = greedy insertion + 2-opt backup heuristic.")

# ----------------------------------------------------------------------------- data + scoring
if upload is not None:
    try:
        raw = pd.read_csv(upload)
    except Exception as exc:  # noqa: BLE001 - show any parse error to the user
        st.error(f"Could not read the CSV: {exc}")
        st.stop()
    problems = validate(raw)
    if problems:
        st.error("This CSV can't be used:\n\n- " + "\n- ".join(problems))
        st.stop()
    source_label = f"Uploaded: {upload.name}"
else:
    raw = load_sample()
    source_label = "Sample data: 22 fictional dealers in Pune"

if sum(weights.values()) == 0:
    st.error("Set at least one priority weight above zero.")
    st.stop()
dealers = score_dealers(raw.reset_index(drop=True), {k: v / 100 for k, v in weights.items()})

points = ((BRANCH_OFFICE["latitude"], BRANCH_OFFICE["longitude"]),) + tuple(
    zip(dealers["latitude"].astype(float), dealers["longitude"].astype(float))
)
matrix = get_matrix(points, use_osrm, traffic)
solver_label = "OR-Tools" if use_ortools and HAS_ORTOOLS else "Greedy + 2-opt"

# ----------------------------------------------------------------------------- header + controls
ui.hero(
    date.today().strftime("%a, %d %b %Y"),
    BRANCH_OFFICE["name"].split("(")[-1].rstrip(")"),
    short_source(matrix.source),
    solver_label,
)
st.write("")

labels = [f"{r.dealer_id} · {r.dealer_name} ({r.area}) · {r.priority_score:.0f}" for r in dealers.itertuples()]
default_must = []
if "must_visit" in dealers.columns:
    default_must = [labels[i] for i in dealers.index[dealers["must_visit"].fillna(0).astype(bool)]]

ctrl_left, ctrl_right = st.columns([3.2, 1], vertical_alignment="bottom")
with ctrl_left:
    must_labels = st.multiselect(
        "Must visit today",
        labels,
        default=default_must,
        placeholder="Pick dealers that must be on today's route (escalations, promised visits...)",
        help="These dealers are always included in the route.",
    )
must = tuple(labels.index(lbl) for lbl in must_labels)

if use_osrm and not matrix.source.startswith("OSRM"):
    st.warning("Could not reach the OSRM server, so distances are estimated (straight line x 1.35 at 20 km/h).")

# ----------------------------------------------------------------------------- plan
settings = PlanSettings(visit_minutes=visit_minutes, day_hours=day_hours, max_stops=max_stops,
                        km_per_priority_point=km_per_point)
try:
    plan = get_plan(matrix.km, matrix.minutes, tuple(dealers["priority_score"]), must, settings, use_ortools)
except PlanningError as exc:
    st.error(f"Can't build a plan: {exc} Try fewer must-visit dealers, a longer day or shorter visits.")
    st.stop()

schedule = build_schedule(dealers, plan, matrix.km, matrix.minutes, visit_minutes, start_time)
skipped = not_visited(dealers, plan)
kpis = compute_kpis(dealers, plan, matrix.km, matrix.minutes, visit_minutes)

info = {
    "Data": source_label,
    "Distance source": matrix.source,
    "Solver": plan.method,
    "Day start": start_time.strftime("%H:%M"),
    "Working day (h)": day_hours,
    "Minutes per visit": visit_minutes,
    "Max stops": max_stops,
    "Must-visit dealers": ", ".join(dealers.iloc[list(must)]["dealer_id"]) or "None",
}
with ctrl_right:
    st.download_button(
        "Export to Excel",
        to_excel(schedule, skipped, summary_table(kpis, info)),
        f"visit_plan_{date.today():%Y%m%d}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        icon=":material/download:",
        width="stretch",
    )

for note in plan.notes:
    st.info(note)

# ----------------------------------------------------------------------------- KPIs
ui.kpi_cards(kpis, schedule.iloc[-1]["Arrive"])
st.write("")

# ----------------------------------------------------------------------------- map + itinerary
map_col, plan_col = st.columns([2.1, 1], gap="medium")
with map_col:
    ui.section("Route map", "Click a stop for dealer details")
    with st.container(border=True):
        route_points = (points[0],) + tuple(points[i + 1] for i in plan.order) + (points[0],)
        geometry = get_geometry(route_points, use_osrm)
        st_folium(build_map(dealers, plan, geometry), height=MAP_HEIGHT, use_container_width=True,
                  returned_objects=[])
with plan_col:
    ui.section("Today's itinerary", f"{len(plan.order)} stops · {start_time:%H:%M}–{schedule.iloc[-1]['Arrive']}")
    with st.container(height=MAP_HEIGHT + 34, border=False):
        ui.itinerary(schedule, start_time.strftime("%H:%M"))

st.write("")
cmp_col, cov_col = st.columns(2, gap="medium")
with cmp_col:
    ui.section("Planned vs. unplanned", "Same dealers, two routes")
    ui.comparison_panel(kpis)
with cov_col:
    ui.section("Coverage by priority tier", f"{kpis['dealers_visited']} of {kpis['dealers_total']} dealers today")
    ui.coverage_panel(dealers, plan.order)

# ----------------------------------------------------------------------------- details
st.write("")
ui.section("Details", source_label)
tab_plan, tab_skip, tab_scores, tab_method = st.tabs(
    ["Visit schedule", f"Not visited today ({len(skipped)})", "Dealer priorities", "How it works"]
)

with tab_plan:
    st.dataframe(
        schedule,
        hide_index=True,
        width="stretch",
        column_config={
            "Priority": st.column_config.NumberColumn(format="%.1f"),
            "Drive km": st.column_config.NumberColumn(format="%.1f km"),
            "Drive min": st.column_config.NumberColumn(format="%d min"),
            "Navigate": st.column_config.LinkColumn("Navigate", display_text="Open in Google Maps ↗"),
        },
    )

with tab_skip:
    if skipped.empty:
        st.success("Every dealer fits in today's plan.")
    else:
        st.caption("Ranked by priority — the top of this list is the starting point for tomorrow.")
        st.dataframe(
            skipped,
            hide_index=True,
            width="stretch",
            column_config={"Priority": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")},
        )

with tab_scores:
    visited = set(plan.order)
    chart_df = dealers.assign(
        label=dealers["dealer_name"] + " · " + dealers["area"],
        status=["Visiting today" if i in visited else "Not today" for i in dealers.index],
    )
    bars = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusEnd=4, height=14)
        .encode(
            x=alt.X("priority_score:Q", title="Priority score", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("label:N", sort="-x", title=None),
            color=alt.Color(
                "priority_tier:N",
                title="Tier",
                scale=alt.Scale(domain=list(TIER_COLOURS), range=list(TIER_COLOURS.values())),
            ),
            opacity=alt.Opacity("status:N", title=None,
                                scale=alt.Scale(domain=["Visiting today", "Not today"], range=[1.0, 0.35])),
            tooltip=[
                alt.Tooltip("dealer_name:N", title="Dealer"),
                alt.Tooltip("area:N", title="Area"),
                alt.Tooltip("priority_score:Q", title="Priority", format=".1f"),
                alt.Tooltip("priority_tier:N", title="Tier"),
                alt.Tooltip("status:N", title="Today"),
            ],
        )
    )
    rules = alt.Chart(pd.DataFrame({"x": [MEDIUM_THRESHOLD, HIGH_THRESHOLD]})).mark_rule(
        strokeDash=[4, 4], color=SKIPPED_COLOUR
    ).encode(x="x:Q")
    st.altair_chart((bars + rules).properties(height=max(320, 22 * len(chart_df))), width="stretch")

    view = dealers[["dealer_id", "dealer_name", "area", "monthly_target_lakh", "achieved_lakh",
                    "pending_issues", "days_since_last_visit", "f_target_gap", "f_pending_issues",
                    "f_days_since_visit", "f_dealer_size", "priority_score", "priority_tier"]].copy()
    view.insert(0, "today", ["✓" if i in visited else "" for i in view.index])
    st.dataframe(
        view.sort_values("priority_score", ascending=False),
        hide_index=True,
        width="stretch",
        column_config={
            "today": st.column_config.TextColumn("Today", width="small"),
            "dealer_id": "ID",
            "dealer_name": "Dealer",
            "area": "Area",
            "monthly_target_lakh": st.column_config.NumberColumn("Target (₹L)", format="%.0f"),
            "achieved_lakh": st.column_config.NumberColumn("Achieved (₹L)", format="%.1f"),
            "pending_issues": "Issues",
            "days_since_last_visit": "Days since visit",
            "f_target_gap": st.column_config.NumberColumn("Gap", format="%.2f"),
            "f_pending_issues": st.column_config.NumberColumn("Issues f", format="%.2f"),
            "f_days_since_visit": st.column_config.NumberColumn("Recency f", format="%.2f"),
            "f_dealer_size": st.column_config.NumberColumn("Size f", format="%.2f"),
            "priority_score": st.column_config.ProgressColumn("Priority", min_value=0, max_value=100, format="%.1f"),
            "priority_tier": "Tier",
        },
    )

with tab_method:
    w = {k: v / sum(weights.values()) for k, v in weights.items()}
    st.markdown(
        f"""
**1 · Priority scoring.** Each dealer gets a score from 0 to 100:

`Score = 100 × ({w['target_gap']:.2f} × Target gap + {w['pending_issues']:.2f} × Pending issues + {w['days_since_visit']:.2f} × Days since visit + {w['dealer_size']:.2f} × Dealer size)`

Target gap = (Target − Achieved) ÷ Target · Issues ÷ 5 (capped) · Days ÷ 30 (capped) · Target ÷ largest target.
Tiers: High ≥ {HIGH_THRESHOLD}, Medium {MEDIUM_THRESHOLD}–{HIGH_THRESHOLD}, Low < {MEDIUM_THRESHOLD}.

**2 · Distance matrix.** Road distance and drive time between every pair of locations — {matrix.source}.

**3 · Route optimisation.** A prize-collecting travelling-salesman problem solved with Google OR-Tools:
start and end at the branch, fit drive + visit time into the working day, at most {max_stops} stops,
skipping a dealer costs its priority score (so low-priority dealers are dropped first), and must-visit
dealers can never be skipped. Path Cheapest Arc builds a first route; Guided Local Search improves it.

**4 · Output.** Timed schedule, map, KPIs and an Excel report. The *unplanned* baseline visits the same
dealers in most-urgent-first order without route planning.
"""
    )

ui.footer()
