# Cyber News Alert Monitor

Dockerized Python 3.11 service that monitors free cybersecurity news sources (RSS, Google News RSS, optional GDELT), detects likely social-engineering attack incidents, deduplicates results in PostgreSQL, and sends SMTP email alerts.

## Features

- Free sources only: curated RSS feeds, Google News RSS queries, optional GDELT Doc API.
- Attack detection heuristics for phishing, malvertising, impersonation, BEC, smishing, vishing, fake updates, SEO poisoning, watering hole attacks, social media scams, and credential theft.
- Victim extraction and category detection (company, government, university, hospital/healthcare).
- Deduplication by canonical URL and normalized content/title fingerprints.
- Hourly scheduling via `supercronic` sidecar.
- Typed Python modules, logging, retry/backoff, robust failure handling.

## Project Structure

- `app/main.py`: single-run entrypoint
- `app/pipeline.py`: orchestration
- `app/sources/`: RSS, Google News RSS, GDELT source adapters
- `app/fetch/article_fetcher.py`: local article extraction and abstract generation
- `app/detection/`: attack and victim heuristics
- `app/dedup/deduplicator.py`: canonicalization and hashing
- `app/alerts/emailer.py`: SMTP alert sender
- `app/models.py`: SQLAlchemy models
- `app/schema_init.py`: idempotent schema creation
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

## Run with Docker

Build and run scheduler + database:

```bash
docker compose up --build -d postgres scheduler
```

Run one manual execution:

```bash
docker compose run --rm app
```

Check logs:

```bash
docker compose logs -f scheduler
```

Stop all services and remove containers/network:

```bash
docker compose down
```

Restart everything cleanly:

```bash
docker compose up --build -d
```

Full reset (also removes Postgres data volume):

```bash
docker compose down -v
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
3. **Content hash**: SHA-256 over normalized full text (stored for audit/analysis).

If canonical URL or fingerprint already exists, no alert is sent.

## Testing

Run tests locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Limitations

- Heuristic victim extraction can miss entities when article prose is ambiguous.
- Article extraction quality depends on source HTML structure.
- Near-duplicate stories with heavily rewritten text can bypass fingerprint matching.
- Schema initialization uses `create_all` (idempotent) instead of full migration tooling.

## Future Improvements

- Add Alembic migrations.
- Add better named-entity extraction (e.g., NLP model) with local-only inference.
- Add per-source quality scoring and circuit-breakers.
- Add optional digest mode (batched alerts) and metrics endpoint.
