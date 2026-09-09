# Contract data — target spec & build worksheet

**Why this exists.** The reporting stack can't show real recurring revenue, contract-vs-project
margin, or renewal runway because Syncro's **Contracts** are stale: 70 rows, all expired
2025-12-31, and only 8 ever carried a dollar amount. Someone did a clean pass in Jan 2025
("Managed Workplace – Fully Managed Cloud Services") and it lapsed.

Goal: **one contract record per active client, kept current**, so `OS_Finance` can replace
its *estimated* MRR (~$67K, derived from invoice history) with a real number.

---

## 1. Target contract record (Syncro Contracts object)

| Field | What it must hold | Notes |
|---|---|---|
| `customer` | the client | one contract per client (use the newest if a client has several) |
| `name` | the **plan**, from the taxonomy in §2 | drop the year suffixes ("- 2024") — the term dates carry that |
| `description` | one-line human summary | e.g. "45 endpoints + M365, flat monthly, Standard SLA" |
| `contract_amount` | **monthly recurring $** (the covered fee only — exclude project/T&M) | this is the field that's almost always blank today |
| `start_date` | current term start | |
| `end_date` | term end; for month-to-month set +12 months and renew on rollover | a blank end date reads as "no term" and breaks renewal reporting |
| `sla_id` | SLA tier from §3 | set once the tiers exist in Syncro |
| `status` | `Won` for anything active | |
| `apply_to_all` | `true` if the contract covers all of that client's tickets & assets | |

`contract_amount`, `start_date`, `end_date` are the three that unlock reporting. Everything
else is nice-to-have.

---

## 2. Plan taxonomy (collapse 15 historical names → 5)

| Use this | Historical names it replaces | Billing basis |
|---|---|---|
| **Managed Workplace** | Managed Workplace, "\| Classic", "\| Business Cloud", "- 2024", "– Fully Managed Cloud Services", "FWW - Managed IT Services" | flat monthly, sized by endpoints or seats |
| **Co-Managed IT** | Co-Managed IT | flat monthly (client keeps their own IT staff) |
| **Retainer / Block Hours** | Block Hours, "20 Hours Monthly", "X Hours Monthly" | flat monthly for N hours; overage billed T&M |
| **M365 Management** | "On-Demand \| M365", "On-Demand \| M65", "…M65 - Premium Support", "…M365 & Azure" | per seat |
| **On-Demand (T&M)** | On-Demand Business Services, Internal IT, no prior plan | **no recurring** — break-fix, no contract row needed unless there's a minimum |

Pick the one that matches how the client is actually billed today, not what they had in 2022.

---

## 3. SLA tiers (draft — leadership to finalize, then create in Syncro)

| Tier | First response | Resolution target | Coverage |
|---|---|---|---|
| **Standard** | 4 business hours | next business day | Mon–Fri 8×5 |
| **Priority** | 1 business hour | same business day | Mon–Fri 8×5 |
| **Critical / 24×7** | 1 hour | 4 hours | 24×7 incl. holidays |

First-response reporting also needs Syncro configured to stamp the first public reply — see
workstream 5 in the data-improvement plan. Until then SLA reporting is resolution-time only.

---

## 4. Filling `worksheet.csv`

One row per active client (billed 6+ of the last 13 months, or 3+ active endpoints).

**Pre-filled context** (do not edit): billing history, median monthly invoice, a
**suggested recurring** figure (25th-percentile monthly invoice over the last 6 months — a
rough "floor" with project spikes stripped out), active endpoints, ticket volume, and the
prior plan name(s) on file.

**To fill:** Plan · Billing basis · Recurring $/mo · Contract start · Contract end / M2M ·
SLA tier · Covers all? · Notes.

The "suggested recurring" is a starting point, not the answer — e.g. FW Walton's $29K median
is mostly project work, so its true covered fee needs the owner's input. Cobalt ($11,650)
and Vanderford ($4,000) are near-exact recurring and can likely be taken as-is.

Then enter the filled rows into Syncro Contracts. Regenerate the worksheet any time with
`Finance/contract-data/gen_worksheet.py`.

---

## 5. What reporting does once this is populated

`OS_Finance` changes (not built yet — waiting on the data):

- **Contracted MRR** card — sum of `contract_amount` for active contracts, replacing the
  derived `Estimated MRR`.
- **Covered vs billable** per client — contract fee vs actual invoiced total; shows who's
  over- or under-serviced against their plan.
- **Renewal runway** — contracts with `end_date` in the next 90 days.
- **$/endpoint** and (once time logging improves) **$/hour** benchmarks by plan — are we
  pricing Managed Workplace consistently?

---

## 6. Keeping it current

- New client signed → create the contract record same day (amount, term, plan, SLA).
- Renewal / price change → update `contract_amount` and roll `end_date`.
- Client leaves → set `status` away from `Won`.

If this doesn't stay current the reporting silently goes stale again — same failure as 2025.
