# Testing, CI and Docker

## Local checks

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest --cov --cov-report=term-missing --cov-report=xml
```

All test fixtures create file-backed SQLite databases in pytest temporary directories. They never drop production tables. Tests exercise actual Alembic initialization, migration rollback and upgrade preservation, factory restart persistence, relationship constraints, atomic ledger changes, negative stock rejection, authenticated HTML/API CRUD, CSRF, cross-user access, CSV atomicity, images, profiles and UI rendering. ML tests fit actual scikit-learn CPU estimators, verify preprocessing and zero days, compare baseline/model MAE, check cutoff-specific artifacts, inject future data and inspect anomalies. LLM tests validate schema boundaries and deterministic fallback; local endpoint responses are mocked. CLI integration tests run init/demo/train commands end to end.

Coverage includes app, main routes, configuration, authentication, profile, API, commands, models, forms, extensions and all services. The overall minimum is 80%; ML, inventory and commentary logic are included. Tests do not claim model quality merely by asserting a model outperforms the baseline. Evaluation numbers are recorded from the reproducible demo in [verification.md](verification.md).

## Docker

The Dockerfile uses Ubuntu 24.04, Python 3.12 in a virtual environment, a non-root runtime user and CPU packages. The app listens on port 5000; Compose publishes it on localhost only. Gunicorn runs two workers with two threads, and OpenMP/OpenBLAS threads are capped at one. A healthcheck calls `/health`. No model is built into the image. Optional llama.cpp is activated by `--profile llm` and requires an explicitly supplied local GGUF.

```bash
docker compose config --quiet
docker compose build app
docker compose run --rm app flask --app app init-db
docker compose up -d --wait app
curl --fail http://127.0.0.1:5000/health
curl --fail http://127.0.0.1:5000/auth/login
docker compose logs app
docker compose down
```

The persistent volume contains SQLite, model artifacts, uploads and the generated local secret. Container recreation preserves them. To run the complete tests in a disposable development container without adding dependencies to the runtime image:

```bash
docker run --rm --user root --entrypoint sh stockpilot-ai-app \
  -c 'pip install --no-cache-dir -r requirements-dev.txt && ruff check . && ruff format --check . && pytest --cov --cov-report=term-missing'
```

This creates test data inside that disposable container, with no application volume mounted. The image tag above is Compose's default for this repository directory. No GPU service or running LLM is needed.

## CI/CD

`.github/workflows/quality.yml` runs on push/PR against Ubuntu 24.04 with Python 3.12: Ruff analysis and formatting, all unit/integration tests and XML coverage, coverage artifact upload, Compose config validation, CPU Docker build, explicit DB initialization, healthy container startup and HTTP login/health smoke checks. Cleanup runs even on failures. It does not deploy, push an image, merge, or alter repository remotes. GitHub-hosted execution is separate from the locally verified workflow commands; see verification status.

`SECRET_KEY` is optional locally: a random mode-0600 secret is persisted. For deployment, inject a stable secret and use HTTPS with `COOKIE_SECURE=1`. Copy `.env.example` to `.env` only when configuring overrides; environment secrets and data/model files are ignored by Git and Docker contexts.
