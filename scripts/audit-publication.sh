#!/usr/bin/env bash
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

echo "=============================================="
echo " OmniTwin Independent Pre-Publication Auditor"
echo "=============================================="

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILURES=0

echo -n "[1] Checking for private character names & prototype artifacts... "
# Forbidden strings (case-insensitive where applicable)
if grep -riI --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="__pycache__" --exclude-dir="scripts" \
   "gehad" "$REPO_ROOT" > /dev/null 2>&1; then
    echo "FAILED!"
    echo "Found private character name 'gehad' in public tree:"
    grep -rnI --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="scripts" "gehad" "$REPO_ROOT"
    FAILURES=$((FAILURES + 1))
else
    echo "PASSED (Clean)"
fi

echo -n "[2] Checking for private source directory paths... "
if grep -riI --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="scripts" \
   "gehad-digital-twin-final" "$REPO_ROOT" > /dev/null 2>&1; then
    echo "FAILED!"
    echo "Found private source workspace path in repository:"
    grep -rnI --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="scripts" "gehad-digital-twin-final" "$REPO_ROOT"
    FAILURES=$((FAILURES + 1))
else
    echo "PASSED (Clean)"
fi

echo -n "[3] Checking for binary database files (.db, .sqlite)... "
FOUND_DBS=$(find "$REPO_ROOT" -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.db-journal" -o -name "*.db-wal" \) -not -path "*/.git/*" || true)
if [ -n "$FOUND_DBS" ]; then
    echo "FAILED!"
    echo "Found database files in repository tree: $FOUND_DBS"
    FAILURES=$((FAILURES + 1))
else
    echo "PASSED (Clean)"
fi

echo -n "[4] Checking for vendored Harlo source tree... "
if [ -d "$REPO_ROOT/Harlo-master" ] || find "$REPO_ROOT" -type d -name "harlo" | grep -q "harlo"; then
    echo "FAILED!"
    echo "Found vendored Harlo directory in public tree."
    FAILURES=$((FAILURES + 1))
else
    echo "PASSED (Excluded)"
fi

echo -n "[5] Checking for real private Egyptian phone numbers... "
if grep -rE --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="tests" \
   "(\+20\s*1[0125][0-9]{8}|01[0125][0-9]{8})" "$REPO_ROOT" > /dev/null 2>&1; then
    echo "FAILED!"
    echo "Found potential real Egyptian phone numbers in non-test files:"
    grep -rnE --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="tests" \
       "(\+20\s*1[0125][0-9]{8}|01[0125][0-9]{8})" "$REPO_ROOT"
    FAILURES=$((FAILURES + 1))
else
    echo "PASSED (Clean)"
fi

echo -n "[6] Checking for secret credentials and private keys... "
if grep -rE --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="tests" \
   "(AIzaSy[0-9A-Za-z_-]{33}|sk-or-v1-[0-9a-f]{64}|-----BEGIN [A-Z]+ PRIVATE KEY-----)" "$REPO_ROOT" > /dev/null 2>&1; then
    echo "FAILED!"
    echo "Found credentials or private keys in repository:"
    grep -rnE --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir=".venv" --exclude-dir="tests" \
       "(AIzaSy[0-9A-Za-z_-]{33}|sk-or-v1-[0-9a-f]{64}|-----BEGIN [A-Z]+ PRIVATE KEY-----)" "$REPO_ROOT"
    FAILURES=$((FAILURES + 1))
else
    echo "PASSED (Clean)"
fi

echo "----------------------------------------------"
if [ "$FAILURES" -eq 0 ]; then
    echo "ALL PRE-PUBLICATION AUDIT CHECKS PASSED (FAIL CLOSED GATES GREEN)."
    exit 0
else
    echo "AUDIT FAILED: $FAILURES critical check(s) violated. DO NOT PUBLISH."
    exit 1
fi
