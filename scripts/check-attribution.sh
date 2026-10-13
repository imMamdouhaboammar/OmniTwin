#!/usr/bin/env bash
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

echo "=== Checking SPDX Copyright Headers ==="
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MISSING=0

while IFS= read -r file; do
  # Skip git, node_modules, dist, .venv, proto generated files, json, and lockfiles
  case "$file" in
    *.git*|*node_modules*|*.venv*|*__pycache__*|*.db*|*.json|*.lock*|*.cff|*pb2*.py|*.html|*.yaml|*.yml)
      continue
      ;;
  esac

  if ! grep -q "SPDX-License-Identifier: Apache-2.0" "$file"; then
    echo "MISSING HEADER: $file"
    MISSING=$((MISSING + 1))
  fi
done < <(find "$REPO_ROOT" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.sh" -o -name "*.proto" -o -name "*.sql" \))

if [ "$MISSING" -eq 0 ]; then
  echo "All inspected source files have valid Apache-2.0 attribution headers."
  exit 0
else
  echo "Found $MISSING files missing SPDX headers."
  exit 1
fi
