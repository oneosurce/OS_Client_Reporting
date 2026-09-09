#!/usr/bin/env python3
"""Generate the contract build worksheet CSV from the Syncro billing history.

One row per active client. Context columns are pre-filled from invoices/assets/tickets;
the entry columns (Plan, Recurring $/mo, term, SLA, ...) are left blank for the team.
"""
import csv, subprocess, io, os, pathlib

SQL = r"""
WITH mo AS (
  SELECT customer_id,
         max(customer_business_then_name) nm,
         date_trunc('month', date) m,
         sum(NULLIF(regexp_replace(coalesce(total,'0'),'[^0-9.-]','','g'),'')::numeric) tot
  FROM invoices
  WHERE date > now() - interval '13 months'
  GROUP BY 1, 3
),
recent AS (  -- last 6 complete calendar months
  SELECT * FROM mo
  WHERE m >= date_trunc('month', now()) - interval '6 months'
    AND m <  date_trunc('month', now())
),
bill AS (
  SELECT customer_id,
         max(nm) nm,
         count(*) FILTER (WHERE tot > 0) mos_billed,
         round(sum(tot) FILTER (WHERE m >= date_trunc('month', now()) - interval '12 months')) billed_12mo,
         round(percentile_cont(0.5) WITHIN GROUP (ORDER BY tot) FILTER (WHERE tot > 0)) median_mo
  FROM mo GROUP BY 1
),
floor AS (
  SELECT customer_id,
         round(percentile_cont(0.25) WITHIN GROUP (ORDER BY tot) FILTER (WHERE tot > 0) / 50.0) * 50 suggested_recurring
  FROM recent GROUP BY 1
),
ast AS (
  SELECT customer_id, count(*) FILTER (WHERE updated_at > now() - interval '30 days') active_ep
  FROM assets WHERE asset_type = 'Syncro Device' GROUP BY 1
),
tk AS (
  SELECT customer_id, count(*) tix_90d FROM tickets WHERE created_at > now() - interval '90 days' GROUP BY 1
),
ct AS (
  SELECT customer_id, string_agg(DISTINCT COALESCE(NULLIF(name,''), description), ' / ') prior_plan
  FROM contracts GROUP BY 1
)
SELECT b.nm, b.customer_id, b.mos_billed, b.billed_12mo, b.median_mo,
       COALESCE(f.suggested_recurring, 0) suggested_recurring,
       COALESCE(a.active_ep, 0) active_ep, COALESCE(t.tix_90d, 0) tix_90d,
       COALESCE(c.prior_plan, '') prior_plan
FROM bill b
LEFT JOIN floor f USING (customer_id)
LEFT JOIN ast a USING (customer_id)
LEFT JOIN tk t USING (customer_id)
LEFT JOIN ct c USING (customer_id)
WHERE b.mos_billed >= 6 OR COALESCE(a.active_ep, 0) >= 3
ORDER BY b.billed_12mo DESC NULLS LAST;
"""

env = dict(os.environ, PGPASSFILE=str(pathlib.Path.home() / ".pgpass"))
out = subprocess.run(
    ["psql",
     "host=os-syncro-db.postgres.database.azure.com port=5432 dbname=syncro_reporting user=osdbsyncro sslmode=require",
     "-P", "pager=off", "-A", "-F", "\t", "-t", "-c", SQL],
    capture_output=True, text=True, env=env,
)
if out.returncode != 0:
    raise SystemExit(out.stderr)

rows = [line.split("\t") for line in out.stdout.strip().splitlines()]

ENTRY_COLS = [
    "Plan (taxonomy)", "Billing basis", "Recurring $/mo", "Contract start", "Contract end / M2M",
    "SLA tier", "Covers all tickets & assets? (Y/N)", "Notes",
]
CONTEXT_COLS = [
    "Client", "customer_id", "Months billed (of 13)", "Billed last 12mo", "Median monthly invoice",
    "Suggested recurring (25th pct, last 6mo)", "Active endpoints", "Tickets last 90d", "Prior plan name(s)",
]

csv_path = pathlib.Path(__file__).resolve().parent / "worksheet.csv"

with csv_path.open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(CONTEXT_COLS + ENTRY_COLS)
    for r in rows:
        r = (r + [""] * 9)[:9]
        w.writerow(r + [""] * len(ENTRY_COLS))

print("wrote", csv_path, f"({len(rows)} clients)")
print(csv_path.read_text())
