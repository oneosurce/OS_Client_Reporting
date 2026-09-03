# OS_FWW_Tickets — Executive Overview

A Power BI Project (PBIP) containing a **semantic model** and an **Executive Overview** report page for FW Walton (FWW) ticket performance, built on the Syncro PostgreSQL export.

---

## How to open it

1. Make sure **Power BI Desktop** is set to emit/open PBIP:
   *File → Options and settings → Options → Preview features →* enable **"Power BI Project (.pbip) save option"** and **"Store semantic model using TMDL format"**. Restart Desktop.
2. Open **`OS_FWW_Tickets.pbip`**.
3. Power BI will prompt for the **PostgreSQL** credentials for `os-syncro-db.postgres.database.azure.com` / `syncro_reporting`. Enter them and set privacy level to *Organizational*. (The Npgsql provider must be installed; Desktop will link you to it if missing.)
4. Click **Refresh**. The model loads `tickets` and `customers`, builds the Date table, and the report renders.

> The `.pbip` is plain text (TMDL for the model, PBIR JSON for the report), so it diffs cleanly in git and can be edited outside Desktop.

---

## What's in the model

### Tables

| Table | Role | Notes |
|---|---|---|
| **Tickets** | Fact | One row per ticket (~8,600). Trimmed to the columns the dashboard needs; adds cleaned/derived fields (below). |
| **Customers** | Dimension | One row per customer (342). `Site` column drives the Site slicer and RLS. |
| **Date** | Dimension | Calculated date table (`CALENDAR`) from the first ticket year through the end of the current year. Marked as the model's date table. |
| **Aging Bucket** | Disconnected helper | Static bands (`0–1 / 1–3 / 3–7 / 7+ days`) for backlog aging. |
| **Measures** | Measure holder | Empty hidden table that stores all DAX measures in display folders. |

### Relationships

- `Tickets[Customer ID]` → `Customers[Customer ID]` (many-to-one). **The key types were mismatched** — `customers.id` came through as text while `tickets.customer_id` was numeric — so the Customers query casts the key to a whole number to make the join work.
- `Tickets[Created Date]` → `Date[Date]` — **active**. All date-sliced volume is by creation date by default.
- `Tickets[Resolved Date]` → `Date[Date]` — inactive; activated inside the resolved/resolution-time measures via `USERELATIONSHIP`.
- `Tickets[Due Date]` → `Date[Date]` — inactive; available for due-date analysis.

The eight auto-generated hidden date tables from the original file are **removed** (time-intelligence auto date/time is turned off), which shrinks and simplifies the model.

### Cleaning done in Power Query (Tickets)

- **Priority** — Syncro stores priority as `"0 Urgent"`, `"1 High"`, `"2 Normal"`, `"3 Low"`. A step strips the numeric prefix to give a clean `Priority` plus a `Priority Sort` column so it always orders Urgent → Low.
- **Is Open** — `true` for every status **except** `Resolved`, `Closed`, `Invoiced` (per your choice). If your Syncro instance uses different terminal status names, edit the list in the `IsOpen` step.
- **Resolution Hours** — hours from `Created At` to `Resolved At`.
- **Resolved On Time** — `Resolved At <= Due At`; blank when unresolved or no due date. This is the basis of SLA compliance.
- Date-only helper columns (`Created Date`, `Resolved Date`, `Due Date`) feed the three date relationships.

---

## Measures (by folder)

**Backlog** (point-in-time — these ignore the date slicer, respect Site & Priority)
`Open Tickets`, `Open Tickets 7 Days Ago`, `Open Tickets vs Last Week`, `Open Tickets Change Label`, `Overdue Open Tickets`, `Open Tickets by Age`, `Avg Open Ticket Age (Days)`.

**Rolling 30 Days** (relative to today, for the KPI cards)
`Tickets Created (30D)`, `Tickets Created (Prior 30D)`, `Tickets Created (30D) vs Prior %`, `Tickets Resolved (30D)`, plus their `... Change Label` / `... Label` text measures that render the "▲ 6 vs last week" style captions.

**Volume** (respect the date slicer, for trends)
`Tickets Created`, `Tickets Resolved`, `Net Backlog Change`.

**Resolution Time**
`Avg Resolution Hours`, `Median Resolution Hours`, `Avg Resolution Hours (30D)`, `Avg Resolution Target Label`.

**SLA**
`SLA Met Tickets`, `SLA Breached Tickets`, `SLA Compliance %`, `SLA Compliance % (30D)`, `SLA Target Label`, `SLA Target Line`.

**Targets** (parameters — change these two to re-tune every target caption)
`SLA Target %` = 90%, `Resolution Target Hours` = 12.

### How SLA compliance is defined
Share of tickets **that have a due date** resolved **on or before** that due date. Open tickets that aren't yet due are excluded from the denominator; open tickets already past due count as breached (`SLA Breached Tickets`). This matches "resolved on or before the ticket's `due_date`."

---

## The report page — Executive Overview

Matches the mockup, wired to live measures:

- **Header** with title and three **slicers**: Date range (between), Site (dropdown), Priority (dropdown).
- **Five KPI cards**: Open Tickets, Created (30D), Resolved (30D), Avg Resolution, SLA Compliance — each with a dynamic caption measure underneath.
- **Tickets Created vs. Resolved — Weekly Trend**: line chart over `Date[Week Label]`.
- **Open Tickets by Priority**: donut, colored Urgent→Low.
- **Backlog Aging**: bar chart over the Aging Bucket bands.
- **SLA Compliance by Priority**: column chart with a dashed reference line at the 90% target.

### Row-level security
A role named **`FW Walton`** filters `Customers` to rows where `Site` contains "Walton" (`SEARCH("Walton", Customers[Site]) > 0`), and that flows to Tickets through the relationship. Assign members to this role in the Power BI Service (or test it with *Modeling → View as*). If FWW spans several customer records whose names don't all contain "Walton," edit the role filter to list them.

---

## Things you'll likely want to adjust

- **Terminal statuses** — confirm your exact Syncro status names and update the `Is Open` list if needed.
- **Per-priority SLA targets** — the current model uses Syncro's own `due_date`. If FWW has agreed hour targets per priority (e.g. Urgent 4h, High 8h…), tell me and I'll add a priority-targets table and switch the SLA logic to it.
- **Site definition** — `Site` currently uses `business_name` (falling back to the contact name for residential records). Swap to city or another field if that's your notion of "site."
- **Card deltas** — "vs last week" and "vs prior 30 days" are computed against `TODAY()`. On a scheduled refresh they stay meaningful; in a static file they reflect the last refresh date.

---

*Built from `OS_FWW_Tickets.pbix`. Model = TMDL, report = PBIR; open the `.pbip` in Power BI Desktop.*
