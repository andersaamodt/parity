import unittest
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace

from parity.core import (
    ParityError, audit_status, build_matrix, load_data, route_job,
    validate_job_request, validate_profile, validate_receipt,
)
from parity.lab import evidence_record, test_plan as make_test_plan
from parity.cli import command_report


class AuditSemanticsTests(unittest.TestCase):
    def test_green_requires_all_dimensions_and_real_evidence(self):
        result = {
            "discoverable": True,
            "installed": True,
            "executable": True,
            "outcome_passed": True,
            "evidence_kind": "manual_on_device",
            "evidence_refs": ["artifact://run/1"],
        }
        self.assertEqual(audit_status(result)[0], "green")

    def test_simulation_never_turns_green(self):
        result = {
            "discoverable": True,
            "installed": True,
            "executable": True,
            "outcome_passed": True,
            "evidence_kind": "simulated",
            "evidence_refs": ["fixture://android"],
        }
        status, reason = audit_status(result)
        self.assertEqual(status, "yellow")
        self.assertIn("simulated", reason)

    def test_manual_prerequisite_is_yellow(self):
        status, reason = audit_status({"missing_prerequisites": ["wifi_debugging_enabled"]})
        self.assertEqual(status, "yellow")
        self.assertIn("wifi_debugging_enabled", reason)

    def test_unsupported_is_red(self):
        self.assertEqual(audit_status(None, platform_supported=False)[0], "red")

    def test_baseline_never_claims_unverified_green(self):
        rows = build_matrix()
        self.assertFalse(any(row["status"] == "green" for row in rows))

    def test_live_device_evidence_matches_recorded_platform_results(self):
        evidence = load_data("live_device_audit_2026-08-04.json")
        expected = {
            ("terminal_system", "android_termux"): "yellow",
            ("mobile_debug_control", "android_termux"): "yellow",
            ("terminal_system", "debian"): "green",
        }
        for result in evidence["results"]:
            status, reason = audit_status(result)
            key = (result["capability_id"], result["platform_id"])
            self.assertEqual(status, expected[key])
            self.assertEqual(result["derived_status"], status)
            self.assertEqual(result["status_reason"], reason)


class RoutingTests(unittest.TestCase):
    request = {
        "schema_version": 1,
        "job_id": "job-1",
        "capability_id": "mobile_debug_control",
        "intent": {"action": "open settings"},
        "authorization": {"granted_scopes": ["device.debug", "device.control"]},
        "target": {"platform": "android_termux", "preferred_transports": ["lan", "tor"]},
    }

    def test_android_gate_is_explicit(self):
        devices = [{"id": "phone", "platform": "android_termux", "transports": ["lan", "tor"]}]
        decision = route_job(self.request, devices)
        self.assertEqual(decision.status, "manual_gate")
        self.assertEqual(decision.missing_prerequisites, ("wifi_debugging_enabled",))

    def test_android_routes_after_gate(self):
        devices = [{
            "id": "phone", "platform": "android_termux", "transports": ["tor", "lan"],
            "satisfied_prerequisites": ["wifi_debugging_enabled"],
        }]
        decision = route_job(self.request, devices)
        self.assertEqual((decision.status, decision.transport), ("eligible", "lan"))

    def test_selection_is_stable_by_device_id(self):
        devices = [
            {"id": "z-phone", "platform": "android_termux", "transports": ["lan"], "satisfied_prerequisites": ["wifi_debugging_enabled"]},
            {"id": "a-phone", "platform": "android_termux", "transports": ["lan"], "satisfied_prerequisites": ["wifi_debugging_enabled"]},
        ]
        self.assertEqual(route_job(self.request, devices).device_id, "a-phone")

    def test_missing_scope_is_rejected(self):
        request = {**self.request, "authorization": {"granted_scopes": ["device.debug"]}}
        decision = route_job(request, [])
        self.assertEqual(decision.status, "rejected")
        self.assertIn("device.control", decision.reason)

    def test_ios_is_control_path_not_wizardry_host(self):
        request = {**self.request, "target": {"platform": "ios", "preferred_transports": ["official_debug"]}}
        devices = [{"id": "iphone", "platform": "ios", "transports": ["official_debug"]}]
        decision = route_job(request, devices)
        self.assertEqual(decision.status, "manual_gate")
        self.assertIn("official_debug_session", decision.missing_prerequisites)


class LabAndReceiptTests(unittest.TestCase):
    def test_android_plan_carries_manual_gate(self):
        plan = make_test_plan("android_termux")
        self.assertTrue(plan)
        mobile = next(item for item in plan if item["capability_id"] == "mobile_debug_control")
        terminal = next(item for item in plan if item["capability_id"] == "terminal_system")
        self.assertTrue(mobile["manual_gates"])
        self.assertFalse(terminal["manual_gates"])

    def test_ios_plan_exists_only_as_control_target(self):
        plan = make_test_plan("ios")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["test_role"], "control_target")
        self.assertTrue(plan[0]["manual_gates"])

    def test_debian_plan_remains_generic(self):
        plan = make_test_plan("debian")
        self.assertEqual(len(plan), 10)
        self.assertTrue(all(item["platform_id"] == "debian" for item in plan))
        self.assertTrue(all("platform_metadata" not in item for item in plan))

    def test_bad_job_request_rejected(self):
        with self.assertRaises(ParityError):
            validate_job_request({"schema_version": 1})

    def test_record_derives_yellow_for_simulated_fixture(self):
        record = evidence_record(
            "terminal_system", "android_termux",
            {"discoverable": True, "installed": True, "executable": True, "outcome_passed": True},
            "simulated", ["fixture://termux"],
        )
        self.assertEqual(record["derived_status"], "yellow")

    def test_receipt_validation(self):
        validate_receipt({
            "schema_version": 1,
            "receipt_id": "r-1",
            "job_id": "j-1",
            "device_id": "mac",
            "executor": "artificer",
            "transport": "local",
            "status": "succeeded",
            "started_at": "2026-08-04T00:00:00Z",
            "finished_at": "2026-08-04T00:00:01Z",
            "result": {},
        })

    def test_bad_receipt_rejected(self):
        with self.assertRaises(ParityError):
            validate_receipt({"schema_version": 1})

    def test_report_attributes_pi_hardware_to_debian_test_environment(self):
        output = StringIO()
        with redirect_stdout(output):
            command_report(SimpleNamespace(
                evidence="src/parity/data/live_device_audit_2026-08-04.json",
                json=False,
            ))
        report = output.getvalue()
        self.assertIn("Debian/Ubuntu", report)
        self.assertIn("tested environment: Raspberry Pi 5 Model B Rev 1.0", report)
        self.assertIn("aarch64", report)
        self.assertIn("authorized-install-and-test via SSH over Tor", report)

    def test_external_profile_drives_plan_matrix_and_routing(self):
        profile = {
            "schema_version": 1,
            "project": {"id": "example", "label": "Example"},
            "capabilities": [{
                "id": "message",
                "outcome": "Send a message",
                "discovery": "Conversation",
                "installation": "application",
                "executor": "external",
                "platforms": ["phone"],
                "authorization_scopes": ["app.test"],
            }],
            "platforms": [{
                "id": "phone",
                "label": "Phone",
                "supported": True,
                "status": "required",
                "transports": ["official_debug"],
                "prerequisites": [],
            }],
        }
        validate_profile(profile)
        plan = make_test_plan("phone", profile["capabilities"], profile["platforms"])
        self.assertEqual(plan[0]["discovery"], "Conversation")
        self.assertEqual(
            build_matrix(None, profile["capabilities"], profile["platforms"])[0]["status"],
            "yellow",
        )
        profile["platforms"].append({
            "id": "desktop", "label": "Desktop", "supported": True,
            "transports": ["local"], "prerequisites": [],
        })
        self.assertEqual(len(build_matrix(None, profile["capabilities"], profile["platforms"])), 1)
        request = {
            "schema_version": 1,
            "job_id": "one",
            "capability_id": "message",
            "intent": {},
            "authorization": {"granted_scopes": ["app.test"]},
            "target": {"platform": "phone", "preferred_transports": ["official_debug"]},
        }
        device = {"id": "phone-1", "platform": "phone", "transports": ["official_debug"]}
        self.assertEqual(
            route_job(request, [device], profile["capabilities"], profile["platforms"]).status,
            "eligible",
        )

    def test_external_profile_rejects_unknown_platform(self):
        with self.assertRaises(ParityError):
            validate_profile({
                "schema_version": 1,
                "project": {"id": "bad", "label": "Bad"},
                "capabilities": [{
                    "id": "x",
                    "outcome": "x",
                    "installation": "x",
                    "executor": "external",
                    "platforms": ["missing"],
                }],
                "platforms": [],
            })


if __name__ == "__main__":
    unittest.main()
