#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <bucket-name>"
  exit 1
fi

bucket="$1"

upload_tree() {
  local root="$1"
  if [[ ! -d "$root" ]]; then
    return
  fi

  while IFS= read -r file; do
    echo "Uploading ${file}"
    npx wrangler r2 object put "${bucket}/${file}" --file "${file}" --remote >/dev/null
  done < <(find "$root" -type f | sort)
}

upload_tree "artifacts/web"
upload_tree "outputs/section2/charts"
upload_tree "outputs/section2/results"
upload_tree "outputs/section3/charts"

echo "Web asset upload complete."
