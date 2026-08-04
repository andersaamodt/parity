from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from .core import build_matrix, load_data, load_json, route_job, validate_receipt
from .lab import evidence_record, test_plan


SYMBOLS = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def command_report(args: argparse.Namespace) -> int:
    evidence = load_json(args.evidence) if args.evidence else load_data("baseline_evidence.json")
    rows = build_matrix(evidence)
    platforms = load_data("platforms.json")["platforms"]
    capabilities = load_data("capabilities.json")["capabilities"]
    environments = evidence.get("test_environments", [])
    if args.json:
        _print_json({"schema_version": 1, "platforms": platforms, "test_environments": environments, "rows": rows})
        return 0

    print("parity — Wizardry capability audit")
    print("Green requires menu discovery + installation + execution + passing real outcome evidence.")
    print()
    for platform in platforms:
        platform_rows = [row for row in rows if row["platform_id"] == platform["id"]]
        counts = Counter(row["status"] for row in platform_rows)
        print(
            f"{platform['label']:<22} "
            f"{SYMBOLS['green']} {counts['green']:>2}  "
            f"{SYMBOLS['yellow']} {counts['yellow']:>2}  "
            f"{SYMBOLS['red']} {counts['red']:>2}  "
            f"({platform['official_status']})"
        )
        if platform.get("derived_from"):
            architectures = ", ".join(platform.get("target_architectures", []))
            print(
                f"  derived from {platform['derived_from']}; "
                f"hardware {platform.get('hardware_family', 'unspecified')}; "
                f"architectures {architectures or 'unspecified'}"
            )
        for environment in (item for item in environments if item.get("platform_id") == platform["id"]):
            access_mode = environment.get("access_mode", "unspecified").replace("_", "-")
            print(
                "  tested environment: "
                f"{environment.get('hardware', 'unknown hardware')}; "
                f"{environment.get('operating_system', platform['label'])} "
                f"{environment.get('release', '')}; "
                f"{environment.get('architecture', 'unknown architecture')}; "
                f"{access_mode} via {environment.get('access', 'unspecified access')}"
            )
    print()
    print("Outcome matrix")
    for capability in capabilities:
        print(f"\n{capability['id']}: {capability['outcome']}")
        for row in (item for item in rows if item["capability_id"] == capability["id"]):
            print(f"  {row['platform_id']:<16} {SYMBOLS[row['status']]:<6} {row['reason']}")
    return 0


def command_route(args: argparse.Namespace) -> int:
    request = load_json(args.request)
    devices_doc = load_json(args.devices)
    devices = devices_doc.get("devices", devices_doc) if isinstance(devices_doc, dict) else devices_doc
    decision = route_job(request, devices)
    _print_json(decision.as_dict())
    return 0 if decision.status in {"eligible", "manual_gate"} else 2


def command_plan(args: argparse.Namespace) -> int:
    plan = test_plan(args.platform)
    if args.json:
        _print_json({"schema_version": 1, "tests": plan})
        return 0
    for item in plan:
        print(f"{item['platform_id']} / {item['capability_id']}")
        print(f"  outcome: {item['outcome']}")
        print(f"  discover: {item['menu_path']}")
        for gate in item["manual_gates"]:
            print(f"  manual gate: {gate['description']}")
    return 0


def command_validate_receipt(args: argparse.Namespace) -> int:
    validate_receipt(load_json(args.receipt))
    print("valid receipt")
    return 0


def command_record(args: argparse.Namespace) -> int:
    checks = {name: name in args.check for name in ("discoverable", "installed", "executable", "outcome_passed")}
    record = evidence_record(
        args.capability,
        args.platform,
        checks,
        args.kind,
        args.evidence_ref,
        args.missing_prerequisite,
        args.notes,
    )
    _print_json(record)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parity", description="Wizardry parity audit and neutral remote routing")
    subparsers = parser.add_subparsers(dest="command", required=True)

    report = subparsers.add_parser("report", help="show the evidence-backed outcome matrix")
    report.add_argument("--evidence", type=Path, help="external evidence JSON (runtime state should stay outside this repo)")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=command_report)

    route = subparsers.add_parser("route", help="deterministically select an authorized target")
    route.add_argument("--request", type=Path, required=True)
    route.add_argument("--devices", type=Path, required=True)
    route.set_defaults(func=command_route)

    plan = subparsers.add_parser("plan", help="emit the shared cross-platform test plan")
    plan.add_argument("--platform")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=command_plan)

    record = subparsers.add_parser("record", help="emit one evidence record without storing repository state")
    record.add_argument("--capability", required=True)
    record.add_argument("--platform", required=True)
    record.add_argument(
        "--check", action="append", default=[],
        choices=["discoverable", "installed", "executable", "outcome_passed"],
        help="repeat for each passing check",
    )
    record.add_argument(
        "--kind", required=True,
        choices=["automated_on_platform", "manual_on_device", "source_assertion", "simulated"],
    )
    record.add_argument("--evidence-ref", action="append", default=[])
    record.add_argument("--missing-prerequisite", action="append", default=[])
    record.add_argument("--notes", default="")
    record.set_defaults(func=command_record)

    receipt = subparsers.add_parser("validate-receipt", help="validate deterministic receipt fields")
    receipt.add_argument("receipt", type=Path)
    receipt.set_defaults(func=command_validate_receipt)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"parity: {error}", file=sys.stderr)
        return 2
