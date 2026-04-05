# Hybrid Ops CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a hybrid `ops` CLI with equal support for interactive shell usage and scriptable subcommands, separated into `ai` and `project` domains over a shared project/scope context.

**Architecture:** Implement a shared service layer for project/session, scope, ingestion, review/reporting, capability inventory, and gap analysis. Put two frontends on top of it: a scriptable command interface and an interactive shell that reuses the same commands while displaying domain/project/scope context in the prompt.

**Tech Stack:** Python 3.14, pytest, argparse, Rich, ChromaDB, JSON-backed local state

---

### Task 1: Add domain and scope context persistence

**Files:**
- Modify: `project_session.py`
- Modify: `project_contract.py`
- Modify: `project.contract.example.json`
- Test: `tests/test_project_session.py`
- Test: `tests/test_project_contract.py`

**Step 1: Write the failing tests**

Create tests for:
- active domain persistence
- active scope persistence
- contract parsing for `project_type`, `package_roots`, and `service_docs`

```python
def test_set_active_domain_persists_ai(tmp_path, monkeypatch):
    ...

def test_project_contract_reads_service_docs(tmp_path, monkeypatch):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_project_session.py tests/test_project_contract.py -q
```

Expected: FAIL because active domain and extended contract fields do not exist yet

**Step 3: Implement domain/scope persistence**

Add to `project_session.py`:

```python
ACTIVE_DOMAIN_FILE = ".active_domain"
ACTIVE_SCOPE_FILE = ".active_scope"

def set_active_domain(domain: str) -> None:
    ...

def get_active_domain() -> str | None:
    ...

def set_active_scope(scope: str) -> None:
    ...

def get_active_scope() -> str | None:
    ...
```

**Step 4: Extend `ProjectContract`**

Add:
- `project_type`
- `package_roots`
- `service_docs`

with safe defaults.

**Step 5: Update the example contract**

Add the new metadata fields to `project.contract.example.json`.

**Step 6: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_project_session.py tests/test_project_contract.py -q
```

Expected: PASS

**Step 7: Commit**

```bash
git add project_session.py project_contract.py project.contract.example.json tests/test_project_session.py tests/test_project_contract.py
git commit -m "feat: add domain and scope context persistence"
```

### Task 2: Extract shared project and scope services

**Files:**
- Create: `services/project_registry_service.py`
- Create: `services/scope_service.py`
- Test: `tests/test_project_registry_service.py`
- Test: `tests/test_scope_service.py`

**Step 1: Write the failing tests**

Create tests covering:
- project registration
- project listing
- active project selection
- package scope discovery from `package_roots`
- current scope fallback to `app`

```python
def test_scope_service_lists_app_and_package_scopes(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_project_registry_service.py tests/test_scope_service.py -q
```

Expected: FAIL because the shared services do not exist yet

**Step 3: Implement the services**

Keep the interface reusable by both shell and subcommands.

**Step 4: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_project_registry_service.py tests/test_scope_service.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add services/project_registry_service.py services/scope_service.py tests/test_project_registry_service.py tests/test_scope_service.py
git commit -m "feat: add shared project and scope services"
```

### Task 3: Build the scriptable `ops` command surface

**Files:**
- Create: `ops.py`
- Test: `tests/test_ops_scriptable_cli.py`
- Modify: `README.md`

**Step 1: Write the failing CLI tests**

Create tests for scriptable commands:
- `ops ai project list`
- `ops ai project add`
- `ops ai project use`
- `ops ai scope list`
- `ops ai scope use package svgate-sdk`
- `ops project analyze gaps --scope app`

```python
def test_ops_ai_project_add_registers_contract(...):
    ...
```

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_ops_scriptable_cli.py -q
```

Expected: FAIL because `ops.py` does not exist yet

**Step 3: Implement the top-level parser**

Support:
- `ops ai ...`
- `ops project ...`

Keep parser output deterministic and non-interactive.

**Step 4: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_ops_scriptable_cli.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add ops.py README.md tests/test_ops_scriptable_cli.py
git commit -m "feat: add scriptable ops CLI"
```

### Task 4: Normalize review/report storage for both domains

**Files:**
- Create: `services/report_service.py`
- Modify: `memory_review.py`
- Test: `tests/test_report_service.py`
- Test: `tests/test_memory_review.py`

**Step 1: Write the failing tests**

Create tests for:
- `bug_report`
- `missing_sdk_client`
- `missing_sdk_operation`
- stored `scope`
- stored `source`
- status transitions

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_report_service.py tests/test_memory_review.py -q
```

Expected: FAIL because the normalized model does not exist yet

**Step 3: Implement the normalized model**

Make report creation reusable by both domains.

**Step 4: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_report_service.py tests/test_memory_review.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add services/report_service.py memory_review.py tests/test_report_service.py tests/test_memory_review.py
git commit -m "feat: normalize review and report storage"
```

### Task 5: Add the `ai` domain services and commands

**Files:**
- Create: `services/ingest_service.py`
- Modify: `app.py`
- Modify: `ops.py`
- Test: `tests/test_ingest_service.py`
- Test: `tests/test_ops_ai_domain.py`

**Step 1: Write the failing tests**

Create tests for:
- `ops ai ingest run`
- `ops ai ingest status`
- `ops ai review list`
- `ops ai review resolve`
- `ops ai report bug`
- `ops ai report missing-sdk`

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_ingest_service.py tests/test_ops_ai_domain.py -q
```

Expected: FAIL because the `ai` domain commands are not implemented yet

**Step 3: Implement `ingest_service.py`**

Make ingestion scope-aware and project-aware.

**Step 4: Extend `ops.py` for `ai` domain**

Add:
- project commands
- scope commands
- ingest commands
- review commands
- report commands

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_ingest_service.py tests/test_ops_ai_domain.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add app.py ops.py services/ingest_service.py tests/test_ingest_service.py tests/test_ops_ai_domain.py
git commit -m "feat: add ai domain ops commands"
```

### Task 6: Add capability inventory and project-domain gap analysis

**Files:**
- Create: `services/capability_inventory_service.py`
- Create: `services/gap_analysis_service.py`
- Modify: `ops.py`
- Test: `tests/test_capability_inventory_service.py`
- Test: `tests/test_gap_analysis_service.py`
- Test: `tests/test_ops_project_domain.py`
- Optional Create: `tests/fixtures/laravel_app/`

**Step 1: Write the failing tests**

Create tests for:
- expected capability extraction from module/app logic
- implemented capability extraction from SDK package code
- app-scope missing SDK operation detection
- package-scope capability reporting
- `ops project analyze gaps --scope app`
- `ops project analyze gaps --scope package:svgate-sdk`

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_capability_inventory_service.py tests/test_gap_analysis_service.py tests/test_ops_project_domain.py -q
```

Expected: FAIL because the project-domain analysis logic does not exist yet

**Step 3: Implement capability extraction**

Keep the first pass heuristic and deterministic.

**Step 4: Implement gap analysis**

Diff:
- module/app expected capabilities
- SDK implemented capabilities

Emit structured findings.

**Step 5: Extend `ops.py` for `project` domain**

Add:
- `analyze gaps`
- `analyze capabilities`
- optional review/report bridging

**Step 6: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_capability_inventory_service.py tests/test_gap_analysis_service.py tests/test_ops_project_domain.py -q
```

Expected: PASS

**Step 7: Commit**

```bash
git add ops.py services/capability_inventory_service.py services/gap_analysis_service.py tests/test_capability_inventory_service.py tests/test_gap_analysis_service.py tests/test_ops_project_domain.py tests/fixtures/laravel_app
git commit -m "feat: add project domain gap analysis"
```

### Task 7: Build the interactive shell frontend

**Files:**
- Create: `shell.py`
- Modify: `ops.py`
- Test: `tests/test_shell.py`

**Step 1: Write the failing shell tests**

Create tests for:
- prompt includes domain/project/scope
- `/domain ai`
- `/domain project`
- `/project use ...`
- `/scope use ...`
- `/ingest`
- `/analyze gaps`
- `/review`

**Step 2: Run the targeted tests to verify failure**

Run:

```bash
./.venv/bin/pytest tests/test_shell.py -q
```

Expected: FAIL because no interactive shell exists yet

**Step 3: Implement `shell.py`**

Requirements:
- shared command handlers with `ops.py`
- slash-command aliases
- domain-aware prompt
- concise help output

**Step 4: Update `ops.py` entry behavior**

Support:
- `python ops.py` -> interactive shell
- `python ops.py ai ...` -> scriptable command
- `python ops.py project ...` -> scriptable command

**Step 5: Re-run the targeted tests**

Run:

```bash
./.venv/bin/pytest tests/test_shell.py -q
```

Expected: PASS

**Step 6: Commit**

```bash
git add shell.py ops.py tests/test_shell.py
git commit -m "feat: add hybrid interactive shell for ops"
```

### Task 8: Final documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-04-05-hybrid-ops-cli-design.md`

**Step 1: Update documentation**

Document:
- `ai` vs `project` domain split
- scriptable workflows
- interactive shell workflows
- active project/scope behavior
- app-level module-vs-SDK gap detection

**Step 2: Run the full verification**

Run:

```bash
./.venv/bin/pytest -q
./.venv/bin/python -m compileall ops.py shell.py app.py memory_review.py project_contract.py project_session.py services tests
```

Expected: PASS

**Step 3: Commit**

```bash
git add README.md docs/plans/2026-04-05-hybrid-ops-cli-design.md
git commit -m "docs: add hybrid ops CLI workflows"
```

