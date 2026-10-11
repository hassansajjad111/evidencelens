# EvidenceLens

**Hybrid retrieval for biomedical literature, designed so each returned passage
can eventually be traced to its source.** This README is the project handoff
document: it explains the motivation, scope, current behavior, one-time setup,
commands, code layout, and a safe order for future work.

> **Important status:** this repository is an early engineering scaffold, not a
> finished biomedical search or clinical product. The databases can start and
> the API can connect to them, but no corpus is currently loaded. The PubMed
> parser, schemas, and retrievers are pieces of the pipeline; end-to-end corpus
> generation/indexing and grounded answer generation are not implemented.
> `/v1/ask` intentionally returns HTTP 501 instead of inventing an answer.

## 1. What the project is for

EvidenceLens is intended to explore how different search methods find passages
in biomedical evidence. The planned domain is type 2 diabetes and related
cardiometabolic topics, including hypertension, obesity, chronic kidney disease,
and heart failure. Example research questions include:

- Exact: “What is the primary outcome for trial NCT…?”
- Semantic: “Which therapies lower blood sugar without weight gain?”
- Filtered: “Show randomized trials after 2020.”
- Relational: “Which drugs studied for condition X list adverse event Y?”

The long-term product goal is retrieval first, then (only when evidence is
sufficient) an answer with verifiable passage citations. It is **not** a
diagnosis, dosing, treatment recommendation, or clinical decision-support tool.
Any future answer UI/API must preserve this boundary and make refusals possible.

### Intended architecture (target, not all implemented)

```text
source data → parse/clean/filter → stable chunk IDs → versioned corpus
  ├─ Elasticsearch: BM25 and metadata filters
  ├─ Qdrant: dense/sparse vector retrieval
  └─ Neo4j: entity relations and provenance
question → retrieve → RRF fusion → hydrate/rerank passages
  → evidence sufficiency check → grounded answer + verified citations
```

Each store has a different role:

| Component | Intended responsibility | Current state |
| --- | --- | --- |
| PubMed parser | Stream PubMed XML articles and tombstones | Basic streaming parser exists; no downloader, filter, Parquet writer, or update applicator |
| Elasticsearch | Lexical BM25 search, biomedical analyzers, filters | Mapping/settings are declared; no index-creation or document-load workflow |
| Qdrant | Dense/sparse nearest-neighbor search and payload filters | Collection schema helper exists; no embedding/upsert pipeline |
| Neo4j | Entities, trials, evidence links, provenance, graph retrieval | Constraints/index helper exists; no graph loader or query retriever |
| Reciprocal Rank Fusion | Combine rank lists without comparing incompatible raw scores | Implemented as a small pure-Python function |
| FastAPI | Health and retrieval API | Health and search routes exist; search needs pre-populated indexes |
| Grounded RAG | Generate and verify cited responses | Not implemented; `/v1/ask` returns 501 |
| Evaluation | Measure retrieval and answer quality | Only small unit tests exist; no benchmark/evaluation harness yet |

The full intended scope is broader than the current code. Planned sources include
PubMed, permissively licensed PMC Open Access content, ClinicalTrials.gov,
openFDA, MeSH/RxNorm, and carefully selected public-health sources. Before
adding a source, check its terms, license, attribution requirements, robots
policy, privacy impact, and whether text may be redistributed. Do not put
restricted UMLS-derived, DrugBank, or non-commercially licensed data in this
repository.

## 2. What works today (and what does not)

### Implemented building blocks

- Python 3.12 project and lockfile managed with `uv`.
- Docker Compose definitions for local Elasticsearch, Qdrant, and Neo4j.
- Typed `EL_*` configuration defaults and an `.env.example` template.
- Async FastAPI lifespan/client setup and `/healthz` connectivity checks.
- `/v1/search` dispatch for `bm25`, `dense`, or `hybrid`; hybrid fuses IDs with
  RRF. The response contains chunk IDs and scores, not source text.
- Lazy query-time loading of `BAAI/bge-small-en-v1.5` for dense retrieval, with
  normalized query embeddings computed outside the async event loop.
- A memory-conscious `gzip` + `lxml.iterparse` PubMed parser that yields article
  upserts and `DeleteCitation` delete events.
- Unit tests for retrieval-mode dispatch, the unimplemented answer route, and
  basic RRF behavior.

### Known gaps — do not mistake these for working features

- A fresh clone has **no searchable corpus**. We verified the running ES server
  had no `el_chunks_v1` index and Qdrant had no collections at that time.
- There is no sample-data command, PubMed download/resume manager, Parquet output,
  chunk-ID generation, ES bulk indexer, Qdrant upserter, or Neo4j graph loader.
- `/v1/search` does not hydrate passages, so it cannot yet show text/citations.
- Neo4j is checked by health but not queried by search.
- The Qdrant sparse vector schema is reserved; query code currently uses dense
  vectors only.
- `/v1/ask` accepts a request schema only to return HTTP 501; no LLM, verifier,
  safety router, citation checking, or streaming answer exists.
- No real evaluation corpus, MLflow runs, Langfuse traces, CI workflow, or
  production deployment is currently wired into this checkout.
- `tests/test_placeholder.py` is only a pytest discovery smoke test; it is not
  evidence of pipeline correctness.

Therefore a successful `make up` or `/healthz` means **services are reachable**,
not that ingestion/search/answers work. Search requests against empty services
will fail because the expected index or collection has not been created.

## 3. Hardware and operating assumptions

This setup is tailored to the project owner’s **2017 Intel MacBook Pro, 8 GB RAM,
256 GB SSD**. It is a development and small-corpus machine—not a realistic host
for the full planned corpus or all model services at once.

- Python is pinned to 3.12, with CPU PyTorch 2.2.2 and NumPy `<2` for the Intel
  Mac compatibility path. Do not casually upgrade these pins mid-project.
- Compose places memory caps of approximately 1.5 GB (Elasticsearch), 1 GB
  (Qdrant), and 1 GB (Neo4j), about 3.5 GB combined before Docker overhead.
- Prefer a tiny fixture/SciFact-sized experiment before any larger corpus. The
  planning guide’s target of 100k abstracts and full local indexing is likely
  impractical on this machine without close disk/RAM monitoring or offloading.
- Dense search downloads model weights on first use and caches them. BM25-only
  requests avoid loading the embedding model. Avoid running a local LLM alongside
  all three databases and an embedding model; use an external endpoint or a
  separate machine if generation is later added.
- Keep several GB of disk free for Docker images, indexes, model cache, and
  temporary downloads. Check `df -h .` and Docker Desktop storage periodically.
- This is a localhost development configuration. Do not expose these ports to a
  network or use the example credentials in a shared environment.

## 4. One-time setup

### Prerequisites

1. macOS on Intel (this lock/config path is currently Darwin + Python 3.12).
2. Docker Desktop with Compose v2, started before `make up`.
3. `uv` available on `PATH` and Python 3.12 available to `uv`.
4. Git and Make (provided by the macOS command line developer tools).

### First checkout

Commands below run from the repository directory containing this README,
`setup/evidencelens` in the parent workspace:

```sh
cd /path/to/evidencelens
uv sync --locked
```

`uv sync --locked` creates/updates `.venv` using `uv.lock` and installs the
runtime and development dependencies. This scaffold has no packaging/build-system
configuration yet, so the application is imported from `src/` by pytest and the
Makefile rather than installed as a wheel. Do not use system `pip install` for
this project; it risks installing into the wrong Python or changing the pinned
set. To choose the project interpreter in VS Code, select `.venv/bin/python`
(Python 3.12).

Create the local environment file only if it does not already exist:

```sh
test -f .env || cp .env.example .env
```

Edit `.env` locally. Set distinct development passwords for
`EL_ES_PASSWORD`, `EL_QDRANT_API_KEY`, and `EL_NEO4J_PASSWORD`; keep the file
private. The defaults in the example are placeholders, not production secrets.
The default local embedding settings are `BAAI/bge-small-en-v1.5` and 384
dimensions. If changing the model, change `EL_EMBED_MODEL` and `EL_EMBED_DIM`
together and recreate/rebuild the Qdrant collection and all corresponding
vectors. Never mix models or dimensions in one collection.

Optional source-ingestion variables are `EL_NCBI_API_KEY`,
`EL_OPENFDA_API_KEY`, and `EL_CONTACT_EMAIL`. They are not currently consumed by
an end-to-end ingester. Optional LLM settings are also future-facing.

### Check before starting services

```sh
make check
docker compose config --quiet
```

`make check` synchronizes the locked environment, runs Ruff, runs mypy, executes
pytest, and validates Compose syntax. It does not require healthy databases for
the current unit tests.

### Start, inspect, and stop the stores

```sh
make up
docker compose ps
docker compose logs --tail=100 elasticsearch qdrant neo4j
```

`make up` starts three containers and waits for configured health checks. Ports
are bound to loopback: Elasticsearch `9200`, Qdrant `6333`, Neo4j Browser
`7474`, and Neo4j Bolt `7687`. Confirm connectivity with:

```sh
curl -s http://127.0.0.1:8000/healthz
```

That last request requires the API to be running; first start it in another
terminal with `make serve`. Expected healthy response has `status: "ok"` and
true values for `es`, `qdrant`, and `neo4j`.

Stop containers with:

```sh
make down
```

This preserves named Elasticsearch/Qdrant volumes and the Neo4j files under
`data/neo4j`. **Do not use `docker compose down -v` as routine cleanup**: it
deletes persistent database data. Back up anything valuable before any volume or
database reset.

## 5. Day-to-day commands and API

| Command | Purpose |
| --- | --- |
| `make setup` / `make sync` | Run `uv sync --locked` |
| `make venv` | Compatibility alias for the locked uv sync; uv manages `.venv` |
| `make check` | Run lint, type check, unit tests, and Compose parse |
| `make lint` | Ruff and mypy |
| `make test` | Pytest |
| `make compose-check` | Validate Compose without starting/restarting services |
| `make up` | Start services and wait for health checks |
| `make down` | Stop services while preserving their data |
| `make serve` | Run FastAPI/Uvicorn on port 8000 with reload |

Start the API with `make serve`; interactive API schema is at
`http://127.0.0.1:8000/docs`. `make serve` currently expects the databases to
start first. It does not create indexes or seed data.

Health check:

```sh
curl -s http://127.0.0.1:8000/healthz
```

Search request examples (these need indexes/data that are not currently
provided by the repository):

```sh
curl -s http://127.0.0.1:8000/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"SGLT2 kidney outcomes","mode":"bm25","k":10,"year_min":2020}'

curl -s http://127.0.0.1:8000/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"therapies that lower blood sugar","mode":"dense","k":10}'

curl -s http://127.0.0.1:8000/v1/search \
  -H 'content-type: application/json' \
  -d '{"query":"metformin kidney disease","mode":"hybrid","k":10}'
```

Modes:

- `bm25`: Elasticsearch only; title is boosted over body text, with optional
  `year_min` filter.
- `dense`: Qdrant only; encodes the query using configured `EL_EMBED_MODEL`,
  then filters by `year_min` if supplied.
- `hybrid`: calls both retrievers and applies equal-weight RRF with the default
  smoothing constant 60. It combines ranks, not raw BM25/cosine scores.

The endpoint returns `{query, mode, k, results:[{chunk_id, score}, ...]}`. It
does not return passage contents or metadata yet. Unsupported modes such as
`graph` are rejected during request validation. `/v1/ask` returns HTTP 501 until
there is a real evidence-grounded answer pipeline.

## 6. Pipeline workflow and data contracts

### Intended ingestion lifecycle

The safe target workflow is source → raw/versioned data → parse → validate and
filter → deterministic chunks → derived indexes. Parquet is intended to become
the rebuildable source of truth; Elasticsearch, Qdrant, and Neo4j should be
derived views rather than the only copy of data. Each stage should be resumable
and idempotent so a retry does not silently duplicate records.

Planned PubMed stages are baseline/update download with a manifest and checksums,
streaming XML parse, handling `DeleteCitation` tombstones, domain/language/year
filters, then normalized storage. Today only the parse iterator exists. It emits
article dictionaries and delete operation dictionaries; it does not download,
persist, chunk, or index them.

The shared retrieval key is intended to be a stable `chunk_id`, used consistently
as Elasticsearch `_id`, Qdrant point ID/payload, and a Neo4j `Chunk` property.
When chunking is implemented, document updates must replace prior chunks by
`doc_id`, not leave stale versions behind. Abstracts are planned as one chunk
with title context; long documents should use explicit token-based chunk size
and overlap. Keep source URL/identifier, document ID, year, license, and
provenance alongside every chunk.

### Intended request lifecycle

Current `/v1/search`: validate request → call requested retrieval backend(s) →
fuse rank lists if needed → return chunk IDs/scores. Future work must add passage
hydration, metadata, graph candidate retrieval, error/degraded-backend handling,
reranking, evaluation, and only later answer generation. A future `/v1/ask` must
check that evidence is adequate, cite actual retrieved passages, verify citation
IDs, and refuse when support is insufficient. Retrieved web/document text must
be treated as untrusted input, not instructions to the model.

## 7. Repository map and file responsibilities

### Application code

| File | Purpose and extension point |
| --- | --- |
| `src/evidencelens/__init__.py` | Package marker and leftover scaffold greeting; the API entry point is elsewhere. |
| `src/evidencelens/config.py` | Typed settings/defaults and cached `EL_*` configuration. Add new service/model options here and to `.env.example`. |
| `src/evidencelens/api/main.py` | FastAPI app, shared client lifecycle, dependency injection, `/healthz`, `/v1/search`, and intentionally unimplemented `/v1/ask`. |
| `src/evidencelens/ingest/pubmed.py` | Streaming `.xml.gz` parser; extend with tests before adding download/filter/persistence logic. |
| `src/evidencelens/index/es.py` | Elasticsearch analyzer settings, strict mappings, index name, and a connectivity helper. Add explicit creation/bulk indexing separately. |
| `src/evidencelens/index/qdrant.py` | Collection name, dense/sparse schema and payload indexes. Point embeddings/upserts are still missing. |
| `src/evidencelens/kg/schema.py` | Neo4j uniqueness constraints and entity full-text index; graph population/retrieval are missing. |
| `src/evidencelens/retrieval/lexical.py` | BM25 query and ranked chunk-ID extraction from Elasticsearch. |
| `src/evidencelens/retrieval/dense.py` | Lazy sentence-transformer query encoding and filtered Qdrant search. |
| `src/evidencelens/retrieval/fusion.py` | Pure-Python weighted Reciprocal Rank Fusion. Keep this independent of services. |

### Project and contributor files

| File | Purpose |
| --- | --- |
| `README.md` | Handoff, setup, operating instructions, behavior, and roadmap (this file). |
| `Makefile` | Named repeatable developer/service/check commands. |
| `pyproject.toml` | Python version, direct/dev dependencies, uv CPU index/source, Ruff and pytest settings. |
| `uv.lock` | Machine-generated exact dependency resolution; update only intentionally with uv and review the dependency diff. |
| `.python-version` | Tells uv/tools to use Python 3.12. It is a one-line tool file, so comments do not belong in it. |
| `.env.example` | Safe template for local settings; copy to `.env`, never put actual credentials here. |
| `.env` | Local secrets/settings. This file is currently tracked in Git and needs security cleanup before further pushes (see §9). Do not inspect, paste, or document its values. |
| `.gitignore` | Excludes secrets, environments, caches, local data, and Parquet outputs from new Git additions. Ignoring does not untrack already tracked files. |
| `docker-compose.yml` | Local store versions, memory caps, ports, persistence, credentials, and health checks. |
| `LICENSE` | MIT terms for the code; does not change the license of third-party datasets. |
| `tests/test_api.py` | API mode dispatch, unimplemented graph mode, and no-fake-answer behavior. |
| `tests/test_fusion.py` | Basic rank-fusion behavior. |
| `tests/test_placeholder.py` | Temporary test-discovery placeholder; replace/remove as meaningful coverage grows. |

`src/evidencelens.egg-info/` is generated packaging metadata, not source code.
Python `__pycache__` files and `.venv/` are also generated. Do not add comments
to generated lock/metadata or binary artifacts; explain their roles here instead.

### Companion planning documents

The parent workspace currently has `../../doc/README.md`,
`../../doc/beginner-guide.md`, `../../doc/checklist.md`,
`../../doc/implementation-guide.md`, and two setup/scope PDFs. These are planning
and learning references, not imported runtime dependencies. Some contain target
features and schedules beyond this repository’s implementation; treat the status
table above and executable code as authoritative for what works now. Include
these companion documents separately when handing off a copy of the entire
workspace; they are outside this repository directory.

## 8. Development and testing conventions

- Use Python 3.12 and run commands via `uv run --locked` or the Makefile. Never
  rely on whichever `python3` happens to be first on `PATH`.
- Keep service calls behind small modules and pass clients/settings explicitly;
  avoid importing/loading heavyweight models at API module import time.
- Add unit tests for pure logic and parsers. Mark tests requiring Docker as
  `integration`; tests requiring an external model/API as `llm` (markers are
  registered in `pyproject.toml`).
- Test stable identifiers, XML edge cases, tombstones, filter behavior, retry and
  resume semantics before scaling ingestion.
- Keep one embedding model/dimension per collection. Rebuild vectors when the
  model changes; do not silently mix embeddings.
- Make index creation and ingestion idempotent, log counts, and preserve source
  and license metadata. Never claim benchmark numbers that were not measured.
- Do not make a database mutation or destructive volume reset casually. Confirm
  target and backup before any delete/recreate operation.

The expected pre-commit gate is:

```sh
make check
git diff --check
git status --short
```

## 9. Security, safety, and data handling

### Immediate Git hygiene item

`.env` is currently a tracked file in this repository. `.gitignore` prevents new
untracked environment files from being added, but does not remove a file already
in Git. Before pushing further changes, coordinate this cleanup:

```sh
git rm --cached .env
```

This removes `.env` from the Git index but leaves the local file on disk. Then
rotate any real credentials that were ever committed. If secrets were pushed to
a remote, removing the latest file is not enough: follow your host’s secret
incident procedure and consider history cleanup with collaborators. Do not
commit the local file back. `.env.example` should contain placeholders only.

Other safeguards:

- Compose binds service ports to `127.0.0.1`; keep this a local-only setup unless
  authentication, TLS, firewall, and deployment controls are added.
- Credentials are transmitted over plain HTTP/Bolt on localhost in this dev
  setup. Do not reuse these settings on an untrusted network.
- Medical answers are not implemented. Future answer generation requires clear
  non-medical-advice language, safety/refusal handling, evidence-grounded
  citations, and citation validation.
- Preserve original source, stable identifiers, license/attribution, and
  provenance. Do not redistribute data merely because an API allowed download.
- Avoid storing prompt/answer bodies or personal data in observability traces by
  default; add redaction and explicit retention policy before tracing user data.

## 10. Troubleshooting

| Symptom | Likely cause / next check |
| --- | --- |
| `uv sync --locked` complains about Python | Install/select Python 3.12; `.python-version` and `requires-python` intentionally reject other versions. |
| VS Code/Pylance cannot find installed packages | Select `setup/evidencelens/.venv/bin/python` (or the workspace-relative `setup/evidencelens/.venv/bin/python` from the parent workspace), then reload Pylance. For commands use `uv run --locked`, not system Python. |
| Docker command cannot connect | Start Docker Desktop; check `docker info` and `docker compose ps`. |
| Compose says a port is occupied | Find the process/container using 9200, 6333, 7474, or 7687; stop only the intended conflicting service. Do not delete volumes to solve a port conflict. |
| A container is unhealthy | Inspect `docker compose logs --tail=200 <service>`, available disk/RAM, and credentials. Existing Neo4j data may retain an old password; changing `NEO4J_AUTH` does not necessarily reset an initialized database. |
| `/healthz` is degraded | The response identifies which service failed. Check that service’s health/logs and local credentials. Health checks do not test whether data has been indexed. |
| `/v1/search` reports missing index/collection or returns no hits | Expected until index creation and data-loading pipeline is implemented. A green health check is only a connectivity check. |
| Dense search fails on first request | It may be downloading model files; check network/cache/disk. Ensure configured model/dimension match the Qdrant schema and indexed vectors. Use `bm25` to avoid loading the embedding model. |
| Mac becomes memory- or disk-constrained | Stop services with `make down` (persistent indexes remain), close model-heavy processes, inspect Docker Desktop storage and `df -h .`; reduce corpus before increasing memory caps. |
| Git still lists `.env` after adding ignore rule | It is already tracked. Use the security procedure above; do not print its contents into logs. |

## 11. Recommended handoff roadmap

Build in small verified increments rather than trying to implement every item in
the planning documents at once:

1. **Secure baseline:** untrack `.env`, rotate exposed credentials, keep only
  placeholders in `.env.example`, and agree on the committed dependency lock.
2. **Small vertical slice:** create a tiny licensed fixture corpus and one
  command that creates ES/Qdrant schemas, embeds a few documents, upserts the
  same `chunk_id` to both stores, then verifies counts. Keep it comfortably
  small for the 8 GB machine.
3. **Complete retrieval contract:** return text/source metadata (not only IDs),
  handle empty/unavailable backends predictably, and test exact/semantic/year
  filtered examples against fixtures.
4. **Resumable ingestion:** download a small PubMed subset, manifest hashes,
  parse and handle tombstones, normalize/filter, write Parquet, and make reruns
  idempotent. Add integration tests before increasing data volume.
5. **Measure retrieval:** add a frozen tiny relevance set and compute nDCG@10,
  Recall@k, and MRR for BM25, dense, and hybrid before tuning weights/models.
6. **Graph only when justified:** load structured, provenance-backed edges;
  test graph query templates and compare value against non-graph retrieval.
7. **RAG last:** hydrate/rerank evidence, add sufficiency/refusal gates, generate
  answers from evidence only, validate every citation, then add API streaming
  and safety/evaluation tests.
8. **Scale/operations:** only after the small path is repeatable, version data,
  document licenses, test fresh-clone setup, and consider external compute for
  larger corpora/models.

For decisions, record the problem, alternatives, resource impact, and validation
in a short ADR. Update this README whenever a planned component becomes
implemented; keep “implemented” and “planned” clearly distinguished.

## 12. License and disclaimer

The project code is MIT-licensed; see `LICENSE`. Dataset terms remain specific
to each upstream source. EvidenceLens is an engineering/research prototype and
does not provide medical advice. Do not use it to make clinical decisions.
