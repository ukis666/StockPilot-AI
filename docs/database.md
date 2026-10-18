# Database and migrations

SQLite file storage is persistent. Local default: `inventory.db` at the project root, preserving the original path. Docker: `/data/inventory.db`, in a named volume. Set `DATABASE_URL=sqlite:////absolute/path/file.db` to select another file. Normal operation never uses memory databases.

Run `flask --app app init-db` explicitly before registering. Alembic revision 001 creates or adopts the original user/item schema. Revision 002 adds suppliers, archival, indexes, nonnegative checks and the movement ledger. Existing users, password hashes, identifiers, profile fields, product images and quantities are preserved. Legacy nullable item ownership is retained for compatibility; unowned records remain inaccessible through application routes. New products always have authenticated owners.

Pending upgrades create a consistent SQLite `.bak` using the SQLite backup API. All migration DDL and version updates run in one explicit `BEGIN IMMEDIATE` transaction. Failed upgrades roll back; negative legacy balances/prices or broken foreign keys require manual review, never automatic data removal. Re-running initialization at the current revision does nothing. Destructive downgrades are disabled. Stop application writers during migrations; retain and verify backups before future schema changes.

Core relationships:

| Relationship | Enforcement |
|---|---|
| User → products | `item.user_id` FK; owner-scoped routes |
| User → suppliers | Non-null `supplier.user_id` FK |
| Supplier → products | Optional `supplier_id`; composite FK requires same owner |
| Product → movements | `stock_movement.item_id` FK; composite FK requires same owner |
| User → movements | `stock_movement.user_id` FK; nullable only for legacy unowned balances |

Unique usernames/emails and supplier names within an owner prevent duplicate identities. Product names are deliberately not unique: separate products can share a display name. Owner/time and item/time indexes support history queries. Surrogate/composite unique keys support owner-safe references. ER and UML diagrams are in [architecture.md](architecture.md).

Every nonzero stock change creates a movement in the same transaction: opening, receipt, consumption, adjustment, archive. Quantity edits create adjustments, not consumption observations. Conditional SQL updates prevent negative inventory and lost relative updates. Absolute edits and archive operations reject stale balances. Failed operations roll back the whole request/batch. Physical product deletion is unavailable; archival keeps the audit ledger.

`occurred_at` is the inventory event time; `created_at` is the insertion time. Both use naive UTC for SQLite interoperability. Demo generation supplies explicit historical event times. Ordinary users cannot backdate events. Historical balances sum deltas before midnight following the selected UTC day; future movements and later archives are excluded.

Existing upstream quantities have no genuine consumption history. Migration records an opening balance at migration time; earlier balances are unknown and are not reconstructed. Names, supplier descriptions and unit prices are current metadata, not temporal records. The dashboard labels valuation accordingly. The ledger supports historical stock quantities and consumption, not historical prices.

To restore a backup, stop writers, preserve the current database and its SQLite sidecar files, copy the verified backup into the configured location, then run `init-db` to apply any necessary forward migrations. Never run test teardown against an operational database: fixtures always use `tmp_path` SQLite files.
