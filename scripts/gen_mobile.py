#!/usr/bin/env python3
"""Generate phone layouts (mobile.json per visual) for every report in OS_Client_Reporting.

Power BI phone layout in PBIR is emergent: a page has a phone layout iff at least one of
its visuals has a mobile.json. Visuals without one are hidden on phone. So we place only
what matters on a phone — the key slicer, KPI cards, the primary table, charts — stacked
in a single ~324px column, and omit the rest.

Omitted on phone: the in-report header band + title (the mobile app already shows the
report/page name in its own chrome, and the light-on-navy title clips without the band),
footers, card_sub_* change labels, date_from/date_to, secondary slicers, chart_pulse_last.

KPI cards are full-width single column — 2-up made large dollar values ("$823K") truncate.
"""
import json, pathlib
from collections import defaultdict

REPO = pathlib.Path.home() / "Developer" / "OS_Client_Reporting"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/2.0.0/schema.json"

CANVAS_W = 324
GAP = 8
H = {"slicer": 56, "card": 72, "chart": 210, "table": 380}
ORDER = {"slicer": 0, "card": 1, "table": 2, "chart": 3}


def classify(name, vtype):
    n = name.lower()
    if "hdrband" in n or n == "title":
        return None
    if "footer" in n or "card_sub" in n or n.startswith("date_"):
        return None
    if n.endswith("_last"):            # keep only the current-quarter Ops Pulse chart
        return None
    if vtype == "slicer":
        return "slicer" if ("range" in n or "client" in n) else None
    if vtype in ("card", "multiRowCard"):
        return "card"
    if vtype in ("tableEx", "pivotTable", "matrix", "table"):
        return "table"
    if "chart" in vtype.lower():
        return "chart"
    return None


pages = defaultdict(list)
for vpath in sorted(REPO.glob("*/*.Report/definition/pages/*/visuals/*/visual.json")):
    d = json.loads(vpath.read_text())
    name = d.get("name", vpath.parent.name)
    vtype = d.get("visual", {}).get("visualType", "")
    pos = d.get("position", {})
    pages[vpath.parent.parent].append(
        (vpath.parent, name, classify(name, vtype), float(pos.get("y", 0)), float(pos.get("x", 0)))
    )

written = removed = 0
for _pagedir, vis in sorted(pages.items()):
    for vdir, _n, cat, _y, _x in vis:
        if not cat and (vdir / "mobile.json").exists():
            (vdir / "mobile.json").unlink()
            removed += 1

    placed = sorted((v for v in vis if v[2]), key=lambda v: (ORDER[v[2]], v[3], v[4]))
    cursor = GAP
    for i, (vdir, _name, cat, _y, _x) in enumerate(placed):
        mh = H[cat]
        entry = {"x": 0, "y": cursor, "z": (i + 1) * 1000, "width": CANVAS_W, "height": mh,
                 "tabOrder": (i + 1) * 1000}
        cursor += mh + GAP
        (vdir / "mobile.json").write_text(json.dumps(
            {"$schema": SCHEMA, "position": entry}, indent=2) + "\n")
        written += 1

print(f"wrote {written} mobile.json, removed {removed}")
for pd, vis in sorted(pages.items()):
    rep = pd.parents[3].name
    kept = [v[1] for v in sorted((x for x in vis if x[2]), key=lambda v: (ORDER[v[2]], v[3], v[4]))]
    print(f"  {rep:26} -> {', '.join(kept)}")
