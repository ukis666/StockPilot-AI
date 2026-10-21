# Phase 2 Strategic Quality and Contract Planning

Course: Software Quality Standards  
Project: StockPilot AI  
Team: Emirhan Keven, Ulaş Şahin, Volkan Yılmaz, Berat Kahraman  
Branch: coursework/phase-2  
Predecessor snapshot: 23051e7e1b6a9cc663de0f625c93be4c3c5839c6

## 1 Purpose and delivery boundary

This phase refines Phase 1 requirements and defines acceptance gates, test planning, and security-by-design risk treatment. The branch contains planning documents only. The existing implementation on main is a reference for later staged delivery, not a claim of development performed during this phase. No new product features are proposed.

StockPilot AI includes application-integrated, CPU-based machine learning: Gradient Boosting demand forecasts and Isolation Forest movement alerts. These are core scope, not deferred features. Training produces local artifacts through explicit CLI commands; web requests perform read-only inference. The optional local language-model adapter arranges trusted commentary sentences and has a deterministic fallback. It is distinct from the forecasting and anomaly models.

All cases below are planned acceptance scenarios, not executed results. Existing main-branch verification reports do not establish a pass for this documentation-only branch.

## 2 Team and balanced responsibilities

The same initial four members are responsible for Phase 2. A later membership update will be recorded in Phase 3.

| Member | Owned Phase 2 deliverables | Independent reviewer |
|---|---|---|
| Emirhan Keven | Requirements review, acceptance gates, dashboard cases TC-01, TC-07 and TC-10, traceability consolidation | Berat Kahraman |
| Ulaş Şahin | Inventory/database cases TC-04, TC-05, TC-06 and TC-13; transactional integrity and ownership risks | Volkan Yılmaz |
| Volkan Yılmaz | ML cases TC-08, TC-09 and TC-14; historical correctness, reproducibility and artifact risks | Emirhan Keven |
| Berat Kahraman | Authentication/product/CSV/API cases TC-02, TC-03, TC-11 and TC-12; input and browser security risks | Ulaş Şahin |

Each owner prepares case details and evidence for their component; cross-cutting execution and document consolidation do not transfer ownership of component correctness. The table assigns work and does not certify completed reviews or historical code authorship.

## 3 Requirements review and refinement

The Phase 1 scope, four use cases, technology choices and relative milestone plan remain the baseline. No feature is added or removed. The following clarifications control acceptance; original FR and QR identifiers remain stable.

| Review ID | Requirement | Clarification and rationale |
|---|---|---|
| RV-01 | FR-09 | Historical quantities use movements up to the selected UTC day; valuation uses current prices. Historical valuation is not claimed. |
| RV-02 | FR-10 | Forecasting needs at least 45 history days and 14 nonzero consumption days under the current reference design. Forecasts cover up to 90 future days. |
| RV-03 | FR-10 | Evaluate MAE on the final chronological 20% of supervised samples using rolling one-step features; compare against a seven-day moving-average baseline. This is not 90-day error. |
| RV-04 | FR-11 | Anomaly alerts are review flags, not confirmed fraud or guaranteed abnormality. At least 30 eligible movements are needed under the reference design. |
| RV-05 | FR-12 | The optional LLM only orders allowed sentences. Forecasts and reorder quantities are computed outside the LLM. A missing LLM must not block the core workflow. |
| RV-06 | FR-08 | CSV import accepts at most 1,000 product rows. Any invalid row rejects the entire batch. Export includes active products owned by the requester. |
| RV-07 | FR-07 | Archival removes a product from active operations without erasing audit history. |
| RV-08 | FR-13 | API access requires a signed, expiring bearer token; browser session cookies alone are insufficient. |
| RV-09 | QR-07 | Schema changes are explicit, backed up when pending, and must preserve legacy records. Tests must never use the operational database. |
| RV-10 | QR-06 | Core ML is CPU-based and requires no external AI account. Windows operation uses WSL2 or a Linux container because of Unix-specific application dependencies. |

Acceptance boundaries for supplementary requirements: FR-01 requires unique validated account details and safe local login redirection; FR-02 requires current-password verification for password change; FR-03 requires ownership, field and image validation; FR-04 requires owned suppliers and owner-scoped uniqueness; FR-05/06 require valid direction, nonzero movements and atomic balance/ledger writes; FR-14 requires explicit initialization, separate demo usernames and owner/date-specific artifacts.

These are planned acceptance rules to be checked against the delivered implementation, not declarations that all rules have already passed.

## 4 Quality gates

A gate is satisfied only with evidence tied to an exact implementation commit and recorded environment. Documentation branches without application code receive content review only; code checks become applicable on implementation-bearing branches.

| Gate | Acceptance condition | Required evidence |
|---|---|---|
| QG-01 Requirements | Every FR-01 to FR-14 and QR-01 to QR-09 maps to a scenario or review; no scope contradiction remains unresolved | Traceability matrix and review record |
| QG-02 Static checks | Ruff analysis and format checks exit successfully | Command, commit, environment and exit status |
| QG-03 Automated tests | All applicable cases pass; no acceptance case is silently omitted or counted as passed while skipped | Pytest report and mapping of manual cases |
| QG-04 Coverage | At least 80% overall coverage over configured application modules | Coverage XML and terminal summary; omissions recorded |
| QG-05 Data integrity | No tested invalid stock change, failed CSV batch or failed migration produces partial committed state; ownership constraints hold | State before/after and isolated DB assertions |
| QG-06 Security | Ownership, CSRF, upload, redirect and bearer-authentication cases pass; no open blocking security defect | Security scenario results and defect register |
| QG-07 ML validity | Correct cutoff and chronological evaluation; recorded model/baseline MAE; reproducible inputs/configuration; missing models handled explicitly | Dataset seed/cutoff, artifact metadata, metrics and invariance tests |
| QG-08 Resilience | Deterministic commentary works without a local LLM; persistence survives restart | Failure-path checks and restart evidence |
| QG-09 Packaging | Compose validates; image builds; explicit initialization and real HTTP startup succeed | Build/startup/health logs on an implementation-bearing snapshot |
| QG-10 Review and traceability | Changed components have a named reviewer; decisions, actual contributions, sources and AI assistance are recorded | PR/review record and linked documents |

ML does not have to beat the baseline on every product. A worse result must be reported, investigated and explained. Synthetic anomaly recovery is a controlled demonstration, not independent real-world accuracy. Test coverage is not a substitute for scenario correctness.

## 5 Test strategy and environment

The planned levels are:
- Unit and white-box checks: validators, stock operations, preprocessing/features, cutoff rules, token verification and commentary output validation.
- Integration and black-box checks: Flask requests, isolated SQLite databases, real migrations, authentication, CRUD, CSV, API and CLI.
- User acceptance: four primary use cases, visible validation/error states and dashboard interpretation.
- Packaging and smoke checks: CPU Docker build, explicit initialization, healthy HTTP startup and restart persistence.

Use Ubuntu 24.04/Python 3.12 or the supplied Linux container. Record actual package versions and container/image identity. Automated tests use temporary file-backed SQLite databases and temporary model/upload directories. CPU ML tests fit real scikit-learn estimators; local LLM HTTP responses are mocked for contract tests. Real GGUF inference is separate optional compatibility evidence and must not be claimed from mocks.

Use deterministic synthetic histories with a recorded seed and cutoff. Minimum-data and no-data cases are separate fixtures. Create at least two users for ownership tests. Use valid tiny images, invalid bytes, boundary quantities and CSV files containing a valid row followed by an invalid row. Never use production credentials, operational databases or external business data.

Entry conditions: reviewed requirement IDs; runnable selected implementation snapshot; installed test dependencies; isolated fixtures; documented expected results. Exit conditions: all applicable gates assessed, no open blocking defects, results traceable to the tested commit, and explicit limits for unexecuted or optional checks.

Formal performance/load targets are not part of the agreed scope. Runtime may be recorded for context but will not be presented as a production scalability benchmark. Actual user and systematic test execution is completed in later implementation/QA stages; this phase plans that work.

## 6 Planned acceptance cases

Every case starts in an isolated environment. After each mutation case inspect both HTTP response and persistent state. Unauthenticated requests, ownership failures and invalid input must be checked without assuming that a successful HTML response means the operation succeeded.

| ID | Setup and action | Expected result |
|---|---|---|
| TC-01 Dashboard | Log in with owned products, including zero stock and available forecasts; open dashboard and select a product | Correct owner-scoped totals, recent history and risk indicators; commentary corresponds to selected product; viewing changes no records |
| TC-02 Authentication/account | Register valid details, repeat username/email, use wrong password, log in, change password with wrong/correct current password, log out; try external next URL | Duplicate/invalid actions fail without partial updates; password is hashed; successful change accepts new password; logout is POST/CSRF protected; redirect remains local |
| TC-03 Products/suppliers/uploads | Create owned supplier and product with valid image; edit metadata and quantity; search/paginate; try foreign supplier, invalid price/quantity/image; test duplicate supplier | Valid records are owned and retrievable; invalid values or foreign references are rejected; quantity edits are audited; supplier uniqueness enforced per owner; protected images are not exposed |
| TC-04 Stock movement | Begin at 10; receive 5 then consume 3; try zero, wrong direction and consuming more than available | Final valid balance 12 with corresponding movements; invalid actions change neither balance nor ledger |
| TC-05 Atomicity/concurrency | Force a failure inside a stock transaction; test stale absolute update after another session commits | Entire failed operation rolls back; stale update is rejected; successful concurrent changes are not silently overwritten |
| TC-06 Archival | Archive an owned product containing stock, then request active list/detail and inspect audit records | Product leaves active operations; reference archive semantics reduce balance to zero with an archive movement; audit history remains |
| TC-07 Historical view | Select a past cutoff, add movements after it, revisit; submit malformed and future dates; inspect an empty account | Earlier balances and consumption remain unchanged; later model is not used; invalid dates rejected; empty view remains usable; value uses current prices |
| TC-08 Forecasting/evaluation | Build chronological synthetic series, train with sufficient history, compare recorded MAE to independently calculated holdout/baseline; test insufficient/no history and zero stock | Correct six lag/calendar features using only prior observations; chronological split; finite nonnegative forecasts up to 90 days; correct unavailable and stockout states; honest metric labels |
| TC-09 Anomalies | Train with recorded eligible movements; inspect flags, introduce controlled synthetic spikes and test insufficient-data state | Only eligible owned movements at/before cutoff are considered; report flag count and detected controlled spikes; no eligibility gives unavailable model, not proof of normality |
| TC-10 Commentary | Request summary without endpoint; supply valid sentence-index response, timeout, invalid/oversized response, disallowed host or redirect | Only trusted complete sentences are rendered; all invalid/unavailable paths use deterministic fallback; stock/model data remains unchanged |
| TC-11 CSV | Import two valid rows; then import valid first row and invalid second; test missing headers, bad encoding, >1,000 rows; export formula-like names | Valid batch creates audited products; any invalid batch commits none; limits enforced; export contains only owned active products and neutralizes spreadsheet-formula prefixes |
| TC-12 API/access | Obtain token; perform product CRUD and allowed movements; try missing/expired/invalid token, session-only auth, foreign IDs and internal movement kind | Valid actions return documented success statuses; malformed inputs and unauthorized access fail; tokens expire; owner boundaries and stock rules match HTML services |
| TC-13 Migration/persistence | Initialize empty DB twice; upgrade a legacy fixture; force failed migration; restart/recreate app/container after recording stock | Repeated initialization safe; old records preserved; failed migration rolled back with planned backup evidence; committed data/session secret persist; FK checks clean |
| TC-14 CLI/reproducibility | Generate separate demo with fixed seed/date, repeat using another new username, reject existing username, train for two cutoffs | Existing users unchanged; equivalent seeded histories; owner/date-specific artifacts; repeated same-input metrics reproducible; later records do not affect earlier training/forecast |

For real user checks, each scenario owner walks through their Phase 1 use case and a different member observes the result. Record usability defects separately from automated test failures. Boundary assertions are expanded into executable parametrized tests when applicable, rather than treating this table as evidence of execution.

## 7 Requirements traceability

| Requirement | Planned cases | Gate |
|---|---|---|
| FR-01 | TC-02, TC-12 | QG-03, QG-06 |
| FR-02 | TC-02, TC-03 | QG-03, QG-06 |
| FR-03 | TC-03, TC-06, TC-12 | QG-03, QG-05 |
| FR-04 | TC-03 | QG-03, QG-05 |
| FR-05 | TC-04, TC-12 | QG-03, QG-05 |
| FR-06 | TC-03, TC-04, TC-05, TC-11 | QG-05 |
| FR-07 | TC-06 | QG-03, QG-05 |
| FR-08 | TC-11 | QG-03, QG-05, QG-06 |
| FR-09 | TC-01, TC-07 | QG-03, QG-07 |
| FR-10 | TC-07, TC-08, TC-14 | QG-07 |
| FR-11 | TC-09, TC-14 | QG-07 |
| FR-12 | TC-01, TC-10 | QG-08 |
| FR-13 | TC-12 | QG-03, QG-06 |
| FR-14 | TC-13, TC-14 | QG-05, QG-07, QG-09 |
| QR-01 | TC-01, TC-03, TC-07, TC-12 | QG-06 |
| QR-02 | TC-04, TC-05, TC-06, TC-11 | QG-05 |
| QR-03 | TC-02, TC-03, TC-10, TC-11, TC-12 | QG-06 |
| QR-04 | TC-07, TC-08, TC-09, TC-14 | QG-07 |
| QR-05 | TC-08, TC-09, TC-14 | QG-07 |
| QR-06 | TC-08, TC-09, TC-10, TC-13, TC-14 | QG-08, QG-09 |
| QR-07 | TC-13 | QG-05, QG-08, QG-09 |
| QR-08 | Static/test/coverage runs over the delivered snapshot | QG-02, QG-03, QG-04 |
| QR-09 | Setup instructions, attribution, contributions and AI-record content review | QG-01, QG-10 |

## 8 Security risk assessment

Likelihood and impact use 1 low, 2 medium and 3 high. Score = likelihood × impact. Scores 6–9 receive high priority, 3–4 medium and 1–2 low. These are initial planning estimates, not measured exploitability. A proposed control is not considered verified until its case passes.

| Risk | Threat and affected asset | L/I/score | Required treatment and verification | Owner |
|---|---|---|---|---|
| R-01 | Foreign product/image access exposes or changes another user's inventory | 2/3/6 | Owner-scoped reads/writes and composite references; two-user HTML/API/image checks in TC-03/12 | Ulaş |
| R-02 | CSRF or unsafe redirect permits unintended browser actions | 2/3/6 | CSRF protection on mutations, POST logout and local redirect validation; TC-02/03 | Berat |
| R-03 | Malformed or oversized uploads expose files or exhaust resources | 2/2/4 | Content/dimension/body limits, randomized names, private retrieval; invalid and ownership checks TC-03 | Berat |
| R-04 | Partial/stale updates corrupt balances and history | 2/3/6 | Atomic conditional writes, constraints, stale update rejection and rollback; TC-04/05/11 | Ulaş |
| R-05 | Insecure secret/token handling grants unauthorized access | 2/3/6 | Persistent private secret, hashed passwords, expiring bearer token, no secrets in commits; TC-02/12/13 and configuration review | Berat |
| R-06 | Spreadsheet formulas in exported user text execute when opened | 2/2/4 | Neutralize formula prefixes; TC-11 | Berat |
| R-07 | Future data contaminates past forecasts and misleads decisions | 2/3/6 | Cutoff-bound queries/artifacts and prior-only features; TC-07/08/14 | Volkan |
| R-08 | Untrusted joblib artifact can execute code on deserialization | 1/3/3 | Load only trusted locally generated artifacts from protected paths; no user artifact uploads; CLI/path and permissions review | Volkan |
| R-09 | LLM endpoint or output enables unintended requests or fabricated advice | 2/2/4 | Local-host allowlist, no redirects, time/size limits and trusted sentence indexes; TC-10 | Volkan |
| R-10 | Migration/test actions delete operational data | 2/3/6 | Explicit migration, backup, rollback, isolated test DBs and safe volume commands; TC-13 | Ulaş |
| R-11 | Synthetic metrics or missing-model states are presented as proven real-world accuracy | 2/2/4 | Accurate labels, explicit unavailable states and evaluation limitations; TC-01/08/09 and report review | Emirhan |
| R-12 | Exposed deployment or repeated login attempts compromise the local prototype | 2/3/6 | Keep demo localhost-bound; review HTTPS/secure-cookie configuration before external deployment; rate limiting is not established by this plan | Emirhan |

External production deployment is outside the fixed scope. If that scope changes, revisit R-05 and R-12 before exposure rather than treating localhost assumptions as production controls. Findings that cannot be fixed within scope require documented restriction or acceptance by the responsible team and instructor where relevant; they are not silently marked closed.

## 9 Defect handling and review evidence

Record each finding with ID, requirement/case, reproducible steps, expected/actual result, severity, owner, affected commit, evidence, fix commit and independent retest.

- Blocking: unauthorized data exposure/mutation, data loss, ledger corruption, core workflow unavailable, or invalid evaluation that undermines reported results.
- Major: a required workflow fails while a limited workaround exists.
- Minor: presentation or usability defect without data/security impact.

No blocking finding may remain open at acceptance. Major/minor exceptions require explicit rationale, owner and scope statement; do not count failed cases as passed. Planned reviews in the responsibility table are pending, not approvals. Use actual GitHub PRs or review records in implementation stages.

## 10 Phase 3 handoff and staged implementation order

Phase 3 starts from this documentation snapshot, updates the team, and brings reviewed code from the reference main branch in dependency order:
1. Application factory/configuration, database entities, migrations and explicit initialization, with relevant validation checks.
2. Authentication and owner-scoped product/supplier/stock workflows, including shared inventory rules.
3. CSV/API and dashboard integration.
4. CPU ML, seeded demo/training commands and optional commentary integration.
5. Applicable tests and packaging accompany components as needed; Phase 4 expands systematic execution, complexity analysis and deployment evidence.

Architecture and design alternatives are documented before accepting each increment. The sequence is a planned packaging/review order for an existing reference implementation, not a statement of original creation dates. Detailed commit boundaries are decided during Phase 3. Main remains untouched.

## 11 Phase 2 status and outstanding inputs

Prepared: requirements refinements, acceptance gates, test strategy, 14 scenario groups, complete FR/QR mapping, risk register, contribution allocation and Phase 3 handoff.

Not claimed: executed tests, achieved coverage, completed member reviews, real local-LLM compatibility or instructor approval. Official calendar dates and the exact class-specific DIR format remain pending.

The upstream attribution and blank LICENSE discrepancy identified in Phase 1 remain open. Preserve accurate upstream disclosure and verify the authoritative license; original-work acceptance must be clarified with the instructor. No document changes imply that approval exists.

## 12 AI assistance record

Task: Phase 2 planning and documentation.  
Tool: OpenAI ChatGPT with GitHub integration.  
Inputs: Current Phase 1 snapshot, previously inspected main-branch implementation/docs/tests, course handout, and user instructions to retain existing models/features, use English and keep four members in Phase 2.  
Assistance: Drafted refinements, gates, test scenarios, traceability, risks and responsibilities; prepared the documentation-only branch.  
Human review: Pending team review; member approvals and work completion are not inferred.  
Verification: Branch file-tree/content checks only; no application test execution for this planning task.

Map this factual record to the instructor's DIR format and scoring rubric when supplied. It is not a completed class-specific DIR declaration and does not reconstruct earlier implementation AI use.

## 13 References

1. Software Quality Standards Group Project handout supplied by the team.
2. Phase 1 predecessor: https://github.com/ukis666/StockPilot-AI/tree/23051e7e1b6a9cc663de0f625c93be4c3c5839c6
3. Existing implementation reference: https://github.com/ukis666/StockPilot-AI/tree/50984580836c4131ebeed5c7182149e0101c2da1
4. Implementation architecture, ML, testing and upstream documents in the reference snapshot.
5. OpenAI ChatGPT assistance, as recorded in Section 12.
