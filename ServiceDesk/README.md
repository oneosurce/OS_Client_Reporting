# OS_ServiceDesk — Daily Ops

Internal service-desk operations board for OneSource technicians. One folder in the
[`OS_Client_Reporting`](../README.md) monorepo; deploys to the **OneSource Reporting**
Fabric workspace. Refreshes **hourly at :30** (it's a live queue view).

## Model

Single table **Tickets** (all clients, from `tickets`). Money-free — this is an operations model.
- `Assigned To` / `Tech Group` parsed from the `user` JSON blob.
- `Age (Days)` = since created, `Idle (Days)` = since last update, `Overdue By (Days)` = past the Syncro `due_date` — all computed at refresh time (`DateTime.LocalNow()`), so they're accurate to the last hourly refresh.
- `Attention Score` = age + idle×2 + 30 if overdue (available for sorting; the list currently sorts by Idle).
- `Completed At` = `resolved_at` for Resolved, else `updated_at` for Ready-for-Invoice (same convention as the client dashboards).

## Page — Daily Ops

- **Slicers:** Technician · Client · Status (a tech filters to their own queue).
- **KPI row:** Open · Overdue · Idle 7d+ · Oldest (days) · Closed this week · Net backlog this week.
- **Open tickets — most neglected first:** every open ticket, sorted by days idle. Ticket # · Client · Assigned To · Status · Age · Idle · Due. Work it top-down.
- **By technician:** open / overdue / idle-7d+ / closed-30d per person (only staff with open tickets). Shows load balance and throughput concentration.

## What it surfaced (baseline, 2026-09-08)

- 93 open, **85 overdue, 80 idle 7+ days** — the backlog is almost entirely stale.
- **41 of 93 open tickets sit on Antonio's queue**, all overdue, all idle — a dumping ground, not a worked queue.
- **Minerva Ruiz closed 143 of the last 30 days' ~178** — ~80% of throughput on one person.
- Two `@cobalt-engineering.com` accounts (client-side portal users) hold 20 stale tickets nobody at OneSource is driving.
- Throughput keeps pace with intake (net backlog −6 this week) — the problem is neglected old tickets, not capacity.

## Not built (data can't support it)

Reopen rate, first-response time, time-in-status — Syncro's export has no status-transition history.
Utilization / billable % — time tracking is inconsistently captured (the top closer logs zero timer hours).
