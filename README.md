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
- [ ] Run the CRAG pipeline without blocking the event loop
- [ ] Password hashing and authentication
- [ ] Automated tests with pytest
- [ ] PostgreSQL with pgvector in place of Chroma
- [ ] Docker Compose for the API, database and Ollama
- [ ] CI with GitHub Actions

## Tech stack

Python 3.12 · FastAPI · Pydantic · SQLAlchemy (async) · SQLite · LangGraph · LangChain · Ollama · Chroma · uv

## Project structure

```
.
├── main.py           # FastAPI app, lifespan (creates tables), router registration
├── router/
│   ├── query.py      # POST/GET /api/query
│   └── user.py       # POST/GET /api/users
├── schemas.py        # Pydantic request/response models
├── models.py         # SQLAlchemy models: User, Response
├── database.py       # Async engine and session dependency
├── capped_crag.py    # LangGraph Capped Agentic CRAG pipeline
├── vector_store.py   # PDF loading, chunking, Chroma vector store and search
└── data/             # Synthetic GDPR compliance policy used as the corpus
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/query` | Run a question through the Capped CRAG pipeline and store the result |
| `GET` | `/api/query` | List stored queries and responses |
| `POST` | `/api/users` | Create a user |
| `GET` | `/api/users` | List users |

Interactive documentation is available at `/docs` once the server is running.

## Getting started

**Prerequisites:** Python 3.12, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/).

```bash
# 1. Pull the models
ollama pull llama3.2:1b
ollama pull nomic-embed-text

# 2. Install dependencies
uv sync

# 3. Start the development server
uv run fastapi dev main.py
```

Open <http://127.0.0.1:8000/docs> to try the endpoints. On the first query, the vector store is built from the PDF in `data/` and saved to `data/vector_db/`.

### Example

```bash
curl -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Within how many hours must a data breach be reported?"}'
```

## Notes

- The dissertation experiments used `llama3.1` (8B). This repository defaults to the smaller `llama3.2:1b` so it runs on lighter machines; change the model in `capped_crag.py`.
- The corpus is a fully synthetic compliance policy. No real corporate or personal data is included.
- Latency and quality figures from the dissertation do not carry over to this version and will be re-measured once the service layer is complete.