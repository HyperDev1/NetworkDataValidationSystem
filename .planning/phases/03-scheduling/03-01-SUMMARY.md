---
phase: 03-scheduling
plan: 01
subsystem: api
tags: [flask, http-status-codes, cloud-scheduler, retry, tdd, pytest]

# Dependency graph
requires:
  - phase: 01-containerization
    provides: server.py Flask HTTP server with /validate endpoint
provides:
  - /validate endpoint returning 500 on partial network failure for Cloud Scheduler retry
  - tests/test_server.py with 5 isolated unit tests covering all response paths
affects: [cloud-scheduler-integration, retry-policy]

# Tech tracking
tech-stack:
  added: [pytest, unittest.mock.AsyncMock]
  patterns: [sys.modules stubbing for heavy-dep isolation in Flask tests, TDD red-green for HTTP status contracts]

key-files:
  created:
    - tests/__init__.py
    - tests/test_server.py
  modified:
    - server.py

key-decisions:
  - "Return 500 with status=completed for partial failure — distinguishes network-level failures from system crashes (status=error)"
  - "Stub main module in sys.modules to prevent sys.stdout replacement and pyarrow import during tests"
  - "len(failed) == 0 branch for 200, else branch for 500 — minimal change to existing logic"

patterns-established:
  - "TDD red-green for HTTP status contracts: write 5 behavior tests first, then implement"
  - "sys.modules pre-stubbing pattern for isolating Flask apps with heavy transitive dependencies"

requirements-completed: [SCHED-02]

# Metrics
duration: 8min
completed: 2026-03-02
---

# Phase 3 Plan 01: /validate Partial Failure Response Codes Summary

**Flask /validate endpoint now returns 500 on any network failure so Cloud Scheduler triggers its 5-retry exponential backoff, with status="completed" in body to distinguish partial failures from system crashes (status="error")**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-02T11:19:53Z
- **Completed:** 2026-03-02T11:27:00Z
- **Tasks:** 1 (TDD: RED + GREEN phases)
- **Files modified:** 3 (server.py modified, tests/test_server.py created, tests/__init__.py created)

## Accomplishments

- Fixed /validate response code: 200 only when all networks succeed (failed_networks=[])
- Partial failures (failed_networks non-empty) now return 500 so Cloud Scheduler retries
- Status body distinguishes partial failure (status="completed") from system crash (status="error")
- Updated docstring with all three response path documentation
- 5 isolated pytest tests covering full response contract, importable without pyarrow/GCP

## Task Commits

Each TDD phase committed atomically:

1. **Task 1 RED: Failing tests for /validate response codes** - `bc2ca01` (test)
2. **Task 1 GREEN: Fix /validate to return 500 on partial failure** - `aa6303d` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD task has two commits — test (RED) then implementation (GREEN). No refactor needed._

## Files Created/Modified

- `server.py` - Added `if len(failed) == 0: return 200 else: return 500` branch; updated docstring
- `tests/__init__.py` - Empty init to make tests/ a Python package
- `tests/test_server.py` - 5 pytest tests using Flask test client and sys.modules stubbing to isolate server from pyarrow/GCP/main.py side-effects

## Decisions Made

- **status="completed" for 500 partial failure** — keeps "completed" in body instead of "error" to distinguish network-level failures from unhandled exceptions. The exception handler already returns status="error"; reusing it would make it ambiguous whether the job ran at all.
- **sys.modules pre-stubbing** — `main.py` replaces `sys.stdout` at import time (breaks pytest capture) and requires pyarrow (not installed locally). Stubbing `main` entirely before importing `server` is cleaner than installing all GCP dependencies in the test environment.
- **Minimal code change** — only the return logic at end of try block was modified; no other server.py behavior touched (health_check, Config, date range, asyncio.run, logging).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stubbed `main` module to prevent sys.stdout corruption and pyarrow import error**
- **Found during:** Task 1 RED (test collection failed with ModuleNotFoundError: pyarrow, then I/O error on closed file)
- **Issue:** `server.py` imports `from main import run_validation`. `main.py` replaces `sys.stdout` at module level (corrupts pytest capture) and imports pyarrow via gcs_exporter (not installed). Test collection failed before any test ran.
- **Fix:** Pre-populated `sys.modules['main']` with a stub module containing `run_validation = AsyncMock()` before importing server. Also stubbed pyarrow and google-cloud sub-modules. Tests then isolate server.py cleanly.
- **Files modified:** tests/test_server.py
- **Verification:** All 5 tests collect and run without import errors
- **Committed in:** `bc2ca01` (RED phase commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking import issue)
**Impact on plan:** The stub strategy is the standard pattern for testing Flask apps with heavy transitive dependencies. No scope creep; tests still test the actual server.py logic.

## Issues Encountered

- `main.py` mutates `sys.stdout` at module-level for Windows encoding compatibility — this corrupts pytest's I/O capture when imported directly. Resolved via sys.modules stubbing (no changes to main.py).

## Next Phase Readiness

- server.py /validate endpoint is now correctly signaling failure to Cloud Scheduler
- Ready for 03-02 (next scheduling plan)
- Tests infrastructure in place at `tests/test_server.py` — future plans can add to it

## Self-Check: PASSED

| Item | Status |
|------|--------|
| server.py | FOUND |
| tests/test_server.py | FOUND |
| tests/__init__.py | FOUND |
| 03-01-SUMMARY.md | FOUND |
| Commit bc2ca01 (RED tests) | FOUND |
| Commit aa6303d (GREEN impl) | FOUND |
| 5/5 pytest tests pass | CONFIRMED |

---
*Phase: 03-scheduling*
*Completed: 2026-03-02*
