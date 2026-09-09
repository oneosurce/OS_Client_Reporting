# OS_ServiceDesk — Daily Ops

Internal service-desk operations board for OneSource technicians. One folder in the
[`OS_Client_Reporting`](../README.md) monorepo; deploys to the **OneSource Reporting**
Fabric workspace. Refreshes **hourly at :30** (it's a live queue view).

## Model

Single table **Tickets** (from `tickets`). Money-free — this is an operations model.

**Co-managed scoping (model-level filter):** Cobalt Engineering is co-managed — Cobalt's own IT hold `@cobalt-engineering.com` Syncro logins. The model drops:
- every ticket assigned to an `@cobalt-engineering.com` address (anywhere), and
- every Cobalt Engineering ticket **not** assigned to `ae@onesource.tech` (Alexander) or `ar@onesource.tech` (Antonio).

Filtering is by **email**, not name — there are two "Rafael Vera" in Syncro (the Cobalt one, and a former OneSource tech `rv@onesource.tech`); only the Cobalt one is excluded.

**Minerva Ruiz (`mr@onesource.tech`) is excluded** — she's Accounting, not a tech. She's the assignee on every "Ready for Invoice" ticket (the billing holding queue), so all her tickets are dropped. Side effect: CLOSED (WK) / Closed-30d only count closures still held by a tech, not ones already handed to billing.

**Closed tickets** are handled two ways: (1) the model keeps only tickets completed in the **last 35 days** (plus all open) — the ~8,000-row Resolved history is dropped, model ~260 rows; (2) a **page-level filter defaults to open tickets only**, so Resolved / Ready-for-Invoice are hidden by default on every visual. That filter shows in the Filters pane as *"Show closed tickets"* and can be expanded to include recent closures. `Closed This Week` / `Created This Week` / `Closed 7d` / `Closed 30d` carry `REMOVEFILTERS(Tickets[Is Open])` so they ignore the page filter and keep counting.

- `Assigned To` / `Assigned Email` (hidden) / `Tech Group` parsed from the `user` JSON blob.
- `Age (Days)` = since created, `Idle (Days)` = since last update, `Overdue By (Days)` = past the Syncro `due_date` — all computed at refresh time (`DateTime.LocalNow()`), so they're accurate to the last hourly refresh.
- `Attention Score` = age + idle×2 + 30 if overdue (available for sorting; the list currently sorts by Idle).
- `Completed At` = `resolved_at` for Resolved, else `updated_at` for Ready-for-Invoice (same convention as the client dashboards).

## Page — Daily Ops

- **Slicers:** Technician · Client · Status (a tech filters to their own queue).
- **KPI row:** Open · Overdue · Idle 7d+ · Oldest (days) · Closed this week · Net backlog this week.
- **Open tickets — most neglected first:** every open ticket, sorted by days idle. Ticket # · Client · Assigned To · Status · Age · Idle · Due. Work it top-down.
- **By technician:** open / overdue / idle-7d+ / closed-30d per person (only staff with open tickets). Shows load balance and throughput concentration.
- **Ops Pulse (two stacked charts):** *Ops Pulse · Q<n>-20xx (last quarter)* above *Ops Pulse · Q<n>-20xx (current quarter)*, each a weekly Created-vs-Resolved column chart on the SAME 0–70 y-scale, x-axis = W01…W13 (week of quarter, so the two align). Both titles are dynamic measures; the pair auto-rolls at each quarter boundary. Fed by the separate `Ticket Flow` table (trailing 13 months, no 35-day cutoff, KEEPS Minerva/Accounting — overall flow, not tech-queue scoped; still drops @cobalt-engineering.com).

## What it surfaced (baseline, 2026-09-08)

- 93 open, **85 overdue, 80 idle 7+ days** — the backlog is almost entirely stale.
- **41 of 93 open tickets sit on Antonio's queue**, all overdue, all idle — a dumping ground, not a worked queue.
- **Minerva Ruiz closed 143 of the last 30 days' ~178** — ~80% of throughput on one person.
- Two `@cobalt-engineering.com` accounts (client-side portal users) hold 20 stale tickets nobody at OneSource is driving.
- Throughput keeps pace with intake (net backlog −6 this week) — the problem is neglected old tickets, not capacity.

## Not built (data can't support it)

Reopen rate, first-response time, time-in-status — Syncro's export has no status-transition history.
Utilization / billable % — time tracking is inconsistently captured (the top closer logs zero timer hours).
