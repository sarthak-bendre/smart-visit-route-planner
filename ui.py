"""Presentation helpers for the Streamlit app: global CSS and small HTML components."""
from html import escape

import streamlit as st

from planner.report import OFFICE_COLOUR, SKIPPED_COLOUR, TIER_COLOURS

NAVY = "#14233C"
BLUE = "#1F4E9C"
MUTED = "#6B7485"
GREEN = "#2E9E6A"

# Light tints of the tier colours for pills and bars.
TIER_TINTS = {"High": "#FBE9E9", "Medium": "#FDF1E3", "Low": "#E5F4EC"}

CSS = f"""
<style>
[data-testid="stHeader"] {{ background: transparent; height: 2.5rem; }}
[data-testid="stMainBlockContainer"], .block-container {{ padding-top: 3rem; padding-bottom: 3rem; max-width: 1440px; }}
[data-testid="stSidebar"] {{ border-right: 1px solid #E2E7EF; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
[data-testid="stSidebarHeader"] {{ height: 0.5rem; min-height: 0; padding: 0; }}

/* Sidebar */
.brand {{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }}
.brand-logo {{ width: 36px; height: 36px; border-radius: 9px; background: linear-gradient(135deg, {BLUE}, {NAVY});
  color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; }}
.brand-name {{ font-weight: 700; font-size: 15px; color: {NAVY}; line-height: 1.15; }}
.brand-sub {{ font-size: 11.5px; color: {MUTED}; }}
.side-label {{ font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: {MUTED}; margin: 18px 0 2px; padding-top: 14px; border-top: 1px solid #EDF0F5; }}

/* Hero */
.hero {{ background: linear-gradient(120deg, {NAVY} 0%, {BLUE} 70%, #2F6BC9 100%); border-radius: 16px;
  padding: 26px 30px; color: #fff; display: flex; justify-content: space-between; align-items: flex-end;
  gap: 24px; flex-wrap: wrap; box-shadow: 0 10px 30px rgba(20,35,60,.18); position: relative; overflow: hidden; }}
.hero::after {{ content: ""; position: absolute; right: -60px; top: -80px; width: 280px; height: 280px;
  border-radius: 50%; background: rgba(255,255,255,.06); }}
.hero-eyebrow {{ font-size: 11.5px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; opacity: .75; }}
.hero-title {{ font-size: 30px; font-weight: 800; letter-spacing: -.02em; margin: 4px 0 4px; }}
.hero-sub {{ font-size: 14.5px; opacity: .85; }}
.hero-meta {{ display: flex; gap: 8px; flex-wrap: wrap; position: relative; z-index: 1; }}
.chip {{ background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18); border-radius: 999px;
  padding: 6px 12px; font-size: 12.5px; white-space: nowrap; }}
.chip b {{ font-weight: 600; opacity: .7; margin-right: 4px; }}

/* Rows of side-by-side panels wrap into one column when the main area is narrow. */
[data-testid="stHorizontalBlock"]:has(.tl), [data-testid="stHorizontalBlock"]:has(.cmp-row) {{ flex-wrap: wrap; }}
[data-testid="stHorizontalBlock"]:has(.tl) > [data-testid="stColumn"]:first-child {{ min-width: min(100%, 520px); }}
[data-testid="stHorizontalBlock"]:has(.tl) > [data-testid="stColumn"]:last-child {{ min-width: min(100%, 290px); }}
[data-testid="stHorizontalBlock"]:has(.cmp-row) > [data-testid="stColumn"] {{ min-width: min(100%, 340px); }}

/* Section headings */
.section {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin: 6px 0 10px; }}
.section h3 {{ font-size: 16px; font-weight: 700; color: {NAVY}; margin: 0; padding: 0; white-space: nowrap; }}
.section span {{ font-size: 12.5px; color: {MUTED}; }}

/* KPI cards */
.kpi-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; margin: 4px 0 6px; }}
@media (max-width: 1180px) {{ .kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
@media (max-width: 640px) {{ .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .kpi.accent {{ grid-column: 1 / -1; }} }}
.kpi {{ background: #fff; border: 1px solid #E2E7EF; border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 1px 2px rgba(20,35,60,.04); }}
.kpi-label {{ font-size: 12px; font-weight: 600; color: {MUTED}; text-transform: uppercase; letter-spacing: .06em; }}
.kpi-value {{ font-size: 28px; font-weight: 800; color: {NAVY}; letter-spacing: -.02em; margin: 6px 0 2px; }}
.kpi-value small {{ font-size: 15px; font-weight: 600; color: {MUTED}; margin-left: 2px; }}
.kpi-sub {{ font-size: 12.5px; color: {MUTED}; }}
.kpi-bar {{ height: 6px; background: #EDF0F5; border-radius: 99px; margin-top: 8px; overflow: hidden; }}
.kpi-bar div {{ height: 100%; border-radius: 99px; }}
.kpi.accent {{ background: linear-gradient(135deg, #EAF6F0, #FFFFFF); border-color: #CBE8D8; }}
.kpi.accent .kpi-value {{ color: {GREEN}; }}

/* Itinerary timeline */
.tl {{ position: relative; padding-left: 4px; }}
.tl-item {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; position: relative; padding-bottom: 14px; }}
.tl-item:not(:last-child)::before {{ content: ""; position: absolute; left: 16px; top: 30px; bottom: -2px;
  width: 2px; background: #E2E7EF; }}
.tl-dot {{ width: 30px; height: 30px; border-radius: 50%; color: #fff; font-weight: 700; font-size: 13px;
  display: flex; align-items: center; justify-content: center; border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(20,35,60,.25); z-index: 1; }}
.tl-dot.office {{ background: {OFFICE_COLOUR}; border-radius: 8px; font-size: 10px; letter-spacing: .04em; }}
.tl-card {{ background: #fff; border: 1px solid #E2E7EF; border-radius: 12px; padding: 10px 12px; }}
.tl-top {{ display: flex; justify-content: space-between; gap: 4px 8px; align-items: baseline; flex-wrap: wrap; }}
.tl-name {{ font-weight: 700; font-size: 14px; color: {NAVY}; }}
.tl-time {{ font-size: 12.5px; font-weight: 600; color: {BLUE}; white-space: nowrap; font-variant-numeric: tabular-nums; }}
.tl-meta {{ font-size: 12.5px; color: {MUTED}; margin-top: 2px; }}
.tl-foot {{ display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 12px; color: {MUTED}; }}
.tl-foot a {{ color: {BLUE}; font-weight: 600; text-decoration: none; }}
.pill {{ display: inline-block; padding: 1px 8px; border-radius: 99px; font-size: 11.5px; font-weight: 600; }}

/* Panels */
.panel {{ background: #fff; border: 1px solid #E2E7EF; border-radius: 14px; padding: 16px 18px; height: 100%; }}
.cmp-row {{ margin: 10px 0 12px; }}
.cmp-head {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 5px; }}
.cmp-head b {{ color: {NAVY}; font-variant-numeric: tabular-nums; }}
.cmp-bar {{ height: 12px; background: #EDF0F5; border-radius: 99px; overflow: hidden; }}
.cmp-bar div {{ height: 100%; border-radius: 99px; }}
.callout {{ margin-top: 10px; background: #EAF6F0; color: #1D6B47; border-radius: 10px; padding: 9px 12px; font-size: 13px; }}
.note {{ font-size: 12px; color: {MUTED}; margin-top: 8px; }}

/* Tabs and footer */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
.footer {{ text-align: center; font-size: 12px; color: {MUTED}; margin-top: 28px; padding-top: 16px;
  border-top: 1px solid #E2E7EF; }}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def sidebar_brand() -> None:
    st.html(
        '<div class="brand"><div class="brand-logo">RP</div><div>'
        '<div class="brand-name">Route Planner</div><div class="brand-sub">Field team visit planning</div>'
        "</div></div>"
    )


def side_label(text: str) -> None:
    st.html(f'<div class="side-label">{escape(text)}</div>')


def section(title: str, note: str = "") -> None:
    st.html(f'<div class="section"><h3>{escape(title)}</h3><span>{escape(note)}</span></div>')


def hero(date_label: str, branch: str, distance_source: str, solver: str) -> None:
    chips = [("Date", date_label), ("Branch", branch), ("Distances", distance_source), ("Solver", solver)]
    chip_html = "".join(f'<div class="chip"><b>{k}</b>{escape(v)}</div>' for k, v in chips)
    st.html(
        '<div class="hero"><div style="position:relative;z-index:1">'
        '<div class="hero-eyebrow">Field operations &middot; Daily visit plan</div>'
        '<div class="hero-title">Smart Visit Route Planner</div>'
        '<div class="hero-sub">Whom to visit today, in what order, and how much travel it saves.</div>'
        f'</div><div class="hero-meta">{chip_html}</div></div>'
    )


def pill(tier: str, text: str | None = None) -> str:
    colour = TIER_COLOURS.get(tier, SKIPPED_COLOUR)
    tint = TIER_TINTS.get(tier, "#EDF0F5")
    return f'<span class="pill" style="background:{tint};color:{colour}">{escape(text or tier)}</span>'


def kpi_cards(k: dict, day_end: str) -> None:
    high_pct = 100 * k["high_visited"] / k["high_total"] if k["high_total"] else 100
    deferred = k["dealers_total"] - k["dealers_visited"]
    cards = [
        ("Dealers visited", f'{k["dealers_visited"]}<small>/ {k["dealers_total"]}</small>',
         f"{deferred} deferred to another day", ""),
        ("High priority covered", f'{k["high_visited"]}<small>/ {k["high_total"]}</small>',
         f'<div class="kpi-bar"><div style="width:{high_pct:.0f}%;background:{TIER_COLOURS["High"]}"></div></div>', ""),
        ("Planned route", f'{k["planned_km"]:.1f}<small>km</small>', f'{k["drive_hours"]:.1f} h on the road', ""),
        ("Day length", f'{k["day_hours"]:.1f}<small>h</small>', f"Back at the office by {day_end}", ""),
        ("Distance saved", f'{k["pct_saved"]:.0f}<small>%</small>',
         f'{k["km_saved"]:.1f} km &middot; {k["minutes_saved"]} min less driving', "accent"),
    ]
    html = "".join(
        f'<div class="kpi {cls}"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>'
        for label, value, sub, cls in cards
    )
    st.html(f'<div class="kpi-grid">{html}</div>')


def itinerary(schedule, start_label: str) -> None:
    """Vertical timeline of today's stops."""
    items = [
        '<div class="tl-item"><div class="tl-dot office">HQ</div><div class="tl-card">'
        f'<div class="tl-top"><div class="tl-name">Leave branch office</div><div class="tl-time">{start_label}</div></div>'
        '<div class="tl-meta">Shivajinagar</div></div></div>'
    ]
    for row in schedule.to_dict("records"):
        drive = f'{row["Drive km"]:.1f} km &middot; {row["Drive min"]} min drive'
        if row["Stop"] == "End":
            items.append(
                '<div class="tl-item"><div class="tl-dot office">HQ</div><div class="tl-card">'
                f'<div class="tl-top"><div class="tl-name">Back at office</div><div class="tl-time">{row["Arrive"]}</div></div>'
                f'<div class="tl-meta">{drive}</div></div></div>'
            )
            continue
        colour = TIER_COLOURS.get(row["Tier"], SKIPPED_COLOUR)
        tier_pill = pill(row["Tier"], f'{row["Tier"]} {row["Priority"]:.0f}')
        items.append(
            f'<div class="tl-item"><div class="tl-dot" style="background:{colour}">{row["Stop"]}</div><div class="tl-card">'
            f'<div class="tl-top"><div class="tl-name">{escape(str(row["Dealer"]))}</div>'
            f'<div class="tl-time">{row["Arrive"]} &ndash; {row["Leave"]}</div></div>'
            f'<div class="tl-meta">{escape(str(row["Area"]))} &middot; {escape(str(row["Dealer ID"]))} &nbsp;{tier_pill}</div>'
            f'<div class="tl-foot"><span>{drive}</span>'
            f'<a href="{escape(row["Navigate"])}" target="_blank" rel="noopener">Navigate &#8599;</a></div>'
            "</div></div>"
        )
    st.html(f'<div class="tl">{"".join(items)}</div>')


def comparison_panel(k: dict) -> None:
    longest = max(k["unplanned_km"], k["planned_km"], 1e-9)
    rows = [
        ("Optimised route", k["planned_km"], BLUE),
        ("Unplanned (most urgent first)", k["unplanned_km"], "#B8C0CC"),
    ]
    bars = "".join(
        f'<div class="cmp-row"><div class="cmp-head"><span>{label}</span><b>{km:.1f} km</b></div>'
        f'<div class="cmp-bar"><div style="width:{100 * km / longest:.1f}%;background:{colour}"></div></div></div>'
        for label, km, colour in rows
    )
    st.html(
        f'<div class="panel">{bars}'
        f'<div class="callout">Saves <b>{k["km_saved"]:.1f} km</b> and <b>{k["minutes_saved"]} minutes</b> '
        f"of driving for the same {k['dealers_visited']} dealers.</div>"
        '<div class="note">Baseline visits the same dealers in priority order without route planning.</div></div>'
    )


def coverage_panel(dealers, order: list[int]) -> None:
    visited = set(order)
    rows = []
    for tier in ("High", "Medium", "Low"):
        idx = dealers.index[dealers["priority_tier"] == tier]
        total = len(idx)
        done = sum(1 for i in idx if i in visited)
        pct = 100 * done / total if total else 0
        rows.append(
            f'<div class="cmp-row"><div class="cmp-head"><span>{pill(tier)}</span><b>{done} / {total}</b></div>'
            f'<div class="cmp-bar"><div style="width:{pct:.1f}%;background:{TIER_COLOURS[tier]}"></div></div></div>'
        )
    st.html(
        f'<div class="panel">{"".join(rows)}'
        '<div class="note">Tiers: High &ge; 40 &middot; Medium 30&ndash;40 &middot; Low &lt; 30. '
        "Skipped dealers carry over to tomorrow's ranking.</div></div>"
    )


def footer() -> None:
    st.html(
        '<div class="footer">Smart Visit Route Planner &middot; Python &middot; OR-Tools &middot; OSRM &middot; '
        "Streamlit &middot; Folium &middot; Map data &copy; OpenStreetMap contributors</div>"
    )
