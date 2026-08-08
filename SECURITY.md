# Security Policy

Deal Hunter AI is a solo/small-team project (see [CLAUDE.md](CLAUDE.md)),
not a company with a dedicated security team — this policy sets honest
expectations rather than promising an SLA nobody's staffed to meet.

## Reporting a vulnerability

**Please do not open a public GitHub issue for a security vulnerability.**
Issues are public the moment they're filed, and this repo has no private
triage step — a public report on an unpatched, deployable vulnerability
is a live exploit for anyone else who reads it.

Instead, use GitHub's private vulnerability reporting:
[open a draft security advisory](https://github.com/Tikus1810/Dealer-Hunter-Ai/security/advisories/new)
for this repository (**Security** tab → **Advisories** → **Report a
vulnerability**). This reaches the repo owner privately and lets you
attach a proof of concept without exposing it publicly.

If GitHub advisories aren't reachable for some reason, contact the repo
owner directly through their GitHub profile.

Please include:
- What the vulnerability is and its likely impact.
- Steps to reproduce (a minimal repro beats a general description).
- Which component: `backend/` (FastAPI/Python) or `mobile/` (Flutter).

## What to expect

- Acknowledgement: best-effort, no fixed SLA (see above — solo project).
- A confirmed vulnerability gets fixed and disclosed via a GitHub
  Security Advisory once a fix is available, crediting the reporter
  unless they ask not to be.
- This project has no bug bounty — reports are appreciated, not paid.

## Scope

In scope: this repository's own code (`backend/`, `mobile/`, `infra/`,
`.github/workflows/`). Known, already-documented gaps are **not** new
reports — see [docs/security.md](docs/security.md)'s "Known gaps"
section first (e.g. accepted CVEs in `starlette`/`pytest`/`ecdsa` with
documented reasoning, the login-timing side channel, no secrets-rotation
policy). If you found something not already listed there, it's likely
new and worth reporting.

Out of scope: vulnerabilities in third-party dependencies themselves —
report those upstream (and feel free to also flag it here if this
project's pin is affected and not yet tracked in `docs/security.md`).
No production deployment exists yet for this project (see
[README.md](README.md#status)), so there's no live environment to test
against beyond what you run yourself from this source.

## Supported versions

Pre-1.0, single `main` branch, no version branches maintained — fixes
land on `main` and there is currently no older release line to
backport to.
