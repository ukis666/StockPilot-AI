# StockPilot AI

**Predictive Inventory Intelligence** — a Flask/Jinja inventory application for a four-person undergraduate Software Quality Standards assignment. SQLite keeps inventory and an auditable stock ledger; scikit-learn provides CPU forecasting and anomaly detection. An optional local llama.cpp service arranges short English commentary. No GPU or external AI account is required.

## Run locally (Ubuntu 24.04 / Python 3.12)

```bash
cd ~/Belgeler/StockPilot-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app init-db
flask --app app run --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000/auth/register and create an account. Stop with Ctrl+C. The default database is the original repository's `inventory.db`. Initialization is explicit, idempotent, and upgrades an empty or original upstream database without deleting users. Pending migrations create a timestamped SQLite backup. Startup never recreates the database.

## Reproducible demonstration

Use a new username; existing usernames are rejected. Choose a completed date in the past. The following fixed example creates 30 products, four suppliers and 180 days ending on 2026-06-30.

```bash
read -rsp 'New demo account password (8+ characters): ' DEMO_PASSWORD; echo
export DEMO_PASSWORD
flask --app app demo-data --username demo --end-date 2026-06-30 --days 180 --seed 42
flask --app app train-models --username demo --as-of 2026-05-31
flask --app app train-models --username demo --as-of 2026-06-30
unset DEMO_PASSWORD
```

Log in as `demo` using the password you entered. Open the dashboard and select **2026-06-30**, then **2026-05-31**. Inspect stock balances, consumption bars, forecasts, estimated stockout dates, model/baseline MAE, movement history, anomaly alerts and English commentary. Select a product in the briefing. Dates before the first eligible model show an explicit unavailable state. Forecasts cover 90 days; a missing stockout date can mean insufficient history or no stockout within that horizon.

## Docker (CPU only)

```bash
docker compose build app
docker compose run --rm app flask --app app init-db
docker compose up -d --wait app
# Stop, preserving database, uploads, secret and model artifacts:
docker compose down
```

Initialize demo data and train inside Docker:

```bash
read -rsp 'New demo password (8+ characters): ' DEMO_PASSWORD; echo
export DEMO_PASSWORD
docker compose run --rm -e DEMO_PASSWORD app flask --app app demo-data --username demo --end-date 2026-06-30 --days 180 --seed 42
docker compose run --rm app flask --app app train-models --username demo --as-of 2026-06-30
unset DEMO_PASSWORD
```

Open http://127.0.0.1:5000. Docker uses a separate persistent named volume, `stockpilot-data`, mounted at `/data`; the host's original `inventory.db` is never overwritten or copied into an image. `docker compose down` preserves data. Avoid `down -v` unless deliberately deleting that separate Docker dataset. Port can be changed with `APP_PORT=5050 docker compose up -d app`.

The application starts without an LLM. See [LLM setup](docs/llm.md) for optional Qwen3-0.6B GGUF setup. Model files are never downloaded automatically. See [.env.example](.env.example) for configuration.

## Quality checks

```bash
source .venv/bin/activate
ruff check .
ruff format --check .
pytest --cov --cov-report=term-missing --cov-report=xml
# Container checks use the disposable development-container command in docs/testing.md.
```

The runtime image contains runtime dependencies only. For container tests, use the disposable development-container command in [testing documentation](docs/testing.md).

CI runs static checks, all unit/integration tests, an 80% coverage gate, a Docker build and real HTTP startup checks. No test needs a running LLM or GPU.

## Documentation and attribution

- [Architecture, ER and UML diagrams](docs/architecture.md)
- [Database and migrations](docs/database.md)
- [ML design and historical correctness](docs/ml.md)
- [Local LLM integration](docs/llm.md)
- [Docker and verification](docs/testing.md)
- [Four-person deliverables](docs/team.md)
- [Upstream attribution and changes](docs/upstream.md)
- [Verified implementation report](docs/verification.md)

Based on [Rumaisa Islam's inventory-management-flask](https://github.com/Rumaisas-islam/inventory-management-flask), MIT licensed, copyright © 2025 Rumaisa Islam. The upstream [LICENSE](LICENSE) is preserved unchanged. StockPilot AI modifications are documented in `docs/upstream.md`.
