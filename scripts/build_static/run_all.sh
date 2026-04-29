#!/usr/bin/env bash
# Run all build-time data pipeline scripts in order.
# Output goes to web/public/data/ and web/src/config/.
set -euo pipefail

cd "$(dirname "$0")/../.."

PY="${PYTHON:-python3}"

echo "==> 06_copy_configs"
"$PY" scripts/build_static/06_copy_configs.py

echo "==> 02_build_layer_geojsons"
"$PY" scripts/build_static/02_build_layer_geojsons.py

echo "==> 03_build_state_summary"
"$PY" scripts/build_static/03_build_state_summary.py

echo "==> done"
