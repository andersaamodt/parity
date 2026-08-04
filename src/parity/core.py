"""Deterministic audit semantics and remote routing.

This module deliberately has no transport implementation and performs no OS input.
Upstream sources provide structured intent, and Artificer owns automation. The
parity layer only decides whether an authorized job can be routed and what
evidence is sufficient for an audit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterable


AUDIT_DIMENSIONS = ("discoverable", "installed", "executable", "outcome_passed")
TRANSPORT_ORDER = ("local", "lan", "tor", "official_debug")


class ParityError(ValueError):
    """An invalid manifest, request, or routing decision."""


@dataclass(frozen=True)
class RouteDecision:
    status: str
    device_id: str | None
    transport: str | None
    executor: str | None
    missing_prerequisites: tuple[str, ...] = ()
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "device_id": self.device_id,
            "transport": self.transport,
            "executor": self.executor,
            "missing_prerequisites": list(self.missing_prerequisites),
            "reason": self.reason,
        }


def load_data(name: str) -> dict[str, Any]:
    path = files("parity").joinpath("data", name)
    return json.loads(path.read_text(encoding="utf-8"))


def load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def index_by_id(items: Iterable[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise ParityError(f"{label} entry has no id")
        if item_id in indexed:
            raise ParityError(f"duplicate {label} id: {item_id}")
        indexed[item_id] = item
    return indexed


def audit_status(result: dict[str, Any] | None, platform_supported: bool = True) -> tuple[str, str]:
    """Return traffic-light status and a precise explanation.

    A green result requires real, passing evidence for all four user-outcome
    dimensions. Simulated evidence is useful for core tests but cannot turn an
    audit green. Red is reserved for an unavailable host/outcome. Everything
    incomplete remains yellow with its missing prerequisite or evidence.
    """
    if not platform_supported:
        return "red", "unavailable on this platform"
    if result is None:
        return "yellow", "missing outcome evidence"
    if result.get("availability") == "unavailable":
        return "red", result.get("reason", "unavailable on this platform")
    prerequisites = result.get("missing_prerequisites", [])
    if prerequisites:
        return "yellow", "prerequisite: " + ", ".join(sorted(prerequisites))
    evidence_kind = result.get("evidence_kind")
    missing = [dimension for dimension in AUDIT_DIMENSIONS if result.get(dimension) is not True]
    if missing:
        return "yellow", "missing passing evidence: " + ", ".join(missing)
    if evidence_kind not in {"automated_on_platform", "manual_on_device"}:
        return "yellow", "real platform evidence required (source assertions and simulated fixtures do not pass)"
    if not result.get("evidence_refs"):
        return "yellow", "evidence reference required"
    return "green", "discoverable, installed, executable, and outcome evidence passed"


def _candidate_transport(device: dict[str, Any], preferred: list[str]) -> str | None:
    supported = set(device.get("transports", []))
    ordered = preferred or list(TRANSPORT_ORDER)
    return next((transport for transport in ordered if transport in supported), None)


def route_job(
    request: dict[str, Any],
    devices: list[dict[str, Any]],
    capabilities: list[dict[str, Any]] | None = None,
    platforms: list[dict[str, Any]] | None = None,
) -> RouteDecision:
    """Select the first eligible device using stable id ordering.

    Selection is deterministic and side-effect free. A matching device with an
    unmet manual gate produces ``manual_gate`` rather than silently passing or
    being treated as unreachable.
    """
    capabilities = capabilities or load_data("capabilities.json")["capabilities"]
    platforms = platforms or load_data("platforms.json")["platforms"]
    capability_map = index_by_id(capabilities, "capability")
    platform_map = index_by_id(platforms, "platform")

    validate_job_request(request)
    capability_id = request.get("capability_id")
    if capability_id not in capability_map:
        return RouteDecision("rejected", None, None, None, reason=f"unknown capability: {capability_id}")
    capability = capability_map[capability_id]
    granted = set(request.get("authorization", {}).get("granted_scopes", []))
    required = set(capability.get("authorization_scopes", []))
    missing_scopes = sorted(required - granted)
    if missing_scopes:
        return RouteDecision(
            "rejected", None, None, capability["executor"], reason="missing authorization scopes: " + ", ".join(missing_scopes)
        )

    selector = request.get("target", {})
    requested_device = selector.get("device_id")
    requested_platform = selector.get("platform")
    preferred = selector.get("preferred_transports", [])
    candidates: list[tuple[dict[str, Any], str, tuple[str, ...]]] = []

    for device in sorted(devices, key=lambda item: item.get("id", "")):
        device_id = device.get("id")
        platform_id = device.get("platform")
        if not device_id or platform_id not in platform_map:
            continue
        if requested_device and device_id != requested_device:
            continue
        if requested_platform and platform_id != requested_platform:
            continue
        platform = platform_map[platform_id]
        as_control_target = platform_id in capability.get("control_target_platforms", [])
        as_host = platform_id in capability.get("host_platforms", []) and platform.get("wizardry_host")
        if not (as_host or as_control_target):
            continue
        transport = _candidate_transport(device, preferred)
        if transport is None:
            continue
        required_prereqs = {item["id"] for item in platform.get("prerequisites", [])}
        required_prereqs.update(device.get("required_prerequisites", []))
        satisfied = set(device.get("satisfied_prerequisites", []))
        missing = tuple(sorted(required_prereqs - satisfied))
        candidates.append((device, transport, missing))

    if not candidates:
        return RouteDecision("ineligible", None, None, capability["executor"], reason="no eligible target and transport")
    device, transport, missing = candidates[0]
    if missing:
        return RouteDecision(
            "manual_gate", device["id"], transport, capability["executor"], missing, "manual prerequisite must be satisfied"
        )
    return RouteDecision("eligible", device["id"], transport, capability["executor"], reason="authorized eligible route")


def validate_job_request(request: dict[str, Any]) -> None:
    required = {"schema_version", "job_id", "capability_id", "intent", "authorization", "target"}
    missing = sorted(required - request.keys())
    if missing:
        raise ParityError("job request missing fields: " + ", ".join(missing))
    if request["schema_version"] != 1:
        raise ParityError("unsupported job request schema_version")
    if not isinstance(request["intent"], dict) or not isinstance(request["target"], dict):
        raise ParityError("job request intent and target must be objects")
    scopes = request["authorization"].get("granted_scopes") if isinstance(request["authorization"], dict) else None
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
        raise ParityError("job request granted_scopes must be a list of strings")
    preferred = request["target"].get("preferred_transports", [])
    if not isinstance(preferred, list) or any(item not in TRANSPORT_ORDER for item in preferred):
        raise ParityError("job request contains an invalid preferred transport")


def build_matrix(
    evidence: dict[str, Any] | None = None,
    capabilities: list[dict[str, Any]] | None = None,
    platforms: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    capabilities = capabilities or load_data("capabilities.json")["capabilities"]
    platforms = platforms or load_data("platforms.json")["platforms"]
    evidence_results = evidence.get("results", []) if evidence else []
    evidence_map = {(item["capability_id"], item["platform_id"]): item for item in evidence_results}
    rows: list[dict[str, str]] = []
    for capability in capabilities:
        for platform in platforms:
            platform_id = platform["id"]
            supported = platform_id in capability.get("host_platforms", []) and platform.get("wizardry_host", False)
            result = evidence_map.get((capability["id"], platform_id))
            status, reason = audit_status(result, supported)
            rows.append(
                {
                    "capability_id": capability["id"],
                    "platform_id": platform_id,
                    "status": status,
                    "reason": reason,
                }
            )
    return rows


def validate_receipt(receipt: dict[str, Any]) -> None:
    required = {
        "schema_version", "receipt_id", "job_id", "device_id", "executor",
        "transport", "status", "started_at", "finished_at", "result",
    }
    missing = sorted(required - receipt.keys())
    if missing:
        raise ParityError("receipt missing fields: " + ", ".join(missing))
    if receipt["schema_version"] != 1:
        raise ParityError("unsupported receipt schema_version")
    if receipt["status"] not in {"succeeded", "failed", "rejected", "manual_gate"}:
        raise ParityError("invalid receipt status")
    if receipt["executor"] not in {"artificer", "external"}:
        raise ParityError("invalid receipt executor")
    if receipt["transport"] not in TRANSPORT_ORDER:
        raise ParityError("invalid receipt transport")
