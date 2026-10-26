"""HTTP entry point, deliberately separated from rule evaluation."""
from typing import Any
from fastapi import FastAPI
from app.rules import validate_application

app = FastAPI(title="FAFSA Edit Rule Processor", version="0.1.0")


@app.post("/validate")
def validate(data: dict[str, Any]) -> dict[str, Any]:
    return validate_application(data)
