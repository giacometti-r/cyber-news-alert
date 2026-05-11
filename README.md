# Cyber News Alert Monitor

Dockerized Python 3.11 service that monitors free cybersecurity news sources (RSS, Google News RSS, optional GDELT), classifies social-engineering stories, deduplicates results in PostgreSQL, and sends SMTP alerts.

## Features

- Free sources only: curated RSS feeds, Google News RSS queries, optional GDELT Doc API.
- Closed attack taxonomy for immediate alerts: phishing, malvertising, impersonation, business email compromise, smishing, vishing, fake updates, SEO poisoning, watering hole, social media scams, credential theft.
- Article-type gating: `incident`, `campaign_report`, `advisory`, `press_release`, `legal_followup`, `opinion`.
- Strict immediate alerting: immediate emails only for qualified incidents with in-taxonomy attack type and confident victim extraction.
- Digest channel: one digest email per run for queued non-immediate items.
- Cross-source incident dedupe: 48-hour incident-key dedupe to suppress syndicated rewrites in immediate channel.
- Boilerplate-resistant article cleanup and improved abstract generation with metadata fallback.
- URL/fingerprint/content-hash dedupe plus robust retries/logging.

## Project Structure

- `app/main.py`: single-run entrypoint
- `app/pipeline.py`: routing/orchestration for immediate + digest channels
- `app/sources/`: RSS, Google News RSS, GDELT source adapters
- `app/fetch/article_fetcher.py`: article extraction and abstract generation
- `app/detection/`: attack classifier and victim extractor
- `app/dedup/deduplicator.py`: canonicalization, hashes, incident key
- `app/alerts/emailer.py`: SMTP sender and digest formatting
- `app/models.py`: SQLAlchemy models
- `app/schema_init.py`: idempotent schema setup and column backfill
- `ops/supercronic/cronjobs`: hourly scheduler expression
- `tests/`: unit and integration-lite tests

## Configuration

1. Copy and edit environment file:

```bash
cp .env.example .env
```

2. Set SMTP credentials and recipient values in `.env`.
3. Keep `DATABASE_URL` using service host `postgres` for Docker Compose.

Required variables:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SENDER_EMAIL`
- `RECIPIENT_EMAIL`
- `DATABASE_URL`

Optional runtime controls:

- `LOG_LEVEL`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_ARTICLES_PER_SOURCE`
- `ENABLE_GDELT`
- `GDELT_QUERY_WINDOW_MINUTES`
- `RSS_FEEDS` (comma-separated or JSON array)
- `GOOGLE_NEWS_QUERIES` (comma-separated or JSON array)
- `MIN_VICTIM_CONFIDENCE` (default: `0.65`)
- `INCIDENT_DEDUPE_WINDOW_HOURS` (default: `48`)
- `DIGEST_ENABLED` (default: `true`)
- `DIGEST_RECIPIENT_EMAIL` (default: fallback to `RECIPIENT_EMAIL`)
- `DIGEST_MAX_ITEMS_PER_RUN` (default: `100`)
- `ABSTRACT_MAX_CHARS` (default: `420`)
- `MAX_VICTIM_WORDS` (default: `8`)

Deprecated compatibility controls:

- `ENABLE_GENERIC_VICTIM_FALLBACK` (kept for compatibility, not used for immediate channel in v2)
- `GENERIC_VICTIM_NAME`
- `DEFAULT_VICTIM_CATEGORY`

## Security Controls

- **Outbound URL safety**: article and source URLs are restricted to `http/https`, reject embedded credentials, and block localhost/private/link-local/multicast/reserved/non-global targets.
- **Redirect safety**: article fetches use manual redirect handling with URL re-validation on each hop to prevent SSRF via open redirects.
- **Transport hardening**: SMTP delivery uses STARTTLS with explicit certificate-verifying TLS context.
- **Request isolation**: HTTP clients use a dedicated `requests.Session` with `trust_env=False` to avoid `.netrc`/proxy credential leakage through ambient environment settings.
- **Response limits**: article downloads enforce content-type checks and response size limits before parsing.
- **Dependency policy**: pin dependencies and update promptly for security advisories (including transitive/development tooling).

## Run with Docker

Build and run scheduler + database:

```bash
sudo docker compose up --build -d postgres scheduler
```

Run one manual execution:

```bash
sudo docker compose run --rm app
```

Check logs:

```bash
sudo docker compose logs -f scheduler
```

Stop all services and remove containers/network:

```bash
sudo docker compose down
```

Restart everything cleanly:

```bash
sudo docker compose up --build -d
```

Full reset (also removes Postgres data volume):

```bash
sudo docker compose down -v
```

## Hourly Scheduling

The scheduler container runs:

- `supercronic /app/ops/supercronic/cronjobs`

Default cron expression:

- `0 * * * * /usr/local/bin/python -m app.main`

This executes at minute 0 every hour.

## Deduplication Logic

Each candidate article is deduplicated by:

1. **Canonical URL**: strips tracking parameters (`utm_*`, `gclid`, `fbclid`) and normalizes URL parts.
2. **Fingerprint hash**: SHA-256 over normalized title + article text prefix.
3. **Incident key (immediate channel only)**: SHA-256 over normalized `(victim + attack type)` with a time window (`INCIDENT_DEDUPE_WINDOW_HOURS`) to suppress cross-source duplicate incident alerts.
4. **Content hash**: SHA-256 over normalized full text (stored for audit/analysis).

If canonical URL or fingerprint already exists, the article is skipped.

## Alert Qualification Flow (Two Channels)

1. Fetch article and generate cleaned text + abstract.
2. Classify article type and attack type using weighted title/lead/body scoring.
3. Extract victim with title-first and body fallback patterns.
4. Immediate channel requires all of:
   - `article_type == incident`
   - in-taxonomy `attack_type` present
   - victim confidence >= `MIN_VICTIM_CONFIDENCE`
   - no incident-key duplicate within `INCIDENT_DEDUPE_WINDOW_HOURS`
5. If immediate criteria fail, route to digest queue with routing reason:
   - `low_victim_confidence`
   - `duplicate_incident`
   - `campaign_report`
   - `advisory`
   - `press_release`
   - `legal_followup`
   - `opinion`
   - `out_of_taxonomy`
6. At end of run, send one digest email (if enabled) with queued items grouped by reason.

## False Positive Controls

- Article-type gating blocks press releases, legal recaps, advisories, and opinion pieces from immediate channel.
- Confidence thresholds enforce both incident context and victim quality.
- Incident-key dedupe suppresses syndicated wire rewrites from immediate channel.
- Digest routing preserves visibility while keeping immediate alerts conservative.

## Sample Outputs

Immediate alert example:

```text
Subject: Acme Corp was attacked using phishing

Abstract:
...

Attack type: phishing
Victim: Acme Corp
Victim category: company
Source: Example News
Published date: 2026-04-29T00:00:00+00:00
Article link: https://example.com/article
```

Digest item example:

```text
Reason: campaign_report (1)
- CTM360 Exposes Global GovTrap Campaign...
  Source: Google News
  Attack type: phishing
  Victim: n/a
  Published date: 2026-04-27T08:01:00+00:00
  Link: https://...
```

## Testing

Run tests locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

## Limitations

- Heuristic extraction remains deterministic and can mislabel edge-case stories.
- Abstract quality still depends on source HTML structure and metadata quality.
- Schema initialization is idempotent but is not a full migration system.
- Closed taxonomy intentionally routes some real incidents to digest as `out_of_taxonomy`.
