#!/bin/bash
# ReplayPack E2E Test Script for macOS/Linux
# Run this from the repo root: ./test_e2e.sh

set -e  # Exit on error

echo "=========================================="
echo "ReplayPack E2E Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "[1/7] Checking prerequisites..."
which python3 || { echo -e "${RED}ERROR: python3 not found${NC}"; exit 1; }
python3 --version
echo ""

# Create clean venv
echo "[2/7] Setting up clean environment..."
rm -rf .venv_test
python3 -m venv .venv_test
source .venv_test/bin/activate
pip install -q --upgrade pip
pip install -q -e .
pip install -q requests  # For session demo
echo -e "${GREEN}✓ Environment ready${NC}"
echo ""

# Verify CLI
echo "[3/7] Verifying CLI installation..."
which replaypack
replaypack --help | head -5
echo -e "${GREEN}✓ CLI installed${NC}"
echo ""

# Test record
echo "[4/7] Testing: replaypack record..."
rm -rf runs
mkdir runs
replaypack record -- python3 examples/session_demo.py
echo ""

# Verify artifact
echo "[4.5/7] Verifying artifact..."
python3 << 'PY'
import json, glob, sys
files = glob.glob("runs/*.rpk")
if not files:
    print("ERROR: No .rpk files found")
    sys.exit(1)

with open(files[0]) as f:
    data = json.load(f)

steps = data.get("recording", {}).get("steps", [])
print(f"Steps captured: {len(steps)}")
for s in steps:
    print(f"  - {s.get('function')}")

if len(steps) < 3:
    print("WARNING: Expected at least 3 steps (2 tools + 1 HTTP)")
else:
    print("✓ Step count looks good")
PY
echo ""

# Test replay
echo "[5/7] Testing: replaypack replay..."
LATEST=$(ls -t runs/*.rpk | head -1)
replaypack replay "$LATEST"
echo ""

# Test diff
echo "[6/7] Testing: replaypack diff..."
# Create a second run for comparison
sleep 1
replaypack record -- python3 examples/session_demo.py > /dev/null 2>&1

RUN_A=$(ls -t runs/*.rpk | sed -n '2p')
RUN_B=$(ls -t runs/*.rpk | sed -n '1p')

echo "Comparing:"
echo "  A: $(basename $RUN_A)"
echo "  B: $(basename $RUN_B)"
echo ""
echo "Diff output:"
replaypack diff "$RUN_A" "$RUN_B" --first-divergence || true
echo ""

# Test bundle
echo "[7/7] Testing: replaypack bundle..."
rm -f test.bundle
replaypack bundle "$RUN_B" --redact default --out test.bundle
ls -lh test.bundle

echo ""
echo "=========================================="
echo -e "${GREEN}E2E Test Complete!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Artifact created: runs/*.rpk"
echo "  - Bundle created: test.bundle"
echo ""
echo "To cleanup:"
echo "  rm -rf .venv_test runs test.bundle"
