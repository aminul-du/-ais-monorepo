#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")" || exit 2
RED=$'\033[31m'; GRN=$'\033[32m'; RST=$'\033[0m'
[ -t 1 ] || { RED=''; GRN=''; RST=''; }
fail() { printf '%sFAIL%s %s\n' "$RED" "$RST" "$*"; exit 1; }
pass() { printf '%sPASS%s %s\n' "$GRN" "$RST" "$*"; }

# 1. secrets
if git grep -nEI '(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----)' -- ':!*.md' ':!*.lock' >/dev/null 2>&1; then
  fail "secrets in tracked files"
fi
if [ -f apps/shorbornoai-agent/.env ] && ! git check-ignore -q apps/shorbornoai-agent/.env; then
  fail ".env not ignored"
fi
pass "secrets clean"

# 2. YAML
if ! python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('config/policy/*.yaml')]"; then
  fail "policy YAML invalid"
fi
pass "policy YAML"

# 3. Python
if [ -d apps/ai-orchestrator/tests ]; then
  ( cd apps/ai-orchestrator && python3 -m pytest -q ) || fail "pytest failed"
  pass "python agent"
fi

# 4. Rust
if [ -f apps/core-api/Cargo.toml ]; then
  source "$HOME/.cargo/env" 2>/dev/null || true
  ( cd apps/core-api && cargo test --quiet ) || fail "cargo test failed"
  pass "rust core-api"
fi

# 5. git state
[ -z "$(git status --porcelain)" ] || printf 'warn: dirty tree\n'
printf '\n%sZERO_GAP: GREEN%s\n' "$GRN" "$RST"
