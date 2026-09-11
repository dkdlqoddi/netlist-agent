#!/usr/bin/env bash
# SessionStart hook: print MANDATE.md to stdout so it is injected into session context.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat "$DIR/../MANDATE.md"
