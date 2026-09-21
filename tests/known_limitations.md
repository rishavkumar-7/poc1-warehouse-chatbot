# Known Limitations — POC1

Update this list as the build proceeds; it's part of the exit-criteria deliverable.

- **Mock data only.** Schema and seed data are hand-built approximations of the
  Manhattan WM tables, not validated against the real DB's schema, volumes, or
  actual field names/types.
- **No SSO/auth.** Matches the brief's stated POC scope (read-only DB access, no
  SSO needed), but is a gap to close before any phase beyond this POC.
- **Cutoff-risk thresholds are placeholders.** The 30-minute at-risk buffer in
  `estimation/spd_cutoff.py` (`AT_RISK_BUFFER_MINUTES`) has not been reviewed or
  approved by the business — treat it as a starting point for discussion, not a
  final rule.
- **Throughput calculation is naive.** `estimation/throughput.py` uses a single
  fixed trailing window (default 60 minutes) and doesn't account for shift
  changes, breaks, or multi-user parallelism beyond a simple completed-task count.
- **No concurrency/session handling.** The FastAPI layer in this POC does not
  handle multiple simultaneous users/sessions robustly — fine for a demo, not
  for production load.
- **No reverse/search lookups by design.** All 6 use cases take a known ID
  (shipment_id, user_id) and return details about it — none search across
  records by an attribute like carrier (e.g. "which shipments are FedEx?").
  This is a deliberate scope decision to stay within the brief's 6 approved
  use cases, not an oversight. The assistant correctly declines these rather
  than guessing, which is itself a working demonstration of the "never answer
  from your own knowledge" rule.
- **ADK API surface — confirmed, not guessed.** `Agent(...)` requires a `name`
  kwarg; invocation is via `InMemoryRunner.run(user_id=, session_id=,
  new_message=types.Content(...))` after an async
  `session_service.create_session(...)` call, not a simple `agent.run(text)`.
  All confirmed working end-to-end against real Vertex AI as of this session.
- **BigQuery vs SQLite datetime handling differs.** Tests run against SQLite via
  `DATABASE_URL` override with naive UTC datetimes; the real BigQuery path uses
  `TIMESTAMP` columns and should be re-verified once real credentials are
  available, particularly around timezone handling.
