#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <bucket-name>"
  exit 1
fi

bucket="$1"
wrangler_r2_put() {
  local object_key="$1"
  local file_path="$2"
  npx wrangler r2 object put "${object_key}" --file "${file_path}" --remote >/dev/null
}

upload_tree() {
  local root="$1"
  if [[ ! -d "$root" ]]; then
    return
  fi

  while IFS= read -r file; do
    echo "Uploading ${file}"
    wrangler_r2_put "${bucket}/${file}" "${file}"
  done < <(find "$root" -type f | sort)
}

upload_tree "artifacts/web"
while IFS= read -r file; do
  echo "Uploading ${file}"
  wrangler_r2_put "${bucket}/${file}" "${file}"
done < <(
  find outputs/section1/results/final -maxdepth 1 -type f \
    \( -name 'dashboard_market_overview.csv' \
    -o -name 'planning_area_hdb_map_2019.geojson' \
    -o -name 'budget_affordability.csv' \
    -o -name 'budget_affordability_metrics.csv' \
    -o -name 'budget_affordability_legend.csv' \) | sort
)
upload_tree "outputs/section2/charts"
upload_tree "outputs/section2/results"
upload_tree "outputs/section3/charts"

echo "Web asset upload complete."
