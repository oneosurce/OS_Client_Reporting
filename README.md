# OS_Client_Reporting

OneSource client-facing service-desk dashboards, built as Power BI Projects (PBIP — plain-text TMDL model + PBIR report) on the Syncro RMM PostgreSQL export.

One folder per client. All of them share the same design; they differ only by the `CustomerId` parameter and the client name in the report header/footer.

| Folder | Client | Syncro `customer_id` |
|---|---|---|
| [`FWW/`](FWW/) | FW Walton, Inc. | 33810072 |
| [`Sophia/`](Sophia/) | Sophia Oilfield Supply Services | 29076492 |

Each folder has its own `README.md` with the model/report detail.

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
