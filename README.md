# ResultCloud

**Cloud-Based Student Result Management System** — a college Cloud Computing project on AWS
(EC2, RDS, S3, IAM, CloudWatch).

The academic calculations come from [PyGPA-Analyzer](https://github.com/HarshBang/PyGPA-Analyzer).
The original code is kept in `reference/`, and the tests check that ResultCloud gives the same output for the same input.

## Structure

```
backend/
  services/calculation_engine.py   all academic logic (SAP ID, marks, grades, SGPA, CGPA, goal matrix, planner)
  tests/test_engine.py             unit tests
  tests/test_reference_compat.py   runs reference/ code and the engine on the same inputs
reference/                         original source_code.py and app.py, unchanged
frontend/                          React app (coming next)
```

## Run the tests

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

## Calculation rules (from the reference)

- **SAP ID**: 11 digits. `7057` = CSDS, `7002` = CE. `705722`/`705723`/`700222`/`700223` = old (4.0 scale), others = new (10.0 scale).
- **Marks**: TEE subjects: `ICA + TEE/2`. ICA-only subjects: `ICA * 2`. Rounded half-up with `round_TM`.
- **SGPA**: `sum(credit * grade point) / semester total credits`.
- **CGPA**: credit-weighted over every previous SGPA plus the current one (as in `app.py`).
- **Goal matrix**: `(grade threshold - ICA) * 2`, clamped at 0, `-` when over 100.
- **Target GPA planner**: random ICA/TEE per difficulty, 4 plans, not guaranteed to reach the target.

## Notes: reference quirks that are kept on purpose

1. **CE students use the CSDS credit table** (as in `source_code.py`). This makes CE semesters 2, 3 and 4 fail,
   because they have more subjects than the CSDS table has credits. The original CLI crashes the same way.
   `app.py` uses the CE credit table instead. You can switch with `CE_USES_CSDS_CREDITS` in the engine.
2. **D grade (old scale)**: the grade point is 1.15, but the grade dictionary has `1.5: 'D'`. So `app.py` shows the
   grade as `F` with grade point 0 in the table, while the SGPA still counts 1.15. (The CLI crashes here.)
3. **Planner** adds the raw random ICA and TEE with no `/2` or `*2` adjustment, including for ICA-only subjects.
4. **Subject name** `'Open Elective IV '` has a trailing space in the source.
5. **CGPA**: `app.py` weights all previous semesters, while the CLI uses only one previous CGPA and the
   previous semester's credits. ResultCloud follows `app.py`. The two agree when there is one previous semester.
