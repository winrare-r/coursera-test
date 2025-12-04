#!/usr/bin/env bash
set -euo pipefail

python -m PyInstaller --clean --noconfirm app.spec
