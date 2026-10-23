"""Tests for PoisonGuard against the real policy YAML."""
from __future__ import annotations

from pathlib import Path

import pytest

from security.poison_guard import PolicyLoadError, PoisonGuard, ToolDecision


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = REPO_ROOT / "config" / "policy" / "poison-lifecycle.yaml"


@pytest.fixture(scope="module")
def guard() -> PoisonGuard:
    return PoisonGuard(policy_path=POLICY)


def test_policy_file_exists() -> None:
    assert POLICY.exists(), f"real policy file missing: {POLICY}"


def test_whitelisted_tool_allowed(guard: PoisonGuard) -> None:
    d = guard.check("read_file")
    assert isinstance(d, ToolDecision)
    assert d.allowed is True
    assert d.requires_approval is False


def test_blocked_tool_denied(guard: PoisonGuard) -> None:
    d = guard.check("drop_table")
    assert d.allowed is False
    assert d.requires_approval is False
    assert "blocked" in d.reason.lower()


def test_approval_tool_flagged(guard: PoisonGuard) -> None:
    d = guard.check("push_to_main")
    assert d.allowed is True
    assert d.requires_approval is True


def test_unknown_tool_denied(guard: PoisonGuard) -> None:
    d = guard.check("totally_made_up_tool_xyz")
    assert d.allowed is False
    assert "not in the whitelist" in d.reason


def test_empty_tool_name_denied(guard: PoisonGuard) -> None:
    assert guard.check("").allowed is False
    assert guard.check("   ").allowed is False


def test_env_var_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCORE_POLICY_PATH", str(POLICY))
    g = PoisonGuard()
    assert g.policy_path.resolve() == POLICY.resolve()


def test_missing_policy_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PolicyLoadError):
        PoisonGuard(policy_path=tmp_path / "does-not-exist.yaml")


def test_malformed_policy_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("whitelisted_tools: [read_file\n", encoding="utf-8")
    with pytest.raises(PolicyLoadError):
        PoisonGuard(policy_path=bad)


def test_empty_policy_fails_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(PolicyLoadError):
        PoisonGuard(policy_path=empty)


def test_fail_closed_flag_required(tmp_path: Path) -> None:
    p = tmp_path / "no_fail_closed.yaml"
    p.write_text(
        "whitelisted_tools: []\n"
        "blocked_tools: []\n"
        "require_human_approval: []\n"
        "audit: {fail_closed: false}\n",
        encoding="utf-8",
    )
    with pytest.raises(PolicyLoadError, match="fail_closed"):
        PoisonGuard(policy_path=p)
