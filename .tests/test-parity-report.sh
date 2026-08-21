#!/bin/sh
# Behavioral cases for parity-report:
# - shows help
# - reports conservative green, yellow, and red states

set -eu
test_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd -P)
# shellcheck source=/dev/null
. "$test_root/.tests/test-bootstrap"

parity_report_shows_help() {
  run_spell "parity-report" --help
  assert_success || return 1
  assert_output_contains "Usage: parity-report" || return 1
}

parity_report_preserves_evidence_rules() {
  run_spell "parity-report"
  assert_success || return 1
  assert_output_contains "parity — Wizardry capability audit" || return 1
  assert_output_contains "debian           GREEN  real outcome evidence passed" || return 1
  assert_output_contains "android_termux   YELLOW" || return 1
  assert_output_contains "windows_native   RED" || return 1
}

run_test_case "parity-report shows help" parity_report_shows_help
run_test_case "parity-report preserves evidence rules" parity_report_preserves_evidence_rules

finish_tests
