# Contributing to DSA 40 Application Helper

## Tech stack (for reference)

- **Backend:** Python 3.14+, Django >=5.2,<6.0, Django Ninja, PostgreSQL, [uv](https://docs.astral.sh/uv/)
- **Frontend:** Django templates, HTMX, Alpine.js, Tailwind
- **Config:** mapping/question config is file-based (versioned JSON/YAML), loaded into
  read-only PostgreSQL tables at deploy time. Edit config as files, not in the DB directly.

## Repo layout during migration

The existing `backend/` (FastAPI) and `frontend/` (SvelteKit) folders **stay in place as a
reference implementation** until M1 (MVP parity) is confirmed — useful for diffing new
behavior against old, and for T1's mapping engine port specifically. The new Django project
lives in a sibling folder, `webapp/`. Once M1 is signed off, `backend/` and `frontend/` get
deleted in a dedicated cleanup PR — not before.

## Definition of Done

A task/PR is "done" when:

- [ ] Code is merged to `main` via a reviewed PR
- [ ] Automated tests cover the new behavior (unit tests minimum; integration tests for
      cross-cutting features like auth, consent, or the mapping engine)
- [ ] `python manage.py check --deploy` passes with no new warnings, where relevant
- [ ] Accessibility requirements ([WCAG 2.1 AA](https://www.w3.org/TR/WCAG21/)) checked
      consider WebAIM's [WCAG 2 Checklist](https://webaim.org/standards/wcag/checklist)
      and the [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/);
      run [axe-core](https://www.npmjs.com/package/axe-core) locally for any new UI;
- [ ] Security requirements checked
      check the [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/);
      run snyk’s [Security Headers](https://securityheaders.com/) and/or Mozilla’s
      [HTTP Observatory](https://developer.mozilla.org/en-US/observatory)
      and OWASP's [Top 10](https://top10.owasp.org/2025/0x00_2025-Introduction/) or
      [Cheat Sheets](https://cheatsheetseries.owasp.org/index.html) for anything touching auth,
      file uploads, or user input;
- [ ] Relevant docs updated (README, install guide, or inline docstrings) if behavior or
      setup steps changed

## Branching model and commit messages
- `main` is always deployable.
- Work happens on short-lived feature branches off `main`, with `<type>/<short-description>`, e.g. `feat/case-status-machine`.
- Commits are based on [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat`: new functionality
  - `fix`: bug fixes
  - `chore`: tooling, CI, dependency bumps, non-code housekeeping
  - `docs`: documentation
  - `test`: adding/fixing tests with no behavior change
  - `refactor`: Restructuring code with no functional change
 - issue referencing in commit message using `Refs:`

Example:
```feat: add email verification flow

Refs: #5
```

- No direct commits to `main` — everything goes through a PR.
  - One PR = one clearly scoped slice of a WP task
  - At least **one review from the other developer** before merging
  - CI must pass (lint, tests, build) before merge
  - Squash-merge to `main` to keep a clean, readable history + delete the branch after merge
- Rebase (don't merge) your branch onto `main` before opening a PR, to keep history readable.
- Keep branches short-lived (days, not weeks) — split large WPs (like T1) into smaller PRs
  where possible rather than one giant branch.

## Testing

- New backend logic needs tests, using `pytest` + `pytest-django`.
- Critical paths (application submission, mapping/transformation, auth, consent
  enforcement) need integration tests, not just unit tests.
- Run the full test suite locally before opening a PR: `<TODO: add command once CI is set up>`

## CI pipeline

Defined in `../.github/workflows/test_backend.yml`. Two jobs run in parallel during the
migration:

- **`test-backend`** — the existing MVP (FastAPI) test suite, unchanged. Runs until
  `backend/` is deleted post-M1, at which point this job is removed.
- **`test-webapp`** — the Django migration target, against a real Postgres service
  container (matching `docker-compose.yml` credentials):
  1. Lint: `ruff check` + `pip-audit`
  2. Template lint: `djlint --check`
  3. `python manage.py check --deploy`
  4. Tests + coverage gate: `coverage run -m pytest` then `coverage report`
     (fails once below `fail_under = 80`, set in `pyproject.toml`)
  5. Build check: `collectstatic --dry-run`

All steps in `test-webapp` are blocking for merge. Once `webapp/` becomes the primary
backend, `test-backend` is dropped and `test-webapp` is renamed accordingly.

### Pre-commit hooks

- `pre-commit` runs **formatting only** locally, auto-fixing on commit, non-blocking:
  - `ruff format` for Python
  - `djlint --reformat` for Django templates

Formatting is not re-checked in CI — only linting and the checks above.

## Environments

- **Local:** primary development environment until dev/staging servers are available.
- **Dev/Staging/Prod:** tbd


## Getting started (T1 / T2 scaffold)

### T1 — Django + Ninja + Postgres

```bash
cd webapp
uv init --python 3.14
uv add django django-ninja "psycopg[binary]"
uv add --dev ruff pytest pytest-django pytest-cov coverage django_coverage_plugin \
  djlint pip-audit mypy

uv run django-admin startproject config .
uv run python manage.py startapp dsa40
```

Add a local Postgres service to the root `docker-compose.yml` so development runs against
the real target DB, not SQLite:

```yaml
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: dsa40helper
      POSTGRES_USER: dsa40helper
      POSTGRES_PASSWORD: dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
```

### T2 — Django templates + HTMX + Alpine + Tailwind

Node is build-time only (Tailwind), never a second running web app.
Vendor HTMX and Alpine as static files rather than npm-installing them:

```bash
mkdir -p webapp/static/vendor
curl -sL https://unpkg.com/htmx.org@2/dist/htmx.min.js -o webapp/static/vendor/htmx.min.js
curl -sL https://unpkg.com/alpinejs@3/dist/cdn.min.js -o webapp/static/vendor/alpine.min.js
```

Tailwind via the standalone CLI (no Node required at all):

```bash
curl -sL https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 -o tailwindcss
chmod +x tailwindcss
./tailwindcss -i ./webapp/static/src/input.css -o ./webapp/static/dist/output.css --watch
```
