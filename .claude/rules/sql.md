# SQL rules (apply to backend/app/**/sql.py and any SQL string)
- Portable form only: COALESCE not ISNULL, CURRENT_TIMESTAMP not GETDATE(), CONCAT() not +, OFFSET/FETCH (with ORDER BY) not TOP, always dbo. prefix, no bracket-quoted identifiers.
- Anything MSSQL-only gets a line above it: `-- PG-CONVERT: <what changes on PostgreSQL>`.
- No `:colon` inside SQL comments (SQLAlchemy text() treats it as a bind). Escape a literal colon as `\:`.
- RTRIM() every legacy char(n) column in SELECT and in comparisons.
- Named binds `:name`; lists via `bindparam(name, expanding=True)`.
- Never write SCOPE_IDENTITY() or RETURNING in module SQL — call `db.insert_returning_id()`.
- Header per statement: `# name:`, `# dialect: portable | MSSQL-specific — see PG-CONVERT tags (n)`, `# params:`.
