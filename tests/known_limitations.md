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
- **ADK API surface not yet verified against the installed version.** The exact
  method used to invoke the agent (`agent.run(...)` in `api/routes.py`) and the
  `Agent(...)` constructor kwargs in `agent/agent_definition.py` need to be
  checked against whichever `google-adk` version actually gets installed —
  these have changed across ADK releases.
- **BigQuery vs SQLite datetime handling differs.** Tests run against SQLite via
  `DATABASE_URL` override with naive UTC datetimes; the real BigQuery path uses
  `TIMESTAMP` columns and should be re-verified once real credentials are
  available, particularly around timezone handling.
