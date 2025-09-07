Automated API testing repository

This repo contains integration/API tests using pytest + requests.

Quick start (macOS / Linux):

1. Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install pinned dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) override credentials or base url via environment variables:

```bash
export AUTH_USERNAME=phanith.chhim
export AUTH_PASSWORD="<secret>"
export BASE_URL=http://localhost:8000
```

4. Start the local mock API (useful for running tests without a real server):

```bash
python -m scripts.mock_api &>/tmp/mock_api.log &
```

5. Run tests:

```bash
pytest -q
```

CI

A GitHub Actions workflow `.github/workflows/ci.yml` is included to run tests on push/PR to `main`. It starts the mock server and runs pytest.

Security

Do not store production credentials in `config.yaml`. Use environment variables in CI or local runs.

Project structure

- `tests/` — pytest test files
- `utils/` — helpers (HTTP client, schema loader)
- `scripts/mock_api.py` — lightweight local mock server used by CI and local runs

CI multi-stage

This repo provides a multi-stage CI workflow in `.github/workflows/ci-multi-stage.yml`:

- Stage A (fast-tests): runs unit + mock tests using the local mock API and uploads JUnit/JSON artifacts.
- Stage B (staging-integration): runs tests against a staging environment when the repository secret `STAGING_BASE_URL` is set. Provide `STAGING_USERNAME` and `STAGING_PASSWORD` as needed.

Use `--strict` with `scripts/check_endpoints.py` or enable strict behavior in CI to fail builds when schema mismatches are detected.

Running staging integration locally

You can run integration tests against a staging base URL like this:

```bash
export BASE_URL=https://staging.example.com
export AUTH_USERNAME=ci-user
export AUTH_PASSWORD=supersecret
.venv/bin/python -m pytest -m integration
```

Adding CI secrets

To enable the staging job in CI, add the following repository secrets under Settings → Secrets:

- STAGING_BASE_URL — the base URL of the staging environment
- STAGING_USERNAME — optional
- STAGING_PASSWORD — optional

Where to find CI test artifacts

The workflows upload test artifacts (JUnit XML and the JSON reports) under the `reports/` directory; in GitHub Actions they are attached as job artifacts named `fast-test-artifacts` or `staging-test-artifacts`.

