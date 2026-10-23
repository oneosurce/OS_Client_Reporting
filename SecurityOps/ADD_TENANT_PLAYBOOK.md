# OS_SecurityOps — Add a New Customer Tenant

Use this playbook every time a new client is onboarded to the SOC dashboard.  
Estimated time: 30–60 min (plus 1–2 h for first data ingestion).

### What's in the SOC dashboard now

The `OS_SecurityOps` report (Fabric workspace "OneSource Reporting") has **6 pages**:
`SOC Overview` · `Threat Activity` · `UEBA` (User Behavior Analytics) · `Tenant Risk` · `Security Posture` · `Incident Detail`.

Semantic model: **10 tables / 20 measures**, all sourced from Microsoft Sentinel / Log Analytics via a cross-tenant Lighthouse `union` driven by the `TenantRegistry` table.

Separately, the **Live Geo Threat Map** is a standalone Azure-hosted web page (not a Power BI page) — see the [Live Geo Threat Map](#live-geo-threat-map) section below.

Current tenants: **OneSource** (central/managing), **FW Walton**, **Ocean Marine Services**, **Cobalt Engineering**.

---

## Prerequisites

Before starting, collect the following from the customer:

| Item | Where to find it |
|---|---|
| **Sentinel workspace GUID** | Azure portal → Log Analytics workspaces → Properties → Workspace ID |
| **Sentinel subscription ID** | Azure portal → Subscriptions |
| **Sentinel resource group** | Azure portal → Log Analytics workspaces → Overview |
| **Customer Entra tenant ID** | Azure portal → Microsoft Entra ID → Overview → Tenant ID |
| **Admin credential** | Must be Owner on the Sentinel subscription (to deploy Lighthouse) |

You will also need:
- `ar@onesource.tech` logged in on the local `az` CLI (`az account set --subscription "OneSource Azure"`)
- Access to the customer's Azure portal (or a guest account with Owner rights)

---

## Step 1 — Deploy Azure Lighthouse Delegation

This grants OneSource's `OS-Sentinel-Readers` group **Log Analytics Reader** on the customer's workspace so the `svc-pbi-sentinel` service account can run KQL cross-tenant.

> ⚠️ This step **must be executed in the customer's tenant** by someone with **Owner** on the Sentinel subscription. You can do it via guest access or hand the template to the customer's IT admin.

1. Open the customer's Azure portal → **Deploy a custom template**.
2. Use the template at `SecurityOps/lighthouse/add-sentinel-readers.json` (already in this repo).
3. Set parameters:
   - `managedByTenantId`: `4b5e91ed-2885-49b3-9d58-a87089c51417` (OneSource tenant)
   - `managedByGroupId`: `7a57368d-0b62-4b0c-b9c0-0050af871f41` (`OS-Sentinel-Readers`)
   - `workspaceResourceId`: full ARM ID of the customer's Sentinel workspace
4. Deploy to the **same resource group** that contains the Sentinel workspace.
5. Verify in Azure Lighthouse → **Service providers** — OneSource should appear within a few minutes.

**Confirm access:**
```bash
az account set --subscription "OneSource Azure"
az monitor log-analytics workspace show \
  --workspace-name <CUSTOMER_WORKSPACE_NAME> \
  --resource-group <CUSTOMER_RG> \
  --subscription <CUSTOMER_SUB_ID>
```
A 200 response confirms Lighthouse delegation is active.

---

## Step 2 — Configure Entra ID Diagnostic Settings

This sends the customer's identity logs (sign-ins, audits, risk events) into their Sentinel workspace.

> ⚠️ Execute in the **customer's Entra ID** (Azure portal → Microsoft Entra ID → Diagnostic settings).  
> **Critical:** Never point a customer's Entra diagnostic setting at a *different* customer's workspace — this was the root cause of the FWW data-contamination incident (Oct 2026).

1. Go to **Microsoft Entra ID → Monitoring → Diagnostic settings → + Add diagnostic setting**.
2. Name: `Sentinel-EntraID-<CLIENT_SHORT_NAME>` (e.g. `Sentinel-EntraID-FWW`).
3. Enable **all** of the following log categories:

   | Category |
   |---|
   | SignInLogs |
   | AuditLogs |
   | NonInteractiveUserSignInLogs |
   | ServicePrincipalSignInLogs |
   | ManagedIdentitySignInLogs |
   | ProvisioningLogs |
   | RiskyUsers |
   | UserRiskEvents |
   | RiskyServicePrincipals |
   | ServicePrincipalRiskEvents |

4. Destination: **Send to Log Analytics workspace** → select the customer's own Sentinel workspace (same subscription).
5. Save. First logs appear within **30–60 minutes**.

**Verify (run from OneSource subscription after Lighthouse is active):**
```bash
az monitor diagnostic-settings list \
  --resource "/providers/microsoft.aadiam" \
  --resource-type "microsoft.aadiam/diagnosticSettings" \
  --subscription <CUSTOMER_SUB_ID> 2>/dev/null | \
  python3 -c "import sys,json; [print(d['name'], d['properties']['workspaceId']) for d in json.load(sys.stdin)['value']]"
```
Confirm the workspace ID shown belongs to *this* customer, not another tenant.

---

## Step 3 — Register the Workspace in TenantRegistry

The semantic model's `fnBuildUnion` function reads `TenantRegistry` to build the cross-workspace KQL `union`. Add one row per new tenant.

1. Open `SecurityOps/OS_SecurityOps.SemanticModel/definition/tables/TenantRegistry.tmdl`.
2. Find the `Rows = { ... }` list in the M partition source and add one record (M record syntax, **not** JSON):

   ```
   [   WorkspaceName       = "<SHORT>-Sentinel-0",
       ClientName          = "<Client Display Name>",
       WorkspaceId         = "<WORKSPACE_GUID>",
       WorkspaceResourceId = "/subscriptions/<SUB_ID>/resourceGroups/<RG>/providers/Microsoft.OperationalInsights/workspaces/<WS_NAME>",
       IsManagingWorkspace = false ]
   ```

   - **`ClientName` is the label shown in every chart legend/table** (e.g. `FW Walton`, `Cobalt Engineering`) — use the friendly client name, not the workspace name.
   - `IsManagingWorkspace = false` for every customer; only the central `OS-Sentinel-0` row is `true`.
   - `WorkspaceResourceId` must be the full ARM ID (casing of the RG matters — copy it exactly from the portal).

3. Save and commit. The deploy script will push the updated definition to Fabric on the next sync.

> **isfuzzy warning (core tables):** `fnBuildUnion` (used by Incidents, Alerts, IdentityThreats, ThreatIntelMatches, RulesFired, AzureActivityEvents) has **no `isfuzzy`**. If the new workspace is unreachable at refresh time (Lighthouse not yet active, workspace deleted) the **entire refresh fails**. Do not add a TenantRegistry row until Step 1 is confirmed working.
>
> **UEBA tables are tolerant:** `UEBABehavior` / `UEBAInsights` query each workspace independently wrapped in `try … otherwise null`, so a tenant **without UEBA enabled** (no `BehaviorAnalytics` table) is skipped silently — it will simply not appear on the UEBA / Tenant Risk pages. `isfuzzy` does **not** help here (it does not suppress a missing table referenced via `workspace("…")`), which is why the per-workspace `try` pattern is used.

---

## Step 3b — Enable UEBA (optional, for the UEBA / Tenant Risk pages)

UEBA metrics (scored events, risk score, anomaly reasons, per-tenant risk) only appear for a tenant that has **Entity Behavior Analytics enabled** in its own Sentinel workspace. Without it there is no `BehaviorAnalytics` table and the tenant is silently skipped (Step 3 note). This is optional — the core pages work without it.

To enable:
1. In the customer's **Microsoft Sentinel → Settings → Entity behavior analytics → Enable**, and select the identity data sources (SignIn/Audit logs — the same ones from Step 2).
2. Full value wants **Entra ID P2** licensing on the customer tenant.
3. UEBA needs **a few days** to build behavioral baselines before meaningful anomalies/scores appear.
4. Once `BehaviorAnalytics` starts populating, the tenant appears on the UEBA and Tenant Risk pages **automatically** on the next refresh — no model or report change needed.

> Requires settings-write access in the customer tenant. Lighthouse "Log Analytics Reader" (Step 1) is **not** enough to toggle this — it needs a higher role or the customer's own admin.

---

## Step 4 — Deploy and Refresh

```bash
cd ~/Developer/OS_Client_Reporting
git add SecurityOps/OS_SecurityOps.SemanticModel/definition/tables/TenantRegistry.tmdl
git commit -m "feat(SecurityOps): add <CLIENT_SHORT_NAME> tenant to TenantRegistry"
git push origin main

# Sync definition to Fabric
bash scripts/deploy.sh SecurityOps

# Trigger a manual dataset refresh (optional — next hourly refresh will also pick it up)
PT=$(az account get-access-token --resource "https://analysis.windows.net/powerbi/api" --query accessToken -o tsv)
WS=3ca25e44-c70a-4827-85dd-50064f492051
DS=3bfe45f6-f49c-4a61-86f3-fb2933451545
curl -s -X POST -H "Authorization: Bearer $PT" \
  "https://api.powerbi.com/v1.0/myorg/groups/$WS/datasets/$DS/refreshes"
```

---

## Step 5 — Verify Data

After the refresh completes (check **Data updated** timestamp in the Fabric workspace):

1. **Tenants Monitored** KPI on Security Posture page increments by 1.
2. **Incidents by Tenant** bar chart shows the new `ClientWorkspace` label.
3. **Incident Trend** and **Failed Sign-in Trend** charts show the new tenant in the legend.
4. **Top Targeted Accounts** table shows users from the new tenant's domain.
5. **UEBA / Tenant Risk pages** show the new tenant **only if UEBA was enabled** (Step 3b) and `BehaviorAnalytics` has started populating (allow a few days). If UEBA is off for this tenant, its absence here is expected, not a bug.

If any of those are missing, check:
- Lighthouse delegation is active (Step 1)
- Diagnostic setting is pointing to the **correct** workspace (Step 2)
- `TenantRegistry` row has the correct `WorkspaceId` (Step 3)
- No refresh errors in Fabric → Datasets → Refresh history

---

## Step 6 — Verify No Cross-Tenant Data Leakage

Before calling onboarding complete, confirm the new customer's logs are **not** flowing into any other workspace:

```bash
# List ALL Entra diagnostic settings for the new customer's Entra tenant
# (requires Owner or Contributor in that tenant)
az rest --method GET \
  --uri "https://management.azure.com/providers/microsoft.aadiam/diagnosticSettings?api-version=2017-04-01-preview" \
  --subscription <CUSTOMER_SUB_ID> | \
  python3 -c "import sys,json; [print(d['name'],'→',d['properties'].get('workspaceId','')) for d in json.load(sys.stdin).get('value',[])]"
```

Every entry must point to the customer's **own** Sentinel workspace. Delete any setting that points elsewhere.

> **Leak history (Oct 2026):** OneSource's Entra had a diagnostic setting streaming OneSource identity logs into FWW-Sentinel-0. It was deleted and the contaminated data purged. A residual of UEBA `BehaviorAnalytics` (which the first purge missed) was purged Oct 23. Note: OneSource MSP admins (`@onesource.tech`) signing **into** a client's own tenant is **legitimate** client activity and correctly appears in that client's workspace — distinguish it from directory contamination by `AADTenantId` / `ResourceTenantId` (contamination = both equal OneSource's `4b5e91ed`; legit guest access = both equal the client tenant).

---

## Live Geo Threat Map

The animated Norse-style attack map is a **standalone web page**, not a Power BI page. (It was briefly embedded in a "Geo Threat Map" report page, but Power BI reports can't reliably iframe external web content — and the "HTML Content" custom visual can't either, due to its nested sandbox — so that page was removed.)

| | |
|---|---|
| **Live URL** | `https://ossocmape62cb7.z21.web.core.windows.net/` |
| **Header-less variant** | append `#embed` → hides the internal title bar (for kiosk / iframe / signage) |
| **Source of truth** | `webassets/attack-map.html` (self-contained D3.js + inline world TopoJSON; no external calls) |
| **Hosting** | Azure Blob **static website** — storage account `ossocmape62cb7`, RG `OS-WebAssets`, sub **OS-DIRECT_AR_2026** (`42a6ebff-536a-4d2a-ba20-43225526bef8`) |

> Hosted in **OS-DIRECT_AR_2026**, not the "OneSource Azure" sub, because that sub has a deny-all Azure Policy blocking new storage accounts.

### Update the hosted map

```bash
az account set --subscription 42a6ebff-536a-4d2a-ba20-43225526bef8
KEY=$(az storage account keys list -g OS-WebAssets -n ossocmape62cb7 --query "[0].value" -o tsv)
az storage blob upload --account-name ossocmape62cb7 --account-key "$KEY" \
  --container-name '$web' --name index.html \
  --file ~/Developer/OS_Client_Reporting/webassets/attack-map.html \
  --content-type "text/html; charset=utf-8" --overwrite
```

> Use `--account-key` (not `--auth-mode login`) — `ar@onesource.tech` has no Storage Blob Data RBAC role on the account.

### Add a new client to the map

The map's client markers are **hardcoded** in `webassets/attack-map.html` (real static IPs / geocoded offices — this map is a curated visual, not driven by Sentinel data). To show a new client, edit the data objects near the top of the `<script>`:
`WORLD_MARKERS` (region) · `METRO_MARKERS` (city clusters) · `OFFICES` (per-office coords + static public IP + label) · and the `CLIENT_REGION` / `CLIENT_METROS` / `METRO_OFFICES` maps. Then re-upload with the command above. (The attack arcs in `ATTACKS[]` are illustrative sample data.)

---

## Quick-Reference Checklist

```
[ ] Collected workspace GUID, sub ID, RG, Entra tenant ID
[ ] Lighthouse template deployed in customer's subscription (Owner ran it)
[ ] Lighthouse delegation visible under Azure Lighthouse → Service providers
[ ] Entra diagnostic setting created: Sentinel-EntraID-<CLIENT>
[ ] Diagnostic setting confirmed pointing at customer's own workspace
[ ] TenantRegistry row added (correct M record schema), committed, pushed
[ ] scripts/deploy.sh SecurityOps ran — sync: Succeeded
[ ] Dataset refreshed (manual or waited for next hourly)
[ ] Tenants Monitored KPI incremented
[ ] No cross-tenant diagnostic settings found
[ ] (optional) UEBA enabled in client workspace → appears on UEBA / Tenant Risk pages after baselines build
[ ] (optional) Client added to the Live Geo Threat Map (webassets/attack-map.html) and re-uploaded
```

---

## Reference IDs (OneSource)

| Resource | Value |
|---|---|
| OneSource Azure tenant | `4b5e91ed-2885-49b3-9d58-a87089c51417` |
| OneSource Fabric workspace | `3ca25e44-c70a-4827-85dd-50064f492051` |
| OS_SecurityOps dataset | `3bfe45f6-f49c-4a61-86f3-fb2933451545` |
| OS_SecurityOps report | `34b44b66-bef7-4b68-ac8a-d7c2ff36add6` |
| Central Sentinel workspace (OS-Sentinel-0) | `046d4a05-36e4-4b43-a67a-309741cfc1c7` |
| OS-Sentinel-Readers group | `7a57368d-0b62-4b0c-b9c0-0050af871f41` |
| Service account (svc-pbi-sentinel) | `477d753e-9eb6-4c18-b525-c80e9e62a3c8` |
| SA password (Key Vault) | `os-claude-keys` → secret `svc-pbi-sentinel-password` |
| Lighthouse template | `SecurityOps/lighthouse/add-sentinel-readers.json` |
| Live Geo Threat Map URL | `https://ossocmape62cb7.z21.web.core.windows.net/` (append `#embed` for header-less) |
| Map hosting (storage / RG / sub) | `ossocmape62cb7` / `OS-WebAssets` / OS-DIRECT_AR_2026 (`42a6ebff-536a-4d2a-ba20-43225526bef8`) |
| Map source file | `webassets/attack-map.html` |
