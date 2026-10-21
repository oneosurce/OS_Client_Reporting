# OS_SecurityOps — Add a New Customer Tenant

Use this playbook every time a new client is onboarded to the SOC dashboard.  
Estimated time: 30–60 min (plus 1–2 h for first data ingestion).

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
2. Find the M partition source and add a row:

   ```
   { "ClientWorkspace" = "<LABEL>", "WorkspaceId" = "<WORKSPACE_GUID>", "SubscriptionId" = "<SUB_ID>", "ResourceGroup" = "<RG>" }
   ```

   `<LABEL>` is the `ClientWorkspace` value that will appear in every chart (e.g. `FWW-Sentinel-0`). Keep the format `<SHORT_NAME>-Sentinel-0`.

3. Save and commit. The deploy script will push the updated definition to Fabric on the next sync.

> **isfuzzy warning:** The KQL union has **no `isfuzzy`**. If the new workspace is unreachable at refresh time (Lighthouse not yet active, workspace deleted, etc.) the **entire refresh will fail**. Do not add a row to TenantRegistry until Step 1 is confirmed working.

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

---

## Quick-Reference Checklist

```
[ ] Collected workspace GUID, sub ID, RG, Entra tenant ID
[ ] Lighthouse template deployed in customer's subscription (Owner ran it)
[ ] Lighthouse delegation visible under Azure Lighthouse → Service providers
[ ] Entra diagnostic setting created: Sentinel-EntraID-<CLIENT>
[ ] Diagnostic setting confirmed pointing at customer's own workspace
[ ] TenantRegistry row added, committed, pushed
[ ] scripts/deploy.sh SecurityOps ran — sync: Succeeded
[ ] Dataset refreshed (manual or waited for next hourly)
[ ] Tenants Monitored KPI incremented
[ ] No cross-tenant diagnostic settings found
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
