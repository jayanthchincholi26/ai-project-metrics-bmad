#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""dashboard — renders snapshots/*.json into a single self-contained
metrics-reports/dashboard.html leadership summary (Story 5.5).

Read-only, same as tools/metrics-report/main.py — never writes to snapshots/
or any manifest/event file, and this tool adds no publishing/hosting/upload
mechanism of any kind: the file is written locally only, and the developer
decides how/whether to share it (potentially sensitive leadership/cost data).

Unlike Story 5.3's per-day reports, this dashboard aggregates every story
into ONE flat table (sorted by date, most recent first) with a few headline
stat figures above it. Snapshot discovery and highest-revision selection
(AD-3b) are reused directly from tools/metrics-report/main.py's
discover_snapshots() via bridge-import — not re-implemented here.

No chart of any kind: the user's own request was "an HTML table format," and
a table is the right form for "scan every story's cost/points," per this
project's dataviz guidance on choosing a form. A stat-tile row for the
headline totals is explicitly sanctioned as "not a chart."

Fully self-contained: all CSS inlined, no CDN links, no external fonts or
network calls of any kind — openable by double-clicking, no server needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "metrics-report"))
import main as metrics_report  # noqa: E402 (path must be set up first) - discover_snapshots() reuse

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "hooks")
)  # bridge to the shared field-descriptions dict (Story 5.11)
import _field_guide  # noqa: E402 (path must be set up first)

REPORTS_DIR = "metrics-reports"
OUTPUT_FILE = "dashboard.html"

# Story 5.11: which FIELD_GUIDE entry best explains each table column / stat tile.
COLUMN_FIELD_GUIDE_KEYS = {
    "Story": "pm_metrics.name",
    "Date": "engineering_metrics.last_event_at",
    "Points": "pm_metrics.points",
    "Duration": "estimated_cost.duration_minutes",
    "Estimated Cost": "estimated_cost.usd",
    "AI Token Cost": "token_cost.cost_usd",
    "Defects": "defect_metrics.total_defects",
}
TILE_FIELD_GUIDE_KEYS = {
    "Total Story Points": "pm_metrics.points",
    "Total Estimated Cost": "estimated_cost.usd",
    "Total AI Token Cost": "token_cost.cost_usd",
}


def format_usd(value: float) -> str:
    return f"${value:.2f}"


def format_token_usd(value: float) -> str:
    """AI token cost is often fractions of a cent - 2 decimals would collapse
    small-but-real values to a misleading $0.00, so this stays at 4."""
    return f"${value:.4f}"


def aggregate_stats(snapshots: "list[dict]") -> "dict[str, Any]":
    total_stories = len(snapshots)

    def known_sum(getter) -> "tuple[Optional[float], int]":
        known = [getter(s) for s in snapshots if isinstance(getter(s), (int, float))]
        return (sum(known) if known else None), len(known)

    # (s.get("key") or {}) not s.get("key", {}) - a corrupted/hand-edited snapshot
    # could have the key present but explicitly null, and dict.get()'s default only
    # covers an absent key, not a present-but-None value (review finding, PR #28)
    points_sum, points_known = known_sum(lambda s: (s.get("pm_metrics") or {}).get("points"))
    cost_sum, cost_known = known_sum(lambda s: (s.get("estimated_cost") or {}).get("usd"))
    token_sum, token_known = known_sum(lambda s: (s.get("token_cost") or {}).get("cost_usd"))

    return {
        "total_stories": total_stories,
        "points_sum": points_sum,
        "points_known": points_known,
        "cost_sum": cost_sum,
        "cost_known": cost_known,
        "token_sum": token_sum,
        "token_known": token_known,
    }


def stat_value(total_stories: int, value_sum: Optional[float], known: int, fmt) -> str:
    """A stat tile's value text, honest about how many stories fed the sum
    (AD-10: never a fabricated total, always visible how much is excluded)."""
    if value_sum is None:
        return "not tracked"
    text = fmt(value_sum)
    if known < total_stories:
        text += f" ({known} of {total_stories} stories — {total_stories - known} not tracked)"
    return text


def render_stat_tiles(stats: "dict[str, Any]") -> str:
    total = stats["total_stories"]
    tiles = [
        ("Total Stories", str(total)),
        ("Total Story Points", stat_value(total, stats["points_sum"], stats["points_known"], str)),
        (
            "Total Estimated Cost",
            stat_value(total, stats["cost_sum"], stats["cost_known"], format_usd),
        ),
        (
            "Total AI Token Cost",
            stat_value(total, stats["token_sum"], stats["token_known"], format_token_usd),
        ),
    ]

    def tile_title(label: str) -> str:
        key = TILE_FIELD_GUIDE_KEYS.get(label)
        if key is None:
            return "Count of every story represented in this dashboard (highest revision per story only, AD-3b)."
        return (
            _field_guide.FIELD_GUIDE[key]
            + " This tile sums the value across every story with a known figure."
        )

    cards = "\n".join(
        f'<div class="tile" title="{tile_title(label)}"><div class="tile-label">{label}</div>'
        f'<div class="tile-value">{value}</div></div>'
        for label, value in tiles
    )
    return f'<div class="tiles">{cards}</div>'


def render_row(snapshot: dict) -> str:
    # (s.get("key") or {}) - same present-but-null guard as aggregate_stats() above
    pm = snapshot.get("pm_metrics") or {}
    eng = snapshot.get("engineering_metrics") or {}
    est = snapshot.get("estimated_cost") or {}
    tok = snapshot.get("token_cost") or {}
    defects = snapshot.get("defect_metrics") or {}

    name = pm.get("name") or snapshot.get("story_id", "unknown-story")
    date = (eng.get("last_event_at") or pm.get("created") or "")[:10] or "unknown"
    points = pm.get("points") if pm.get("points") is not None else "not set"
    duration = metrics_report.humanize_minutes(
        est.get("duration_minutes") or metrics_report.duration_minutes_of(eng)
    )
    estimated_cost = (
        format_usd(est["usd"])
        if est.get("usd") is not None
        else f"not tracked — {est.get('reason') or 'no reason given'}"
    )
    token_cost = (
        format_token_usd(tok["cost_usd"])
        if tok.get("cost_usd") is not None
        else f"not tracked — {tok.get('reason') or 'no reason given'}"
    )
    defects_cell = (
        f"{defects['total_defects']} total "
        f"(testing {defects['testing_efficiency']:.2f}% / review {defects['review_efficiency']:.2f}%)"
        if defects.get("total_defects") is not None
        else f"not tracked — {defects.get('reason') or 'no reason given'}"
    )

    cells = [name, date, str(points), duration, estimated_cost, token_cost, defects_cell]
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def render_table(snapshots: "list[dict]") -> str:
    ordered = sorted(
        snapshots,
        key=lambda s: (
            (s.get("engineering_metrics") or {}).get("last_event_at")
            or (s.get("pm_metrics") or {}).get("created")
            or ""
        ),
        reverse=True,
    )

    def th(label: str) -> str:
        description = _field_guide.FIELD_GUIDE.get(COLUMN_FIELD_GUIDE_KEYS.get(label), "")
        title_attr = f' title="{description}"' if description else ""
        return f"<th{title_attr}>{label}</th>"

    header = (
        "<tr>"
        + "".join(
            th(label)
            for label in [
                "Story",
                "Date",
                "Points",
                "Duration",
                "Estimated Cost",
                "AI Token Cost",
                "Defects",
            ]
        )
        + "</tr>"
    )
    rows = "\n".join(render_row(s) for s in ordered)
    return f"<table>\n<thead>{header}</thead>\n<tbody>\n{rows}\n</tbody>\n</table>"


CSS = """
:root{
  --bg:#0a0e14; --panel:#111927; --panel2:#151f30; --line:#22304a;
  --text:#dbe4f3; --dim:#8fa2c2; --dim2:#5f7396; --accent:#3ddc97; --accent2:#5eb6ff;
}
@media (prefers-color-scheme: light){
  :root{
    --bg:#f6f8fb; --panel:#ffffff; --panel2:#f1f4f9; --line:#dde3ee;
    --text:#1b2434; --dim:#4d5b74; --dim2:#7d89ba; --accent:#0b8f57; --accent2:#1f6fd1;
  }
}
:root[data-theme="dark"]{
  --bg:#0a0e14; --panel:#111927; --panel2:#151f30; --line:#22304a;
  --text:#dbe4f3; --dim:#8fa2c2; --dim2:#5f7396; --accent:#3ddc97; --accent2:#5eb6ff;
}
:root[data-theme="light"]{
  --bg:#f6f8fb; --panel:#ffffff; --panel2:#f1f4f9; --line:#dde3ee;
  --text:#1b2434; --dim:#4d5b74; --dim2:#7d89ba; --accent:#0b8f57; --accent2:#1f6fd1;
}
*{box-sizing:border-box;}
body{
  margin:0; background:var(--bg); color:var(--text); min-height:100vh;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  padding:40px 4vw 64px;
}
.wrap{max-width:1100px; margin:0 auto;}
h1{font-size:1.8rem; margin:0 0 24px;}
.tiles{display:flex; gap:14px; flex-wrap:wrap; margin-bottom:32px;}
.tile{
  background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:16px 18px; min-width:200px; flex:1;
}
.tile-label{font-size:0.78rem; color:var(--dim2); text-transform:uppercase; letter-spacing:0.05em;}
.tile-value{font-size:1.1rem; margin-top:6px; color:var(--text);}
table{width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line);}
th, td{text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); font-size:0.9rem;}
th{color:var(--dim2); font-weight:600; background:var(--panel2);}
td{color:var(--text);}
"""


def render_dashboard(snapshots: "list[dict]") -> str:
    stats = aggregate_stats(snapshots)
    # a full HTML5 document, not a bare fragment (found via live E2E: browsers render
    # a fragment leniently, but a real <!doctype html>/<head>/<title> matches this
    # repo's own established HTML-doc convention, e.g. docs/architecture-diagram-leadership.html)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Metrics Dashboard</title>\n"
        f"<style>{CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="wrap">\n'
        "<h1>Metrics Dashboard</h1>\n"
        f"{render_stat_tiles(stats)}\n"
        f"{render_table(snapshots)}\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--repo-root", required=True, help="repository root")
    args = p.parse_args(argv)

    root = Path(args.repo_root)
    if not root.is_dir():
        print(f"error: --repo-root {args.repo_root!r} is not a directory", file=sys.stderr)
        return 2

    snapshots = metrics_report.discover_snapshots(root)

    reports_dir = root / REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    target = reports_dir / OUTPUT_FILE
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(render_dashboard(snapshots))

    print(
        json.dumps(
            {"ok": True, "dashboard": str(target.resolve()), "stories_rendered": len(snapshots)}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
