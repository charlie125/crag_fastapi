# CRAG-FastAPI

A REST API for the **Capped Agentic CRAG** pipeline from my MSc dissertation, so that a fully local RAG system can be called by other services instead of only through a demo web page.

Everything runs on local hardware: the LLM and embedding model are served by Ollama and the vector store is Chroma. No document or query is sent to a cloud API.

> **Work in progress.** See [Status](#status) for what is done and what is planned.

## Background

The dissertation ([capped-agentic-crag](https://github.com/charlie125/capped-agentic-crag)) built a LangGraph corrective-RAG workflow for compliance documents that cannot leave the network. On a local machine the correction loop has no reason to stop on questions the corpus cannot answer, so an iteration cap (K = 2) is written into the control flow: once the cap is reached, the graph routes to an explicit refusal instead of re-retrieving.

The dissertation exposed the pipeline through Django. This project rebuilds the service layer as an API with FastAPI.

## Status

- [x] FastAPI app split into `users` and `query` routers
- [x] Async SQLAlchemy with SQLite (`aiosqlite`) to store users, queries and responses
- [x] Pydantic request and response schemas with input validation
- [x] Password hashing (Argon2) and JWT authentication
- [x] User creation endpoint (`POST /api/users`)
- [x] Users can only view and delete their own queries
- [x] Run the CRAG pipeline in a worker thread so it does not block the event loop
- [ ] Automated tests with pytest
- [ ] PostgreSQL with pgvector in place of Chroma
- [ ] Docker Compose for the API, database and Ollama
- [ ] CI with GitHub Actions

## Tech stack

Python 3.14 · FastAPI · Pydantic · SQLAlchemy (async) · SQLite · LangGraph · LangChain · Ollama · Chroma · uv

## Project structure

```
.
├── main.py           # FastAPI app, lifespan (creates tables), router registration
├── router/
│   ├── query.py      # /api/query: run, list and delete queries
│   └── user.py       # /api/users: sign up, log in, list users, query history
├── auth.py           # Password hashing, JWT creation/verification, current-user dependency
├── config.py         # Settings loaded from environment variables / .env
├── schemas.py        # Pydantic request/response models
├── models.py         # SQLAlchemy models: User, Response
├── database.py       # Async engine and session dependency
├── capped_crag.py    # LangGraph Capped Agentic CRAG pipeline
├── vector_store.py   # PDF loading, chunking, Chroma vector store and search
└── data/             # Synthetic GDPR compliance policy used as the corpus
```

## API

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/users` | – | Create a user (`201`); username and email must be unique, case-insensitive |
| `POST` | `/api/users/token` | – | Log in with email and password (OAuth2 form), returns a bearer token |
| `GET` | `/api/users` | – | List users |
| `GET` | `/api/users/{username}/histories` | Bearer | List the current user's queries (`403` for another username) |
| `POST` | `/api/query` | Bearer | Run a question through the Capped CRAG pipeline and store the result (`201`) |
| `GET` | `/api/query` | – | List stored queries and responses |
| `DELETE` | `/api/query/{query_id}` | Bearer | Delete one of the current user's queries (`204`, `404` if not found or not owned) |

Interactive documentation is available at `/docs` once the server is running. Use the **Authorize** button there to log in; the email goes in the `username` field.

## Getting started

**Prerequisites:** Python 3.14, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/).

```bash
# 1. Pull the models
ollama pull llama3.2:1b
ollama pull nomic-embed-text

# 2. Install dependencies
uv sync

# 3. Create a .env file with a secret key for signing tokens
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env

# 4. Start the development server
uv run fastapi dev main.py
```

Open <http://127.0.0.1:8000/docs> to try the endpoints. On the first query, the vector store is built from the PDF in `data/` and saved to `data/vector_db/`.

### Example

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
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Within how many hours must a data breach be reported?"}'
```

Tokens expire after 30 minutes by default (`ACCESS_TOKEN_EXPIRED_MINUTES`).

## Notes

- The dissertation experiments used `llama3.1` (8B). This repository defaults to the smaller `llama3.2:1b` so it runs on lighter machines; change the model in `capped_crag.py`.
- The corpus is a fully synthetic compliance policy. No real corporate or personal data is included.
- `GET /api/users` and `GET /api/query` are still public and expose every user's email and queries. They will be restricted before any deployment.
- Tables are created at startup with `create_all`, which does not alter existing tables. There are no migrations yet, so after a model change, delete `crag.db` and restart.
- Latency and quality figures from the dissertation do not carry over to this version and will be re-measured once the service layer is complete.