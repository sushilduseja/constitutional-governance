"""
FastAPI governance service.

Run:
    uvicorn service.app:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Governance Service", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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


MOCK_MODELS = ["claude-3-5-sonnet", "gpt-4-turbo", "gpt-4o", "gemini-pro"]


def generate_mock_audit_log(count: int = 20):
    entries = []
    base_time = datetime.utcnow()
    for i in range(count):
        ts = base_time.replace(second=0, microsecond=0)
        ts = ts.replace(minute=ts.minute - i)
        compliant = random.random() > 0.15
        violations_count = 0 if compliant else random.randint(1, 4)
        entries.append({
            "id": f"eval_{1000 + count - i}",
            "timestamp": ts.isoformat() + "Z",
            "model_name": random.choice(MOCK_MODELS),
            "compliant": compliant,
            "score": round(random.uniform(0.4, 1.0), 2) if compliant else round(random.uniform(0.3, 0.7), 2),
            "violations": violations_count
        })
    return entries


def generate_mock_stats():
    return {
        "total_evaluations": random.randint(1200, 1300),
        "compliance_rate": round(random.uniform(93.0, 95.5), 1),
        "active_violations": random.randint(60, 85),
        "constitution_version": "1.0.0"
    }


MOCK_AUDIT_LOG = generate_mock_audit_log(20)


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stats")
async def get_stats():
    return generate_mock_stats()


@app.get("/api/constitution")
async def get_constitution(version: Optional[str] = None):
    constitution_path = BASE_DIR.parent / "constitution" / "rules" / "default_v1.json"
    if constitution_path.exists():
        import json
        with open(constitution_path, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Constitution not found")


@app.get("/api/audit-log")
async def get_audit_log(limit: int = 50):
    global MOCK_AUDIT_LOG
    return MOCK_AUDIT_LOG[:limit]


@app.post("/api/audit-log/refresh")
async def refresh_audit_log():
    global MOCK_AUDIT_LOG
    MOCK_AUDIT_LOG = generate_mock_audit_log(20)
    return {"status": "refreshed", "count": len(MOCK_AUDIT_LOG)}


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    raise HTTPException(status_code=501, detail="Not yet implemented")
