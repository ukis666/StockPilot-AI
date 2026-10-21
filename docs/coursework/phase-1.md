# Phase 1 Team Formation and Environment Setup

Course: Software Quality Standards  
Project: StockPilot AI  
Repository: https://github.com/ukis666/StockPilot-AI  
Phase branch: coursework/phase-1  
Reference implementation commit: 50984580836c4131ebeed5c7182149e0101c2da1

## 1 Purpose and project baseline

StockPilot AI helps small businesses record inventory, trace stock movements, and inspect consumption forecasts and unusual movements. The coursework will assess and document an existing implementation against explicit requirements, quality criteria, and review evidence. No new product features are planned.

This branch contains planning documents only, with no application implementation, runtime dependencies, tests or deployment files. The reference implementation already exists on main. This document establishes the coursework plan; it does not claim that implementation occurred after this plan, that planned reviews have already taken place, or that the responsibility allocation below proves historical code authorship. Phase branches organize deliverables and subsequent verification work rather than reconstructing a development history.

## 2 Problem and intended users

Small businesses need a consistent way to maintain product balances, understand why balances changed, and identify products that may need replenishment. Manual records can obscure movement history and make unusual consumption difficult to investigate.

The intended actor is an authenticated small-business inventory user. Each account owns its products, suppliers, and movement records. Team responsibilities are not application permission roles. The application does not provide a shared company workspace with multiple staff roles.

## 3 Scope and boundaries

Included capabilities are registration and login; profile and password management; product creation and editing; product images; supplier creation and listing; search and pagination; stock receipts and consumption; product archival with retained movement history; atomic CSV import and CSV export; an owner-scoped bearer API; historical inventory views; CPU-based demand forecasting and anomaly detection; and a dashboard with inventory summaries and replenishment commentary.

Forecasting uses Gradient Boosting with a seven-day moving-average comparison. Isolation Forest flags movements for review. Training is explicitly invoked through CLI commands. Seeded synthetic data supports repeatable demonstrations.

The optional local LLM can reorder trusted, precomputed commentary sentences. It does not calculate forecasts, invent recommendations, execute actions, or modify stock. Deterministic commentary remains available without a model service.

Excluded work includes new product features, purchase-order execution, payments, ERP integrations, physical warehouse automation, a new frontend framework, cloud-scale deployment, and claims of demonstrated real-business forecasting accuracy. Existing SQLite and synchronous Flask architecture are retained.

Historical quantities are reconstructed from movements; product names and prices remain current metadata. Forecasts require sufficient history and an eligible trained model. The forecast horizon is 90 days; its one-step validation MAE is not a measurement of 90-day forecast accuracy.

## 4 Initial team and responsibilities

The initial Phase 1 team contains four members.

| Member | Primary responsibility | Concrete coursework outputs | Review partner |
|---|---|---|---|
| Emirhan Keven | Coordination, requirements and dashboard | Scope and requirement register; milestone tracking; UC-01; dashboard requirement mapping and review | Reviews Volkan's forecast presentation and limitations |
| Ulaş Şahin | Database, inventory services and integrity | Data model explanation; UC-02; stock and ownership rules; database and ledger test mapping | Reviews Berat's product validation and ownership integration |
| Volkan Yılmaz | Forecasting, anomaly detection and evaluation | ML design explanation; UC-03; feature and cutoff rules; evaluation and reproducibility test mapping | Reviews Ulaş's historical data semantics |
| Berat Kahraman | User, product, supplier and interface workflows | UC-04; form and access requirements; UI/API workflow mapping; authentication and CSV review | Reviews Emirhan's dashboard and requirement completeness |

Every member documents and tests their assigned area, participates in issue triage, and reviews another area. Emirhan coordinates integration; coordination does not replace the other members' responsibility for their own deliverables.

Phase 1 and Phase 2 use the same four-person allocation. Membership changes will be documented in the Phase 3 team update, without retroactively assigning earlier work.

## 5 Functional requirements

| ID | Requirement | Main use case or verification area |
|---|---|---|
| FR-01 | A visitor can register with valid unique account details and authenticate; an authenticated user can log out. | Authentication |
| FR-02 | A user can view and update their profile and change their password after providing the current password. | Account |
| FR-03 | A user can create, view, edit, search and paginate their own active products, including supported product images and optional supplier association. | UC-04 |
| FR-04 | A user can create and list their own suppliers. | UC-04 |
| FR-05 | A user can record a positive stock receipt or a stock consumption against an owned active product. | UC-02 |
| FR-06 | Each successful quantity change must record a corresponding stock movement; invalid changes must not partially update inventory. | UC-02 |
| FR-07 | A user can archive a product while retaining its movement history; archived products leave active listings. | Product lifecycle |
| FR-08 | A user can import products from CSV atomically and export their active products as CSV. | CSV transfer |
| FR-09 | A user can inspect dashboard stock totals, stock value, recent movements and risk indicators for a selected date no later than the current UTC date. | UC-01 |
| FR-10 | With sufficient history and an eligible trained artifact, the system provides product consumption forecasts, an estimated stockout date when reached within the horizon, and model/baseline MAE. Otherwise it indicates unavailability. | UC-03 |
| FR-11 | With an eligible anomaly model, the system flags unusual owner-scoped movements for investigation. | UC-03 |
| FR-12 | The system provides deterministic product commentary and can optionally arrange the same trusted sentences using a configured local LLM. | UC-01 |
| FR-13 | The bearer API authenticates tokens and supports owner-scoped product CRUD and permitted stock movements. | API |
| FR-14 | CLI commands initialize or upgrade the schema, generate a separate seeded demo account, and train user/date-specific model artifacts. | Environment and reproducibility |

## 6 Initial quality requirements

These requirements establish the Phase 1 baseline. Phase 2 will define explicit gates, risks and test cases.

| ID | Requirement |
|---|---|
| QR-01 | Users must not read or mutate another account's protected inventory or images through supported HTML or API routes. |
| QR-02 | Quantities must remain nonnegative; balance updates and associated ledger writes must commit or roll back together. |
| QR-03 | Browser mutations must receive CSRF protection, passwords must be hashed, and uploads must be validated. |
| QR-04 | A historical calculation must exclude movements after the selected cutoff and must not load a later model artifact. |
| QR-05 | Demo generation and model evaluation must be reproducible with recorded seed, dates and configuration. Synthetic results must be identified as synthetic. |
| QR-06 | The core application and tests must run on CPU without a GPU, external AI account or running LLM. |
| QR-07 | Initialization must be explicit and preserve existing data; container recreation must preserve the configured persistent dataset. |
| QR-08 | Subsequent changes must pass Ruff and the automated test suite with at least 80% overall configured coverage. |
| QR-09 | The repository must include runnable setup/test instructions and accurate attribution, contribution and AI-use records. |

## 7 Use cases

### UC-01 Inspect inventory status

Responsible member: Emirhan Keven  
Actor: Authenticated inventory user  
Related requirements: FR-09, FR-12, QR-01, QR-04

Preconditions: The user has an account and is logged in.

Main flow:
1. The user opens the dashboard.
2. The user selects today or an earlier valid date.
3. The system retrieves only the user's eligible products and movements.
4. The system displays balances, current-price stock value, recent history and available risk indicators.
5. The user selects a product and inspects its available forecast and commentary.

Alternative flows: A malformed or future date is rejected. An account with no eligible products receives an empty dashboard. Missing model/history is displayed as unavailable. Missing or invalid LLM service produces deterministic commentary.

Postconditions: No stock or movement record is changed by viewing the dashboard.

### UC-02 Record a stock movement

Responsible member: Ulaş Şahin  
Actor: Authenticated inventory user  
Related requirements: FR-05, FR-06, QR-01, QR-02, QR-03

Preconditions: The user owns an active product.

Main flow:
1. The user opens the product detail page.
2. The user chooses receipt or consumption and enters a positive quantity and optional note.
3. The system validates the request and ownership.
4. The system updates the stock and records the signed movement in one transaction.
5. The system displays the resulting balance and movement history.

Alternative flows: Invalid inputs are rejected. Consumption exceeding available stock is rejected without changing stock or history. An unavailable or foreign product cannot be modified. A persistence failure rolls back the operation.

Postconditions: On success, the stock balance and movement ledger agree; on failure, neither is partially updated.

### UC-03 Inspect forecasts and unusual movements

Responsible member: Volkan Yılmaz  
Actor: Authenticated inventory user  
Related requirements: FR-10, FR-11, QR-01, QR-04, QR-05

Preconditions: The user has recorded history. Eligible model artifacts have been explicitly generated when enough history exists.

Main flow:
1. The user selects a valid dashboard cutoff date and product.
2. The system loads the latest eligible user-specific artifact at or before the cutoff.
3. The system builds consumption history without later movements.
4. The system shows available demand forecasts, stockout estimates and chronological one-step model/baseline MAE.
5. The user inspects flagged movements and their history.

Alternative flows: Insufficient history or absent model produces an unavailable state. No stockout within 90 days produces no estimated stockout date. No anomaly model produces no model alerts and must not be presented as proof that all movements are normal.

Postconditions: Analysis is read-only; users decide whether any follow-up inventory action is appropriate.

### UC-04 Create a product with an optional supplier

Responsible member: Berat Kahraman  
Actor: Authenticated inventory user  
Related requirements: FR-03, FR-04, FR-06, QR-01, QR-02, QR-03

Preconditions: The user is logged in. An owned supplier can be created first if required.

Main flow:
1. The user opens the product creation form.
2. The user enters a product name, quantity, price and optional descriptive fields, supplier and image.
3. The system validates fields, supplier ownership and image content.
4. The system creates the owned product and an opening movement if the initial quantity is nonzero.
5. The system displays the product detail page.

Alternative flows: Invalid quantity, price, supplier or image is rejected. A zero opening quantity creates no zero-valued movement. A failed operation must not leave a partially created product or committed stock movement.

Postconditions: A valid product appears in the user's active inventory; its initial quantity is traceable through the ledger when nonzero.

## 8 Technology and tool selection

| Area | Selected approach | Reason and boundary |
|---|---|---|
| Runtime | Python 3.12 and Flask | Matches the existing application; small, inspectable server architecture |
| Interface | Jinja templates and local CSS | Retains server rendering without a separate frontend build |
| Persistence | SQLite, Flask-SQLAlchemy and Alembic | Adequate for a local undergraduate application; explicit migrations and transactional integrity |
| Authentication and forms | Flask-Login and Flask-WTF | Existing session and CSRF mechanisms |
| ML | scikit-learn, NumPy and joblib | Reproducible CPU estimators and local artifacts |
| Optional commentary | Local llama.cpp-compatible HTTP endpoint | Optional, bounded use; deterministic fallback required |
| Tests and static checks | Pytest, pytest-cov and Ruff | Existing automated checks and coverage gate |
| Packaging | Docker Compose and Gunicorn | Reproducible CPU environment and persistent application data |
| Collaboration | GitHub issues, branches and pull requests | Traceable assignment, review and verification records |
| Work management | Kanban | Small tasks and continuous review fit documentation and verification of an existing product |

## 9 Planned implementation environment

Use Ubuntu 24.04 with Python 3.12, or the supplied Docker environment. Native Windows compatibility is not assumed: the application imports the Unix-specific fcntl module. Windows users should use WSL2 or the Linux container.

The commands below are reference instructions for a later implementation-bearing branch, not commands runnable from this documentation-only Phase 1 snapshot. Phase 1 environment preparation consists of selecting the OS/runtime/tools and recording member setup status; application execution is not a Phase 1 deliverable.

Local setup on a later implementation-bearing branch:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app init-db
flask --app app run --host 127.0.0.1 --port 5000
```

Initial checks:

```bash
ruff check .
ruff format --check .
pytest --cov --cov-report=term-missing --cov-report=xml
```

Docker alternative:

```bash
docker compose build app
docker compose run --rm app flask --app app init-db
docker compose up -d --wait app
docker compose down
```

Use separate demo/test data and keep secrets, operational databases, uploads and model artifacts out of commits. Each member records their environment, executed commands and observed results in their subsequent work evidence. These instructions are a plan, not a claim that each team member has already completed setup. Previously reported test metrics remain attributed to the existing verification report until rerun.

## 10 Workflow and branch policy

The reference main branch is preserved. Coursework changes are made only on explicitly selected coursework or task branches. No automatic merge to main is authorized.

Kanban columns: Backlog, Ready, In Progress, In Review, Done. Each task records an owner, linked requirement or deliverable, acceptance criteria, reviewer and evidence.

The Phase 1 document is maintained on coursework/phase-1. Phase 2 will start from the Phase 1 snapshot and add only requirements refinements, quality gates, test planning and security risk assessment. Phase 3 will start from Phase 2 and introduce architecture/design evidence and selected implementation increments from the reference main branch, each with review and applicable checks. No complete application is included in Phase 1 or Phase 2. Main remains a reference, not the starting file tree for future phase branches.

A task is Done when its acceptance criteria are met, its assigned reviewer has inspected it, applicable checks are recorded, and related documents are updated. Documentation-only changes require content and consistency review; code changes require relevant tests. Record actual contributors and AI assistance without backdating work or assigning fictional authorship.

## 11 Relative milestone plan

Official calendar deadlines will be taken from the course syllabus when available. The following is a relative plan, not a statement of official due dates.

| Window | Milestone | Outputs |
|---|---|---|
| First 2–3 week interval | Phase 1 | Initial four-person team, scope, requirements, use cases, environment and workflow plan |
| Following 2–3 week interval | Phase 2 | Four-person requirements refinement, quality gates, test plan and security risks; no application implementation |
| Following 2–3 week interval | Phase 3 | Updated team allocation, architecture and alternatives, technical decisions, selected implementation increments, real code reviews and justified corrections |
| Following 2–3 week interval | Phase 4 | Systematic tests, defect resolution, module complexity analysis and deployment evidence |
| Course final submission window | Phase 5 | Consolidated report of at most 20 pages including references, repository/run/test instructions, demo and individual lessons |

The final report will summarize phase artifacts within the page limit. Repository documentation is working evidence, not an instruction to paste every file into the final report. Instructor repository access must be verified before submission.

## 12 Attribution and open decisions

The implementation identifies Rumaisas-islam/inventory-management-flask as an upstream source. Retained baseline functionality must be distinguished from StockPilot-specific extensions and subsequent coursework changes. Instructor acceptance of this reuse under the original-work requirement has not been confirmed.

The current LICENSE file is blank although existing documentation says an MIT notice is preserved. This discrepancy must be resolved from the authoritative upstream license before redistribution or final submission; this Phase 1 documentation change does not silently repair it.

Other open items are official deadlines, actual completion evidence for each member's environment setup, and the instructor's exact DIR disclosure/scoring format. Student numbers are intentionally omitted at the team's request.

## 13 AI assistance disclosure

Task: Phase 1 planning and documentation.  
Tool: OpenAI ChatGPT with GitHub integration.  
Use: Read repository documentation and selected source/test files; draft requirements, use cases, responsibility allocation, environment guidance and relative milestones using team information supplied by Emirhan Keven.  
Human input: Team names, initial four-person membership, four-person scope for Phase 1 and Phase 2, with subsequent onboarding recorded in Phase 3, English-language output, fixed feature scope and branch-only changes.  
Review status: Prepared for team review; no claim that all four members have approved it or performed the assigned work. No application tests were executed for this documentation-only task.

This factual record is not labeled a completed DIR statement: the class-specific DIR structure and scoring instructions were not supplied. The team must map this record and other actual AI uses to that format before submission. This entry does not cover or reconstruct earlier AI-assisted implementation.

## 14 References

1. Course handout, Software Quality Standards Group Project, supplied by the team.
2. StockPilot AI reference implementation, commit 50984580836c4131ebeed5c7182149e0101c2da1: https://github.com/ukis666/StockPilot-AI/tree/50984580836c4131ebeed5c7182149e0101c2da1
3. Repository architecture, database, ML, testing, upstream and verification documents in the reference implementation: https://github.com/ukis666/StockPilot-AI/tree/50984580836c4131ebeed5c7182149e0101c2da1/docs
4. Identified upstream project: https://github.com/Rumaisas-islam/inventory-management-flask
5. OpenAI ChatGPT, AI assistance for this Phase 1 document, as disclosed in Section 13.
