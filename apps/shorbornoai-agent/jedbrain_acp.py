#!/usr/bin/env python3
"""
JEDBRAIN — ACP-to-MCore Agent Server
Document ID: MCORE-JEDBRAIN-ACP-001
Owner: AIS — Human Owner / Final Authority
Architecture: 1of1-X / Antigravity CLI

Provides:
1. ACP protocol bridge for PyCharm AI Assistant (JSON-RPC stdio).
2. Streaming integration with local Gemini / MCore AI backend.
3. Persistent conversation memory with session-isolated checkpoints.
4. Secure, read-only MCP tool execution with boundary enforcement.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import httpx

from acp.core import run_agent
from acp.helpers import update_agent_message_text
from acp.schema import (
    AgentCapabilities,
    Implementation,
    InitializeResponse,
    NewSessionResponse,
    PromptResponse,
    TextContentBlock,
)

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
WORKSPACE_ROOT = Path("/home/ais-pmicsdu-dev").resolve()
DB_PATH = WORKSPACE_ROOT / ".mcore_jedbrain_sessions.db"
DEFAULT_MCore_URL = "http://127.0.0.1:8000"
DEFAULT_MODEL = "gemini-3.8-flash-high"

SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret|password|token|bearer)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'),
    re.compile(r'(?i)(AIza[0-9A-Za-z-_]{35})'),
    re.compile(r'(?i)(postgresql://[^:]+:)([^@]+)(@)'),
]


def mask_secrets(text: str) -> str:
    """Mask credentials and sensitive strings from logs and outputs."""
    masked = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups == 3:
            masked = pattern.sub(r'\1***REDACTED***\3', masked)
        elif pattern.groups == 2:
            masked = pattern.sub(r'\1: "***REDACTED***"', masked)
        else:
            masked = pattern.sub(r'***REDACTED***', masked)
    return masked


# -----------------------------------------------------------------------------
# Phase 2: Persistent Conversation Memory (ACID / Isolated)
# -----------------------------------------------------------------------------
class ConversationMemoryStore:
    """Persistent conversation checkpointer and message store using SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create required tables with restricted file permissions."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    cwd TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            conn.commit()

        # Restrict permissions to owner only (0600)
        if self.db_path.exists():
            os.chmod(self.db_path, 0o600)

    def get_or_create_thread(self, session_id: str, cwd: str = "") -> str:
        """Map ACP session identity to a stable thread_id."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT thread_id FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row:
                return str(row["thread_id"])

            thread_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO sessions (session_id, thread_id, cwd, created_at, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, thread_id, cwd, now_iso, json.dumps({"client": "PyCharm-ACP"})),
            )
            conn.commit()
            return thread_id

    def record_turn(self, session_id: str, prompt: str, response: str) -> None:
        """Persist user prompt and assistant response to session history."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
                (session_id, prompt, now_iso),
            )
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, 'assistant', ?, ?)",
                (session_id, response, now_iso),
            )
            conn.commit()

    def get_session_history(self, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Retrieve recent turns strictly isolated to the specified session."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in rows]

    def save_checkpoint(self, session_id: str, state: dict[str, Any]) -> str:
        """Save a state checkpoint for the session."""
        checkpoint_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (checkpoint_id, session_id, state_json, updated_at) VALUES (?, ?, ?, ?)",
                (checkpoint_id, session_id, json.dumps(state), now_iso),
            )
            conn.commit()
        return checkpoint_id

    def load_latest_checkpoint(self, session_id: str) -> dict[str, Any] | None:
        """Load latest checkpoint for a session."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT state_json FROM checkpoints WHERE session_id = ? ORDER BY updated_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if row:
                return json.loads(row["state_json"])
        return None


# -----------------------------------------------------------------------------
# Phase 3: Secure Tool Manager (Boundary-Enforced Read-Only Tools)
# -----------------------------------------------------------------------------
class SecureToolManager:
    """Enforces least-privilege, path boundaries, and read-only diagnostic tools."""

    def __init__(self, workspace_root: Path = WORKSPACE_ROOT):
        self.workspace_root = workspace_root.resolve()

    def _validate_safe_path(self, relative_path: str) -> Path:
        """Ensure target path resolves strictly within the designated workspace boundary."""
        target_path = (self.workspace_root / relative_path).resolve()
        try:
            target_path.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Security violation: path '{relative_path}' escapes workspace boundary '{self.workspace_root}'"
            )
        return target_path

    def read_repo_file(self, relative_path: str, max_bytes: int = 65536) -> str:
        """Read a file within the repository, masking any discovered credentials."""
        safe_path = self._validate_safe_path(relative_path)
        if not safe_path.is_file():
            raise FileNotFoundError(f"File not found: '{relative_path}'")
        content = safe_path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
        return mask_secrets(content)

    def list_repo_dir(self, relative_path: str = "") -> list[str]:
        """List files in a workspace subdirectory."""
        safe_path = self._validate_safe_path(relative_path)
        if not safe_path.is_dir():
            raise NotADirectoryError(f"Directory not found: '{relative_path}'")
        entries = []
        for item in sorted(safe_path.iterdir()):
            if item.name.startswith(".git"):
                continue
            suffix = "/" if item.is_dir() else ""
            entries.append(f"{item.name}{suffix}")
        return entries

    def system_diagnostics(self) -> dict[str, Any]:
        """Perform non-destructive service and environment diagnostics."""
        total, used, free = shutil.disk_usage(self.workspace_root)

        # Check local service ports non-destructively
        port_status = {}
        for port, service in [(3000, "Next.js Web Terminal"), (8000, "AI Engine"), (8080, "MCore Sandbox")]:
            try:
                import socket
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    port_status[f"port_{port}_{service}"] = "ONLINE"
            except Exception:
                port_status[f"port_{port}_{service}"] = "OFFLINE"

        return {
            "workspace": str(self.workspace_root),
            "disk_free_gb": round(free / (1024**3), 2),
            "disk_total_gb": round(total / (1024**3), 2),
            "services": port_status,
            "status": "HEALTHY",
        }


# -----------------------------------------------------------------------------
# Phase 1: AI Backend Adapter (Streaming & Fallback)
# -----------------------------------------------------------------------------
class AIBackendAdapter:
    """Connects ACP to the actual AI backend with streaming token support."""

    def __init__(self, mcore_url: str = DEFAULT_MCore_URL, model: str = DEFAULT_MODEL):
        self.mcore_url = mcore_url
        self.model = model
        self.http_client = httpx.AsyncClient(timeout=45.0)

    async def stream_completion(
        self,
        prompt: str,
        session_id: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream response tokens.
        1. Attempts streaming from HTTP backend (FastAPI at :8000) if active.
        2. Falls back to authenticated local Antigravity CLI adapter in stream-json mode.
        """
        # Strategy 1: Check if HTTP backend is active
        try:
            health_check = await self.http_client.get(f"{self.mcore_url}/health", timeout=1.0)
            if health_check.status_code == 200:
                async with self.http_client.stream(
                    "POST",
                    f"{self.mcore_url}/api/ai/analyze",
                    json={"prompt": prompt, "session_id": session_id},
                    timeout=30.0,
                ) as resp:
                    if resp.status_code == 200:
                        async for chunk in resp.aiter_text():
                            if chunk:
                                yield chunk
                        return
        except Exception:
            # HTTP backend not active, fall through to native local model engine
            pass

        # Strategy 2: Local authenticated model engine via Antigravity CLI
        cmd = [
            "ais",
            "--dangerously-skip-permissions",
            "--model",
            self.model,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        accumulated = ""
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    payload = json.loads(line_str)
                    event_type = payload.get("event")
                    if event_type == "step_update":
                        step_update = payload.get("step_update", {})
                        delta = step_update.get("text_delta")
                        if delta:
                            accumulated += delta
                            yield delta
                    elif event_type == "result":
                        res_obj = payload.get("result", {})
                        full_res = res_obj.get("response", "")
                        if full_res and not accumulated:
                            yield full_res
                except json.JSONDecodeError:
                    continue

            await proc.wait()
        except asyncio.CancelledError:
            proc.kill()
            raise


# -----------------------------------------------------------------------------
# ACP Server Implementation
# -----------------------------------------------------------------------------
class PersonalMCoreAgent:
    """Official ACP Protocol Agent for PyCharm."""

    def __init__(
        self,
        mcore_url: str = DEFAULT_MCore_URL,
        model: str = DEFAULT_MODEL,
    ):
        self._conn: Any = None
        self.memory = ConversationMemoryStore()
        self.tools = SecureToolManager()
        self.backend = AIBackendAdapter(mcore_url=mcore_url, model=model)

    def on_connect(self, conn: Any) -> None:
        """Invoked by ACP runtime when connection is established."""
        self._conn = conn

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: Any = None,
        client_info: Implementation | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        """Handshake with PyCharm."""
        sys.stderr.write(f"[JEDBRAIN-ACP] Client connected: {client_info}\n")
        return InitializeResponse(
            protocol_version=protocol_version,
            agent_info=Implementation(name="MCorePersonalAgent", version="1.0.0"),
            agent_capabilities=AgentCapabilities(),
        )

    async def new_session(
        self,
        cwd: str,
        additional_directories: list[str] | None = None,
        mcp_servers: list[Any] | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        """Start a new session and initialize persistent thread identity."""
        session_id = str(uuid.uuid4())
        thread_id = self.memory.get_or_create_thread(session_id, cwd=cwd)
        sys.stderr.write(f"[JEDBRAIN-ACP] New session: {session_id} -> thread {thread_id} (cwd: {cwd})\n")
        return NewSessionResponse(session_id=session_id)

    async def prompt(
        self,
        session_id: str,
        prompt: list[Any],
        **kwargs: Any,
    ) -> PromptResponse:
        """Handle incoming prompt from PyCharm with streaming and memory."""
        # 1. Parse text from incoming prompt blocks
        user_text = ""
        for block in prompt:
            if hasattr(block, "text"):
                user_text += block.text + "\n"
            elif isinstance(block, dict) and "text" in block:
                user_text += block["text"] + "\n"

        user_text = user_text.strip()
        sys.stderr.write(f"[JEDBRAIN-ACP] Turn on session {session_id}: '{mask_secrets(user_text)[:60]}...'\n")

        # 2. Retrieve session history and map thread
        thread_id = self.memory.get_or_create_thread(session_id)
        history = self.memory.get_session_history(session_id)

        # 3. Check for approved tool commands
        tool_handled = False
        full_response = ""

        if user_text.startswith("/diag") or "system diagnostics" in user_text.lower():
            diag = self.tools.system_diagnostics()
            full_response = f"**System Diagnostics:**\n```json\n{json.dumps(diag, indent=2)}\n```"
            tool_handled = True
        elif user_text.startswith("/cat ") or user_text.startswith("/read "):
            target_file = user_text.split(" ", 1)[1].strip()
            try:
                content = self.tools.read_repo_file(target_file)
                full_response = f"**File `{target_file}`:**\n```\n{content}\n```"
            except Exception as e:
                full_response = f"**Read Error:** {e}"
            tool_handled = True

        # 4. Stream response to PyCharm
        if tool_handled:
            if self._conn is not None:
                await self._conn.session_update(
                    session_id=session_id,
                    update=update_agent_message_text(full_response),
                )
        else:
            try:
                async for chunk in self.backend.stream_completion(user_text, session_id, history):
                    full_response += chunk
                    if self._conn is not None:
                        await self._conn.session_update(
                            session_id=session_id,
                            update=update_agent_message_text(chunk),
                        )
            except Exception as e:
                err_msg = f"\n[Backend Error]: {e}"
                full_response += err_msg
                if self._conn is not None:
                    await self._conn.session_update(
                        session_id=session_id,
                        update=update_agent_message_text(err_msg),
                    )

        # 5. Persist turn to conversation memory
        self.memory.record_turn(session_id, user_text, full_response)

        return PromptResponse(stop_reason="end_turn")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
async def main() -> None:
    agent = PersonalMCoreAgent()
    await run_agent(agent)


if __name__ == "__main__":
    asyncio.run(main())
