#!/usr/bin/env bash
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=============================================="
echo " OmniTwin Full Release Verification Suite"
echo "=============================================="

echo ""
echo ">>> Step 1/4: Checking SPDX Attribution & Licensing Headers"
bash "$REPO_ROOT/scripts/check-attribution.sh"

echo ""
echo ">>> Step 2/4: Running Independent Pre-Publication Privacy & Security Audit"
bash "$REPO_ROOT/scripts/audit-publication.sh"

echo ""
echo ">>> Step 3/4: Running Python Core & Integration Tests (pytest)"
export PYTHONPATH="$REPO_ROOT/src:${PYTHONPATH:-}"
python3 -m pytest "$REPO_ROOT/tests" -v

echo ""
echo ">>> Step 4/4: Running Gateway Unit & Integration Tests (Bun)"
BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"
(cd "$REPO_ROOT/services/twin-gateway" && "$BUN_BIN" test)

echo ""
echo "=============================================="
echo " ALL RELEASE VERIFICATION GATES PASSED (100% GREEN)"
echo " Ready for GitHub Release & Publication"
echo "=============================================="
