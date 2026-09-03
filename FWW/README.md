# OS_FWW_Tickets — Executive Overview

A Power BI Project (PBIP) containing a **semantic model** and a single-page **Executive Overview** report for **FW Walton, Inc.** service-desk ticket health, built on the Syncro RMM PostgreSQL export.

> One client folder in the [`OS_Client_Reporting`](../README.md) monorepo (sibling: [`Sophia`](../Sophia/)). All client dashboards are identical apart from the `CustomerId` parameter and the client name in the header/footer.

---

## How to open it

1. In **Power BI Desktop**, enable *Options → Preview features →* **"Power BI Project (.pbip) save option"** and **"Store semantic model using TMDL format"**, then restart.
2. Open **`OS_FWW_Tickets.pbip`**.
3. When prompted, enter the **PostgreSQL** credentials for `os-syncro-db.postgres.database.azure.com` / `syncro_reporting` and set privacy to *Organizational*.
4. **Refresh**.

The `.pbip` is plain text (TMDL model, PBIR report) — it diffs cleanly and can be edited without Desktop.

---

## Client scoping

`definition/expressions.tmdl` holds one parameter, **`CustomerId` = 33810072** (`FW Walton, Inc.`). The `Tickets` and `Customers` Power Query steps both filter to it, so the model only ever contains this client's data — the filter folds to Postgres.

There is **no row-level-security role**. It protected nothing (the data is already scoped at source) and it blocked every non-admin viewer with "access denied" on share. Anyone with Viewer access to the workspace/app can open the report.

> Always scope by `customer_id`, never a name match. Adding another client is a folder copy — see the monorepo README.

---

## What's in the model

| Table | Role | Notes |
|---|---|---|
| **Tickets** | Fact | One row per ticket. Trimmed to needed columns plus cleaned/derived fields (below). |
| **Customers** | Dimension | Filtered to the single client row via `CustomerId`. Joins to Tickets on `Customer ID` (key cast to whole number — `customers.id` is text in Syncro, `tickets.customer_id` is numeric). |
| **Date** | Dimension | Calculated `CALENDAR` table, first ticket year → end of current year. Marked as the date table. |
| **Aging Bucket** | Disconnected helper | Static bands (`0–1 / 1–3 / 3–7 / 7+ days`) for backlog aging. |
| **Date Range** | Disconnected helper | Range-picker presets: Today / Last 7 days / Last 30 days / Last 90 days / Last quarter / Year to date / Last 12 months / All time. |
| **_Measures** | Measure holder | Hidden table holding all DAX measures in display folders. |

**Relationships:** `Tickets[Created Date] → Date[Date]` is active; `Completed Date` and `Due Date` relationships are inactive and switched on inside measures via `USERELATIONSHIP`. Auto date/time is off.

### Cleaning in Power Query (Tickets)

- **Priority** — Syncro stores `"0 Urgent" … "3 Low"`; a step strips the digit to a clean `Priority` + `Priority Sort`. Unset priority is folded into `Normal`.
- **Is Open** — `false` only for terminal statuses `Resolved` and `Ready for Invoice`; everything else is open. `Closed`/`Invoiced` do not occur.
- **Completed At** — work-completion timestamp. Syncro only writes `resolved_at` for the old "Resolved" workflow; `Ready for Invoice` tickets carry none, so `Completed At` falls back to `Updated At` for terminal-status tickets. Blank while open.
- **Resolution Hours** — `Created At` → `Completed At`.
- **Resolved On Time** — `Completed At <= Due At`; basis of the (currently unsurfaced) SLA measures.

---

## Measures (by folder)

- **Backlog** (point-in-time, as of the window end, respect Priority): `Open Tickets`, `Open Tickets 7 Days Ago`, `Open Tickets Change Label`, `Overdue Open Tickets`, `Open Tickets by Age`, `Avg Open Ticket Age (Days)`.
- **KPI** (drive the four cards; keyed off the Range picker, default last 90 days): `Created (Card)`, `Resolved (Card)`, `Avg Resolution Days (Card)`, their `… (Prior Window)` and `… Change Label` counterparts, the window bounds `_Window Min` / `_Window Max`, and `Window Start` / `Window End` (those two feed the header From/To fields).
- **Volume** (trend series, clipped to the active window so the chart auto-zooms): `Created`, `Resolved`.
- **Resolution Time**: `Avg Resolution Hours`, `Median Resolution Hours`.
- **SLA** (kept in the model, not shown on the report — bring back once the number matures): `SLA Compliance %`, `SLA Met/Breached Tickets`, `SLA Target %` (90%), `Resolution Target Hours`.

> Per-ticket `due_date` was only recently enabled in Syncro, so historical SLA % is not yet meaningful. That's why the SLA card and by-priority chart are not on the page.

---

## The report page — Executive Overview

- **Header**: title + the **Range** preset dropdown, two read-only **From** / **To** fields showing the resolved window (a Between slicer can't be driven by a preset, so these are display-only and always follow the Range selection), and the **Priority** dropdown. No Site slicer (Syncro has no usable location field).
- **Four KPI cards**: Open Tickets, Created, Resolved, Avg Resolution — each with a dynamic "vs prior window" caption.
- **Tickets Created vs. Resolved — Weekly Trend**: clustered column chart over `Date[Week Label]`, series `Created` / `Resolved`, auto-zooms with the Range selection.
- **Open Tickets by Priority**: donut.
- **Backlog Aging**: bar chart over the Aging Bucket bands.

### Known gaps

- `multiRowCard` ignores `dataLabels.color`, so the caption text renders in the default link-blue (conditional green/amber `* Change Color` measures exist but aren't applied).
- Card "vs prior" deltas are computed against `TODAY()` — meaningful on a scheduled refresh, frozen to last-refresh date in a static file.

---

*Model = TMDL, report = PBIR. Open the `.pbip` in Power BI Desktop, or edit the text directly.*
