# e2e-fixture-app

Minimal app used by Deviax's Phase 5.c real-kind e2e suite.
Ships a `/healthz` for the post-deploy probe and a `/env` that echoes
`$GREETING` so the env-vars e2e test can prove container-side variables.

**Do not use outside the test suite.** No security review, no CVE patching.
