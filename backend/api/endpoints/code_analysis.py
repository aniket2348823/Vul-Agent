"""
PROBLEM 18 FIX: Code Analysis API endpoint.
Exposes the Lambda Agent's pre-code scanning via REST API.
Used by VS Code extension and any CI/CD integration.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from backend.agents.lambda_agent import LambdaAgent

router = APIRouter()
lambda_agent = LambdaAgent("agent_lambda", None)


class CodePayload(BaseModel):
    code: str
    language: str = "python"


@router.post("/analyze-code")
async def analyze_code(payload: CodePayload):
    """
    Analyze source code for security vulnerabilities.
    Returns findings with line numbers, severity, and fix recommendations.
    """
    findings = await lambda_agent.analyze(payload.code, payload.language)
    return {
        "findings": findings,
        "total": len(findings),
        "critical": sum(1 for f in findings if f["severity"] == "CRITICAL"),
        "high": sum(1 for f in findings if f["severity"] == "HIGH"),
        "medium": sum(1 for f in findings if f["severity"] == "MEDIUM"),
        "low": sum(1 for f in findings if f["severity"] == "LOW"),
    }
