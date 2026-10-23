# MCore Project Checklist

**Standard:** Done / In Progress / Blocked / Not Started
**Source of truth:** This file + `DEVOPS.md` + git history
**Rule:** Mark Done only with supporting evidence

## ✅ Done (evidence-backed)

| Item | Evidence |
|---|---|
| Git repo + `v0.1.0-baseline` tag | `git tag -l`, pushed |
| Corporate identity (LICENSE, README, AUTHORS, SECURITY) | `97dba5d` |
| `.gitignore` (59 lines) + tooling configs | `96933ac` |
| L0 policy YAML (3 files) | `yaml.safe_load` OK, `03ec6d5` |
| `PoisonGuard` (L5) — 11 tests | pytest 11 pass, `fa2188a` |
| `main_api.py` FastAPI — 7 tests | pytest 18 total, `d00416b` |
| Rust `core-api` + `/traceroute` — 4 tests | cargo 4 pass, `de85007` |
| Docker: ai-orchestrator, core-api, web | `compose build` OK |
| Caddy HTTPS/HTTP2/HTTP3 + path routing | `curl proto 2`, `4b2fcbb` |
| `docker-compose.prod.yml` + `deploy.sh` | `compose up` OK |
| `verify.sh` + pre-push hook + CI | 22 tests pass each push |
| Live dashboard (`page.tsx`) | SSR + backends verified (this commit) |

## 🔄 In Progress

*None*

## 🚫 Blocked

| Item | Blocker |
|---|---|
| Cloud Run deploy | Needs `gcloud auth` |
| Real-domain TLS | Needs DNS + ports 80/443 open |

## ⬜ Not Started

- `packages/` scaffolds (design-system, ui, shared-models, proto)
- `apps/web/src/hooks/useDiagnostics.ts`, `useWebRTC.ts`
- `apps/ai-orchestrator/rag_store.py` (Qdrant Z1/Z2/Z3)
- `apps/ai-orchestrator/tools/mcp_tools.py`
- `apps/ebpf-agent/` (C, XDP)
- `apps/android-app/`, `apps/vasakos-desktop/`, `apps/qira-analyzer/`
- `site/data/evidence/` WORM (GCS Object Lock)
- `research/p0-memory-security/`, `p1-rag-shield/`, `p2-predictive/`
- `config/nftables/`, `config/systemd/`
- `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`

**Next task:** `packages/design-system/` scaffold
