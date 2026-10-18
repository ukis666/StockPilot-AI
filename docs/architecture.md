# Architecture

One Flask factory (`app.py`) registers inventory (`main.py`), authentication (`auth.py`), profile (`account.py`) and bearer API (`api.py`) blueprints. Jinja templates and local CSS render the responsive navy/teal UI without a JS build or CDN. Flask-Login manages sessions; Flask-WTF protects HTML mutations against CSRF. The bearer-only API does not accept session authentication.

`services/inventory.py` owns product validation and atomic quantity/ledger writes. SQLite is accessed through Flask-SQLAlchemy with foreign keys enabled for every connection. Alembic migrations run only via `init-db`. Products are archived rather than physically deleted. User-scoped queries and composite foreign keys protect tenant boundaries.

`services/demo.py` creates seeded, separate demonstration accounts. `services/ml.py` trains Gradient Boosting and Isolation Forest using CLI commands, persists artifacts, and exposes read-only inference. `services/llm.py` has no database imports and calls an optional CPU llama.cpp HTTP endpoint. It falls back to deterministic sentences.

```mermaid
erDiagram
    USER ||--o{ ITEM : owns
    USER ||--o{ SUPPLIER : owns
    USER ||--o{ STOCK_MOVEMENT : records
    SUPPLIER o|--o{ ITEM : supplies
    ITEM ||--o{ STOCK_MOVEMENT : audits
    USER {
        integer id PK
        string username UK
        string email UK
        string password_hash
        datetime created_at
        datetime last_login
    }
    SUPPLIER {
        integer id PK
        integer user_id FK
        string name
        string email
        datetime created_at
    }
    ITEM {
        integer id PK
        integer user_id FK
        integer supplier_id FK
        string name
        integer quantity
        float price
        datetime created_at
        datetime archived_at
    }
    STOCK_MOVEMENT {
        integer id PK
        integer item_id FK
        integer user_id FK
        integer delta
        integer balance_after
        string kind
        string note
        datetime occurred_at
        datetime created_at
    }
```

```mermaid
classDiagram
    User "1" --> "0..*" Item : owns
    User "1" --> "0..*" Supplier : owns
    Supplier "0..1" --> "0..*" Item : supplies
    Item "1" --> "0..*" StockMovement : movements
    class User {
        int id
        str username
        str password_hash
        set_password(password)
        check_password(password)
        generate_api_token()
        verify_api_token(token)
    }
    class Item {
        int id
        int user_id
        int quantity
        float price
        datetime archived_at
        to_dict()
    }
    class Supplier {
        int id
        int user_id
        str name
    }
    class StockMovement {
        int id
        int item_id
        int delta
        int balance_after
        str kind
        datetime occurred_at
    }
```

The services are ordinary Python functions, not extra classes or running services. There are no background queues, Redis, Celery, Kubernetes or React dependencies. A small synchronous SQLite application is sufficient for this assignment.
