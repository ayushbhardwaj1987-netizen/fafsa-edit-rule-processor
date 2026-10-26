from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_http_accepts_application():
    response = client.post("/validate", json={
        "studentInfo": {"ssn": "123456789", "dateOfBirth": "2000-01-01"},
        "dependencyStatus": "independent", "maritalStatus": "single",
        "household": {"numberInHousehold": 1, "numberInCollege": 1},
        "income": {"studentIncome": 0}, "stateOfResidence": "GA"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "valid"
    assert len(response.json()["results"]) == 7


def test_http_invalid_rules_return_results():
    response = client.post("/validate", json={})
    assert response.status_code == 200
    assert response.json()["status"] == "invalid"


def test_http_non_object_body_is_bad_request():
    response = client.post("/validate", json=[1, 2, 3])
    assert response.status_code == 422
