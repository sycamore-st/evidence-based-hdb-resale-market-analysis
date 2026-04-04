#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <bucket-name>"
  exit 1
fi

bucket="$1"

upload_file() {
  local file="$1"
  echo "Uploading ${file}"
  npx wrangler r2 object put "${bucket}/${file}" --file "${file}" --remote >/dev/null
}

while IFS= read -r file; do
  upload_file "$file"
done < <(
  find outputs/section1/results/final -maxdepth 1 -type f \
    \( -name 'dashboard_market_overview.csv' \
    -o -name 'planning_area_hdb_map_2019.geojson' \
    -o -name 'budget_affordability.csv' \
    -o -name 'budget_affordability_metrics.csv' \
    -o -name 'budget_affordability_legend.csv' \) | sort
)

while IFS= read -r file; do
  upload_file "$file"
done < <(
  find artifacts/web/overview -maxdepth 1 -type f | sort
)

while IFS= read -r file; do
  upload_file "$file"
done < <(
  find artifacts/web/policy -maxdepth 1 -type f | sort
)

while IFS= read -r file; do
  upload_file "$file"
done < <(
  find artifacts/web/model -maxdepth 1 -type f | sort
)

while IFS= read -r file; do
  upload_file "$file"
done < <(
  find artifacts/web/overview/dashboard3 -type f | sort
)

echo "Section 1 upload complete."
