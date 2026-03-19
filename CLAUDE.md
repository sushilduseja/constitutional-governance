# CLAUDE.md — AI Governance MVP

> Project: AI Governance & Safety MVP
> Architecture: `docs/designs/constitutional-governance.md`
> TODOs: `TODOS.md`

---

## Project Overview

This is a greenfield project building a model-agnostic constitutional AI monitoring layer. Any LLM call flows through a wrapper that evaluates the output against a plain-English constitution using a separate LLM as interpreter.

**Core principle:** Monitoring never blocks. The user's LLM response always returns, regardless of whether evaluation succeeds or fails.

## Key Architecture Decisions

1. **Async-first**: The SDK defaults to async evaluation — the original LLM response returns immediately, evaluation happens in the background. Never block the user.
2. **Non-blocking monitoring**: Even if the interpreter LLM fails completely, the user's response still returns. Monitoring is observe-only.
3. **Constitution versioning**: Every constitution change is a version. Every evaluation is tagged with the version it used.
4. **No PII by default**: Prompts may contain sensitive data. Log only evaluation metadata unless PII logging is explicitly enabled.

## Interpreter LLM

- **Provider**: Groq (free tier, OpenAI-compatible) with fallback models
- **Models (in order)**: `llama-3.3-70b-versatile` → `qwen/qwen3-32b` → `groq/compound-mini` → `llama-3.1-8b-instant`
- **API Key**: Loaded from `GROQ_API_KEY` environment variable (see `.env.example`)
- **Retry behavior**: On rate limit/unavailable/timeout, tries next model with 2s delay
- **Prompt**: Defined in `docs/designs/constitutional-governance.md` Section 5
- **Prompt versioning**: Store prompts in `constitution/interpreter_prompts/v{N}.md`
- **Output format**: Structured JSON (see Section 5 for schema)
- **Parse robustness**: Always handle malformed JSON — the LLM is unreliable at strict formatting
- **Consistency checking**: Golden set approach — maintain `tests/golden_set.json` with known outputs

## Constitution Rules

- **Format**: JSON files in `constitution/rules/` directory
- **Default constitution**: `constitution/rules/default_v1.json` — 5 rules, minimal coverage for MVP
- **Versioning**: Git-based. Every change = new file or git commit with version tag.
- **Schema**: Each rule has `id`, `text`, `severity`, `enabled`, `tags`, `created_at`, `updated_at`
- **Truncation**: Smart chunking at paragraph boundaries, max 8K tokens per chunk

## SDK Design

- **Language**: Python (MVP), adapters for Anthropic + OpenAI + Groq
- **Wrapper interface**: `Governance.wrap(provider, call_lambda) -> response`
- **Adapter pattern**: Each LLM provider has an adapter implementing `LLMAdapter` protocol
- **Modes**: sync / async / fire-and-forget. Default: async.

## Audit Log

- **Storage**: SQLite (MVP), PostgreSQL (production)
- **Schema**: Defined in `docs/designs/constitutional-governance.md` Section 7
- **Immutability**: Append-only. No UPDATE or DELETE operations.
- **PII**: No PII stored by default. Configure redaction pipeline if needed.

## File Structure (Target)

```
constitutional-governance/
├── CLAUDE.md              # This file
├── TODOS.md               # Deferred work
├── docs/
│   └── designs/
│       └── constitutional-governance.md   # Architecture doc
├── constitution/
│   ├── rules/
│   │   └── default_v1.json       # Default constitution
│   └── interpreter_prompts/
│       └── v1.md                   # Interpreter prompt v1
├── sdk/
│   ├── __init__.py
│   ├── governance.py       # Main SDK class
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py         # LLMAdapter protocol
│   │   ├── anthropic.py    # Anthropic/Claude adapter
│   │   ├── openai.py       # OpenAI/GPT adapter
│   │   └── groq_adapter.py # Groq adapter (uses Groq free tier)
├── service/
│   ├── __init__.py
│   ├── app.py              # FastAPI governance service
│   ├── static/
│   │   └── index.html      # Dashboard UI (Tailwind CDN)
│   ├── evaluator.py        # Interpreter LLM caller
│   ├── constitution.py      # Constitution store + versioning
│   ├── audit.py             # Audit log writer
│   └── analytics.py         # Violation pattern detection
├── tests/
│   ├── golden_set.json      # Known outputs for consistency checks
│   ├── __init__.py
│   ├── test_constitution.py # Constitution loading + validation
│   ├── test_governance.py   # SDK governance wrapper tests
│   ├── test_json_parse.py   # JSON parsing robustness tests
│   ├── test_smart_chunk.py  # Output truncation tests
│   └── test_integration.py  # End-to-end tests
└── examples/
    ├── quickstart.py        # Minimal working example
    └── demo.py              # Interactive demo
```

## Prompt/LLM Changes

If modifying the interpreter prompt or constitution format:

1. Store the new prompt in `constitution/interpreter_prompts/v{N+1}.md`
2. Update the golden set tests — re-run consistency checks
3. Tag the new evaluations with the new prompt version
4. Do NOT modify past golden set expected values — only update `golden_set.json` deliberately

## Critical Rules

1. **Never block the user response** — The LLM response always returns first
2. **Always log failures** — Even if evaluation fails, log it. Silent failures are the worst kind
3. **Version everything** — Constitution changes, interpreter prompts, SDK versions
4. **Test the interpreter** — Run golden set consistency check before every significant change
5. **No PII in audit logs** — Unless PII logging is explicitly enabled with consent

## Setup

1. Copy `.env.example` to `.env`
2. Add your Groq API key: `GROQ_API_KEY=your_key_here`
3. Get a free Groq API key at: https://console.groq.com/keys
4. Run: `uvicorn service.app:app --reload`
5. Access dashboard at: http://localhost:8000
