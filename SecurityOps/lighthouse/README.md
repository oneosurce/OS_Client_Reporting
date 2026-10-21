# SecurityOps — Lighthouse delegation for the Power BI refresh identity

`OS_SecurityOps` refreshes by querying every managed Sentinel workspace listed in
the model's `TenantRegistry` and unioning the results. The unattended refresh runs
as the service account **`svc-pbi-sentinel@onesource.tech`**, which is a member of
the OneSource security group **`OS-Sentinel-Readers`** (`7a57368d-0b62-4b0c-b9c0-0050af871f41`).

For the refresh to read a **member** tenant's workspace (a different Azure AD tenant,
reached via Azure Lighthouse), that group must be **delegated Log Analytics Reader**
on the member subscription. The central OneSource workspace (`OS-Sentinel-0`) is
same-tenant and is granted directly — no Lighthouse needed there.

## Deploy per member tenant

`add-sentinel-readers.json` is an **additive** subscription-scope deployment. It does
not modify or remove any existing Lighthouse delegation.

**Who can run it:** an identity with **Owner** on the target (customer) subscription,
signed in to the **customer tenant**. OneSource's existing Lighthouse access
(Contributor) is *not* sufficient to create a new delegation — that is by design.

```bash
# Sign in to the CUSTOMER tenant as an Owner of the target subscription, e.g.:
az login --tenant <customer-tenant-id>
az account set --subscription <customer-subscription-id>

az deployment sub create \
  --name add-sentinel-readers \
  --location eastus \
  --template-file add-sentinel-readers.json
```

Propagation takes a few minutes. Verify from the OneSource side:

```bash
az monitor log-analytics query \
  --workspace <member-workspace-guid> \
  --analytics-query "SecurityAlert | take 1" -o table
```

## Known member tenants

| Workspace | Customer tenant | Subscription | Status |
|---|---|---|---|
| `FWW-Sentinel-0` | `84f8cb72-1c64-4479-a313-3dfd99bb217f` | `dbb769af-50cb-4d0a-bf54-ca43e2b26539` | delegation **pending** (deploy this template) |

Add a row here whenever a new client workspace is added to `TenantRegistry`.
