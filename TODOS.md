# TODOS — AI Governance MVP

> Last updated: 2026-03-18
> Status: Active

---

## Phase 1: Core Engine

- [ ] **SDK adapter interface spec** — Define the `LLMAdapter` protocol before writing any adapter. Must support: `call(prompt) -> str`, `extract_text(response) -> str`, `get_model_id() -> str`. Define the adapter pattern in `sdk/adapters/base.py`.
  Priority: P1 | Depends on: None | Filed by: plan review

- [ ] **Interpreter JSON parsing robustness** — The interpreter LLM can return malformed JSON. Add a `safe_parse_json(response: str) -> dict | None` helper that tries primary parse, then attempts JSON repair (strip markdown code blocks, fix common issues), then falls back to returning None and logging PARSE_ERROR.
  Priority: P1 | Depends on: Phase 1 core | Filed by: plan review

- [ ] **Token estimation utility** — Before sending to the interpreter, estimate tokens using a simple character-based approximation (1 token ≈ 4 chars for English). Add `estimate_tokens(text: str) -> int`. Use tiktoken only if performance permits.
  Priority: P1 | Depends on: Phase 1 core | Filed by: plan review

- [ ] **Startup validation health check** — On Governance SDK initialization, run a health check: can it reach the governance service? Can it load the constitution? Log WARN if constitution is empty or governance service is unreachable. Don't fail silently.
  Priority: P1 | Depends on: Phase 1 core | Filed by: plan review

- [ ] **Constitution schema validation** — On load, validate the constitution JSON schema. Reject constitutions missing required fields (`id`, `text`, `severity`, `enabled`). Log which rules are invalid.
  Priority: P1 | Depends on: None | Filed by: plan review

---

## Phase 2: Analytics + Self-Improvement

- [ ] **Constitution health scanner** — Analyze audit log weekly to identify: (1) rules with 0 violations (possibly too broad or wrong scope), (2) rules with >50% violation rate (possibly too narrow or model-weakness indicator), (3) violation patterns with no corresponding rule. Output: ranked suggestions for constitution improvements.
  Priority: P2 | Depends on: Phase 1 complete, audit log populated | Filed by: plan review

- [ ] **Violation clustering** — Group similar violation quotes (semantic similarity via embedding) to detect systematic issues. E.g., "According to MIT researchers..." appearing in 20 different outputs suggests a pattern the model defaults to.
  Priority: P2 | Depends on: Phase 2 analytics | Filed by: plan review

- [ ] **Drift detection for model updates** — When the monitored LLM model version changes (e.g., `claude-3-5-sonnet-20260220` → `claude-3-5-sonnet-20260320`), flag the constitution for re-validation. Violation rates may shift with model updates.
  Priority: P2 | Depends on: Phase 1 complete | Filed by: plan review

- [ ] **Constitution diff view** — When constitution version changes, generate a human-readable diff: what rules were added, removed, or modified? Store diffs as part of version history.
  Priority: P2 | Depends on: Constitution versioning | Filed by: plan review

---

## Phase 3: Polish + Multi-Provider

- [ ] **JS/TS SDK** — Port the governance wrapper to JavaScript/TypeScript for browser and Node.js environments. The governance service API should be the contract — the SDK is just an adapter.
  Priority: P2 | Depends on: Phase 1 complete, API contract stabilized | Filed by: plan review

- [ ] **Multi-org isolation** — When multiple organizations use the same governance service, isolate: (1) separate audit logs per org, (2) separate constitution namespaces, (3) separate analytics. Add org_id to all records.
  Priority: P3 | Depends on: Phase 1 + Phase 2 | Filed by: plan review

- [ ] **Compliance certificate schema** — Define a typed `ComplianceCertificate` that wraps evaluation results. Makes the audit log a compliance artifact, not just a data store. Queryable, shareable, auditable by compliance teams.
  Priority: P2 | Depends on: Phase 1 complete | Filed by: plan review

---

## Cross-Cutting (Anytime)

- [ ] **Interpreter prompt versioning** — The interpreter prompt itself (Section 5) should be versioned. Changes to the prompt change evaluation behavior. Store prompts in `constitution/interpreter_prompts/v1.md`, `v2.md`, etc. Tag evaluations with interpreter prompt version.
  Priority: P1 | Depends on: None | Filed by: plan review

- [ ] **Cost tracking** — Track interpreter LLM token usage and cost separately from user LLM costs. Store in audit log: `interpreter_tokens_in`, `interpreter_tokens_out`, `interpreter_cost_usd`.
  Priority: P2 | Depends on: Token estimation | Filed by: plan review

- [ ] **PII redaction pipeline** — Before storing prompts in the audit log, run PII detection (regex for emails, phones, SSNs, etc.) and replace with `[REDACTED: email]`, etc. Make this configurable — some orgs may want full prompts stored.
  Priority: P2 | Depends on: Phase 1 complete | Filed by: plan review

- [ ] **Shadow mode for new rules** — When a new rule is proposed by the self-improvement engine, test it against the past 100 evaluations in shadow mode (log what would have happened, don't count violations yet). This validates the rule before activating it.
  Priority: P3 | Depends on: Phase 2 self-improvement | Filed by: plan review

---

## Resolved (Do Not Implement)

- ~~**Automated rule activation**~~ — Deferred. Human-in-the-loop required for all rule changes in MVP. Automated activation (Phase 2) requires shadow mode and high-confidence scoring first.
  Reason: Risk of constitution bloat without human oversight.

- ~~**Cross-org constitution federation**~~ — Out of scope for MVP. Requires multi-org isolation, anonymization guarantees, and consent frameworks beyond MVP scope.
  Reason: Premature — solve single-org first.

- ~~**Enforcement mode**~~ — Out of scope. MVP is monitoring-only. Enforcement (blocking/revising outputs) requires different architecture, user research, and safety review.
  Reason: Monitoring is the right first step — proves the concept before adding blocking behavior.
