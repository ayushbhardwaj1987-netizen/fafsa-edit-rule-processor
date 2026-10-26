# FAFSA Edit Rule Processor

A small HTTP service that evaluates the **seven required FAFSA edit rules** and returns each rule's result. Built with Python 3.10+ and FastAPI.

## Setup

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[test]'
```

On Windows PowerShell, use `python -m pip install -e ".[test]"`.

## Run

```bash
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for an interactive API. POST JSON to `http://127.0.0.1:8000/validate`.

### Example request

```bash
curl -X POST http://127.0.0.1:8000/validate \
  -H 'Content-Type: application/json' \
  -d '{"studentInfo":{"firstName":"Jane","lastName":"Smith","ssn":"123456789","dateOfBirth":"2003-05-15"},"dependencyStatus":"dependent","maritalStatus":"single","household":{"numberInHousehold":4,"numberInCollege":1},"income":{"studentIncome":5000,"parentIncome":65000},"stateOfResidence":"CA"}'
```

### Example response (abbreviated)

```json
{
  "status": "valid",
  "evaluationDate": "2026-10-26",
  "results": [
    {"ruleId": "STUDENT_AGE", "severity": "error", "status": "passed", "message": "Student is at least 14 years old."},
    {"ruleId": "SSN_FORMAT", "severity": "error", "status": "passed", "message": "Provided SSNs contain exactly nine digits."},
    {"ruleId": "DEPENDENT_PARENT_INCOME", "severity": "error", "status": "passed", "message": "Parent income was supplied."},
    {"ruleId": "INCOME_VALIDATION", "severity": "error", "status": "passed", "message": "Provided income values are nonnegative numbers."},
    {"ruleId": "HOUSEHOLD_LOGIC", "severity": "error", "status": "passed", "message": "Household counts are consistent."},
    {"ruleId": "STATE_CODE", "severity": "error", "status": "passed", "message": "State of residence is a valid US state abbreviation."},
    {"ruleId": "MARITAL_STATUS", "severity": "error", "status": "not_applicable", "message": "Spouse information is required only when married."}
  ]
}
```

`evaluationDate` is the server's current date, so it changes over time. For a failed rule, `status` is `failed` and `message` explains the correction. Invalid FAFSA data returns HTTP **200** with `"status":"invalid"`; an invalid **HTTP payload shape**, such as a JSON array instead of an object, returns **422**.

## Tests and coverage

```bash
python -m pytest
```

Pytest runs unit tests for the seven rules and HTTP integration tests using FastAPI's TestClient. Coverage reports **line and branch coverage** and fails if total coverage falls below 90%. No AWS credentials or database are needed.

## Repository structure

- `app/main.py`: `/validate` API route
- `app/rules.py`: validation rules and deterministic rule registry
- `tests/test_rules.py`: rule-focused and boundary tests
- `tests/test_api.py`: HTTP-level tests
- `DECISIONS.md`: trade-offs, assumptions, and extension options

## Submission notes

The Git repository has incremental commits. If sharing a zip, ensure the included `.git` directory is retained so reviewers can inspect the history. Do not put real SSNs or private applicant information in sample requests or commits.
