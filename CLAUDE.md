# CLAUDE.md

## Project: ui_testing_software

**Tech Stack:** Python 3.11
**Scaffold Type:** Backend service

## Scaffold Structure

```
  backend/
  backend/app/
  backend/app/core/
  backend/tests/
  backend/tests/unit/
  backend/migrations/
  scripts/
  docs/
```

## Module Pattern

Each feature gets its own subdirectory under the capability folder:

| File | Location |
|------|----------|
| `models.py` | `backend/app/ui_testing_software/<feature>/` |
| `schema.py` | `backend/app/ui_testing_software/<feature>/` |
| `repository.py` | `backend/app/ui_testing_software/<feature>/` |
| `service.py` | `backend/app/ui_testing_software/<feature>/` |
| `api.py` | `backend/app/ui_testing_software/<feature>/` |
| `__init__.py` | `backend/app/ui_testing_software/<feature>/` |
| `test_*_service.py` | `backend/tests/unit/` |

Each feature folder has short file names (`models.py`, not `feature_models.py`).

## Conventions

- **Naming Style:** `snake_case for all files and folders`
- **Layout:** `feature subdirectories under backend/app/ capability folder (backend/app/{cap}/feature_name/models.py)`
- **Test Pattern:** `test_*.py`
- **Model Pattern:** `<feature>/models.py`
- **Schema Pattern:** `<feature>/schema.py`
- **Api Pattern:** `<feature>/api.py`
- **Service Pattern:** `<feature>/service.py`
- **Repository Pattern:** `<feature>/repository.py`
- **Reference Doc:** `CONVENTIONS.md at project root`

## Reference

See `CONVENTIONS.md` at the project root for the full 6-file module
pattern, naming conventions, import patterns, and code snippets.

## Commands

```bash
# Run service (from backend/ directory)
cd backend && uvicorn app.main:app --reload

# Run tests (from backend/ directory)
cd backend && pytest tests/ -v

# Docker
docker-compose up -d
```
