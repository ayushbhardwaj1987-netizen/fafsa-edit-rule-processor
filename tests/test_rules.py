from copy import deepcopy
from datetime import date
import pytest
from app.rules import validate_application, valid_age, nonnegative_number, valid_ssn

TODAY = date(2026, 10, 26)


@pytest.fixture
def valid():
    return {
        "studentInfo": {"firstName": "Jane", "lastName": "Smith", "ssn": "123456789", "dateOfBirth": "2003-05-15"},
        "dependencyStatus": "dependent", "maritalStatus": "single",
        "household": {"numberInHousehold": 4, "numberInCollege": 1},
        "income": {"studentIncome": 5000, "parentIncome": 65000},
        "stateOfResidence": "CA",
    }


def rule(response, name):
    return next(item for item in response["results"] if item["ruleId"] == name)


def test_valid_application(valid):
    response = validate_application(valid, TODAY)
    assert response["status"] == "valid"
    assert response["evaluationDate"] == "2026-10-26"
    assert len(response["results"]) == 7
    assert {item["status"] for item in response["results"]} == {"passed", "not_applicable"}


def test_invalid_application_reports_all_seven_failures(valid):
    invalid = deepcopy(valid)
    invalid["studentInfo"].update(ssn="invalid", dateOfBirth="2015-01-01")
    invalid["income"] = {"studentIncome": -1000}
    invalid["household"]["numberInCollege"] = 5
    invalid["stateOfResidence"] = "XX"
    invalid["maritalStatus"] = "married"
    response = validate_application(invalid, TODAY)
    assert response["status"] == "invalid"
    assert len([item for item in response["results"] if item["status"] == "failed"]) == 7
    assert all(item["message"] for item in response["results"])


@pytest.mark.parametrize("dob,expected", [
    ("2012-10-26", True), ("2012-10-27", False),
    ("2027-01-01", False), ("not-a-date", False), ("2024-02-30", False),
    (None, False), (123, False), ("2000-01-01", True),
])
def test_age_boundaries(dob, expected):
    assert valid_age(dob, TODAY) is expected


@pytest.mark.parametrize("ssn,expected", [
    ("012345678", True), ("12345678", False), ("123-45-6789", False),
    ("abcdefghi", False), (123456789, False), (None, False),
    ("1234567890", False),
])
def test_ssn_format(ssn, expected):
    assert valid_ssn(ssn) is expected


def test_student_ssn_missing(valid):
    valid["studentInfo"].pop("ssn")
    assert rule(validate_application(valid, TODAY), "SSN_FORMAT")["status"] == "failed"


def test_spouse_ssn_format_if_provided(valid):
    valid["spouseInfo"] = {"ssn": "bad"}
    assert rule(validate_application(valid, TODAY), "SSN_FORMAT")["status"] == "failed"
    valid["spouseInfo"]["ssn"] = "987654321"
    assert rule(validate_application(valid, TODAY), "SSN_FORMAT")["status"] == "passed"


def test_dependency_independent_parent_income_not_required(valid):
    valid["dependencyStatus"] = "independent"
    valid["income"].pop("parentIncome")
    assert rule(validate_application(valid, TODAY), "DEPENDENT_PARENT_INCOME")["status"] == "not_applicable"
    assert validate_application(valid, TODAY)["status"] == "valid"


def test_dependent_parent_income_required(valid):
    valid["income"].pop("parentIncome")
    assert rule(validate_application(valid, TODAY), "DEPENDENT_PARENT_INCOME")["status"] == "failed"


@pytest.mark.parametrize("value,expected", [
    (0, True), (0.5, True), (-0.01, False), (False, False),
    ("100", False), (None, False), (float("nan"), False),
    (float("inf"), False), (100, True),
])
def test_nonnegative_numeric_validation(value, expected):
    assert nonnegative_number(value) is expected


def test_parent_income_negative_or_invalid(valid):
    valid["income"]["parentIncome"] = -4
    assert rule(validate_application(valid, TODAY), "INCOME_VALIDATION")["status"] == "failed"
    valid["income"]["parentIncome"] = "not-number"
    assert rule(validate_application(valid, TODAY), "INCOME_VALIDATION")["status"] == "failed"


@pytest.mark.parametrize("household,college,expected", [
    (4, 4, "passed"), (4, 5, "failed"), (-1, 0, "failed"),
    (True, 1, "failed"), (4, 1.5, "failed"), (None, 1, "failed"),
    (0, 0, "passed"),
])
def test_household_counts(valid, household, college, expected):
    valid["household"] = {"numberInHousehold": household, "numberInCollege": college}
    assert rule(validate_application(valid, TODAY), "HOUSEHOLD_LOGIC")["status"] == expected


@pytest.mark.parametrize("state,expected", [("GA", "passed"), ("NY", "passed"), ("DC", "failed"), ("ca", "failed"), ("XX", "failed"), (None, "failed")])
def test_state_codes(valid, state, expected):
    valid["stateOfResidence"] = state
    assert rule(validate_application(valid, TODAY), "STATE_CODE")["status"] == expected


def test_marital_status_requires_spouse_details(valid):
    valid["maritalStatus"] = "married"
    assert rule(validate_application(valid, TODAY), "MARITAL_STATUS")["status"] == "failed"
    valid["spouseInfo"] = {"firstName": "", "lastName": "Doe", "ssn": "123456789"}
    assert rule(validate_application(valid, TODAY), "MARITAL_STATUS")["status"] == "failed"
    valid["spouseInfo"]["firstName"] = "Sam"
    assert rule(validate_application(valid, TODAY), "MARITAL_STATUS")["status"] == "passed"
    assert validate_application(valid, TODAY)["status"] == "valid"


def test_missing_nested_sections_generate_rule_failures_not_crash():
    response = validate_application({"studentInfo": [], "income": None, "household": "wrong"}, TODAY)
    assert response["status"] == "invalid"
    assert len(response["results"]) == 7


def test_all_rule_severities_are_errors(valid):
    assert all(item["severity"] == "error" for item in validate_application(valid, TODAY)["results"])


def test_default_date_is_today(valid):
    assert validate_application(valid)["evaluationDate"] == date.today().isoformat()
