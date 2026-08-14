"""Transport boundaries.

Parity remains side-effect free during routing. The one concrete transport here
is the deliberately small local actuator adapter used after an eligible route
has already been selected.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Protocol

from .core import ParityError, RouteDecision, validate_receipt


class RemoteTransport(Protocol):
    name: str

    def available(self, device: dict[str, Any]) -> bool: ...

    def submit(self, job: dict[str, Any], device: dict[str, Any]) -> dict[str, Any]: ...


PLATFORM_TARGET_KIND = {
    "macos": "desktop",
    "linux": "desktop",
    "windows": "desktop",
    "debian": "desktop",
    "nixos": "desktop",
    "arch": "desktop",
    "windows_wsl": "desktop",
    "windows_native": "desktop",
    "android": "android",
    "android_termux": "android",
    "ios": "ios",
}


def submit_local_actuator(
    job: dict[str, Any],
    decision: RouteDecision,
    device: dict[str, Any],
    command: str = "actuator",
    timeout_seconds: int = 130,
) -> dict[str, Any]:
    """Execute one eligible actuator job and return a Parity receipt.

    The job intent must already be a named actuator action with an arguments
    object. Parity does not reinterpret semantic intent or accept a shell
    command string; ``command`` is one executable path/name.
    """
    if decision.status != "eligible" or decision.executor != "actuator":
        raise ParityError("local actuator submission requires an eligible actuator route")
    if not isinstance(command, str) or not command or any(character.isspace() for character in command):
        raise ParityError("actuator command must be one executable path or name")
    platform_id = device.get("platform")
    target_kind = PLATFORM_TARGET_KIND.get(platform_id)
    if target_kind is None:
        raise ParityError(f"actuator has no target mapping for platform: {platform_id}")
    intent = job.get("intent", {})
    action = intent.get("action")
    arguments = intent.get("arguments", {})
    if not isinstance(action, str) or not action or not isinstance(arguments, dict):
        raise ParityError("actuator intent requires action and arguments")
    target: dict[str, Any] = {"kind": target_kind}
    if target_kind in {"android", "ios"}:
        target["device_id"] = device.get("actuator_device_id", decision.device_id)
    operation = {
        "schema_version": 1,
        "operation_id": job["job_id"],
        "target": target,
        "action": action,
        "arguments": arguments,
    }
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        completed = subprocess.run(
            [command, "execute", "-"],
            input=json.dumps(operation),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        result = json.loads(completed.stdout) if completed.stdout.strip() else {
            "status": "failed",
            "success": False,
            "error": {"code": "empty-result", "message": completed.stderr.strip()},
        }
    except subprocess.TimeoutExpired:
        mutating = action not in {"status", "capabilities", "observe", "snapshot"}
        result = {
            "status": "uncertain" if mutating else "timed-out",
            "success": False,
            "emitted_input": False,
            "input_state": "possibly-emitted" if mutating else "none",
            "error": {
                "code": "actuator-timeout",
                "message": "actuator execution timed out; inspect target state before retrying" if mutating else "actuator execution timed out",
            },
        }
    except OSError as error:
        result = {
            "status": "failed",
            "success": False,
            "emitted_input": False,
            "input_state": "none",
            "error": {"code": "actuator-unavailable", "message": str(error)},
        }
    except json.JSONDecodeError as error:
        result = {
            "status": "failed",
            "success": False,
            "error": {"code": "invalid-result", "message": str(error)},
        }
    if not isinstance(result, dict) or not isinstance(result.get("status"), str):
        result = {
            "status": "failed",
            "success": False,
            "emitted_input": False,
            "input_state": "none",
            "error": {"code": "invalid-result", "message": "actuator returned no structured status"},
        }
    finished_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    actuator_status = result.get("status")
    receipt_status = "succeeded" if result.get("success") is True else (
        "uncertain" if actuator_status == "uncertain" else "failed"
    )
    receipt = {
        "schema_version": 1,
        "receipt_id": f"receipt-{job['job_id']}",
        "job_id": job["job_id"],
        "device_id": decision.device_id,
        "executor": "actuator",
        "transport": decision.transport,
        "status": receipt_status,
        "started_at": started_at,
        "finished_at": finished_at,
        "result": result,
        "evidence": result.get("evidence", []),
    }
    validate_receipt(receipt)
    return receipt
