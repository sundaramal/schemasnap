# schemasnap

Automatically snapshots and diffs database schemas across environments to catch unintended migrations.

---

## Installation

```bash
pip install schemasnap
```

---

## Usage

Capture a snapshot of your database schema:

```bash
schemasnap capture --db postgresql://user:pass@localhost/mydb --env production
```

Diff two snapshots to spot unintended changes:

```bash
schemasnap diff --from production --to staging
```

Use it in Python directly:

```python
from schemasnap import SchemaSnap

snap = SchemaSnap("postgresql://user:pass@localhost/mydb")
snap.capture(env="production")
snap.diff(from_env="production", to_env="staging")
```

Output example:

```
[+] Table added:    user_sessions
[-] Column removed: orders.legacy_id
[~] Column changed: products.price (float → decimal)
```

---

## Features

- Supports PostgreSQL, MySQL, and SQLite
- Store snapshots locally or in a remote backend (S3, GCS)
- CI-friendly exit codes for automated pipelines
- Human-readable and JSON diff output

---

## License

MIT © schemasnap contributors