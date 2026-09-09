# OS_Finance — Business Health

Internal (not client-facing) finance dashboard for OneSource, on the Syncro billing tables.
One folder in the [`OS_Client_Reporting`](../README.md) monorepo; deploys to the same
**OneSource Reporting** Fabric workspace as the client dashboards.

## Model

| Table | Source | Notes |
|---|---|---|
| **Invoices** | `invoices` | Money columns are text in Syncro → parsed to numbers. `Is Billable` = non-zero total; ~42% of invoices are $0 (contract-covered work) and are excluded from revenue. |
| **Payments** | `payments` | `applied_at` (date only). $0 "Cash" rows are contract-covered invoices marked settled. |
| **Customers** | `customers` | All clients, unfiltered. |
| **Ticket Volume** | `tickets` | Trimmed (customer + created date + open flag) for the revenue-vs-load comparison. |
| **Date** / **Date Range** / **AR Bucket** | calculated | Month-scale Range picker; AR aging buckets. |

## Page — Business Health

- **KPI cards:** Billed · Collected · Outstanding (AR) · Collection Rate · **Est. MRR** — the first four honour the Range picker (default *Last 12 months*); Outstanding and Est. MRR are fixed "as of now" / trailing-12 snapshots.
- **Est. MRR** is *derived* (no live contracts feed): for each client, its lowest monthly billable total over the last 12 complete months = its recurring floor (project spikes excluded), summed across clients billed in ≥6 of those months. ~$67K vs ~$97K typical monthly billings, so ~30% of monthly revenue is variable/project work. It's an estimate — treat QuickBooks as the source of truth for true contract MRR.
- **Billings vs. Receipts — Monthly:** column chart, auto-zooms with the Range picker.
- **Revenue by Client:** bar, sorted by billed.
- **Accounts Receivable — Aging:** unpaid billable invoices by age of invoice (0–30 / 31–60 / 61–90 / 90+).

## Known limitations

- **Invoice ↔ ticket linkage broke ~May 2026** (`invoices.ticket_id` went from ~80% populated to <10%). So *revenue per ticket / per technician / effective rate* are **not** built — the join is unreliable.
- **`contracts` table is stale** (all rows end 2025) — no current MRR here; that lives in QuickBooks.
- **`invoices.hardwarecost`** is not a usable cost figure (exceeds revenue on the same invoices) — no hardware-margin metric.
- 701 `Ready for Invoice` tickets match **zero** invoices by `ticket_id` — treat the RFI queue count as the "work awaiting billing" signal, but it can't be reconciled to invoices here.

## Refresh

3× per business day (07:30 / 13:30 / 19:30 Central) — billing data moves slower than tickets.
