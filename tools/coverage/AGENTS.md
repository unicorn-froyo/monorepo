# Coverage rules

- Every language-specific `{prefix}_coverage_test` must emit `lcov.info` under `$TEST_UNDECLARED_OUTPUTS_DIR`. A console summary or tool-specific report does not replace this artifact; additional formats may be retained.
- Use workspace-relative, forward-slash paths in LCOV `SF:` entries. Exclude sandbox paths, external dependencies, generated tooling, and test sources from the measured application scope. Reject an empty report or one without the intended application sources.
- Write `lcov.info` before enforcing the shared coverage threshold, so the report survives a threshold failure. When the coverage tool can produce a report after a test failure, preserve it before propagating the failure.
- Coverage-rule tests must check that LCOV is parseable, has portable source paths, contains intended sources, and remains available on threshold failure. Test raw artifacts too when a rule promises to expose them.

