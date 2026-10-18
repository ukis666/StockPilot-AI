# Four-person task distribution

| Student | Concrete code deliverables | Testing responsibilities |
|---|---|---|
| 1 — Database and inventory backend | `models.py`, `extensions.py`, `services/inventory.py`, migrations, init command, stock/API ownership checks | Migration preservation/rollback, restart persistence, FKs, CRUD, concurrent/stale updates, nonnegative inventory, ledger consistency; `test_models.py`, inventory/API portions of `test_routes.py` and `test_api.py` |
| 2 — Machine learning | `services/ml.py`, `services/demo.py`, train/demo CLI commands, artifact metadata and evaluation JSON | Reproducible histories, lag correctness, chronological MAE/baseline, CPU training, anomaly flags, future-data invariance; `test_ml.py` and training CLI coverage |
| 3 — Frontend and local LLM | `templates/`, `static/css/style.css`, dashboard presentation in `main.py`, `services/llm.py`, account/auth forms and local endpoint integration | Responsive UI inspection, HTML smoke rendering, accessible labels, CSRF forms, LLM JSON bounds, response validation/fallback; `test_llm.py`, UI/auth/profile portions of route tests |
| 4 — Docker, CI/CD and QA | `Dockerfile`, `compose.yaml`, `.dockerignore`, workflow, pinned dependency files, `pyproject.toml`, isolated pytest fixtures and verification documentation | Full suite and ≥80% coverage gate, Ruff, real Docker build/startup, HTTP registration/login/persistence checks, optional LLM boundary status; `conftest.py`, `test_commands.py`, integration review |

Each student reviews one neighboring component's integration (1→2 data semantics, 2→3 forecast display, 3→4 packaging, 4→1 rollback and authorization). Use separate commits/PRs in normal coursework; this implementation does not fabricate student authorship, create artificial histories, push or merge anything. These are suggested responsibility boundaries, not claims that four people already made the changes.
