#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/aura_app"
exec swift run -c release Aura
