"""Cross-platform test-plan interface and evidence-file helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from .core import AUDIT_DIMENSIONS, audit_status, capability_platforms, load_data


class TestRunner(Protocol):
    """Adapter boundary for real platform harnesses and manual lab sessions."""

    def run(self, plan_item: dict[str, Any]) -> dict[str, Any]: ...


def test_plan(
    platform_id: str | None = None,
    capabilities: list[dict[str, Any]] | None = None,
    platforms: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    capabilities = capabilities or load_data("capabilities.json")["capabilities"]
    platforms = platforms or load_data("platforms.json")["platforms"]
    selected = [item for item in platforms if platform_id in (None, item["id"])]
    plan: list[dict[str, Any]] = []
    for platform in selected:
        for capability in capabilities:
            as_host = platform["id"] in capability_platforms(capability)
            as_control_target = platform["id"] in capability.get("control_target_platforms", [])
            if not (as_host or as_control_target):
                continue
            gates = [
                item for item in platform.get("prerequisites", [])
                if item["kind"] == "manual_gate"
                and (
                    as_control_target
                    or set(item.get("applies_to", [])) & {"test_lab", "host_runtime"}
                )
            ]
            plan.append(
                {
                    "capability_id": capability["id"],
                    "platform_id": platform["id"],
                    "outcome": capability["outcome"],
                    "discovery": capability.get("discovery", capability.get("wizardry_menu", "")),
                    "installation": capability["installation"],
                    "checks": list(AUDIT_DIMENSIONS),
                    "test_role": "control_target" if as_control_target else "wizardry_host",
                    "manual_gates": gates,
                }
            )
    return plan


def evidence_record(
    capability_id: str,
    platform_id: str,
    checks: dict[str, bool],
    evidence_kind: str,
    evidence_refs: list[str],
    missing_prerequisites: list[str] | None = None,
    notes: str = "",
    capabilities: list[dict[str, Any]] | None = None,
    platforms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    capability_ids = {
        item["id"] for item in (capabilities or load_data("capabilities.json")["capabilities"])
    }
    platform_ids = {
        item["id"] for item in (platforms or load_data("platforms.json")["platforms"])
    }
    if capability_id not in capability_ids:
        raise ValueError(f"unknown capability: {capability_id}")
    if platform_id not in platform_ids:
        raise ValueError(f"unknown platform: {platform_id}")
    if evidence_kind not in {"automated_on_platform", "manual_on_device", "source_assertion", "simulated"}:
        raise ValueError(f"unknown evidence kind: {evidence_kind}")
    record: dict[str, Any] = {
        "capability_id": capability_id,
        "platform_id": platform_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "evidence_kind": evidence_kind,
        "evidence_refs": evidence_refs,
        "missing_prerequisites": missing_prerequisites or [],
        "notes": notes,
    }
    record.update({dimension: checks.get(dimension, False) for dimension in AUDIT_DIMENSIONS})
    record["derived_status"], record["status_reason"] = audit_status(record)
    return record
