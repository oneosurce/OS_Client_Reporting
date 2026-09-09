#!/usr/bin/env python3
"""Generate phone layouts (mobile.json per visual) for every report in OS_Client_Reporting.

Power BI phone layout in PBIR is emergent: a page has a phone layout iff at least one of
its visuals has a mobile.json. Visuals without one are hidden on phone. So we place only
what matters on a phone — header, key slicer, KPI cards (2-up), primary table, charts —
stacked in a single ~324px column, and omit the rest (footers, secondary slicers,
sub-labels, the second Ops-Pulse chart).
"""
import json, pathlib
from collections import defaultdict

REPO = pathlib.Path.home() / "Developer" / "OS_Client_Reporting"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/2.0.0/schema.json"

CANVAS_W = 324
GAP = 8
H = {"header": 60, "title": 50, "slicer": 56, "card": 76, "chart": 210, "table": 384}
ORDER = {"header": 0, "title": 1, "slicer": 2, "card": 3, "table": 4, "chart": 5}


def classify(name, vtype):
    n = name.lower()
    if "hdrband" in n:
        return "header"
    if n == "title":
        return "title"
    if "footer" in n or "card_sub" in n or n.startswith("date_"):
        return None
    if n.endswith("_last"):            # keep only the current-quarter Ops Pulse chart
        return None
    if vtype == "slicer":
        return "slicer" if ("range" in n or "client" in n) else None
    if vtype in ("card", "multiRowCard"):
        return "card"
    if vtype in ("tableEx", "pivotTable", "matrix", "tableEx", "table"):
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

total_written = total_removed = 0
for _pagedir, vis in sorted(pages.items()):
    placed = sorted((v for v in vis if v[2]), key=lambda v: (ORDER[v[2]], v[3], v[4]))
    for vdir, _n, cat, _y, _x in vis:
        if not cat:
            m = vdir / "mobile.json"
            if m.exists():
                m.unlink()
                total_removed += 1

    cursor = GAP
    card_col = 0
    for i, (vdir, _name, cat, _y, _x) in enumerate(placed):
        if cat != "card" and card_col == 1:   # flush a dangling half-row of cards
            cursor += H["card"] + GAP
            card_col = 0

        if cat == "header":
            mx, my, mw, mh = 0, 0, CANVAS_W, H["header"]
            cursor = mh + GAP
        elif cat == "title":
            mx, my, mw, mh = 8, 6, CANVAS_W - 16, H["title"]
            if cursor == GAP:                 # no header on this page
                cursor = my + mh + GAP
        elif cat == "card":
            mw, mh = (CANVAS_W - GAP) // 2, H["card"]
            mx = card_col * (mw + GAP)
            my = cursor
            if card_col == 1:
                cursor += mh + GAP
                card_col = 0
            else:
                card_col = 1
        else:
            mx, my, mw, mh = 0, cursor, CANVAS_W, H[cat]
            cursor = my + mh + GAP

        z = (i + 1) * 1000
        (vdir / "mobile.json").write_text(json.dumps({
            "$schema": SCHEMA,
            "position": {"x": mx, "y": my, "z": z, "width": mw, "height": mh, "tabOrder": z},
        }, indent=2) + "\n")
        total_written += 1

    if card_col == 1:
        pass

print(f"wrote {total_written} mobile.json, removed {total_removed}")
for pd, vis in sorted(pages.items()):
    rep = pd.parents[3].name
    kept = [v[1] for v in sorted((x for x in vis if x[2]), key=lambda v: (ORDER[v[2]], v[3], v[4]))]
    print(f"  {rep:14} {pd.name:12} -> {', '.join(kept)}")
