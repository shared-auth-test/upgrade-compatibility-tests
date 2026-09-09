# Shared Auth external validation upgrade — DEN-3958

The workflow consumes the actual shared runtime candidate from
`ores-otel/ores-lib-core` at `6ce47f202cef70112950b06af8c3c24abe7eb288` and compares
it with old baseline `5db0c66a85098fa3eff55d2df929d078999712e2`. The shared harness
is itself pinned to `ores-otel-test/contract-conformance-tests` commit
`ee81898748ac6c9885111d4ff9ae6ff3d87b1110`. No application validator is duplicated.

Node 24 provides a second JavaScript runtime lane in addition to the harness
repository's Node 22 lane. Actual versions are recorded in the evidence artifact.
The same 3,504 cases execute in TypeScript, Rust, Dart VM and compiled Dart JS;
all 8,192 byte-value/position combinations execute per runtime. Both old defects
must reproduce in the baseline and be rejected in the candidate. Rust additionally
rejects a non-byte digest consumer at compile time. Dart VM and compiled-JS summary
outputs must agree byte-for-byte. Existing tests/workflows remain untouched.

These checks need no production secrets, deployments, user data, or database
access. They are finite library-consumer tests, not a live Shared Auth route or
session-revocation integration test, not browser UI testing, not Serde/Zod fleet
certification, and not Zed registry/frozen-install evidence. TJSV approval of the
shared interface package remains independent and may still be blocked.
