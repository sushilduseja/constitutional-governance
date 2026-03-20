"""
FastAPI governance service.

Run:
    uvicorn service.app:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import time
import logging

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from service.constitution import ConstitutionStore
from service.audit import AuditStore
from service.evaluator import Evaluator
from service.analytics import Analytics, GoldenSetChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Governance Service",
    version="0.1.0",
    description="Constitutional AI monitoring layer for LLM applications",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

EVALUATE_RATE_LIMIT = 10
_evaluate_timestamps: list[float] = []


def _check_rate_limit() -> None:
    now = time.time()
    global _evaluate_timestamps
    _evaluate_timestamps = [t for t in _evaluate_timestamps if now - t < 60]
    if len(_evaluate_timestamps) >= EVALUATE_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {EVALUATE_RATE_LIMIT} evaluations per minute"
        )
    _evaluate_timestamps.append(now)


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


# --- Monitored LLM configuration (service-side, not caller-controlled) ---

import os

MONITORED_PROVIDER = os.environ.get("MONITORED_PROVIDER", "anthropic").lower()
MONITORED_MODEL = os.environ.get("MONITORED_MODEL", "claude-3-5-sonnet-20241022")

PROVIDER_MODELS = {
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4"},
        {"id": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"},
        {"id": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku"},
        {"id": "claude-3-opus-20240229", "label": "Claude 3 Opus"},
        {"id": "claude-3-haiku-20240307", "label": "Claude 3 Haiku"},
    ],
    "openai": [
        {"id": "gpt-4o", "label": "GPT-4o"},
        {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
        {"id": "gpt-4-turbo", "label": "GPT-4 Turbo"},
        {"id": "gpt-4", "label": "GPT-4"},
        {"id": "o1", "label": "OpenAI o1"},
        {"id": "o3-mini", "label": "o3 Mini"},
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B"},
        {"id": "qwen/qwen3-32b", "label": "Qwen 3 32B"},
        {"id": "groq/compound-mini", "label": "Compound Mini"},
        {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B"},
        {"id": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
    ],
}

_monitored_adapter = None


def _get_monitored_adapter():
    """Lazy-initialize the monitored LLM adapter based on MONITORED_PROVIDER."""
    global _monitored_adapter
    if _monitored_adapter is not None:
        return _monitored_adapter

    from sdk.adapters import get_adapter
    _monitored_adapter = get_adapter(MONITORED_PROVIDER)
    return _monitored_adapter


def _call_monitored_llm(prompt: str, context: Optional[str] = None) -> str:
    """
    Call the configured monitored LLM and return the response text.

    The monitored model is controlled entirely by service configuration
    (MONITORED_PROVIDER + MONITORED_MODEL env vars). Callers cannot
    influence which model is used.
    """
    if context:
        full_prompt = f"[Context]\n{context}\n\n[User Question]\n{prompt}"
    else:
        full_prompt = prompt

    adapter = _get_monitored_adapter()
    resp = adapter.call(full_prompt, model=MONITORED_MODEL, max_tokens=1024, temperature=0.3)
    return resp.text


# --- Request / Response models ---

MAX_PROMPT_CHARS = 8000
MAX_CONTEXT_CHARS = 2000


class EvaluateRequest(BaseModel):
    user_prompt: str = Field(..., max_length=MAX_PROMPT_CHARS)
    context: Optional[str] = Field(default=None, max_length=MAX_CONTEXT_CHARS)


class EvaluateResponse(BaseModel):
    llm_response: str
    evaluation: dict


class DirectEvaluateRequest(BaseModel):
    user_prompt: str = Field(..., max_length=MAX_PROMPT_CHARS)
    llm_response: str = Field(..., max_length=32000)


class DirectEvaluateResponse(BaseModel):
    evaluation: dict


# --- Routes ---

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
        "monitored_provider": MONITORED_PROVIDER,
        "monitored_model": MONITORED_MODEL,
    }


@app.get("/api/config")
async def get_service_config():
    """Expose service configuration to the dashboard."""
    return {
        "monitored_provider": MONITORED_PROVIDER,
        "monitored_model": MONITORED_MODEL,
        "provider_models": PROVIDER_MODELS,
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


@app.post("/api/direct-evaluate", response_model=DirectEvaluateResponse)
async def direct_evaluate(req: DirectEvaluateRequest):
    """
    Evaluate a pre-written LLM response against the constitution.
    Does NOT make an LLM call — caller provides the response directly.
    Used for quick evaluation of example responses.
    """
    _check_rate_limit()
    try:
        result = await asyncio.to_thread(
            evaluator.evaluate,
            user_prompt=req.user_prompt,
            llm_response=req.llm_response,
            model_provider="direct",
            model_name="pre-written",
        )
        return DirectEvaluateResponse(
            evaluation={
                "eval_id": f"eval_{id(result)}",
                "status": result.status,
                "compliant": result.compliant,
                "score": result.score,
                "violations": result.violations,
                "notes": result.notes,
                "constitution_version": result.constitution_version,
                "truncated": result.truncated,
                "failure_reason": result.failure_reason,
            }
        )
    except Exception as e:
        logger.error(f"Direct evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    """
    Orchestrate an LLM call with constitutional monitoring.

    The service calls the configured monitored LLM, captures the response,
    and evaluates it against the constitution — all invisibly to the caller.

    The monitored model is controlled entirely by service configuration
    (MONITORED_PROVIDER + MONITORED_MODEL env vars), NOT by caller input.
    """
    _check_rate_limit()
    try:
        llm_response = await asyncio.to_thread(
            _call_monitored_llm,
            req.user_prompt,
            req.context,
        )

        result = await asyncio.to_thread(
            evaluator.evaluate,
            user_prompt=req.user_prompt,
            llm_response=llm_response,
            model_provider=MONITORED_PROVIDER,
            model_name=MONITORED_MODEL,
        )

        return EvaluateResponse(
            llm_response=llm_response,
            evaluation={
                "eval_id": f"eval_{id(result)}",
                "status": result.status,
                "compliant": result.compliant,
                "score": result.score,
                "violations": result.violations,
                "notes": result.notes,
                "constitution_version": result.constitution_version,
                "truncated": result.truncated,
                "failure_reason": result.failure_reason,
            },
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


@app.get("/api/golden-check")
async def golden_set_check(verbose: bool = False):
    """
    Run the golden set consistency checker.

    Compares current interpreter behavior against known-correct golden
    set outputs. Use after interpreter prompt or constitution changes.
    """
    golden_path = BASE_DIR.parent / "tests" / "golden_set.json"
    checker = GoldenSetChecker(evaluator, str(golden_path))
    return await asyncio.to_thread(checker.check, verbose=verbose)
