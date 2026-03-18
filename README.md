# Constitutional Governance SDK

A model-agnostic constitutional AI monitoring layer that evaluates LLM outputs against a plain-English constitution using a separate LLM as interpreter. Monitoring never blocks - the user's LLM response always returns regardless of evaluation success.

## Features

- **Async-first evaluation**: SDK returns immediately, evaluation happens in background
- **Non-blocking monitoring**: Even if interpreter LLM fails, user response still returns
- **Constitution versioning**: Every constitution change is a version; evaluations tagged with version used
- **No PII by default**: Logs only evaluation metadata unless PII logging explicitly enabled
- **Multi-provider support**: Anthropic (Claude) + OpenAI (GPT) adapters
- **Smart output truncation**: Paragraph-boundary chunking for long outputs (>8K tokens)
- **Golden set consistency checking**: Validate interpreter consistency over time
- **Audit log**: SQLite (MVP), PostgreSQL (production) with append-only schema
- **Dashboard**: Single-page monitoring UI with stats, audit log feed, and constitution rules panel

## Architecture

```
USER / APPLICATION
        │
        ▼
GOVERNANCE WRAPPER SDK
        │
        ┌──────────────┴──────────────┐
        ▼                              ▼
LLM PROVIDER                  GOVERNANCE SERVICE
 (Claude/GPT/etc)               (evaluates output)
                                    │
                                    ┌──────────────┼──────────────┐
                                    ▼              ▼              ▼
                            ┌────────────┐  ┌─────────────┐  ┌────────────┐
                            │CONSTITUTION│  │  AUDIT LOG  │  │ ANALYTICS │
                            │   STORE    │  │  DATABASE   │  │ & REPORTING│
                            └────────────┘  └─────────────┘  └────────────┘
                                        │
                                        ▼
                            ┌─────────────────────┐
                            │SELF-IMPROVEMENT     │
                            │ENGINE               │
                            │(pattern detection + │
                            │ rule suggestions)   │
                            └─────────────────────┘
```

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from sdk.governance import Governance
import anthropic

# Initialize governance wrapper
gov = Governance(
    constitution_path="constitution/rules/default_v1.json",
    mode="sync",  # or "async" for non-blocking
)

# Initialize LLM client
client = anthropic.Anthropic()

# Wrap LLM calls
prompts = [
    "Who discovered penicillin and where?",
    "What is the largest planet in our solar system?",
    "What is the capital of France?"
]

for prompt in prompts:
    raw_response = client.messages.create(
        model="claude-3-5-sonnet-20260220",  # or any other model
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    gov.wrap(
        provider="anthropic",
        raw_response=raw_response,
        user_prompt=prompt,
    )

    # Original response is returned unmodified
    text = raw_response.content[0].text
    print(f"RESPONSE: {text[:200]}...")
```

## Dashboard

Run the governance service to access the monitoring dashboard:

```bash
uvicorn service.app:app --reload
# Then visit: http://localhost:8000/
```

The dashboard shows:
- **Stats bar**: Total evaluations, compliance rate %, active violations, constitution version
- **Audit log feed**: Scrollable table with timestamp, model, compliant status (✓/✗), score, violation count
- **Constitution rules panel**: All rules with severity badges and enabled toggles

## API Endpoints

- `GET /` → Redirects to dashboard (`/static/index.html`)
- `GET /health` → Service health check
- `GET /api/stats` → Dashboard statistics
- `GET /api/constitution` → Current constitution rules
- `GET /api/audit-log` → Audit log entries (with optional `limit` parameter)
- `POST /api/audit-log/refresh` → Refresh mock audit data
- `POST /evaluate` → Evaluate LLM response against constitution (not yet implemented)

## Configuration

See `docs/designs/ai-governance-mvp.md` for full architecture details.

### Constitution Format
JSON files in `constitution/rules/` directory:
```json
{
  "version": "1.0.0",
  "rules": [
    {
      "id": "rule_truth_001",
      "text": "The AI must not make verifiable false claims about real-world facts...",
      "severity": "critical",
      "enabled": true,
      "tags": ["truthfulness", "accuracy"],
      "created_at": "2026-03-18T00:00:00Z",
      "updated_at": "2026-03-18T00:00:00Z"
    }
    // ... more rules
  ],
  "metadata": {
    "name": "Default Safety Constitution v1",
    "description": "MVP starting constitution"
  }
}
```

## Development

Run tests:
```bash
pytest
```

Run specific test suites:
```bash
pytest tests/test_constitution.py
pytest tests/test_governance.py
pytest tests/test_json_parse.py
pytest tests/test_smart_chunk.py
```

## License

MIT