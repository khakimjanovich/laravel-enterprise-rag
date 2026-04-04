# laravel-enterprise-rag

Local LLM knowledge base for generating Laravel enterprise architecture —
PHP client SDKs, Laravel modules that wire SDKs into the application,
and Filament backoffice configuration.

---

## What This Generates

### 1. PHP Client SDK (`packages/service-{name}-sdk/`)
Pure PHP package. Zero Laravel dependencies. PSR interfaces only.
Consumed by the Laravel module via injected adapters.

### 2. Laravel Module (`packages/module-{name}/`)
Wires the SDK into the Laravel application. Owns the domain.
Registers into both application runtimes via a single service provider.

```
src/
├── Adapters/        ← implements SDK interfaces (TelescopeHttpClient etc.)
├── Actions/         ← business logic
├── Models/          ← Eloquent models
├── Events/          ← domain events
├── Listeners/       ← event listeners
├── Commands/        ← Artisan commands
├── Filament/        ← backoffice resources, pages, widgets
└── Providers/       ← service provider — wires everything
```

### 3. Laravel Application (one app, two runtimes)

```
routes/
├── api.php          ← API runtime — REST endpoints, client-facing
└── backoffice.php   ← Backoffice runtime — Filament, admin, config UI

bootstrap/
└── app.php          ← registers both middleware groups
```

Filament resources from each module activate only in the backoffice runtime.
API routes from each module activate only in the API runtime.

---

## Architecture Overview

```
PHP Client SDK
    ↓ injected via PSR interfaces
Laravel Module
    ├── Adapters        ← bridge between SDK contracts and Laravel
    ├── Filament        ← backoffice UI (backoffice runtime only)
    └── ServiceProvider ← registers into both runtimes
    ↓
Laravel Application
    ├── Backoffice runtime   (Filament, middleware: auth:web + filament)
    └── API runtime          (REST, middleware: auth:sanctum + throttle)
```

---

## Prerequisites

- Ollama running at `http://localhost:11434`
- `deepseek-coder-v2:16b` pulled (`ollama pull deepseek-coder-v2:16b`)
- Python 3.14+

---

## Install

```bash
git clone <repo> laravel-enterprise-rag
cd laravel-enterprise-rag
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

---

## Setup

### 1. Create the project contract

Copy `project.contract.example.json` to `project.contract.json` and adjust the paths if needed.

The runtime loads contracts in this order:
- `LER_PROJECT_FILE`
- `.active_project`
- `project.contract.json`
- `project.contract.example.json`

An explicit `LER_PROJECT_FILE` path must exist or startup will fail with a clear error.

### 2. Ingest the knowledge base

```bash
./.venv/bin/python -c "
from app import list_local_files, process_file
files = list_local_files()
print(f'Found {len(files)} files:')
for f in files:
    print(f'  {f[\"name\"]}')
    process_file(f['path'])
print('Done.')
"
```

Run this again whenever you add or update a knowledge file.

### 3. Test retrieval

```bash
./.venv/bin/python -c "
from app import get_collection, get_embedding
query = 'How should I structure a PHP SDK package?'
embedding = get_embedding(query)
results = get_collection().query(query_embeddings=[embedding], n_results=2)
for i, doc in enumerate(results['documents'][0]):
    print(f'[{i+1}] {doc[:300]}')
"
```

### 4. Start the chat

```bash
./.venv/bin/python chat.py
```

### 5. Run tests

```bash
./.venv/bin/pytest -q
```

The automated tests are hermetic: they use a temporary project contract, a temporary Chroma database, and a fake embedding model. Ollama and downloaded Hugging Face models are not required for the default test run.

---

## Usage

Ask anything about your SDK, module, or Filament conventions:

```
Your Question> How should I structure a PHP SDK package?
Your Question> What is forbidden inside an SDK composer.json?
Your Question> Where does TelescopeHttpClient live?
Your Question> How do I register a Filament resource inside a module?
Your Question> What is the difference between the API and backoffice runtime?
```

Type `exit` to quit.

---

## Knowledge Base Structure

```
knowledge/
├── sdk/
│   ├── 01-structure.md              ✅ ingested
│   ├── 02-redaction-and-cache.md
│   ├── 03-exceptions.md
│   ├── 04-dtos.md
│   └── 05-boundaries.md
├── module/
│   ├── 01-structure.md
│   ├── 02-adapters.md
│   ├── 03-exceptions.md
│   └── 04-filament-audit.md
├── diagnostic/
│   ├── 02-correlation.md
│   └── 03-decision-tree.md
└── conventions/
    └── CONVENTIONS.md               ✅ ingested
```

---

## Adding New Knowledge

1. Write your convention or rule as a `.md` file
2. Place it in the correct `knowledge/` subfolder
3. Re-run ingestion
4. The model will use it in all future answers

Never mark a convention as `confirmed` unless it is actually
implemented in code. Fake conventions poison the knowledge base.

---

## Adding New Conventions

1. Implement the convention in code
2. Open `knowledge/conventions/CONVENTIONS.md`
3. Add to the appropriate section with status `confirmed`
4. Re-run ingestion
5. The model will now use this convention in all future generations

---

## Model Configuration

The chat interface uses `deepseek-coder-v2:16b` via Ollama by default.
Embeddings are generated with `BAAI/bge-small-en-v1.5` in `app.py`.

The embedding model is loaded lazily when `get_embedding()` is first called, so importing `app.py` does not require network access.

---

## Current Status

| Component             | Status                |
|-----------------------|-----------------------|
| ChromaDB              | running               |
| Embeddings            | all-MiniLM-L6-v2      |
| LLM                   | deepseek-coder-v2:16b |
| Ingestion             | working               |
| Retrieval             | verified              |
| Chat interface        | working               |
| knowledge/sdk         | 1/5 docs ingested     |
| knowledge/module      | 0/4 docs ingested     |
| knowledge/diagnostic  | 0/2 docs ingested     |
| knowledge/conventions | 1/1 docs ingested     |
