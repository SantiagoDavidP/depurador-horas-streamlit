# Testing Backend/API

This project runs tests only against `backend/` and `api/`.

## 1) Install dependencies

```bash
python -m pip install -r requirements.txt
```

If a `requirements-dev.txt` is added later:

```bash
python -m pip install -r requirements-dev.txt
```

## 2) Run test suite

```bash
python -m pytest -q
```

Run only unit tests:

```bash
python -m pytest -q -m unit
```

Run only contract tests:

```bash
python -m pytest -q -m contract
```

## 3) Coverage

```bash
python -m coverage run -m pytest
python -m coverage report -m
python -m coverage html
```

HTML report output:

- `htmlcov/index.html`

## Scope and notes

- Coverage scope is configured in `.coveragerc` with:
  - `source = backend, api`
- Excluded from coverage:
  - `tests/`, `__pycache__/`, `frontend/`, `react-frontend/`
- Contract expectation for `POST /api/batch/process`:
  - multipart form field `payload` must be JSON string.
  - mapping must be sent as `mappingValues` when `profileId` is null.
