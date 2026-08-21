#!/bin/sh
# Behavioral cases for parity-plan:
# - shows help
# - carries Android's manual gate into the plan
# - rejects unknown platforms

set -eu
test_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd -P)
# shellcheck source=/dev/null
. "$test_root/.tests/test-bootstrap"

parity_plan_shows_help() {
  run_spell "parity-plan" --help
  assert_success || return 1
  assert_output_contains "Usage: parity-plan" || return 1
}

parity_plan_carries_manual_gate() {
  run_spell "parity-plan" android_termux
  assert_success || return 1
  assert_output_contains "android_termux / terminal_system" || return 1
  assert_output_contains "manual gate: wifi_debugging_enabled" || return 1
}

parity_plan_rejects_unknown_platform() {
  run_spell "parity-plan" imaginary_os
  assert_failure || return 1
  assert_error_contains "unknown platform" || return 1
}

run_test_case "parity-plan shows help" parity_plan_shows_help
run_test_case "parity-plan carries manual gate" parity_plan_carries_manual_gate
run_test_case "parity-plan rejects unknown platform" parity_plan_rejects_unknown_platform

finish_tests
