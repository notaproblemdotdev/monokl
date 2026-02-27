# Renaming Plan: monocle → monokl

## Naming Story

The name evolved through a few iterations:
1. **monocli** - one CLI for a lot of things, an easy entrypoint for the user
2. **monocle** - one good looking monocle to see stuff easily, so the dev's life will be easier
3. **monokl** - "monocle" in Polish (the author is Polish)

The goal: make a developer's daily life easier with a unified terminal dashboard.

---

## Changes Required

### 1. Directory Rename
- `src/monocle/` → `src/monokl/`

### 2. pyproject.toml
- `name = "monocle"` → `name = "monokl"`
- Entry points: `monocle` → `monokl`, `monocle-dev` → `monokl-dev`
- Coverage path: `--cov=src/monocle` → `--cov=src/monokl`

### 3. Python Imports (~100+ files)
- All `from monocle.` → `from monokl.`
- All `import monocle` → `import monokl`
- Patch paths in tests: `"monocle.config"` → `"monokl.config"`, etc.

### 4. Environment Variables
- `MONOCLE_OFFLINE_MODE` → `MONOKL_OFFLINE_MODE`
- `MONOCLE_DB_PATH` → `MONOKL_DB_PATH`
- `MONOCLE_GITLAB_GROUP` → `MONOKL_GITLAB_GROUP`
- `MONOCLE_GITLAB_PROJECT` → `MONOKL_GITLAB_PROJECT`
- `MONOCLE_JIRA_PROJECT` → `MONOKL_JIRA_PROJECT`
- `MONOCLE_JIRA_BASE_URL` → `MONOKL_JIRA_BASE_URL`
- `MONOCLE_TODOIST_TOKEN` → `MONOKL_TODOIST_TOKEN`
- `MONOCLE_AZUREDEVOPS_TOKEN` → `MONOKL_AZUREDEVOPS_TOKEN`
- `MONOCLE_CACHE_TTL` → `MONOKL_CACHE_TTL`
- `MONOCLE_FEATURE_EXPERIMENTAL` → `MONOKL_FEATURE_EXPERIMENTAL`

### 5. File System Paths
- Config: `~/.config/monocle/` → `~/.config/monokl/`
- Config file: `~/.monocle.yaml` → `~/.monokl.yaml`
- Database: `monocle.db` → `monokl.db`
- Logs: `~/.local/share/monocle/` → `~/.local/share/monokl/`
- Log files: `monocle_*.log` → `monokl_*.log`

### 6. Keyring Service Name
- `SERVICE_NAME = "monocle"` → `SERVICE_NAME = "monokl"`
- Note: This will require users to re-authenticate after upgrade

### 7. Documentation Updates

#### README.md
- Update all CLI commands (`monocle` → `monokl`)
- Update config paths
- Update environment variable names
- Add naming story section

#### AGENTS.md
- `uv run python -m monocle` → `uv run python -m monokl`
- `uv run monocle-dev` → `uv run monokl-dev`
- Update project structure paths

#### plan.md
- Update all command references
- Update title

#### config.example.yaml
- Update comment references
- Update env var names

#### docs/testing_quality_inventory.md
- Update file paths

### 8. VSCode Config
- `.vscode/launch.json`: `"module": "monocle"` → `"module": "monokl"`
- Launch config name: `"monocle"` → `"monokl"`

---

## Execution Order

1. Rename `src/monocle/` → `src/monokl/`
2. Update pyproject.toml
3. Run find-replace on all Python files (imports + env vars + paths)
4. Update documentation files
5. Update VSCode config
6. Regenerate uv.lock (`uv sync`)
7. Run tests to verify

---

## Files Affected (Summary)

### Core Package
- `src/monocle/` (entire directory)

### Config Files
- `pyproject.toml`
- `uv.lock` (regenerated)
- `.vscode/launch.json`

### Documentation
- `README.md`
- `AGENTS.md`
- `plan.md`
- `config.example.yaml`
- `docs/testing_quality_inventory.md`

### Tests (all files in `tests/`)
- All import statements
- All patch paths
- All environment variable references

---

## Notes

- **Breaking change**: Users will need to update their config files and environment variables
- **Keyring migration**: Users will need to re-enter credentials stored in keyring
- **Database**: Existing `monocle.db` can be manually renamed or will be recreated
