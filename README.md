# rag-for-laravel-modular-monolith-with-client-sdk

Local RAG system powered by `deepseek-coder-v2:16b` for generating and
maintaining Laravel enterprise architecture — pure PHP client SDKs,
Laravel modules that wire SDKs into the application via PSR interfaces,
and Filament backoffice configuration.

---

## What This System Does

Given a question or a pasted log entry, the system:

1. Embeds the query using `BAAI/bge-small-en-v1.5` (local, no network required)
2. Retrieves the most relevant knowledge chunks from ChromaDB
3. Sends retrieved context + query to `deepseek-coder-v2:16b` via Ollama
4. Returns a grounded answer — no invented conventions, no hallucinated patterns
5. Flags knowledge gaps (`GAP:`) and inconsistencies (`INCONSISTENCY:`) for human review via `memory_review.py`

---

## What This Generates

### 1. PHP Client SDK (`packages/service-{name}-sdk/`)

Pure PHP package. Zero Laravel dependencies. PSR interfaces only.
The SDK exposes `HttpClientInterface`, `LoggerInterface`, and
`EventDispatcherInterface` — the consumer injects concrete implementations.

```
src/
├── Service{Name}.php      ← single public entrypoint
├── Contracts/             ← HttpClientInterface, LoggerInterface, EventDispatcherInterface
├── Configs/               ← readonly value objects, fromArray() construction
├── Data/                  ← Request + Response DTOs
│   ├── Requests/
│   └── Responses/
├── Exceptions/            ← SdkException hierarchy
├── Internal/              ← protocol callers, token cache, request builders
└── Redaction/             ← RedactionRule, RedactionPolicy, PayloadRedactor
```

### 2. Laravel Module (`packages/module-{name}/`)

Wires the SDK into the Laravel application. Owns the full business domain.
Registers into both application runtimes via a single service provider.

```
src/
├── Adapters/              ← TelescopeHttpClient, LaravelEventDispatcher, LaravelCacheAdapter
├── Actions/               ← single-purpose business operations
├── Commands/              ← Artisan commands
├── Events/                ← domain events
├── Exceptions/            ← ModuleException hierarchy
├── Filament/              ← backoffice resources, pages, widgets
├── Listeners/             ← event listeners (queued or sync)
├── Models/                ← Eloquent models
└── Providers/
    └── ModuleServiceProvider.php  ← wires SDK interfaces → Laravel implementations
database/
└── migrations/            ← module-owned migrations
```

### 3. Laravel Application (one app, two runtimes)

```
routes/
├── api.php                ← API runtime — REST endpoints, client-facing
└── backoffice.php         ← Backoffice runtime — Filament, admin, ops UI

bootstrap/
└── app.php                ← registers both middleware groups
```

Filament resources from each module activate only in the backoffice runtime.
API routes from each module activate only in the API runtime.

---

## Architecture

```
PHP Client SDK  (zero Laravel dependencies)
    ↓ injected via Contracts/ interfaces
Laravel Module
    ├── Adapters/       ← TelescopeHttpClient → all outbound HTTP visible in Telescope
    ├── Actions/        ← business logic, wraps SDK calls, owns exception handling
    ├── Filament/       ← backoffice UI (backoffice runtime only)
    └── Providers/      ← binds SDK interfaces to Laravel implementations
    ↓
Laravel Application
    ├── Backoffice runtime   (Filament, middleware: auth:web + filament)
    └── API runtime          (REST, middleware: auth:sanctum + throttle)
```

**Critical rule:** `TelescopeHttpClient` uses `Illuminate\Http\Client\Factory` —
this guarantees every outbound SDK HTTP call is visible in Laravel Telescope.

---

## On-Demand Provider Analysis

Provider-specific analysis documents (API shape, auth flows, response envelopes,
known quirks) live inside the Laravel project they describe — not in this repo.

```
your-laravel-app/
└── docs/
    └── analysis/
        ├── svgate.md
        ├── humo-payment.md
        ├── paynet.md
        └── ...
```

When working on a specific provider integration, inject the relevant analysis
file into the vector store on-demand:

```bash
python ops.py ai scope use package svgate-sdk
# or inject directly:
./.venv/bin/python -c "
from app import process_file
process_file('/path/to/your-laravel-app/docs/analysis/svgate.md')
"
```

This keeps the permanent knowledge base clean — architectural rules only.
Provider analysis is ephemeral context, not permanent knowledge.

---

## Prerequisites

- Ollama running at `http://localhost:11434`
- `deepseek-coder-v2:16b` pulled: `ollama pull deepseek-coder-v2:16b`
- Python 3.11+

---

## Install

```bash
git clone https://github.com/khakimjanovich/rag-for-laravel-modular-monolith-with-client-sdk
cd rag-for-laravel-modular-monolith-with-client-sdk
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

---

## Setup

### 1. Create the project contract

```bash
cp project.contract.example.json project.contract.json
# edit project.contract.json — set root to your Laravel monorepo path
```

The runtime resolves the contract in this order:

1. `LER_PROJECT_FILE` environment variable
2. `.active_project` file
3. `project.contract.json`
4. `project.contract.example.json`

### 2. Ingest the knowledge base

```bash
./.venv/bin/python -c "
from app import update_files
update_files()
"
```

Re-run whenever you add or update a knowledge file.
The ingestion engine tracks modification times — only changed files are re-processed.

### 3. Test retrieval

```bash
./.venv/bin/python -c "
from app import get_collection, get_embedding
query = 'How should I structure a PHP SDK package?'
embedding = get_embedding(query)
results = get_collection().query(query_embeddings=[embedding], n_results=3)
for i, doc in enumerate(results['documents'][0]):
    print(f'[{i+1}] {doc[:300]}')
    print()
"
```

### 4. Start the chat

```bash
./.venv/bin/python chat.py
```

### 5. Run the test suite

```bash
./.venv/bin/pytest -q
```

Tests are hermetic — they use a temporary project contract, a temporary Chroma
database, and a fake embedding model. Ollama is not required for the test suite.

---

## CLI Interface

```bash
# Project management
python ops.py ai project list
python ops.py ai project add --name my-project --contract ./project.contract.json

# Scope management — focus the model on one package
python ops.py ai scope use package svgate-sdk

# Gap analysis — find what the model doesn't know yet
python ops.py project analyze gaps --scope app
```

---

## Usage

```
Your Question> How should I structure a PHP SDK package?
Your Question> What is forbidden inside an SDK composer.json?
Your Question> Where does TelescopeHttpClient live and what must it implement?
Your Question> How do I extend the default redaction policy with provider-specific fields?
Your Question> What exception should be thrown when a provider returns an error code?
Your Question> How do I register a Filament resource inside a module?
Your Question> I have this log entry — which layer owns the fix?

/review                    ← list open gaps and inconsistencies
/accept-memory <id>        ← mark a gap as resolved
/fix <id>                  ← mark an inconsistency for fixing
exit                       ← quit
```

---

## Knowledge Base

Permanent architectural knowledge — rules, patterns, conventions.
Provider-specific analysis lives in the Laravel project, not here.

```
knowledge/
├── sdk/
│   ├── 01-structure.md              ✅ ingested  — package layout, entrypoint rules
│   ├── 02-redaction-and-cache.md    ✅ ingested  — RedactionRule, RedactionPolicy, PayloadRedactor, CacheInterface
│   ├── 03-exceptions.md             ✅ ingested  — SdkException hierarchy
│   ├── 04-dtos.md                   ✅ ingested  — Request/Response DTO patterns
│   └── 05-boundaries.md             ✅ ingested  — what SDK must never contain
├── module/
│   └── 01-structure.md              ✅ file present — run ingestion to load
├── diagnostic/
│   └── 03-decision-tree.md          ← not yet written
└── conventions/
    └── CONVENTIONS.md               ✅ ingested  — confirmed/observed/proposed registry
```

**Knowledge base rules:**
- Never mark a convention `confirmed` unless it is implemented in code
- Fake conventions poison the knowledge base and every answer that follows
- Provider analysis belongs in the Laravel project — inject on-demand when needed

---

## Adding New Knowledge

```bash
# 1. Write the rule or convention as a .md file
# 2. Place it in the correct knowledge/ subfolder
# 3. Re-run ingestion
./.venv/bin/python -c "from app import update_files; update_files()"
# 4. The model will use it in all future answers
```

---

## Resetting the Vector Store

If you need a clean slate (e.g. after removing analysis files that shouldn't
have been ingested):

```bash
rm processed_files.json
rm -rf chroma_db/
./.venv/bin/python -c "from app import update_files; update_files()"
```

---

## Model Configuration

| Component   | Value                    |
|-------------|--------------------------|
| LLM         | `deepseek-coder-v2:16b`  |
| Embeddings  | `BAAI/bge-small-en-v1.5` |
| Vector DB   | ChromaDB (local)         |
| Ollama API  | `http://localhost:11434`  |

The embedding model loads lazily — importing `app.py` does not require
network access or a running Ollama instance.

---

## Current Status

| Component              | Status                        |
|------------------------|-------------------------------|
| ChromaDB               | ✅ running                    |
| Embeddings             | ✅ BAAI/bge-small-en-v1.5     |
| LLM                    | ✅ deepseek-coder-v2:16b      |
| Ingestion              | ✅ working                    |
| Retrieval              | ✅ verified                   |
| Chat interface         | ✅ working                    |
| GAP/INCONSISTENCY flags| ✅ working                    |
| CLI (ops.py)           | ✅ working                    |
| Test suite             | ✅ hermetic, passing           |
| knowledge/sdk          | ✅ 5/5 ingested               |
| knowledge/module       | ⚠️  1/1 present, needs ingest |
| knowledge/diagnostic   | ⚠️  0/1 written               |
| knowledge/conventions  | ✅ 1/1 ingested               |