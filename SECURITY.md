# Security Policy

## Supported versions

| Version | Supported          |
|---------|--------------------|
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |
| < 0.1   | :x:                |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: **karthikchinnaiyan0223@gmail.com** (replace with your own security contact before publishing).

Please include:
- Description of the vulnerability
- Reproduction steps
- Potential impact
- Suggested fix (optional)

We aim to acknowledge within 48 hours and patch within 7 days for critical issues.

## Security features

This project ships with several security best practices:

- **gitleaks** runs on every push and pull request via `.github/workflows/security.yml`
- **Trivy** scans Docker images for CRITICAL/HIGH CVEs on every build
- **CodeQL** performs semantic analysis on every PR
- **Pre-commit hooks** (`gitleaks`, `ruff`, `prettier`, `checkov`) block secrets and bad code before commit
- **NetworkPolicies** restrict egress from the backend pod
- **Read-only RBAC** — the backend cannot mutate cluster resources
- **No `latest` tags in production** — images are pinned to git SHAs
- **`.env` gitignored** — secrets never leave the developer's machine

## Secret management

- Local dev: `copilot-backend/.env` (gitignored)
- CI: GitHub Actions secrets
- Production: Helm value `openrouter.apiKey` or external secret reference `openrouter.apiKeyExistingSecret`
- **Never commit secrets to git.** The pre-commit `gitleaks` hook will block the commit.

## Disclosure policy

We follow **coordinated disclosure**. Please give us 90 days to patch before public disclosure.
