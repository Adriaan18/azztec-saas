# Test rules (apply to backend/tests/**)
- Pair rule: every new/changed library module ships with tests in the same slice.
- Pure rules tests use plain dicts, no database.
- DB tests use the rolled-back connection fixture; nothing commits. The dev DB holds real RST data.
- Any function that writes keeps `dry_run=True` as its default; never call it with `dry_run=False` in a test.
- HTTP tests use TestClient with dependency overrides for the actor.
