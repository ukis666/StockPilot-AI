# Implementation and verification report

Verified on 2026-10-18 (Europe/Istanbul). No push, merge, commit or remote modification was performed. Existing user data and the upstream MIT license were preserved.

## 1. Implemented functionality

StockPilot AI has authenticated product CRUD, optional validated product images, suppliers, atomic stock receipts/consumption, archival, search/pagination, atomic CSV import/export, profiles and password changes. The navy/teal Jinja dashboard shows total stock/value, products, history, consumption charts, forecast/baseline MAE, stockout dates, anomaly alerts, historical simulation and English commentary. No React or GPU infrastructure is used.

## 2. Bugs fixed

The existing SQLite file contained no tables, but upstream startup checked only file existence, causing registration to fail with `no such table: user`. Initialization now uses explicit transactional Alembic upgrades. Duplicate factories/forms/dashboards, incompatible dependency pins, missing API methods, incorrect ownership fields and unscoped API reads were repaired. Test teardown no longer touches the operational database. Hardcoded secrets, GET logout, external login redirects, unprotected profile mutations, unsafe uploads (including a reproduced alternate-static-path access bypass), unrecorded quantity edits and silent partial CSV failures were fixed.

## 3. Cleanup and attribution

Removed the duplicate factory, redundant dashboard module, duplicate form definitions, unused templates and obsolete upstream screenshots/banner. Account functionality moved from `profile.py` to `account.py` to avoid shadowing the standard library. Existing uploaded product/avatar files remain. Runtime/dev dependencies are separated; PyJWT, pytz and Flask-Migrate were removed in favor of already-used Flask facilities and direct Alembic. Generated data, artifacts and secrets are ignored. Original MIT license/copyright is unchanged; source attribution and modifications are in [upstream.md](upstream.md).

## 4. Database

Four domain tables: User, Item, Supplier and StockMovement; Alembic maintains its own schema-version table. Foreign keys, owner-safe composite references, uniqueness, nonnegative checks and history indexes are installed. `init-db` was run twice on the original empty database: both succeeded, a consistent pre-upgrade backup was retained, and the second invocation was a no-op. No users existed in the original database. Separate tests verified preserving actual legacy user/product records and rollback on a failed migration.

A real Docker HTTP flow registered/logged in a test account, created ten units and consumed three. After force-recreating the container, authenticated access and the seven-unit balance persisted, including the session secret. Every generated demo product's quantity was checked against the sum of its ledger deltas; all 30 matched and all balances were nonnegative. `PRAGMA foreign_key_check` returned no violations locally and in Docker.

## 5. ML evaluation

Real scikit-learn CPU training used a separate Docker demonstration account, seed 42, 30 products, four suppliers and 180 days ending 2026-06-30. There were 5,645 total stock movements, including 5,400 daily consumption records; 5,615 non-administrative movements were eligible for anomaly training.

| Measurement | Observed result |
|---|---:|
| Products with trained Gradient Boosting models | 30 |
| Mean per-product forecast MAE | 2.270762 units/day |
| Mean per-product seven-day moving-average MAE | 6.191877 units/day |
| Total Isolation Forest flags | 139 |
| Controlled synthetic spikes detected | 10 / 10 |

MAE uses the final chronological 20% as a rolling one-step holdout before refitting. These are synthetic-data results, not claims about real inventory accuracy or 90-day error. Anomaly counts are retrospective and include additional review flags; the ten injected spikes are not an independent validation dataset. Full generated metrics: [demo-evaluation.json](demo-evaluation.json).

Example estimates as of 2026-06-30: Wireless Mouse 27 days / 2026-07-27; USB Keyboard 16 days / 2026-07-16; HDMI Cable 20 days / 2026-07-20. The real HTTP historical dashboard rendered trained forecasts at 2026-06-30 and correctly refused to use that model at 2026-05-31. Unit/integration tests also verified that extreme future movements do not change earlier forecasts or retrained historical metrics.

## 6. LLM status

The local llama.cpp HTTP adapter is implemented with validated JSON input, constrained sentence arrangement, bounded output and deterministic English fallback. Tests covered valid mocked endpoint responses, outages, invalid/hallucinated output and schema boundaries. The real Docker dashboard displayed the deterministic fallback successfully. No GGUF was downloaded and no real Qwen3 model was run; actual inference speed and model compatibility remain unverified until a model is explicitly supplied. CPU startup instructions and the optional Compose profile are in [llm.md](llm.md).

## 7. Docker status

The image built successfully from Ubuntu 24.04. The running container identified itself as Ubuntu 24.04.5 LTS. Compose config validation, explicit DB initialization, healthy Gunicorn startup, HTTP login/health responses, demo generation, CPU ML training and restart persistence all passed. Verification used the separate `stockpilot-verification` Compose project on localhost port 5087. Its application is stopped after verification; its named data volume is preserved. The ordinary project can start independently on port 5000 using the commands below.

## 8. Tests and CI

`pytest --cov --cov-report=term-missing --cov-report=xml`: **94 passed in 92.62 seconds; 94.82% coverage** across all listed application modules, including main routes and services. Inventory and LLM services each reached 100%; ML service reached 96%. Ruff analysis, Ruff formatting, dependency compatibility (`pip check`) and whitespace checks passed. Tests use isolated temporary SQLite files and do not need GPU or a running LLM. A subsequent route/auth smoke run verified markup formatting without changing Python behavior.

GitHub Actions is configured for Ruff, tests, coverage reports/gate, Compose validation, Docker build and actual startup checks. The equivalent primary commands were run locally. The hosted Actions workflow itself was not triggered because no changes were pushed.

## 9. Remaining limits

- Real optional Qwen3 GGUF inference and the optional LLM container were not run; fallback and adapter contracts were verified.
- GitHub-hosted CI has not run; the workflow and corresponding local checks are present.
- UI checks cover actual HTTP rendering and route behavior; no automated browser screenshot/mobile layout test was run.
- Historical stock quantities/consumption are reconstructed from events. Names and prices remain current metadata; pre-migration consumption is unavailable. Models need explicit retraining and sufficient history.
- SQLite and the small synchronous architecture target an undergraduate/local application, not a high-volume multi-tenant deployment.

## 10. Exact commands

Local startup:

```bash
cd ~/Belgeler/StockPilot-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app init-db
flask --app app run --host 127.0.0.1 --port 5000
# Stop with Ctrl+C.
```

Docker startup and stop:

```bash
docker compose build app
docker compose run --rm app flask --app app init-db
docker compose up -d --wait app
docker compose down
```

Seed and train a new local demo account:

```bash
read -rsp 'New demo password (8+ characters): ' DEMO_PASSWORD; echo
export DEMO_PASSWORD
flask --app app demo-data --username demo --end-date 2026-06-30 --days 180 --seed 42
flask --app app train-models --username demo --as-of 2026-05-31
flask --app app train-models --username demo --as-of 2026-06-30
unset DEMO_PASSWORD
```

Docker equivalents use `docker compose run --rm -e DEMO_PASSWORD app flask --app app demo-data ...` and `docker compose run --rm app flask --app app train-models ...`. Never re-use an existing username for seeding.

Checks:

```bash
ruff check .
ruff format --check .
pytest --cov --cov-report=term-missing --cov-report=xml
docker compose config --quiet
```

IMPLEMENTATION STATUS: PASS
