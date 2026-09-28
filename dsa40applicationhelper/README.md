# DSA 40 Application Helper

## Installation

For usage, use docker.
`docker compose build`
`docker compose up`

The service will be available at `localhost:3000`. Swagger API under `localhost:8000/docs`

## Configuration

Both VLOPSE and DSA Questions are saved in a SQLite Database (`backend/app/data/app.db`)
To modify them, either use the swagger API, interact with the questions endpoint (`localhost:8000/api/question`) or modify the database directly with a tool of your choice (recommended).
Mappings and conditionals are defined in `backend/app/data/vlopse/{VLOPSE_NAME}.json`. You can use the (fake) configuration for myspace for orientation.


## Development

### Requirements

- `uv`
- `npm`

### Local Setup

#### Backend

in `backend` run `uv run fastapi dev` (make sure port 8000 is not in use)

You can interact with the backend either via the frontend (as far as functionality is implemented) or via the swagger API at `http://localhost:8000/docs`

#### Frontend

in `frontend` run `npm run generate` and `npm run dev` (make sure port 5173 is not in use)
Browse to `http://localhost:5173` to use the DSA40 Application Helper

#### API

the source of truth for the API definition is the backend.
In case you modify the fastapi backend, make sure to regenerate the API definitions by running `sh scripts/generate_client.sh`

### Django Webapp

> [!IMPORTANT]
> Migration to Django is currently in progress.

To ensure feature-parity between the current FastAPI and the future Django setup, we use a series of plain _migration tests_

#### How to run

- start development server in `backend`: `uv run fastapi dev`
- run tests in `tests`: `uv run pytest`

### Troubleshooting

**Missmatched node version when running frontend**

Make sure you are using node >20.
