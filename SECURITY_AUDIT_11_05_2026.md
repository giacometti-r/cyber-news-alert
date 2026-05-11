# Security Audit Report — May 11, 2026

## Executive Summary
- Audit date: **May 11, 2026**.
- Scope covered all git-tracked repository files plus local untracked security-relevant files (notably `.env`) with redaction.
- Total findings: **5**.
- Highest severity identified: **High**.
- Current status after remediation: **5/5 findings remediated** in the working tree.
- Verification outcomes:
  - `PYTHONPATH=. pytest -q` => **32 passed**.
  - OSV advisory re-check of updated `requirements.txt` => **0 known vulnerabilities**.

## Scope and Methodology
- Repository root: `/home/ric/cyber-news-alert`
- Files audited:
  - Runtime code (`/home/ric/cyber-news-alert/app/**`)
  - Tests (`/home/ric/cyber-news-alert/tests/**`)
  - Infrastructure/config (`/home/ric/cyber-news-alert/Dockerfile`, `/home/ric/cyber-news-alert/docker-compose.yml`, `/home/ric/cyber-news-alert/ops/**`)
  - Dependency manifest (`/home/ric/cyber-news-alert/requirements.txt`)
  - Documentation and env templates (`/home/ric/cyber-news-alert/README.md`, `/home/ric/cyber-news-alert/.env.example`)
  - Local untracked config (`/home/ric/cyber-news-alert/.env`) with strict value redaction
- Methods used:
  - Manual static security review (file-by-file)
  - Targeted risky-pattern inspection (URL handling, SMTP TLS, dependency risk, supply-chain integrity)
  - Unit test expansion for new security controls
  - Dependency advisory lookup against OSV on **May 11, 2026**

## Severity Model
- Severity follows CVSS-aligned qualitative levels: `Critical`, `High`, `Medium`, `Low`.
- Reachability qualifier:
  - `Reachable`: exploit path exists in normal runtime behavior.
  - `Conditional`: requires uncommon deployment conditions or additional preconditions.
  - `Local`: requires local filesystem/user access.
  - `Not Reachable`: advisory exists but no reachable code path in this repository.

## Findings

| ID | Severity | Reachability | Component | Summary |
|---|---|---|---|---|
| CNA-SEC-001 | High | Reachable | Fetch pipeline | Potential SSRF/internal-target fetches via unvalidated URLs and redirects. |
| CNA-SEC-002 | Medium | Reachable | SMTP transport | STARTTLS was not explicitly bound to a verifying TLS context. |
| CNA-SEC-003 | Medium | Reachable | Dependencies / HTTP client | Pinned versions included known advisories (`requests`, `python-dotenv`, `pytest`). |
| CNA-SEC-004 | Medium | Conditional | Container supply chain | Supercronic binary download had no integrity verification. |
| CNA-SEC-005 | Low | Local | Local secret material | `.env` secrets were present locally and file mode was overly permissive before remediation. |

### CNA-SEC-001 — SSRF/Internal Target Exposure in Outbound Fetching
- Evidence:
  - `/home/ric/cyber-news-alert/app/fetch/article_fetcher.py:67`
  - `/home/ric/cyber-news-alert/app/fetch/article_fetcher.py:78`
  - `/home/ric/cyber-news-alert/app/fetch/url_guard.py:19`
  - `/home/ric/cyber-news-alert/app/fetch/url_guard.py:87`
  - `/home/ric/cyber-news-alert/app/sources/rss.py:103`
  - `/home/ric/cyber-news-alert/app/sources/gdelt.py:34`
  - `/home/ric/cyber-news-alert/tests/test_article_fetcher.py:93`
  - `/home/ric/cyber-news-alert/tests/test_article_fetcher.py:128`
- Attack scenario:
  - A malicious feed entry or redirected URL could force requests toward localhost/private/internal IP space or credential-bearing URLs.
- Impact:
  - Internal network probing/data exfiltration risk; potential credential exposure via unsafe URL handling.
- Remediation implemented:
  - Added strict URL guard with scheme restrictions, credential rejection, local/private/link-local/multicast/reserved/non-global blocking, and DNS/IP validation.
  - Enforced redirect hop-by-hop re-validation.
  - Applied URL guardrails in source adapters and article fetch path.
  - Enforced response content-type and size limits.
- Verification steps:
  - `test_validate_public_http_url_rejects_non_http_schemes`
  - `test_validate_public_http_url_rejects_embedded_credentials`
  - `test_validate_public_http_url_rejects_local_or_private_targets`
  - `test_download_rejects_private_redirect_target`
  - `test_download_rejects_oversized_response`

### CNA-SEC-002 — SMTP TLS Verification Hardening
- Evidence:
  - `/home/ric/cyber-news-alert/app/alerts/emailer.py:127`
  - `/home/ric/cyber-news-alert/app/alerts/emailer.py:129`
  - `/home/ric/cyber-news-alert/tests/test_emailer.py:99`
- Attack scenario:
  - STARTTLS without an explicitly verifying context can permit weaker/default trust behavior depending on runtime/environment.
- Impact:
  - Increased risk of SMTP MITM/credential interception in misconfigured environments.
- Remediation implemented:
  - Enforced `ssl.create_default_context()` and passed it explicitly via `starttls(context=...)`.
  - Retained fail-closed behavior (send failure is surfaced and persisted by pipeline logic).
- Verification steps:
  - `test_send_uses_verifying_tls_context`

### CNA-SEC-003 — Dependency Advisory Exposure
- Evidence:
  - `/home/ric/cyber-news-alert/requirements.txt:5`
  - `/home/ric/cyber-news-alert/requirements.txt:6`
  - `/home/ric/cyber-news-alert/requirements.txt:10`
  - `/home/ric/cyber-news-alert/app/fetch/article_fetcher.py:59`
  - `/home/ric/cyber-news-alert/app/sources/gdelt.py:25`
- Attack scenario:
  - Known vulnerable package versions in runtime/dev dependencies can introduce credential leakage or local-file risks.
- Impact:
  - Potential security regression from known CVEs/GHSAs in pinned packages.
- Remediation implemented:
  - Upgraded:
    - `python-dotenv` `1.0.1` -> `1.2.2`
    - `requests` `2.32.3` -> `2.33.0`
    - `pytest` `8.3.3` -> `9.0.3`
  - Added `trust_env=False` sessions for HTTP clients to reduce `.netrc`/ambient credential leakage risk.
- Verification steps:
  - OSV re-query on updated pins returned 0 advisories across all listed requirements.

### CNA-SEC-004 — Unverified Third-Party Binary Download in Docker Build
- Evidence:
  - `/home/ric/cyber-news-alert/Dockerfile:12`
  - `/home/ric/cyber-news-alert/Dockerfile:13`
  - `/home/ric/cyber-news-alert/Dockerfile:15`
- Attack scenario:
  - If an upstream distribution channel is tampered with, an unverified binary can be executed in the image build.
- Impact:
  - Supply-chain compromise risk in runtime artifact.
- Remediation implemented:
  - Added pinned `SUPERCRONIC_SHA256` and build-time `sha256sum -c` verification before `chmod +x`.
- Verification steps:
  - Dockerfile now fails build on checksum mismatch.

### CNA-SEC-005 — Local Secret Handling and File Permissions
- Evidence:
  - `/home/ric/cyber-news-alert/.env:1`
  - `/home/ric/cyber-news-alert/.env:4`
  - `/home/ric/cyber-news-alert/.env:8`
  - `/home/ric/cyber-news-alert/.env:29`
- Attack scenario:
  - Local secret-bearing file with permissive mode can be read by unintended local users/processes.
- Impact:
  - Local confidentiality risk for SMTP/database credentials.
- Remediation implemented:
  - Set local file mode to owner-only read/write (`0600`) on **May 11, 2026**.
- Verification steps:
  - Confirmed filesystem mode: `-rw-------` for `/home/ric/cyber-news-alert/.env`.

## Dependency Vulnerability Analysis

Analysis date: **May 11, 2026** (OSV API lookups).

| Advisory | Package | Previously pinned | Affected range | Fixed in | Reachability in this repo | Status |
|---|---|---|---|---|---|---|
| GHSA-9hjg-9r4m-mvj7 / CVE-2024-47081 | requests | 2.32.3 | `< 2.32.4` | 2.32.4+ | Reachable via outbound HTTP usage | Remediated by upgrade to 2.33.0 |
| GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 | requests | 2.32.3 | `< 2.33.0` | 2.33.0+ | Not directly reachable through `extract_zipped_paths()` in current code; still vulnerable package baseline | Remediated by upgrade to 2.33.0 |
| GHSA-mf9w-mj56-hr94 / CVE-2026-28684 | python-dotenv | 1.0.1 | `< 1.2.2` | 1.2.2+ | Conditional/local (dotenv rewrite APIs not used here) | Remediated by upgrade to 1.2.2 |
| GHSA-6w46-j5rx-g56g / CVE-2025-71176 | pytest | 8.3.3 | `< 9.0.3` | 9.0.3+ | Dev/test local surface | Remediated by upgrade to 9.0.3 |

Post-remediation OSV check of current `requirements.txt`: **0 advisories**.

## Local Configuration Review (Redacted)
- Reviewed local `/home/ric/cyber-news-alert/.env` with values redacted.
- Observations:
  - 24 environment keys present.
  - Secret-bearing keys are present (`SMTP_PASSWORD`, `DATABASE_URL`, etc.) and expected for runtime operation.
  - File mode now hardened to `0600`.
  - `DATABASE_URL` currently has no explicit `sslmode` query parameter; acceptable for internal Docker network but not recommended for external/remote DB transport.

## Remediation Summary
- Added URL safety validation module: `/home/ric/cyber-news-alert/app/fetch/url_guard.py`
- Hardened article fetch path (manual redirect validation, content/size limits, isolated session):
  - `/home/ric/cyber-news-alert/app/fetch/article_fetcher.py`
- Added source adapter URL checks and isolated GDELT HTTP session:
  - `/home/ric/cyber-news-alert/app/sources/rss.py`
  - `/home/ric/cyber-news-alert/app/sources/gdelt.py`
- Enforced certificate-verifying SMTP TLS context:
  - `/home/ric/cyber-news-alert/app/alerts/emailer.py`
- Upgraded vulnerable dependency pins:
  - `/home/ric/cyber-news-alert/requirements.txt`
- Added Supercronic binary checksum verification in image build:
  - `/home/ric/cyber-news-alert/Dockerfile`
- Added explicit README security controls section:
  - `/home/ric/cyber-news-alert/README.md`
- Expanded tests for URL guardrails and SMTP TLS hardening:
  - `/home/ric/cyber-news-alert/tests/test_article_fetcher.py`
  - `/home/ric/cyber-news-alert/tests/test_emailer.py`

## Residual Risks and Recommended Next Actions
1. Enforce TLS-to-database when running outside trusted container networks by adding `sslmode=require` (or stricter) to production `DATABASE_URL`.
2. Pin container base image by digest (not only tag) to tighten supply-chain reproducibility.
3. Add CI security gates (`pip-audit`, static security linting) so dependency and code-level regressions fail pull requests automatically.
4. Consider egress allowlisting (network policy/firewall) as an additional SSRF defense-in-depth layer.
