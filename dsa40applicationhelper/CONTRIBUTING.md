# Contributing to DSA 40 Application Helper

## Tech stack (for reference)

- **Backend:** Python 3.11+, Django, Django Ninja, PostgreSQL, [uv](https://docs.astral.sh/uv/)
- **Frontend:** Django templates, HTMX, Alpine.js, Tailwind
- **Config:** mapping/question config is file-based (versioned JSON/YAML), loaded into
  read-only PostgreSQL tables at deploy time. Edit config as files, not in the DB directly.

## Repo layout during migration

The existing `backend/` (FastAPI) and `frontend/` (SvelteKit) folders **stay in place as a
reference implementation** until M1 (MVP parity) is confirmed — useful for diffing new
behavior against old, and for T1's mapping engine port specifically. The new Django project
lives in a sibling folder, `webapp/`. Once M1 is signed off, `backend/` and `frontend/` get
deleted in a dedicated cleanup PR — not before.

## Branching model
- `main` is always deployable.
- Work happens on short-lived feature branches off `main`, with `<type>/<short-description>`.
  types:
  - 
- No direct commits to `main` — everything goes through a PR, including work by Luis and
  Nico on their own WPs.
- Rebase (don't merge) your branch onto `main` before opening a PR, to keep history readable.
- Keep branches short-lived (days, not weeks) — split large WPs (like T1) into smaller PRs
  where possible rather than one giant branch.
  
  ## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
Example: `feat(t3): add email verification flow`

## Pull requests

- One PR = one WP task or a clearly scoped slice of one (e.g. "T1: mapping engine operator
  registry" rather than all of T1 in one PR).
- PR description should link the relevant WP (F1, T3, etc.) and briefly state what changed
  and why.
- At least **one review from the other developer** before merging (Luis reviews Nico's PRs
  and vice versa) — given the two-person dev team, this is also our main way of keeping
  both people roughly up to speed on both halves of the codebase.
- CI must pass (lint, tests, build) before merge.
- Squash-merge to `main` to keep a clean, readable history.
- Delete the branch after merge.

## Definition of Done

A task/PR is "done" when:

- [ ] Code is merged to `main` via a reviewed PR
- [ ] Automated tests cover the new behavior (unit tests minimum; integration tests for
      cross-cutting features like auth, consent, or the mapping engine)
- [ ] `python manage.py check --deploy` passes with no new warnings, where relevant
- [ ] No new accessibility regressions (WCAG 2.1 AA) — run axe/pa11y locally for any new UI;
      see `docs/accessibility.md` *(TODO: create)*
- [ ] No new security issues introduced — check against the
      [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
      and [OWASP Top 10](https://owasp.org/www-project-top-ten/) for anything touching auth,
      file uploads, or user input
- [ ] Relevant docs updated (README, install guide, or inline docstrings) if behavior or
      setup steps changed
- [ ] If the change touches the domain model (F2) or mapping config format (T1), the
      change is reflected in the domain model doc / mapping engine design note

## Code style

- Python: format with `ruff format` (black-compatible style), lint with `ruff check`,
  type-hint public functions.
- Templates/HTMX/Alpine: keep JS logic in Alpine minimal (local UI state only — draft
  handling, wizard step, conditional visibility, copy-to-clipboard). Mapping/transformation
  logic stays server-side.
- Tailwind: use existing design tokens where available; avoid one-off inline styles.

## Testing

- New backend logic needs tests, using `pytest` + `pytest-django`.
- Critical paths (application submission, mapping/transformation, auth, consent
  enforcement) need integration tests, not just unit tests.
- Run the full test suite locally before opening a PR: `<TODO: add command once CI is set up>`

## Pre-commit hooks

- `pre-commit` runs **formatting only** (`ruff format`) locally, auto-fixing on commit —
  non-blocking, just keeps diffs clean before they hit CI.
- Linting (`ruff check`) and the full test suite run in **CI**, and are blocking — a PR
  can't merge if either fails.

## Getting started (T1 / T2 scaffold)

### T1 — Django + Ninja + Postgres (Luis)

```bash
cd webapp
uv init --python 3.11
uv add django django-ninja "psycopg[binary]"
uv add --dev ruff pytest pytest-django mypy

uv run django-admin startproject config .
uv run python manage.py startapp core   # TODO: confirm app name
```

`webapp/pyproject.toml` — carry over the existing backend's ruff config so lint rules stay
consistent rather than drifting:

```toml
[tool.ruff.lint]
select = ["B", "E", "F", "I", "T20"]
ignore = ["T201"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
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

### T2 — Django templates + HTMX + Alpine + Tailwind (Nico)

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

### CI

Extend the existing `.github/workflows/test_backend.yml` (currently `uv sync` + `pytest`
against the old `backend/`) rather than writing a new pipeline from scratch — add a
`ruff check` step, and once `webapp/` is the primary backend, repoint `working-directory` at
it.

## CI pipeline (skeleton — to be built out under F1)

On every PR (all blocking):
1. Lint (`ruff check`)
2. Tests (`pytest`)
3. Build (Django check / collectstatic dry run)

Formatting (`ruff format`) is handled locally via pre-commit.

## Environments

- **Local:** primary development environment until dev/staging servers are available.
- **Dev/Staging/Prod:** tbd


