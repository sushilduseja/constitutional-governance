# Constitutional Governance SDK

A model-agnostic constitutional AI monitoring layer for production LLM applications. Every LLM output is evaluated against a plain-English constitution using a separate LLM as interpreter — without blocking the user's response.

**The core problem it solves:** LLMs hallucinate, fabricate citations, express bias, and behave inconsistently across runs. Constitutional governance gives you observable, versioned, auditable evidence of what your AI said and whether it violated your standards.

**Who it's for:** Engineering teams deploying LLMs in customer support, financial advisory, HR automation, medical information, legal review, and any domain where AI errors have real consequences.

---

## Features

- **Observe-only, never blocks** — The user's LLM response always returns immediately. Evaluation happens asynchronously in the background.
- **Plain-English constitutions** — Define your standards as JSON rules, not code. "The AI must not fabricate sources" is a rule.
- **Versioned everything** — Constitutions, interpreter prompts, and evaluations are all tagged with versions. Roll back with confidence.
- **No PII by default** — Prompts and responses are stored with length limits and can be redacted. No sensitive data in audit logs unless you explicitly enable it.
- **Groq free tier** — No Anthropic or OpenAI API keys needed for the interpreter. Uses Groq's free tier with automatic model fallbacks.
- **SQLite audit log** — Append-only, immutable. Every evaluation is recorded with timestamp, model, score, and violations.
- **Analytics dashboard** — Live monitoring UI showing compliance rates, violation trends, and per-model breakdown.

---

## Architecture

```
USER / APPLICATION
        │
        ▼
GOVERNANCE WRAPPER SDK
        │
        ▼
LLM PROVIDER ────────────► USER RECEIVES RESPONSE (no delay)
        │
        │ async evaluation
        ▼
CONSTITUTION STORE + GROQ INTERPRETER
        │
        ▼
SQLITE AUDIT LOG ──► ANALYTICS ──► DASHBOARD
```

---

## Enterprise Use Cases

| Domain | What Gets Caught |
|--------|----------------|
| **Customer Support** | Fabricated policies, unsafe refund claims, unverified legal statements |
| **Financial Advisory** | Hallucinated statistics, fake regulatory citations, unqualified recommendations |
| **HR Automation** | Discriminatory language in rejections, unverified skill assessments |
| **Medical Information** | Unverified health claims, fabricated research citations |
| **Legal Review** | Incorrect statute references, fabricated case law |

---

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY (free at console.groq.com)
```

### Python SDK

```python
from sdk.governance import Governance

gov = Governance(
    constitution_path="constitution/rules/default_v1.json",
    mode="async",
)

raw_response = anthropic_client.messages.create(
    model="governance-alpha-7b",
    messages=[{"role": "user", "content": "What is the SEC's regulation for crypto?"}]
)

gov.wrap(
    provider="anthropic",
    raw_response=raw_response,
    user_prompt="What is the SEC's regulation for crypto?",
)
# Response returns immediately — evaluation happens in background
```

### Dashboard

```bash
uvicorn service.app:app --reload
# Visit: http://localhost:8000
```

### REST API

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "What is your refund policy?",
    "context": "You are a customer support bot for an online retailer."
  }'
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard |
| `GET` | `/health` | Health check |
| `GET` | `/api/config` | Service configuration |
| `GET` | `/api/stats` | Compliance statistics |
| `GET` | `/api/constitution` | Current constitution rules |
| `GET` | `/api/audit-log` | Evaluation records |
| `GET` | `/api/analytics` | Full analytics report |
| `POST` | `/evaluate` | Service calls LLM, evaluates response |
| `POST` | `/api/direct-evaluate` | Evaluate a pre-written response |
| `GET` | `/api/golden-check` | Run golden set consistency check |

---

## Constitution Format

Rules are plain-English JSON in `constitution/rules/`:

```json
{
  "version": "1.0.0",
  "rules": [
    {
      "id": "rule_truth_001",
      "text": "The AI must not make verifiable false claims about real-world facts.",
      "severity": "high",
      "enabled": true,
      "tags": ["truthfulness", "accuracy"]
    }
  ]
}
```

---

## Running Tests

```bash
pytest
```

---

## See Also

- `docs/designs/constitutional-governance.md` — Full architecture
- `examples/quickstart.py` — Three enterprise use cases with examples
- `TODOS.md` — What's coming next
