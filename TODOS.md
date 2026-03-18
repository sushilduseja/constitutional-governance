# TODOS — AI Governance MVP

> Last updated: 2026-03-18
> Status: Active

---

## Phase 1: Core Engine

- [x] ~~**SDK adapter interface spec**~~ — Done. `sdk/adapters/base.py` defines `LLMAdapter` protocol.
- [x] ~~**Token estimation utility**~~ — Done. `_estimate_tokens()` uses char approximation.
- [x] ~~**Interpreter JSON parsing robustness**~~ — Done. `_parse_interpreter_response()` handles clean JSON, markdown-wrapped, and repair attempts.
- [x] ~~**Auth error handling**~~ — Done. `_handle_evaluation_error()` distinguishes Auth/RateLimit/Timeout/Generic.

- [ ] **Startup validation health check** — On Governance SDK initialization, run a health check: can it load the constitution? Log WARN if constitution is empty. Don't fail silently.
  Priority: P1 | Depends on: None | Filed by: plan review

- [ ] **Constitution schema validation** — On load, validate the constitution JSON schema. Reject constitutions missing required fields (`id`, `text`, `severity`, `enabled`). Log which rules are invalid.
  Priority: P1 | Depends on: None | Filed by: plan review

- [ ] **SQLite audit log writer** — Currently `_log_evaluation()` only logs via `logging.info()`. Implement actual SQLite writes to the audit log.
  Priority: P1 | Depends on: Architecture doc | Filed by: pre-landing review

- [ ] **Golden set consistency checker** — Implement the consistency check job that re-evaluates golden set outputs against current constitution and alerts on drift.
  Priority: P1 | Depends on: Interpreter, constitution | Filed by: plan review

- [ ] **Startup validation: SDK health check** — Check API key is valid by making a lightweight call. Log WARN if auth fails on startup rather than on first use.
  Priority: P2 | Depends on: Phase 1 core | Filed by: plan review

---

## Phase 2: Analytics + Self-Improvement

- [ ] **Constitution health scanner** — Analyze audit log weekly to identify: (1) rules with 0 violations (possibly too broad), (2) rules with >50% violation rate (possibly too narrow), (3) violation patterns with no corresponding rule. Output: ranked suggestions.
  Priority: P2 | Depends on: Phase 1 complete, audit log populated | Filed by: plan review

- [ ] **Violation clustering** — Group similar violation quotes (semantic similarity via embedding) to detect systematic issues. E.g., "According to MIT researchers..." appearing in 20 different outputs.
  Priority: P2 | Depends on: Phase 2 analytics | Filed by: plan review

- [ ] **Drift detection for model updates** — When the monitored LLM model version changes, flag the constitution for re-validation.
  Priority: P2 | Depends on: Phase 1 complete | Filed by: plan review

- [ ] **Constitution diff view** — When constitution version changes, generate a human-readable diff. Store diffs as part of version history.
  Priority: P2 | Depends on: Constitution versioning | Filed by: plan review

---

## Phase 3: Polish + Multi-Provider

- [ ] **JS/TS SDK** — Port the governance wrapper to JavaScript/TypeScript. The governance service API is the contract — the SDK is just an adapter.
  Priority: P2 | Depends on: Phase 1 complete, API contract stabilized | Filed by: plan review

- [ ] **Multi-org isolation** — When multiple organizations use the same governance service, isolate: (1) separate audit logs per org, (2) separate constitution namespaces, (3) separate analytics. Add org_id to all records.
  Priority: P3 | Depends on: Phase 1 + Phase 2 | Filed by: plan review

- [ ] **Compliance certificate schema** — Define a typed `ComplianceCertificate` that wraps evaluation results. Makes the audit log a compliance artifact, not just a data store.
  Priority: P2 | Depends on: Phase 1 complete | Filed by: plan review

---

## Cross-Cutting (Anytime)

- [ ] **Interpreter prompt versioning** — The interpreter prompt changes evaluation behavior. Store prompts in `constitution/interpreter_prompts/v{N}.md`. Tag evaluations with interpreter prompt version.
  Priority: P1 | Depends on: None | Filed by: plan review

- [ ] **Cost tracking** — Track interpreter LLM token usage and cost separately. Store: `interpreter_tokens_in`, `interpreter_tokens_out`, `interpreter_cost_usd`.
  Priority: P2 | Depends on: Token estimation | Filed by: plan review

- [ ] **PII redaction pipeline** — Before storing prompts in the audit log, run PII detection (regex for emails, phones, SSNs, etc.) and replace with `[REDACTED: type]`. Configurable.
  Priority: P2 | Depends on: Phase 1 complete | Filed by: plan review

- [ ] **Shadow mode for new rules** — Test proposed rules against past 100 evaluations in shadow mode before activating. Log what would have happened without counting violations.
  Priority: P3 | Depends on: Phase 2 self-improvement | Filed by: plan review

- [ ] **Async retry with backoff** — Current `_evaluate_sync` doesn't retry. Add exponential backoff retry (2s, 4s) for timeout and rate limit errors.
  Priority: P1 | Depends on: Auth error handling | Filed by: pre-landing review

---

## Resolved (Do Not Implement)

- ~~**Automated rule activation**~~ — Deferred. Human-in-the-loop required for all rule changes in MVP.
  Reason: Risk of constitution bloat without human oversight.

- ~~**Cross-org constitution federation**~~ — Out of scope for MVP. Requires multi-org isolation, anonymization guarantees, and consent frameworks.
  Reason: Premature — solve single-org first.

- ~~**Enforcement mode**~~ — Out of scope. MVP is monitoring-only.
  Reason: Monitoring proves the concept before adding blocking behavior.
