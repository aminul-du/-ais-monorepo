# MCore DevOps — Zero-Gap Handbook

**Owner:** Aminul Islam Shamim (AIS) — Meticulous Core Ltd.
**Founder ID:** `MCORE-FDR-AIS-001` · **Version:** 1.0.0 · **Date:** 2026-10-23

## 1. Purpose
Single source of truth. If it's not here, docs are wrong — fix here first.

## 2. Zero-Gap Definition
**Testable property:** `./verify.sh` exit 0 = zero-gap. Nothing else.

| Gap | Closed by |
|---|---|
| Unverified code committed | `cargo test` / `pytest` before commit |
| Secrets in history | `.gitignore` verified before push |
| Missing policy | `config/policy/*.yaml` validated in CI |
| Contract broken | test reads real YAML, not mock |
| Docs drift | `DEVOPS.md` updated same commit |
| Works-on-my-machine | CI runs same as `./verify.sh` |

## 3. Layout
Every `apps/*` has tests OR entry in §10 Known Gaps.

## 4. Commit Conventions
Format: `<type>(<scope>): <subject>`
Types: feat, fix, chore, docs, test, ci
Scopes: core-api, ai-orchestrator, web, api-core, agent, policy, devops, identity
Rules: tests pass at every commit · `./verify.sh` before push · one change per commit · never force-push main

## 5. Verification
`./verify.sh` = single-command audit (secrets + YAML + pytest + cargo + git).
CI runs same via `.github/workflows/verify-stack.yml`.

## 6. Secrets
`.env` gitignored at every depth · `.env.example` = keys only · leak = rotate FIRST then scrub.
Current ignored: `apps/shorbornoai-agent/.env`

## 7. Tags
`vX.Y.Z-baseline` = first commit · `vX.Y.Z` = release · annotated only (`-a`).
Current: `v0.1.0-baseline` → `97dba5d`

## 8. Recovery
- Locally broken: `git stash; ./verify.sh; git stash pop`
- Secret leaked: rotate → `git filter-repo` → force-push (only time allowed)
- Lost dir: `git clone ~/mcore-*.bundle restored/`

## 9. Next Work (priority)
1. `traceroute.rs` (TCP, Cloud Run safe)
2. `main_api.py` + `main_acp.py`
3. Dockerfiles (3 apps)
4. `packages/` scaffolds
5. `site/data/evidence/` + write path

## 10. Known Gaps (deliberate)
- Dockerfiles: until traceroute+main_api exist
- `packages/design-system/`: tokens.json not finalized
- `config/{nftables,systemd}/`: host-level, only at deploy
- `site/data/evidence/`: WORM needs GCS Object Lock
- `research/`: add when research starts
- `apps/backend-api/`: merged into `api-core` (same role)
- `apps/ai-orchestrator/rag_store.py`: needs Qdrant instance
- `apps/ai-orchestrator/tools/mcp_tools.py`: depends on real agent
- `apps/web/src/hooks/useDiagnostics.ts`: needs traceroute endpoint

Rule: gap references priority OR `Never` + reason.

## 11. What This Replaces
No ad-hoc audits. `./verify.sh` IS the audit. No 200-line scripts. Exit code answers "is it zero-gap?".
If wrong, edit this file. Do not create a second document.

*End — update on every structural change.*
