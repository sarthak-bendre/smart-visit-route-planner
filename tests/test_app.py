"""Smoke-test the Streamlit app headlessly (offline distances so it doesn't need internet)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _run(**toggles):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    for label, value in toggles.items():
        next(t for t in at.toggle if t.label == label).set_value(value)
    at.run()
    return at


def test_app_renders_plan_offline():
    at = _run(**{"Real road distances (OSRM)": False})
    assert not at.exception
    assert not at.error
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "Dealers visited" in html and "Distance saved" in html  # KPI cards
    assert "Back at office" in html  # itinerary timeline
    assert len(at.dataframe) == 3  # plan, not visited, priorities


def test_must_visit_selection():
    at = _run(**{"Real road distances (OSRM)": False})
    ms = at.multiselect[0]
    lowest = min(ms.options, key=lambda o: float(o.rsplit("·", 1)[1]))
    ms.select(lowest).run()
    assert not at.exception and not at.error
    plan = at.dataframe[0].value
    assert lowest.split(" · ")[0] in plan["Dealer ID"].tolist()
