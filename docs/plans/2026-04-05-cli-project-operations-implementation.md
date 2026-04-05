# CLI Project Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI-first project operations layer for Laravel enterprise app and SDK package workflows, including project selection, scope selection, ingestion, gap analysis, and review/report management.

**Architecture:** Keep the CLI thin and move operational behavior into reusable Python service modules. Persist project registry, active scope, findings, and generated analysis artifacts under the active project so the future HTTP API can wrap the same service layer without reimplementing logic.

**Tech Stack:** Python 3.14, pytest, ChromaDB, Rich, JSON-backed local state

---

### Task 1: Add active-scope persistence and contract metadata

**Files:**
- Modify: `project_session.py`
- Modify: `project_contract.py`
- Modify: `project.contract.example.json`
- Test: `tests/test_project_session.py`
- Test: `tests/test_project_contract.py`

**Step 1: Write the failing scope/session tests**

Create tests covering:
- save and load the active scope
- default scope behavior when no scope is set
- contract parsing for `project_type`, `package_roots`, and `service_docs`

```python
def test_set_active_scope_persists_value(tmp_path, monkeypatch):
    ...

def test_project_contract_reads_package_roots(tmp_path, monkeypatch):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_project_session.py tests/test_project_contract.py -q
```

Expected: FAIL because active scope support and extended contract fields do not exist yet

**Step 3: Implement active scope persistence**

Add to `project_session.py`:

```python
ACTIVE_SCOPE_FILE = ".active_scope"

def set_active_scope(scope: str) -> None:
    ...

def get_active_scope() -> str | None:
    ...
```

Keep the file format minimal: a single scope string such as `app` or `package:svgate-sdk`.

**Step 4: Extend `ProjectContract`**

Add optional fields:

```python
project_type: str = "laravel-app"
package_roots: list[str] = field(default_factory=list)
service_docs: list[str] = field(default_factory=list)
```

Update `from_file()` to read these fields safely with defaults.

**Step 5: Update the example contract**

Ensure `project.contract.example.json` includes:
- `project_type`
- `package_roots`
- `service_docs`

**Step 6: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_project_session.py tests/test_project_contract.py -q
```

Expected: PASS

**Step 7: Commit**

```bash
git add project_session.py project_contract.py project.contract.example.json tests/test_project_session.py tests/test_project_contract.py
git commit -m "feat: add scope persistence and contract metadata"
```

### Task 2: Create project registry and scope service layer

**Files:**
- Create: `services/project_registry_service.py`
- Create: `services/scope_service.py`
- Modify: `project_session.py`
- Test: `tests/test_project_registry_service.py`
- Test: `tests/test_scope_service.py`

**Step 1: Write the failing service tests**

Create tests for:
- listing registered projects
- adding a project
- selecting the active project
- discovering package scopes from `package_roots`
- validating `app` and `package:<name>` scopes

```python
def test_list_projects_returns_registered_names(...):
    ...

def test_scope_service_discovers_package_scopes(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_project_registry_service.py tests/test_scope_service.py -q
```

Expected: FAIL because the service modules do not exist yet

**Step 3: Implement `project_registry_service.py`**

Export functions like:

```python
def list_projects() -> list[dict]:
    ...

def add_project(name: str, contract_path: str) -> None:
    ...

def use_project(name: str) -> bool:
    ...

def current_project() -> dict | None:
    ...
```

Back them with `project_session.py`.

**Step 4: Implement `scope_service.py`**

Export functions like:

```python
def list_scopes(contract: ProjectContract) -> list[str]:
    ...

def set_scope(scope: str, contract: ProjectContract) -> None:
    ...

def current_scope(contract: ProjectContract) -> str:
    ...
```

Use:
- `app`
- discovered `package:<name>` scopes from `package_roots`

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_project_registry_service.py tests/test_scope_service.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add services/project_registry_service.py services/scope_service.py project_session.py tests/test_project_registry_service.py tests/test_scope_service.py
git commit -m "feat: add project registry and scope services"
```

### Task 3: Add a dedicated CLI entrypoint for project and scope commands

**Files:**
- Create: `cli.py`
- Modify: `README.md`
- Test: `tests/test_cli_project_commands.py`

**Step 1: Write the failing CLI tests**

Create subprocess or direct command-parser tests for:
- `project list`
- `project add`
- `project use`
- `project current`
- `scope list`
- `scope use`
- `scope current`

```python
def test_cli_project_add_registers_contract(...):
    ...

def test_cli_scope_use_package_sets_active_scope(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_cli_project_commands.py -q
```

Expected: FAIL because `cli.py` does not exist yet

**Step 3: Implement the CLI command parser**

Use `argparse` and keep the parser structure flat and explicit:

```python
project list
project add --name NAME --contract PATH
project use NAME
project current
scope list
scope use app
scope use package PACKAGE_NAME
scope current
```

Each command should print deterministic text and exit non-zero on invalid input.

**Step 4: Update README**

Document the new CLI entrypoint and basic project/scope usage.

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_cli_project_commands.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add cli.py README.md tests/test_cli_project_commands.py
git commit -m "feat: add project and scope CLI commands"
```

### Task 4: Normalize review and report storage

**Files:**
- Create: `services/report_service.py`
- Modify: `memory_review.py`
- Test: `tests/test_report_service.py`
- Test: `tests/test_memory_review.py`

**Step 1: Write the failing persistence tests**

Create tests for:
- creating a bug report
- creating a missing SDK report
- listing open review items
- resolving review items
- persisting `scope` and `kind`

```python
def test_report_service_creates_missing_sdk_item(...):
    ...

def test_memory_review_resolve_updates_status(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_report_service.py tests/test_memory_review.py -q
```

Expected: FAIL because the normalized report model does not exist yet

**Step 3: Implement `report_service.py`**

Support:

```python
def create_bug_report(scope: str, title: str, details: str) -> dict:
    ...

def create_missing_sdk_report(scope: str, title: str, details: str) -> dict:
    ...
```

Persist into the active project reports directory.

**Step 4: Extend `memory_review.py`**

Make stored items include:
- `scope`
- `kind`
- `status`

Keep existing chat behavior working for `gap` and `inconsistency`.

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_report_service.py tests/test_memory_review.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add services/report_service.py memory_review.py tests/test_report_service.py tests/test_memory_review.py
git commit -m "feat: normalize review and report persistence"
```

### Task 5: Implement package discovery and capability inventory

**Files:**
- Create: `services/capability_inventory_service.py`
- Test: `tests/test_capability_inventory_service.py`
- Optional Create: `tests/fixtures/laravel_app/`

**Step 1: Write the failing inventory tests**

Build fixture trees that simulate:
- Laravel app/module logic expecting service operations
- SDK package code implementing some but not all operations

Create tests for:

```python
def test_expected_capabilities_are_inferred_from_module_logic(...):
    ...

def test_implemented_capabilities_are_inferred_from_sdk_package(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_capability_inventory_service.py -q
```

Expected: FAIL because no inventory service exists yet

**Step 3: Implement expected capability extraction**

From app/module logic, infer expected service operations by scanning code patterns inside the project root and package roots. Keep the first pass intentionally narrow and documented.

The first version should:
- use regex/file heuristics
- produce deterministic operation identifiers
- avoid trying to solve general static analysis

**Step 4: Implement implemented capability extraction**

From package scope, infer implemented operations by scanning SDK package code, public clients, methods, and transport/action names.

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_capability_inventory_service.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add services/capability_inventory_service.py tests/test_capability_inventory_service.py tests/fixtures/laravel_app
git commit -m "feat: add capability inventory analysis"
```

### Task 6: Implement gap analysis between module intent and SDK implementation

**Files:**
- Create: `services/gap_analysis_service.py`
- Test: `tests/test_gap_analysis_service.py`

**Step 1: Write the failing gap-analysis tests**

Create tests for:
- app scope detects missing SDK operations
- package scope shows missing package capabilities
- findings are emitted with `kind`, `scope`, `title`, and `details`

```python
def test_gap_analysis_reports_missing_sdk_operation_for_app_scope(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_gap_analysis_service.py -q
```

Expected: FAIL because no gap analysis service exists yet

**Step 3: Implement `gap_analysis_service.py`**

Expose functions like:

```python
def analyze_app_scope(contract: ProjectContract) -> list[dict]:
    ...

def analyze_package_scope(contract: ProjectContract, package_name: str) -> list[dict]:
    ...
```

Diff:
- expected capabilities
- implemented capabilities

Emit normalized findings with:
- `kind`
- `scope`
- `title`
- `details`
- `source`
- `status`

**Step 4: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_gap_analysis_service.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add services/gap_analysis_service.py tests/test_gap_analysis_service.py
git commit -m "feat: add module-to-sdk gap analysis"
```

### Task 7: Expose ingest, analyze, review, and report commands in the CLI

**Files:**
- Modify: `cli.py`
- Modify: `app.py`
- Create: `services/ingest_service.py`
- Test: `tests/test_cli_analysis_commands.py`
- Test: `tests/test_ingest_service.py`

**Step 1: Write the failing command tests**

Create tests for:
- `ingest run`
- `analyze gaps --scope app`
- `analyze gaps --scope package:svgate-sdk`
- `review list`
- `review resolve`
- `report bug`
- `report missing-sdk`

```python
def test_cli_analyze_gaps_app_creates_findings(...):
    ...

def test_cli_report_missing_sdk_persists_item(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_cli_analysis_commands.py tests/test_ingest_service.py -q
```

Expected: FAIL because these commands and services do not exist yet

**Step 3: Implement `ingest_service.py`**

Support:
- active project ingestion
- scope-aware ingestion
- generated artifact ingestion for findings and summaries

Reuse `app.py` helpers for collection access instead of duplicating Chroma setup.

**Step 4: Extend `cli.py`**

Add commands:

```text
ingest run
ingest status
analyze gaps --scope ...
review list --scope ...
review resolve ID --action ...
report bug --scope ... --title ... --details ...
report missing-sdk --scope ... --title ... --details ...
```

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_cli_analysis_commands.py tests/test_ingest_service.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add cli.py app.py services/ingest_service.py tests/test_cli_analysis_commands.py tests/test_ingest_service.py
git commit -m "feat: add ingest, analysis, review, and report CLI commands"
```

### Task 8: Document the CLI workflows end to end

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-04-05-cli-project-operations-design.md`

**Step 1: Write the documentation checklist**

Document:
- project registration
- scope selection
- app overview workflow
- package-specific workflow
- gap triage flow
- review resolution flow

**Step 2: Update README examples**

Include real command examples such as:

```bash
./.venv/bin/python cli.py project add --name app --contract ./project.contract.json
./.venv/bin/python cli.py scope use package svgate-sdk
./.venv/bin/python cli.py analyze gaps --scope app
./.venv/bin/python cli.py review list --scope package:svgate-sdk
```

**Step 3: Re-run the full verification**

Run:

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall cli.py app.py memory_review.py project_contract.py project_session.py services tests
```

Expected: PASS

**Step 4: Commit**

```bash
git add README.md docs/plans/2026-04-05-cli-project-operations-design.md
git commit -m "docs: add project operations CLI workflows"
```

