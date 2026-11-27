# CRAG-FastAPI

A REST API for the **Capped Agentic CRAG** pipeline from my MSc dissertation, so that a fully local RAG system can be called by other services instead of only through a demo web page.

Everything runs on local hardware: the LLM and embedding model are served by Ollama, and the document chunks with their embeddings, users and queries are all stored in PostgreSQL with pgvector. No document or query is sent to a cloud API.

> **Work in progress.** See [Status](#status) for what is done and what is planned.

## Background

The dissertation ([capped-agentic-crag](https://github.com/charlie125/capped-agentic-crag)) built a LangGraph corrective-RAG workflow for compliance documents that cannot leave the network. On a local machine the correction loop has no reason to stop on questions the corpus cannot answer, so an iteration cap (K = 2) is written into the control flow: once the cap is reached, the graph routes to an explicit refusal instead of re-retrieving.

The dissertation exposed the pipeline through Django. This project rebuilds the service layer as an API with FastAPI.

## Architecture

![Capped Agentic CRAG architecture](https://github.com/user-attachments/assets/775ba550-2207-4ca2-8138-4ff39a660608)

`Count Check` is the iteration cap: once `rewrite_counts` reaches K = 2, it routes to `give_up_msg`, which returns an explicit refusal instead of looping back through `Rewrite`. The `LLM` step stands for whichever node actually produces the reply — `generate_answer` after a successful retrieval, or `Query_or_Response`'s own output when it answers without calling the retrieval tool.

## Status

- [x] FastAPI app split into `users` and `query` routers
- [x] Async SQLAlchemy with PostgreSQL (`psycopg` 3) to store users, queries and responses
- [x] Schema migrations with Alembic
- [x] PostgreSQL in Docker Compose for local development
- [x] Pydantic request and response schemas with input validation
- [x] Password hashing (Argon2) and JWT authentication
- [x] User creation endpoint (`POST /api/users`)
- [x] Users can only view and delete their own queries
- [x] Run the CRAG pipeline in a worker thread so it does not block the event loop
- [x] Automated tests with pytest against a separate PostgreSQL test database
- [x] pgvector in place of Chroma: chunks and embeddings live in PostgreSQL, searched by cosine distance
- [x] One-command start with Docker Compose: API, Ollama, model download, migrations and document ingestion
- [ ] CI with GitHub Actions

## Tech stack

Python 3.14 · FastAPI · Pydantic · SQLAlchemy (async) · PostgreSQL · Alembic · Docker Compose · LangGraph · LangChain · Ollama · pgvector · uv

## Project structure

```
.
├── main.py           # FastAPI app, lifespan (disposes the engine), router registration
├── router/
│   ├── query.py      # /api/queries: run, list and delete queries
│   └── user.py       # /api/users: sign up, log in, list users, a user's own queries
├── auth.py           # Password hashing, JWT creation/verification, current-user dependency
├── config.py         # Settings loaded from environment variables / .env
├── schemas.py        # Pydantic request/response models
├── models.py         # SQLAlchemy models: User, Query, VectorDB (document chunks)
├── database.py       # Async engine and session dependency
├── alembic/          # Migration environment and versioned migrations
├── alembic.ini       # Alembic configuration (the database URL comes from config.py)
├── Dockerfile        # API image built with uv
├── .dockerignore     # Keeps .env, .venv and caches out of the image
├── docker-compose.yaml  # PostgreSQL + pgvector, Ollama, and the API with its one-shot setup services
├── capped_crag.py    # LangGraph Capped Agentic CRAG pipeline
├── vector_store.py   # PDF ingestion (split, embed, store) and pgvector similarity search
├── data/             # Synthetic GDPR compliance policy used as the corpus
└── test/
    ├── conftest.py   # Test database, per-test rollback, test client and fixtures
    ├── test_user.py  # Sign-up, user listing, reading a user's queries (incl. 403)
    └── test_query.py # Creating, listing and deleting queries (incl. 404 for another user's query)
```

## API

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/users` | – | Create a user (`201`); username and email must be unique, case-insensitive (`409` if taken) |
| `POST` | `/api/users/token` | – | Log in with email and password (OAuth2 form), returns a bearer token |
| `GET` | `/api/users` | – | List users |
| `GET` | `/api/users/{username}/queries` | Bearer | List the current user's queries (`403` for another username) |
| `POST` | `/api/queries` | Bearer | Run a question through the Capped CRAG pipeline and store the result (`201`) |
| `GET` | `/api/queries` | – | List stored queries and responses |
| `DELETE` | `/api/queries/{query_id}` | Bearer | Delete one of the current user's queries (`204`, `404` if not found or not owned) |

Interactive documentation is available at `/docs` once the server is running. Use the **Authorize** button there to log in; the email goes in the `username` field.

## Getting started

Both ways of running the project need a `.env` file in the project root. It is read by the app and by Docker Compose, and is never copied into the image.

```bash
cat > .env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_USER=crag
POSTGRES_PASSWORD=$(openssl rand -hex 16)
POSTGRES_DB=crag
POSTGRES_PORT=5433
EOF
```

### Option A: Docker Compose (one command)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) only.

```bash
docker compose up -d --build
```

Open <http://localhost:8080/docs> once the API is up. The first start downloads about 1.6 GB of models, so it takes a few minutes; later starts reuse them.

Compose starts the services in this order:

```
crag_db (healthy) ──→ migration_db (exit 0) ──┐
                                              ├─→ ingest_vector_db (exit 0) ──→ crag_fastapi
ollama (healthy) ──→ ollama_pull (exit 0) ────┘
```

| Service | Role |
| --- | --- |
| `crag_db` | PostgreSQL 17 with pgvector |
| `ollama` | Ollama server for the LLM and embedding model |
| `ollama_pull` | One-shot: pulls `llama3.2:1b` and `nomic-embed-text` |
| `migration_db` | One-shot: `alembic upgrade head` |
| `ingest_vector_db` | One-shot: loads the PDF into pgvector (safe to re-run) |
| `crag_fastapi` | The API on port `8080` |

`docker compose ps -a` shows the one-shot services as `Exited (0)` when they have finished successfully. If one of them exits with a non-zero code, the API is not started; check it with `docker compose logs <service>`.

After changing the code or the Dockerfile, keep `--build` so Compose rebuilds the image instead of reusing the old one.

### Option B: local development

**Prerequisites:** Python 3.14, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/) and [Docker](https://docs.docker.com/get-docker/). The app runs on the host with hot reload; only PostgreSQL runs in Docker.

```bash
# 1. Pull the models
ollama pull llama3.2:1b
ollama pull nomic-embed-text

# 2. Install dependencies
uv sync

# 3. Start PostgreSQL only
docker compose up -d crag_db

# 4. Create the tables (also enables the vector extension)
uv run alembic upgrade head

# 5. Load the document into the vector store (Ollama must be running)
uv run python vector_store.py

# 6. Start the development server
uv run fastapi dev main.py
```

PostgreSQL listens on port `5433` on the host so it does not clash with a local installation. `POSTGRES_HOST` defaults to `localhost` and `OLLAMA_BASE_URL` to `http://localhost:11434`; Docker Compose overrides both for the containers.

Open <http://127.0.0.1:8000/docs> to try the endpoints. Step 5 only needs to run once per database. Run it again after changing the PDF, the chunk settings or the embedding model; it replaces that document's chunks, so re-running it does not create duplicates.

### Database migrations

The schema is managed by Alembic; the app does not create tables on startup.

```bash
# After changing models.py, generate a migration and review it before applying
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head

# Show the current revision / check that models and database match
uv run alembic current
uv run alembic check
```

Autogenerate cannot detect renames (it emits a drop and a create), so always read the generated file.

### Running tests

The tests run against a separate database, `test_crag_db`, on the same PostgreSQL container. Create it once:

```bash
docker compose up -d crag_db
docker compose exec crag_db sh -c 'createdb -U "$POSTGRES_USER" test_crag_db'
```

Then run:

```bash
uv run pytest
```

- `test/conftest.py` switches `POSTGRES_DB` to `test_crag_db` before the app is imported, so the tests never touch the development database. The other connection settings still come from `.env`.
- Tables (and the `vector` extension) are created at the start of the test run and dropped at the end; no migration step is needed.
- Each test runs inside a transaction that is rolled back afterwards, so tests do not affect each other.
- The CRAG pipeline is replaced with a stub, so Ollama does not need to be running.

### Example

These commands use port `8000` (Option B). With Option A, replace it with `8080`.

```bash
# Create a user
curl -X POST http://127.0.0.1:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "change-me-123"}'

# Log in (the OAuth2 form field is called "username", but it takes the email)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/users/token \
  -d "username=alice@example.com&password=change-me-123" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Ask a question
curl -X POST http://127.0.0.1:8000/api/queries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Within how many hours must a data breach be reported?"}'
```

Tokens expire after 30 minutes by default (`ACCESS_TOKEN_EXPIRED_MINUTES`).

## Notes

- The dissertation experiments used `llama3.1` (8B). This repository defaults to the smaller `llama3.2:1b` so it runs on lighter machines. To change it, edit `capped_crag.py` and the `ollama_pull` command in `docker-compose.yaml`.- The corpus is a fully synthetic compliance policy. No real corporate or personal data is included.
- `GET /api/users` and `GET /api/queries` are still public and expose every user's email and queries. They will be restricted before any deployment.
- Database data lives in the `pgdata` volume and downloaded models in `ollama_llm`. Docker Compose prefixes them with the project name, which defaults to the folder name (e.g. `crag-fastapi_pgdata`). Both survive `docker compose down`; `docker compose down -v` deletes them.
- `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` only take effect when the volume is first initialised. Changing them later requires recreating the volume.
- Latency and quality figures from the dissertation do not carry over to this version and will be re-measured once the service layer is complete.