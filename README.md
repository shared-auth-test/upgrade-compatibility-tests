# shared-auth-test/upgrade-compatibility-tests

Forward/backward schema compatibility, migration round-trip, negotiation, snapshot replay, and destructive-change guard tests.

This repository is the `upgrade` deep-test suite for `shared-auth`. It is intentionally dependency-light and deterministic so failures can be reproduced locally without production credentials or customer data.

## Run

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/verify_repository.py
```

The initial model is executable rather than a placeholder. Product adapters should be added through focused pull requests while preserving the reference-model tests as an oracle.

Tracking: https://github.com/ORESoftware/ai-agent-coordinator.rs/issues/139
