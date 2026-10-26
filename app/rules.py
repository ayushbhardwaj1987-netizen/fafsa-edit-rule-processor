"""Seven independently evaluated FAFSA application edit rules."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Callable

STATE_CODES = frozenset("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
SSN_PATTERN = re.compile(r"^[0-9]{9}$")


def section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def nonnegative_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return False
    try:
        return Decimal(str(value)).is_finite() and Decimal(str(value)) >= 0
    except InvalidOperation:
        return False


def valid_ssn(value: Any) -> bool:
    return isinstance(value, str) and SSN_PATTERN.fullmatch(value) is not None


def valid_age(value: Any, today: date) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dob = date.fromisoformat(value)
    except ValueError:
        return False
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return years >= 14


def age_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    if valid_age(section(data, "studentInfo").get("dateOfBirth"), today):
        return "passed", "Student is at least 14 years old."
    return "failed", "studentInfo.dateOfBirth must be a valid ISO date and the student must be at least 14."


def ssn_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    student_ssn = section(data, "studentInfo").get("ssn")
    if not valid_ssn(student_ssn):
        return "failed", "studentInfo.ssn must contain exactly nine digits."
    spouse_ssn = section(data, "spouseInfo").get("ssn")
    if spouse_ssn is not None and not valid_ssn(spouse_ssn):
        return "failed", "spouseInfo.ssn, if provided, must contain exactly nine digits."
    return "passed", "Provided SSNs contain exactly nine digits."


def parent_income_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    if data.get("dependencyStatus") != "dependent":
        return "not_applicable", "Parent income is required only for dependent students."
    if section(data, "income").get("parentIncome") is None:
        return "failed", "income.parentIncome is required when dependencyStatus is dependent."
    return "passed", "Parent income was supplied."


def income_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    income = section(data, "income")
    if not nonnegative_number(income.get("studentIncome")):
        return "failed", "income.studentIncome must be a nonnegative number."
    if income.get("parentIncome") is not None and not nonnegative_number(income["parentIncome"]):
        return "failed", "income.parentIncome, if provided, must be a nonnegative number."
    return "passed", "Provided income values are nonnegative numbers."


def household_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    household = section(data, "household")
    members, college = household.get("numberInHousehold"), household.get("numberInCollege")
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (members, college)):
        return "failed", "household counts must be nonnegative whole numbers."
    if college > members:
        return "failed", "household.numberInCollege cannot exceed household.numberInHousehold."
    return "passed", "Household counts are consistent."


def state_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    state = data.get("stateOfResidence")
    if isinstance(state, str) and state in STATE_CODES:
        return "passed", "State of residence is a valid US state abbreviation."
    return "failed", "stateOfResidence must be a valid uppercase two-letter US state abbreviation."


def marital_rule(data: dict[str, Any], today: date) -> tuple[str, str]:
    if data.get("maritalStatus") != "married":
        return "not_applicable", "Spouse information is required only when married."
    spouse = section(data, "spouseInfo")
    if not all(isinstance(spouse.get(key), str) and spouse[key].strip() for key in ("firstName", "lastName")) or not valid_ssn(spouse.get("ssn")):
        return "failed", "spouseInfo.firstName, lastName, and nine-digit ssn are required when married."
    return "passed", "Required spouse information is present."


Rule = tuple[str, str, Callable[[dict[str, Any], date], tuple[str, str]]]
# Order is fixed for deterministic results, not short-circuit evaluation.
RULES: tuple[Rule, ...] = (
    ("STUDENT_AGE", "error", age_rule),
    ("SSN_FORMAT", "error", ssn_rule),
    ("DEPENDENT_PARENT_INCOME", "error", parent_income_rule),
    ("INCOME_VALIDATION", "error", income_rule),
    ("HOUSEHOLD_LOGIC", "error", household_rule),
    ("STATE_CODE", "error", state_rule),
    ("MARITAL_STATUS", "error", marital_rule),
)


def validate_application(data: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Evaluate every edit; client validation failures are ordinary HTTP 200 results."""
    evaluation_date = today or date.today()
    results = [
        {"ruleId": name, "severity": severity, "status": status, "message": message}
        for name, severity, rule in RULES
        for status, message in [rule(data, evaluation_date)]
    ]
    return {
        "status": "invalid" if any(item["status"] == "failed" for item in results) else "valid",
        "evaluationDate": evaluation_date.isoformat(),
        "results": results,
    }
