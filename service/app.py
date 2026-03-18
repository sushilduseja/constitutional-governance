"""
FastAPI governance service.

Run:
    uvicorn service.app:app --reload
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Governance Service", version="0.1.0")


class EvaluateRequest(BaseModel):
    user_prompt: str
    llm_response: str
    model_provider: str
    model_name: str
    constitution_version: Optional[str] = "latest"


class EvaluateResponse(BaseModel):
    eval_id: str
    status: str
    compliant: bool
    score: float
    violations: list


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    raise HTTPException(status_code=501, detail="Not yet implemented")


@app.get("/constitution")
async def get_constitution(version: Optional[str] = None):
    raise HTTPException(status_code=501, detail="Not yet implemented")


@app.get("/evaluations")
async def list_evaluations(
    limit: int = 100,
    offset: int = 0,
    compliant: Optional[bool] = None,
):
    raise HTTPException(status_code=501, detail="Not yet implemented")
