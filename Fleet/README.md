# OS_Fleet — Fleet Health

Endpoint / asset health across all OneSource-managed clients, built from the Syncro
`assets` export.

- **Model** `OS_Fleet.SemanticModel` — a single `Assets` table (one row per Syncro
  device seen in the last 90 days). Hardware, OS and health facts are parsed from the
  asset `properties` JSON at refresh time.
- **Report** `OS_Fleet.Report` — one `Fleet Health` page: KPI cards (endpoints,
  Windows 10, pending reboots, low RAM, low disk, stale), an OS-mix bar chart, a
  per-client table and a risk-ranked "devices needing attention" list.

Deploy: `bash scripts/deploy.sh Fleet refresh`
