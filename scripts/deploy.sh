#!/bin/bash
# Sync the OneSource Reporting workspace from this repo (Fabric Git integration),
# then optionally refresh one client's semantic model and export a preview PNG.
#
#   scripts/deploy.sh <ClientFolder>          e.g. scripts/deploy.sh Sophia
#   scripts/deploy.sh <ClientFolder> refresh  also triggers a dataset refresh
#
# Item names in the workspace are assumed to be OS_<ClientFolder>_Tickets.
set -uo pipefail

WS=3ca25e44-c70a-4827-85dd-50064f492051
FB=https://api.fabric.microsoft.com/v1
PB=https://api.powerbi.com/v1.0/myorg
OUT="$(cd "$(dirname "$0")" && pwd)/out"
mkdir -p "$OUT"

CLIENT="${1:?usage: deploy.sh <ClientFolder> [refresh]}"
DO_REFRESH="${2:-no}"
ITEM="OS_${CLIENT}_Tickets"

FT=$(az account get-access-token --resource "https://api.fabric.microsoft.com" --query accessToken -o tsv)
PT=$(az account get-access-token --resource "https://analysis.windows.net/powerbi/api" --query accessToken -o tsv)

echo "### git sync"
st=$(curl -s -H "Authorization: Bearer $FT" "$FB/workspaces/$WS/git/status")
RC=$(echo "$st" | python3 -c "import sys,json;print(json.load(sys.stdin)['remoteCommitHash'])")
WH=$(echo "$st" | python3 -c "import sys,json;print(json.load(sys.stdin).get('workspaceHead') or '')")
echo "remote=$RC head=$WH"
if [ "$RC" != "$WH" ]; then
  body=$(python3 -c "import json;print(json.dumps({'remoteCommitHash':'$RC','workspaceHead':('$WH' or None),'conflictResolution':{'conflictResolutionType':'Workspace','conflictResolutionPolicy':'PreferRemote'},'options':{'allowOverrideItems':True}}))")
  op=$(curl -s -D - -o /dev/null -X POST -H "Authorization: Bearer $FT" -H "Content-Type: application/json" -d "$body" "$FB/workspaces/$WS/git/updateFromGit" | awk 'tolower($1)=="x-ms-operation-id:"{print $2}' | tr -d '\r')
  for i in $(seq 1 40); do sleep 6
    s=$(curl -s -H "Authorization: Bearer $FT" "$FB/operations/$op" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status'))" 2>/dev/null || echo '')
    [ -n "$s" ] && echo "  sync: $s"
    [ "$s" = "Succeeded" ] && break
    [ "$s" = "Failed" ] && { curl -s -H "Authorization: Bearer $FT" "$FB/operations/$op" | python3 -m json.tool; exit 1; }
  done
else
  echo "  already in sync"
fi

echo "### resolve items for $ITEM"
items=$(curl -s -H "Authorization: Bearer $FT" "$FB/workspaces/$WS/items")
DS=$(echo "$items" | python3 -c "import sys,json;print(next((i['id'] for i in json.load(sys.stdin)['value'] if i['type']=='SemanticModel' and i['displayName']=='$ITEM'),''))")
RP=$(echo "$items" | python3 -c "import sys,json;print(next((i['id'] for i in json.load(sys.stdin)['value'] if i['type']=='Report' and i['displayName']=='$ITEM'),''))")
echo "  dataset=$DS report=$RP"
[ -z "$RP" ] && { echo "  report not found"; exit 1; }

if [ "$DO_REFRESH" = "refresh" ] && [ -n "$DS" ]; then
  echo "### refresh"
  curl -s -X POST -H "Authorization: Bearer $PT" -H "Content-Type: application/json" -d '{"notifyOption":"NoNotification"}' "$PB/groups/$WS/datasets/$DS/refreshes" -o /dev/null
  for i in $(seq 1 40); do sleep 6
    s=$(curl -s -H "Authorization: Bearer $PT" "$PB/groups/$WS/datasets/$DS/refreshes?\$top=1" | python3 -c "import sys,json;print(json.load(sys.stdin)['value'][0]['status'])")
    echo "  refresh: $s"; [ "$s" != "Unknown" ] && [ "$s" != "InProgress" ] && break; done
fi

echo "### export"
EID=$(curl -s -X POST -H "Authorization: Bearer $PT" -H "Content-Type: application/json" -d '{"format":"PDF"}' "$PB/groups/$WS/reports/$RP/ExportTo" | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
for i in $(seq 1 40); do sleep 6
  s=$(curl -s -H "Authorization: Bearer $PT" "$PB/groups/$WS/reports/$RP/exports/$EID" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  echo "  export: $s"; [ "$s" = "Succeeded" ] && break; [ "$s" = "Failed" ] && exit 1; done
curl -s -H "Authorization: Bearer $PT" -o "$OUT/$CLIENT.pdf" "$PB/groups/$WS/reports/$RP/exports/$EID/file"
sips -s format png --resampleWidth 1600 "$OUT/$CLIENT.pdf" --out "$OUT/$CLIENT.png" >/dev/null 2>&1
echo "OK -> $OUT/$CLIENT.png"
