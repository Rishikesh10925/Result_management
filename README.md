# ResultCloud

**Cloud-Based Student Result Management System**: a college Cloud Computing project on AWS
(EC2, RDS, S3, IAM, CloudWatch). Flask API + React frontend, with separate Student, Faculty and Admin logins.

The academic calculations come from [PyGPA-Analyzer](https://github.com/HarshBang/PyGPA-Analyzer).
The original code is kept in `reference/`, and the tests check that ResultCloud gives the same output for the same input.

## Structure

```
backend/
  app.py                       Flask app, logging, serves the React build
  config.py                    settings from .env (DB, S3, secrets)
  models.py                    users, students, marks, results, audit logs
  routes/                      auth, student, faculty, admin APIs (role checked)
  services/calculation_engine.py   ALL academic logic (unchanged from the reference)
  services/result_service.py   DB <-> engine glue
  services/s3_service.py       PDF upload to Amazon S3 (boto3, IAM role)
  services/pdf_service.py      marksheet PDF
  tests/                       engine tests + reference comparison tests
frontend/                      React (Vite) app
deploy/                        EC2 setup script, Gunicorn service, Nginx, CloudWatch agent, IAM policy
docs/AWS_DEPLOYMENT.md         step-by-step AWS console guide
reference/                     original source_code.py and app.py, unchanged
```

## Run locally

Backend (terminal 1):

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python seed.py                   # creates tables + demo accounts
python app.py                    # http://127.0.0.1:5000
```

Frontend (terminal 2):

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173 (calls the API on :5000)
```

Demo logins (local only):

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Faculty | `faculty` | `faculty123` |
| Student (CSDS, new scale) | `70572400001` | `student123` |
| Student (CSDS, old scale) | `70572200027` | `student123` |
| Student (CE, new scale) | `70022500001` | `student123` |

### Database

Without `DB_HOST` in `.env` the app uses a local SQLite file, so it runs with no setup.
To use local MySQL, create the database and fill in `.env` (copy `.env.example`):

```sql
CREATE DATABASE resultcloud;
```

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=<your mysql password>
```

Then run `python seed.py` again. On AWS the same settings point to Amazon RDS.

### Tests

```bash
cd backend
python -m pytest -q
```

## AWS

See **[docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)**.

| Service | Used for |
|---|---|
| EC2 | runs Nginx + Gunicorn + Flask, serves the React build |
| RDS (MySQL) | users, students, marks, results, audit logs |
| S3 | marksheet PDFs (`marksheets/<sap id>/semN.pdf`), key stored in the results table |
| IAM | EC2 role with S3 access limited to the bucket's `marksheets/*`, plus CloudWatch agent |
| CloudWatch | CPU and status checks, memory and disk, app and Nginx logs, alarms |

## Calculation rules (from the reference)

- **SAP ID**: 11 digits. `7057` = CSDS, `7002` = CE. `705722`/`705723`/`700222`/`700223` = old (4.0 scale), others = new (10.0 scale).
- **Marks**: TEE subjects: `ICA + TEE/2`. ICA-only subjects: `ICA * 2`. Rounded half-up with `round_TM`.
- **SGPA**: `sum(credit * grade point) / semester total credits`.
- **CGPA**: credit-weighted over every previous SGPA plus the current one (as in `app.py`). Uses the stored SGPAs, so all previous semesters must have results.
- **Goal matrix**: `(grade threshold - ICA) * 2`, clamped at 0, `-` when over 100.
- **Target GPA planner**: random ICA/TEE per difficulty, 4 plans, not guaranteed to reach the target.

## Notes: reference quirks that are kept on purpose

1. **CE students use the CSDS credit table** (as in `source_code.py`). This makes CE semesters 2, 3 and 4 fail,
   because they have more subjects than the CSDS table has credits. The original CLI crashes the same way, and
   ResultCloud shows an error message. `app.py` uses the CE credit table instead. You can switch with
   `CE_USES_CSDS_CREDITS` in the engine.
2. **D grade (old scale)**: the grade point is 1.15, but the grade dictionary has `1.5: 'D'`. So `app.py` shows the
   grade as `F` with grade point 0 in the table, while the SGPA still counts 1.15. (The CLI crashes here.)
3. **Planner** adds the raw random ICA and TEE with no `/2` or `*2` adjustment, including for ICA-only subjects.
4. **Subject name** `'Open Elective IV '` has a trailing space in the source.
5. **CGPA**: `app.py` weights all previous semesters, while the CLI uses only one previous CGPA and the
   previous semester's credits. ResultCloud follows `app.py`. The two agree when there is one previous semester.
6. Academic configuration is shown read-only in the Admin portal, because editing it would change the reference logic.
