"""MCore ai-orchestrator — FastAPI entrypoint (L5 runtime enforcement).

Owner: Aminul Islam Shamim (AIS) — Meticulous Core Ltd.
Founder ID: MCORE-FDR-AIS-001
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from security.poison_guard import PoisonGuard, PolicyLoadError

app = FastAPI(title="mcore-ai-orchestrator", version="0.1.0")

try:
    guard = PoisonGuard()
except PolicyLoadError as e:
    raise SystemExit(f"PoisonGuard failed to initialize — refusing to start: {e}")


class ToolRequest(BaseModel):
    tool: str = Field(..., min_length=1, max_length=128)
    args: dict[str, Any] = Field(default_factory=dict)


class ToolDecisionResponse(BaseModel):
    tool: str
    allowed: bool
    requires_approval: bool
    reason: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "mcore-ai-orchestrator"}


@app.post("/tool/check", response_model=ToolDecisionResponse)
def check_tool(req: ToolRequest) -> ToolDecisionResponse:
    d = guard.check(req.tool)
    return ToolDecisionResponse(
        tool=req.tool,
        allowed=d.allowed,
        requires_approval=d.requires_approval,
        reason=d.reason,
    )


@app.post("/tool/invoke")
def invoke_tool(req: ToolRequest) -> dict[str, Any]:
    d = guard.check(req.tool)
    if not d.allowed:
        raise HTTPException(status_code=403, detail=d.reason)
    if d.requires_approval:
        raise HTTPException(status_code=409, detail=f"human approval required: {d.reason}")
    return {"tool": req.tool, "status": "executed_stub", "args": req.args}
