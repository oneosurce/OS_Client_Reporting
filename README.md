# OS_Client_Reporting

OneSource client-facing service-desk dashboards, built as Power BI Projects (PBIP — plain-text TMDL model + PBIR report) on the Syncro RMM PostgreSQL export.

One folder per client. All of them share the same design; they differ only by the `CustomerId` parameter and the client name in the report header/footer.

| Folder | Client | Syncro `customer_id` |
|---|---|---|
| [`FWW/`](FWW/) | FW Walton, Inc. | 33810072 |
| [`Sophia/`](Sophia/) | Sophia Oilfield Supply Services | 29076492 |
| [`BayOil/`](BayOil/) | Bay Oil Co. | 12432163 |
| [`Vanderford/`](Vanderford/) | Vanderford Air and Plumbing | 34611186 |
| [`Millforest/`](Millforest/) | Millforest Dental Group | 12315250 |
| [`MartinWalton/`](MartinWalton/) | Martin Walton Attorneys at Law | 12309358 |
| [`Cobalt/`](Cobalt/) | Cobalt Engineering | 16527837 |
| [`Curry/`](Curry/) | Curry Excavation & Site Work Inc. | 12701269 |
| [`TDEC/`](TDEC/) | TDEC, Inc | 14623202 |

**Internal (not client-facing):**

| Folder | Report | Source |
|---|---|---|
| [`Finance/`](Finance/) | Business Health — billed / collected / AR aging / revenue by client / est. MRR | `invoices`, `payments`, `tickets` (all clients) |
| [`ServiceDesk/`](ServiceDesk/) | Daily Ops — open-ticket action list + team board for technicians | `tickets` (all clients) |
| [`Fleet/`](Fleet/) | Fleet Health — endpoints per client, OS mix, Windows 10 / pending-reboot / low-RAM / low-disk exposure, risk-ranked device list | `assets` (all clients) |

**Data-improvement work (feeding future reports):**

| Folder | Purpose |
|---|---|
| [`Finance/contract-data/`](Finance/contract-data/) | Target spec + build worksheet for rebuilding Syncro Contracts, so `OS_Finance` can show real MRR / contract-vs-project margin / renewal runway instead of a derived estimate |
| [`Contracts/`](Contracts/) | Contract Coverage dashboard — Contracted MRR vs target recurring, coverage gap, renewal runway; fills in as Syncro Contracts are rebuilt |

Each folder has its own `README.md` with the model/report detail.

---

## Mobile / phone layout

Every report has a **phone layout** for the Power BI mobile app, stored as `mobile.json`
next to each visual (PBIR `visualContainerMobileState`). A page shows a phone layout only
for the visuals that have a `mobile.json`; everything else (footers, secondary slicers,
sub-labels, the second Ops-Pulse chart) is hidden on phone. Regenerate after layout changes:

```bash
python3 scripts/gen_mobile.py     # rewrites mobile.json for all reports, then commit + sync
```

New client dashboards inherit the phone layout automatically (cloned from `FWW/`).

---

## Deployment

All items live in the **OneSource Reporting** Fabric workspace (`3ca25e44-c70a-4827-85dd-50064f492051`), connected to this repo's `main` branch via **Fabric Git integration**. A workspace can only bind one repo, which is why every client dashboard lives here rather than in its own repo.

To ship a change:

```bash
git add -A && git commit -m "..." && git push
scripts/deploy.sh FWW            # sync workspace from Git + export a preview
scripts/deploy.sh Sophia refresh # ...also trigger a dataset refresh first
```

`deploy.sh` runs `updateFromGit` on the workspace, then (optionally) refreshes that client's semantic model, then exports the report to `scripts/out/<client>.png`.

The Postgres credentials are stored once on the shared cloud connection (`os-syncro-db.postgres.database.azure.com` / `syncro_reporting`); new semantic models auto-bind to it, so there's no per-client credential step.

---

## Adding a client

1. `cp -R FWW/ <NewClient>/` and rename the three `OS_FWW_Tickets.*` entries to `OS_<NewClient>_Tickets.*` (folder names, the `.pbip`, and the `path` refs inside `.pbip` and `definition.pbir`).
2. In `<NewClient>/OS_<NewClient>_Tickets.SemanticModel/`:
   - `definition/expressions.tmdl` — set `CustomerId` to the client's Syncro id.
   - `.platform` (both items) — new `logicalId` GUIDs, `displayName` = `OS_<NewClient>_Tickets`.
3. `OS_<NewClient>_Tickets.Report/definition/pages/ExecOverview/visuals/`:
   - `title/visual.json` — client name in the eyebrow line.
   - `footer/visual.json` — client name in the disclaimer.
4. Commit, push, then in the Fabric workspace **Source control → Update all** (or run `deploy.sh` once the items exist). Refresh the new semantic model and share.

> Always scope by `customer_id`, never a name match — e.g. "Walton" also matches `Martin Walton Attorneys at Law`.
