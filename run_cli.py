"""Run the planner without the UI.

Example:
    python run_cli.py --hours 8 --visit-min 30 --max-stops 10 --must-visit D004 D011
"""
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from planner import BRANCH_OFFICE, REQUIRED_COLUMNS
from planner.distance import build_matrix
from planner.optimizer import PlanningError, PlanSettings, plan_route
from planner.priority import score_dealers
from planner.report import build_schedule, compute_kpis, not_visited, summary_table, to_excel

ROOT = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Plan today's dealer visits.")
    ap.add_argument("--data", default=ROOT / "data" / "dealers.csv", type=Path)
    ap.add_argument("--hours", type=float, default=8.0, help="working day length")
    ap.add_argument("--visit-min", type=float, default=30, help="minutes per dealer visit")
    ap.add_argument("--max-stops", type=int, default=10)
    ap.add_argument("--start", default="09:30", help="day start time HH:MM")
    ap.add_argument("--must-visit", nargs="*", default=[], metavar="DEALER_ID")
    ap.add_argument("--offline", action="store_true", help="skip OSRM, use estimated distances")
    ap.add_argument("--traffic", type=float, default=1.5, help="multiplier on OSRM free-flow drive times")
    ap.add_argument("--heuristic", action="store_true", help="use the backup heuristic instead of OR-Tools")
    ap.add_argument("--out", type=Path, default=ROOT / "visit_plan.xlsx")
    args = ap.parse_args()

    dealers = pd.read_csv(args.data)
    missing = set(REQUIRED_COLUMNS) - set(dealers.columns)
    if missing:
        raise SystemExit(f"CSV is missing columns: {', '.join(sorted(missing))}")
    dealers = score_dealers(dealers)

    unknown = set(args.must_visit) - set(dealers["dealer_id"])
    if unknown:
        raise SystemExit(f"Unknown dealer IDs: {', '.join(sorted(unknown))}")
    must = set(dealers.index[dealers["dealer_id"].isin(args.must_visit)])

    points = [(BRANCH_OFFICE["latitude"], BRANCH_OFFICE["longitude"])]
    points += list(zip(dealers["latitude"], dealers["longitude"]))
    matrix = build_matrix(points, use_osrm=not args.offline, traffic_factor=args.traffic)

    settings = PlanSettings(visit_minutes=args.visit_min, day_hours=args.hours, max_stops=args.max_stops)
    try:
        plan = plan_route(matrix.km, matrix.minutes, dealers["priority_score"], must, settings,
                          use_ortools=not args.heuristic)
    except PlanningError as exc:
        raise SystemExit(f"Cannot plan the day: {exc}")

    start = datetime.strptime(args.start, "%H:%M").time()
    schedule = build_schedule(dealers, plan, matrix.km, matrix.minutes, settings.visit_minutes, start)
    skipped = not_visited(dealers, plan)
    kpis = compute_kpis(dealers, plan, matrix.km, matrix.minutes, settings.visit_minutes)

    print(f"Distances: {matrix.source}\nSolver:    {plan.method}\n")
    print(schedule.drop(columns=["Navigate"]).to_string(index=False))
    print(f"\nNot visited today ({len(skipped)}):")
    print(skipped.to_string(index=False))
    print(
        f"\nVisited {kpis['dealers_visited']}/{kpis['dealers_total']} dealers "
        f"({kpis['high_visited']}/{kpis['high_total']} high priority) | "
        f"{kpis['planned_km']} km vs {kpis['unplanned_km']} km unplanned "
        f"-> saved {kpis['km_saved']} km ({kpis['pct_saved']}%) | day {kpis['day_hours']} h"
    )
    for note in plan.notes:
        print(f"Note: {note}")

    info = {"Distance source": matrix.source, "Solver": plan.method, "Working day (h)": args.hours,
            "Minutes per visit": args.visit_min, "Max stops": args.max_stops, "Start time": args.start}
    args.out.write_bytes(to_excel(schedule, skipped, summary_table(kpis, info)))
    print(f"\nExcel report: {args.out}")


if __name__ == "__main__":
    main()
