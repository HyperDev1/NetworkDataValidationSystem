# Phase 1: Containerization - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Production-ready Docker image that builds and runs locally. Container starts a Flask HTTP server with health check and validation trigger endpoints. Sensitive files (credentials/, config.yaml, .git) are excluded from the image. Cloud Run deployment, secret management, and scheduling are separate phases.

</domain>

<decisions>
## Implementation Decisions

### HTTP Framework & Endpoints
- Flask as HTTP framework (lightweight, sufficient for few endpoints)
- Health check endpoint returning simple `{"status": "healthy"}` with 200 OK
- Validation trigger endpoint (e.g., /validate) that runs the validation pipeline and returns JSON result summary: `{"status": "completed", "networks_processed": 12, "failed": ["meta"]}`
- Health check path: Claude's discretion (standard convention)

### Container Entry Point & Modes
- Container runs Flask HTTP server as primary entry point
- Port 8080 by default, reads from PORT environment variable (Cloud Run convention)
- Existing CLI mode (python main.py) preserved for local development/debugging — two separate entry points coexist
- Container stays alive serving HTTP requests (not one-shot CLI)

### Credential & Config Management
- Volume mount for Phase 1 local testing: `docker run -v ./config.yaml:/app/config.yaml -v ./credentials:/app/credentials`
- config.yaml and credentials/ excluded from Docker image (security requirement)
- Non-root user inside container (create appuser in Dockerfile)
- docker-compose.yml for convenient local testing (volume mounts, port mapping, env vars all predefined)
- Logs to stdout/stderr only (12-factor app principle, Cloud Run auto-captures)

### Docker Build Strategy
- Base image: python:3.13-slim (Debian-based, compatible with pandas/pyarrow C extensions)
- 2-stage multi-stage build: Stage 1 installs dependencies with build tools, Stage 2 copies only runtime artifacts
- Broad .dockerignore: .git, credentials/, config.yaml, __pycache__, .planning/, scripts/, docs/, templates/, *.pyc, .env
- Image tag strategy: Claude's discretion

### Claude's Discretion
- Exact health check path (/health, /, or other)
- Image tag strategy (latest + git sha vs other approach)
- Flask app file location and structure
- Gunicorn vs Flask dev server for production
- Exact .dockerignore entries beyond the listed ones
- WORKDIR path inside container

</decisions>

<specifics>
## Specific Ideas

- Phase 3 will add Cloud Scheduler triggering validation via HTTP — the /validate endpoint added here prepares for that seamlessly
- CLI mode staying around means developers can still run `python main.py` locally without Docker for quick iteration
- docker-compose.yml should be simple enough to `docker compose up` and have a working validation system

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py`: Contains `run_validation()` (async), `run_single_validation()` (sync wrapper) — validation logic to be called from Flask endpoint
- `src/config.py`: Config class with YAML loading — already works with file-based config, will work with volume-mounted config.yaml
- `requirements.txt`: All Python dependencies listed — direct input for pip install in Dockerfile
- `Pipfile` / `Pipfile.lock`: Alternative dependency management available

### Established Patterns
- Async-first with asyncio: validation pipeline is async — Flask endpoint will need to bridge async/sync (asyncio.run or similar)
- Logging via Python `logging` module with `basicConfig()` — already outputs to stdout, compatible with container logging
- Graceful degradation: failed networks tracked in `_failed_networks` — natural fit for validation response summary

### Integration Points
- New Flask app file (e.g., `app.py` or `server.py`) will import and call existing validation functions from `main.py`
- `config.yaml` path currently hardcoded or default — may need env var override for container flexibility
- `credentials/` directory used by OAuth token cache and service account — container expects this mounted at same relative path

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-containerization*
*Context gathered: 2026-03-02*
