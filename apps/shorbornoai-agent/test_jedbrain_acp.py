#!/usr/bin/env python3
"""
Automated Verification Suite for JEDBRAIN ACP-to-MCore Integration
Document ID: MCORE-JEDBRAIN-ACP-001
Tests:
- ACP protocol handshake and turn completion
- Streaming token delivery through ACP session_update
- Persistent conversation memory across agent restarts
- Strict session isolation
- Secure MCP tool boundary enforcement and path traversal protection
- Secret masking in outputs
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from acp.schema import TextContentBlock
from acp.stdio import spawn_agent_process

VENV_PYTHON = "/home/ais-pmicsdu-dev/.venv-acp/bin/python"
AGENT_SCRIPT = "/home/ais-pmicsdu-dev/my_agent.py"
WORKSPACE_DIR = "/home/ais-pmicsdu-dev"


class TestClient:
    def __init__(self):
        self.received_chunks: list[str] = []

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        if hasattr(update, "content") and hasattr(update.content, "text"):
            self.received_chunks.append(update.content.text)
        elif hasattr(update, "session_update"):
            self.received_chunks.append(str(update.session_update))


async def test_acp_handshake_and_tool_call() -> bool:
    print("\n[TEST 1] ACP Protocol Handshake & Tool Diagnostics...")
    client = TestClient()
    async with spawn_agent_process(client, VENV_PYTHON, AGENT_SCRIPT) as (conn, process):
        # 1. Initialize
        init_res = await conn.initialize(protocol_version=1)
        assert init_res.agent_info.name == "MCorePersonalAgent", f"Unexpected agent: {init_res.agent_info}"
        print("  ✓ Handshake successful: Agent 'MCorePersonalAgent'")

        # 2. New session
        session_res = await conn.new_session(cwd=WORKSPACE_DIR)
        assert session_res.session_id, "Missing session ID"
        print(f"  ✓ Session created: {session_res.session_id}")

        # 3. Diagnostic Tool via prompt
        prompt_res = await conn.prompt(
            session_id=session_res.session_id,
            prompt=[TextContentBlock(type="text", text="/diag")],
        )
        assert prompt_res.stop_reason == "end_turn", f"Unexpected stop reason: {prompt_res.stop_reason}"
        assert len(client.received_chunks) > 0, "No chunks received"
        combined = "".join(client.received_chunks)
        assert "System Diagnostics" in combined, f"Tool response missing in: {combined}"
        assert "HEALTHY" in combined, "Health status missing"
        print("  ✓ Tool call executed and returned diagnostics through ACP.")

    return True


async def test_persistent_memory_and_isolation() -> bool:
    print("\n[TEST 2] Persistent Conversation Memory & Session Isolation...")
    sys.path.insert(0, WORKSPACE_DIR)
    from my_agent import ConversationMemoryStore

    mem = ConversationMemoryStore()
    sess_a = f"test-sess-a-{uuid.uuid4().hex[:8]}"
    sess_b = f"test-sess-b-{uuid.uuid4().hex[:8]}"

    # Map threads
    thread_a1 = mem.get_or_create_thread(sess_a, cwd=WORKSPACE_DIR)
    thread_a2 = mem.get_or_create_thread(sess_a)
    assert thread_a1 == thread_a2, "Thread ID changed for same session"
    print(f"  ✓ Stable thread mapping: session {sess_a} -> thread {thread_a1}")

    # Record turn in session A
    mem.record_turn(sess_a, "Hello from Session A", "Response for Session A")

    # Record turn in session B
    mem.record_turn(sess_b, "Hello from Session B", "Response for Session B")

    # Verify session isolation
    hist_a = mem.get_session_history(sess_a)
    hist_b = mem.get_session_history(sess_b)

    assert len(hist_a) == 2, f"Expected 2 messages in A, got {len(hist_a)}"
    assert hist_a[0]["content"] == "Hello from Session A"
    assert len(hist_b) == 2, f"Expected 2 messages in B, got {len(hist_b)}"
    assert hist_b[0]["content"] == "Hello from Session B"
    print("  ✓ Strict session isolation verified: zero cross-session data leakage.")

    # Test continuity across simulated agent restart (new instance of ConversationMemoryStore)
    reloaded_mem = ConversationMemoryStore()
    reloaded_thread = reloaded_mem.get_or_create_thread(sess_a)
    assert reloaded_thread == thread_a1, "Thread ID lost after memory reload"
    reloaded_hist = reloaded_mem.get_session_history(sess_a)
    assert len(reloaded_hist) == 2, "History lost after memory reload"
    print("  ✓ Continuity across restart verified: history and thread intact.")

    return True


async def test_mcp_security_boundaries() -> bool:
    print("\n[TEST 3] Security Boundaries & Path Traversal Protection...")
    from my_agent import SecureToolManager, mask_secrets

    tools = SecureToolManager()

    # 1. Allowed read within repository
    content = tools.read_repo_file("my_agent.py")
    assert "PersonalMCoreAgent" in content, "Failed reading authorized file"
    print("  ✓ Authorized repository read allowed.")

    # 2. Block path traversal attempts
    traversal_paths = [
        "../../etc/shadow",
        "../../../etc/passwd",
        "/etc/passwd",
        "mcore-ecosystem/../../../../root/.bashrc",
    ]
    for bad_path in traversal_paths:
        try:
            tools.read_repo_file(bad_path)
            assert False, f"Security failure: Allowed access to forbidden path '{bad_path}'"
        except (PermissionError, FileNotFoundError):
            pass
    print("  ✓ Path traversal protection verified: unauthorized paths blocked.")

    # 3. Secret masking verification
    test_secret_str = 'DATABASE_URL="postgresql://shorbornoai:MySecretPass123@localhost:5432/db" api_key: "AIzaSyD-secret-key-12345"'
    masked = mask_secrets(test_secret_str)
    assert "MySecretPass123" not in masked, f"Password leaked: {masked}"
    assert "AIzaSyD-secret-key-12345" not in masked, f"API key leaked: {masked}"
    assert "***REDACTED***" in masked, "Masking placeholder missing"
    print("  ✓ Secret masking verified: credentials redacted from outputs.")

    return True


async def test_acp_backend_streaming() -> bool:
    print("\n[TEST 4] ACP Live Backend Response & Token Streaming...")
    client = TestClient()
    async with spawn_agent_process(client, VENV_PYTHON, AGENT_SCRIPT) as (conn, process):
        await conn.initialize(protocol_version=1)
        session_res = await conn.new_session(cwd=WORKSPACE_DIR)

        # Submit prompt to live backend
        prompt_res = await conn.prompt(
            session_id=session_res.session_id,
            prompt=[TextContentBlock(type="text", text="Respond with the single word VERIFIED.")],
        )

        assert prompt_res.stop_reason == "end_turn", f"Stop reason: {prompt_res.stop_reason}"
        assert len(client.received_chunks) > 0, "No streamed chunks received"
        full_reply = "".join(client.received_chunks)
        print(f"  ✓ Live backend streamed response received: '{full_reply.strip()}'")
        assert len(full_reply.strip()) > 0, "Empty backend response"

    return True


async def main():
    print("=============================================================")
    print(" 🛡️ Running Automated Verification Suite: MCORE-JEDBRAIN-ACP ")
    print("=============================================================")

    try:
        await test_acp_handshake_and_tool_call()
        await test_persistent_memory_and_isolation()
        await test_mcp_security_boundaries()
        await test_acp_backend_streaming()
        print("\n=============================================================")
        print(" ✅ ALL VERIFICATION SUITE TESTS PASSED!")
        print("=============================================================")
        return 0
    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
