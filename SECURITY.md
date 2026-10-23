# Security Policy

Report vulnerabilities **privately** to the founder.
Do **not** open public issues for security findings.

**Contact:** Aminul Islam Shamim (AIS) — Founder, Meticulous Core Ltd.
**Founder ID:** `MCORE-FDR-AIS-001`

Secrets live in `.env` files and are never committed. See `.gitignore`.

If a secret leaks, rotate it at the provider (e.g. Gemini API keys at
https://aistudio.google.com/apikey) **before** the next commit.
