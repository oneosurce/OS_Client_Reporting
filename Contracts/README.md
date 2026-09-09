# OS_Contracts — Contract Coverage

Tracks how much of the client base has a live Syncro contract, **Contracted MRR** vs the
**target recurring** estimate, the coverage gap, and renewal runway.

Starts near-empty (Contracted MRR ~$0 — the contract table is stale) and fills in as the
team rebuilds Syncro Contracts using the kit in [`../Finance/contract-data/`](../Finance/contract-data/).

- **Model** `OS_Contracts.SemanticModel` — `Clients` (active client + its current contract,
  merged) and `Contracts` (every contract row). Both are native SQL against the Syncro replica.
- **Report** `OS_Contracts.Report` — one `Contract Coverage` page: KPI cards, a coverage
  punch list, target-vs-contracted bar chart, and a renewal-runway table.

Deploy: `bash scripts/deploy.sh Contracts refresh`
