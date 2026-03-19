# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities through GitHub Security Advisories —
**do NOT open public issues for security bugs**.

**[Report a vulnerability →](https://github.com/kagenti/plugins-adapter/security/advisories/new)**

Include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Any suggested mitigations (optional)

## Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 7 days |
| Status update | Weekly until resolved |
| Credit | In the security advisory (if desired) |

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main`  | ✅ |

Older tagged releases receive security fixes on a best-effort basis.

## Security Controls

This repository implements the following security measures:

| Control | Tool |
|---------|------|
| Dependency vulnerability scanning | Trivy (CRITICAL/HIGH on PRs) |
| Dependency updates | Dependabot (weekly, all ecosystems) |
| Python SAST | Bandit (HIGH severity blocks PRs) |
| Code analysis | CodeQL (security-extended queries) |
| Dockerfile lint | Hadolint |
| Secret detection | Pre-commit hooks |
| Supply chain | OpenSSF Scorecard (weekly), SHA-pinned actions |
| License compliance | Dependency Review Action (GPL/AGPL blocked) |

## Security-Sensitive Areas

Changes to the following require extra scrutiny:

- `src/server.py` — gRPC ext-proc server handling all traffic
- `plugins/` — Plugin interface and example implementations
- `.github/workflows/` — CI/CD pipeline
- `Dockerfile` — Container image

## Disclosure Policy

We follow coordinated disclosure. Once a fix is available:
1. A security advisory is published on GitHub
2. A new release tag is pushed
3. The advisory is made public (typically 7 days after the fix is released)
