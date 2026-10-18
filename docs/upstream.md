# Upstream attribution and changes

Original project: [Rumaisas-islam/inventory-management-flask](https://github.com/Rumaisas-islam/inventory-management-flask), by Rumaisa Islam. The upstream MIT license and `Copyright (c) 2025 Rumaisa Islam` are preserved verbatim in the repository's `LICENSE`. Existing Git remotes and branch history are not modified.

StockPilot AI continues the original Flask, SQLAlchemy, Flask-Login, Flask-WTF and Jinja approach. Existing root modules are repaired and reused where practical. New services contain the inventory ledger, synthetic history, scikit-learn analytics and optional local commentary. The old public branding and hardcoded footer are replaced by StockPilot AI / Predictive Inventory Intelligence. License attribution remains in this documentation and the license.

Reproducible upstream defects addressed:

- Existing-but-empty SQLite file skipped table creation, producing `no such table: user`. Explicit versioned migrations replace file-existence initialization.
- Two separate application factories, multiple AddItemForm definitions, duplicate dashboards and inconsistent template contexts.
- Test setup could create/drop operational tables; all fixtures now use isolated file-backed databases.
- Invalid Flask-Login version in upstream dependencies and Flask-WTF/Werkzeug incompatibilities. Pinned runtime/dev requirements replace unnecessary PyJWT, pytz and Flask-Migrate dependencies; Alembic is used directly.
- API was unregistered and called missing token/serialization methods, used `owner_id` instead of `user_id`, and exposed unscoped reads. The registered API now uses expiring signed bearer tokens and owner-scoped CRUD/movements.
- Hardcoded secret, GET logout, unsafe `next` redirects, unprotected profile mutations, unsafe avatar overwrites and silent CSV row errors. Sessions, CSRF, validation, randomized image names and atomic imports fix these paths.
- Direct quantity edits lacked an audit record; deletion erased history. Shared stock operations and archival now preserve a complete ledger.
- `profile.py` shadowed the Python standard library module used by profiling tools; its useful account functionality is retained in `account.py`.

Cleanup removes the duplicate factory file, redundant dashboard module, duplicate forms, obsolete templates and old screenshot/banner artifacts. Existing uploaded product/avatar images are retained to preserve user files. Local virtual environments, caches, databases, backups, model weights, artifacts and environment secrets are excluded from versioned/deliverable content. Useful original product images, profiles, password changes, search, pagination and CSV import/export remain functional.

New functionality: Supplier and StockMovement entities; atomic inventory transactions; forward migrations/backups; seeded 30-product history; Gradient Boosting MAE comparison; Isolation Forest alerts; historical simulation; validated commentary; CPU Docker Compose; tests, coverage, Ruff, GitHub Actions and aligned architecture/team documentation.
