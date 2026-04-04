# Test Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the project boot and test reliably in a fresh checkout without requiring hidden local files, downloaded models, or pre-populated Chroma state.

**Architecture:** Move import-time setup behind explicit helpers so `app.py` can be imported in tests without opening external resources. Add a deterministic test harness with a temporary project contract, stub embeddings, and isolated Chroma storage, then align the docs and dependency setup with the actual runtime expectations.

**Tech Stack:** Python 3.14, pytest, ChromaDB, Sentence Transformers, Ollama, Rich

---

### Task 1: Reproduce the current failures and capture the baseline

**Files:**
- Modify: `README.md`
- Test: `tests/test_app.py`

**Step 1: Verify the current test command**

Run: `./.venv/bin/pytest -q`
Expected: FAIL with import errors against `app`

**Step 2: Verify the first import-time root cause**

Run:

```bash
./.venv/bin/python -c "import app"
```

Expected: FAIL because `project.contract.json` is missing

**Step 3: Verify the next blocker after supplying a temporary contract**

Run a one-off import with `LER_PROJECT_FILE` pointed at a temporary JSON contract.
Expected: FAIL because `SentenceTransformer('BAAI/bge-small-en-v1.5')` attempts a network/model fetch during import

**Step 4: Record the verified baseline in the README troubleshooting section**

Add a short note that the current failures are caused by import-time project-contract and model initialization, not by test assertions themselves.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: record current test baseline"
```

### Task 2: Remove import-time side effects from `app.py`

**Files:**
- Modify: `app.py`
- Modify: `chat.py`
- Test: `tests/test_app.py`

**Step 1: Write a failing test for import safety**

Add a test that imports `app` with a temporary contract and patched dependencies without requiring network access or a pre-existing database.

```python
def test_app_imports_with_temp_contract(monkeypatch, tmp_path):
    ...
```

**Step 2: Run only that test**

Run: `./.venv/bin/pytest tests/test_app.py::test_app_imports_with_temp_contract -q`
Expected: FAIL because import currently initializes contract, Chroma, and model immediately

**Step 3: Refactor `app.py` into explicit initialization helpers**

Introduce small functions for:

```python
def load_project() -> ProjectContract: ...
def create_collection(persist_directory: str): ...
def create_embedding_model(model_name: str): ...
```

Initialize them lazily or behind overridable module-level helpers so tests can patch them before use.

**Step 4: Update callers in `chat.py`**

Replace direct reliance on import-time globals with helper accessors or explicit initialization so chat mode still works after the refactor.

**Step 5: Re-run the targeted test**

Run: `./.venv/bin/pytest tests/test_app.py::test_app_imports_with_temp_contract -q`
Expected: PASS

**Step 6: Commit**

```bash
git add app.py chat.py tests/test_app.py
git commit -m "refactor: remove import-time app side effects"
```

### Task 3: Make project configuration explicit and testable

**Files:**
- Modify: `project_contract.py`
- Create: `project.contract.example.json`
- Modify: `README.md`
- Test: `tests/test_app.py`

**Step 1: Write failing tests for config discovery**

Add tests covering:
- explicit `LER_PROJECT_FILE`
- optional fallback example/default contract
- clear error message when no contract can be found

```python
def test_project_contract_reads_env_file(...): ...
def test_project_contract_missing_file_has_clear_error(...): ...
```

**Step 2: Run the targeted config tests**

Run: `./.venv/bin/pytest tests/test_app.py -k contract -q`
Expected: FAIL until config handling is improved

**Step 3: Implement deterministic contract loading**

Keep the contract abstraction, but stop depending on an untracked local file with no documented setup. Either:
- ship a checked-in example/default contract for local repo usage, or
- make the error path explicit and actionable

Use one path consistently and document it.

**Step 4: Update setup documentation**

Document:
- how to create/select the contract
- required env vars
- where reports are written

**Step 5: Re-run the targeted config tests**

Run: `./.venv/bin/pytest tests/test_app.py -k contract -q`
Expected: PASS

**Step 6: Commit**

```bash
git add project_contract.py project.contract.example.json README.md tests/test_app.py
git commit -m "feat: make project contract setup explicit"
```

### Task 4: Replace brittle integration assertions with hermetic tests

**Files:**
- Modify: `tests/test_app.py`
- Create: `tests/conftest.py`

**Step 1: Write fixtures for isolated runtime state**

Create fixtures for:
- temporary knowledge directory
- temporary reports directory
- temporary Chroma persistence directory
- fake embedding model
- test contract JSON

```python
@pytest.fixture
def fake_model():
    class FakeModel:
        def encode(self, text):
            return [float(len(text))] * 4
    return FakeModel()
```

**Step 2: Replace assertions that depend on local persisted data**

Remove assumptions like:
- `collection.count() >= 39`
- semantic relevance depending on existing embedded knowledge

Replace them with tests that ingest controlled markdown fixtures and assert exact outcomes.

**Step 3: Split unit tests from integration tests**

Keep default tests fast and deterministic. Mark any live-model or live-Ollama coverage explicitly, for example with `@pytest.mark.integration`.

**Step 4: Run the full test suite**

Run: `./.venv/bin/pytest -q`
Expected: PASS for unit tests; integration tests skipped unless enabled

**Step 5: Commit**

```bash
git add tests/conftest.py tests/test_app.py
git commit -m "test: make app coverage hermetic"
```

### Task 5: Align dependencies and developer workflow with reality

**Files:**
- Modify: `requirements.txt`
- Modify: `README.md`
- Optional Create: `Makefile` or `scripts/test.sh`

**Step 1: Write a failing workflow note test or checklist item**

Document the mismatch first:
- `pytest` is used but not listed in `requirements.txt`
- README setup does not mention `.venv`, contract setup, or offline behavior
- README model details differ from current code

**Step 2: Add the missing dev dependency**

Add `pytest` to `requirements.txt` or split runtime/dev requirements if you want cleaner separation.

**Step 3: Correct the README**

Update:
- test command to `./.venv/bin/pytest -q` or documented virtualenv activation
- actual embedding model in `app.py`
- contract/bootstrap requirements
- expected local services for chat vs tests

**Step 4: Add a single documented test command**

Prefer one stable command, for example:

```bash
./.venv/bin/pytest -q
```

**Step 5: Verify from the documented path**

Run:

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall app.py chat.py analyse.py tests
```

Expected: tests pass; compilation passes

**Step 6: Commit**

```bash
git add requirements.txt README.md
git commit -m "docs: align setup and test workflow"
```

### Task 6: Optional follow-up for analysis/reporting modules

**Files:**
- Modify: `analyse.py`
- Modify: `memory_review.py`
- Test: `tests/test_app.py` or new dedicated tests

**Step 1: Add focused tests for report persistence paths**

Verify `memory_review.py` writes into the configured reports directory and handles missing report files cleanly.

**Step 2: Make `analyse.py` failure modes explicit**

Handle missing `PHP_PROJECT`, Ollama request failures, and output directory expectations with clearer messages and test coverage.

**Step 3: Run targeted tests**

Run: `./.venv/bin/pytest -k "memory_review or analyse" -q`
Expected: PASS

**Step 4: Commit**

```bash
git add analyse.py memory_review.py tests
git commit -m "test: cover report and analysis paths"
```

