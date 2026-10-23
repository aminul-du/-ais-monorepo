"""MCore Poison Guard — policy-enforced tool gate for the AI agent.

Consumes config/policy/poison-lifecycle.yaml. Denies by default.
Owner: Aminul Islam Shamim (AIS) — Meticulous Core Ltd.
Founder ID: MCORE-FDR-AIS-001
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError("pyyaml is required: pip install pyyaml") from e


class PolicyLoadError(RuntimeError):
    """Raised when the policy file is missing, empty, or malformed."""


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    requires_approval: bool
    reason: str


def _default_policy_path() -> Path:
    """Locate poison-lifecycle.yaml without hardcoded ../../ paths."""
    env = os.environ.get("MCORE_POLICY_PATH")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    # security/poison_guard.py -> security -> ai-orchestrator -> apps -> repo root
    repo_root = here.parents[3]
    return repo_root / "config" / "policy" / "poison-lifecycle.yaml"


class PoisonGuard:
    """Policy-driven allow/deny for agent tool calls. Fails closed."""

    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = Path(policy_path) if policy_path else _default_policy_path()
        self._policy: dict[str, Any] | None = None
        self._load()

    def _load(self) -> None:
        if not self.policy_path.exists():
            raise PolicyLoadError(f"policy file not found: {self.policy_path}")
        try:
            data = yaml.safe_load(self.policy_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise PolicyLoadError(f"policy YAML parse error: {e}") from e
        if not isinstance(data, dict):
            raise PolicyLoadError("policy root must be a mapping")
        for key in ("whitelisted_tools", "blocked_tools", "require_human_approval"):
            if key not in data or not isinstance(data[key], list):
                raise PolicyLoadError(f"policy missing or invalid list: {key}")
        if data.get("audit", {}).get("fail_closed", True) is not True:
            raise PolicyLoadError("audit.fail_closed must be true")
        self._policy = data

    @property
    def policy(self) -> dict[str, Any]:
        assert self._policy is not None, "policy not loaded"
        return self._policy

    def check(self, tool_name: str) -> ToolDecision:
        """Decide whether tool_name is allowed."""
        if not isinstance(tool_name, str) or not tool_name.strip():
            return ToolDecision(False, False, "tool_name must be a non-empty string")
        whitelist = set(self.policy["whitelisted_tools"])
        blocklist = set(self.policy["blocked_tools"])
        approval = set(self.policy["require_human_approval"])
        if tool_name in blocklist:
            return ToolDecision(False, False, f"'{tool_name}' is explicitly blocked")
        if tool_name in approval:
            return ToolDecision(True, True, f"'{tool_name}' requires human approval")
        if tool_name in whitelist:
            return ToolDecision(True, False, f"'{tool_name}' is whitelisted")
        return ToolDecision(False, False, f"'{tool_name}' is not in the whitelist (deny by default)")

    def is_allowed(self, tool_name: str) -> bool:
        return self.check(tool_name).allowed
