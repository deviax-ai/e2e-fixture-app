# e2e-fixture-app

Minimal app used by Deviax's real-cluster e2e suites (`make qa-gui`,
`make test-kind`) to exercise the full analysis → build → deploy
pipeline.

## Why it's not clean code

The fixture **intentionally** ships with:

- Hardcoded `localhost:4000` upstream URL
- Hardcoded session secret constant
- Hardcoded listen port (8080)
- SQLite file on `/tmp` (local state, won't survive a restart)
- Dockerfile runs as root, no `HEALTHCHECK`
- No graceful-shutdown signal handler

Each of these is a deployment issue Deviax's `issue_detection` phase
should flag with an `<ISSUE>` marker — that's how the QA suite proves
the end-to-end flow: Claude sees the issue, emits a rich IssueCard,
the UI renders it, and the canned answers dismiss it.

**Do not use outside the test suite.** No security review, no CVE
patching, no production hardening.

## Routes

| Path           | Response                                    |
|----------------|---------------------------------------------|
| `GET /healthz` | `200 ok` — used by the post-deploy probe    |
| `GET /env`     | echoes `$GREETING`                          |
| `GET /api/ping`| JSON `{service, upstream}` — exercises JSON |
| `GET /api/count`| JSON `{hits}` — exercises the SQLite path  |

## Build

```
docker build -t e2e-fixture-app .
docker run --rm -p 8080:8080 e2e-fixture-app
curl http://localhost:8080/healthz   # → ok
curl http://localhost:8080/api/ping  # → JSON
```
