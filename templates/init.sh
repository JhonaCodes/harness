#!/usr/bin/env bash
set -u

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$1"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$1"; }

EXIT_CODE=0
run_step() {
  label="$1"; shift
  if "$@"; then ok "$label"; else fail "$label"; EXIT_CODE=1; fi
}

echo "-- Harness validation ({{workflow}}/{{profile}}) --"

{{required_file_checks}}

{{sdd_validation}}

echo "-- Project checks --"
{{verification_commands}}

if [ $EXIT_CODE -eq 0 ]; then ok "Harness environment ready."; else fail "Harness environment not ready."; fi
exit $EXIT_CODE
