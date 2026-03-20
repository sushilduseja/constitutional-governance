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
from dotenv import load_dotenv
import asyncio
import logging

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from service.constitution import ConstitutionStore
from service.audit import AuditStore
from service.evaluator import Evaluator
from service.analytics import Analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Governance Service", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

CONSTITUTION_PATH = BASE_DIR.parent / "constitution" / "rules" / "default_v1.json"
AUDIT_DB_PATH = BASE_DIR.parent / "audit.db"

constitution_store = ConstitutionStore(str(CONSTITUTION_PATH))
audit_store = AuditStore(str(AUDIT_DB_PATH))
evaluator = Evaluator(
    constitution_path=str(CONSTITUTION_PATH),
    audit_db_path=str(AUDIT_DB_PATH),
    interpreter_provider="groq",
)
analytics = Analytics(audit_store)

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
    constitution_version: str


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "governance",
        "constitution_version": constitution_store.get_version(),
        "rules_count": len(constitution_store.get_rules()),
    }


@app.get("/api/stats")
async def get_stats():
    return analytics.get_stats()


@app.get("/api/analytics")
async def get_analytics():
    return analytics.get_full_report()


@app.get("/api/constitution")
async def get_constitution(version: Optional[str] = None):
    constitution_store.reload()
    return constitution_store.to_dict()


@app.get("/api/constitution/rules")
async def get_constitution_rules():
    return {
        "version": constitution_store.get_version(),
        "rules": constitution_store.get_rules(),
    }


@app.get("/api/audit-log")
async def get_audit_log(limit: int = 50, offset: int = 0):
    return audit_store.query(limit=limit, offset=offset)


@app.get("/api/audit-log/count")
async def get_audit_count():
    total = audit_store.count()
    compliant = audit_store.count(compliant=True)
    failed = audit_store.count(compliant=False)
    return {
        "total": total,
        "compliant": compliant,
        "non_compliant": failed,
    }


@app.post("/api/audit-log/refresh")
async def refresh_audit_log():
    records = audit_store.query(limit=100)
    return {"status": "ok", "count": len(records)}


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    try:
        result = await asyncio.to_thread(
            evaluator.evaluate,
            user_prompt=req.user_prompt,
            llm_response=req.llm_response,
            model_provider=req.model_provider,
            model_name=req.model_name,
        )
        return EvaluateResponse(
            eval_id=f"eval_{id(result)}",
            status=result.status,
            compliant=result.compliant,
            score=result.score,
            violations=result.violations,
            constitution_version=result.constitution_version,
        )
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/constitution/reload")
async def reload_constitution():
    constitution_store.reload()
    return {
        "status": "reloaded",
        "version": constitution_store.get_version(),
        "rules_count": len(constitution_store.get_rules()),
    }
