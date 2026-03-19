"""
Main Governance SDK class.

Wraps LLM calls with constitutional AI monitoring.
"""

import asyncio
import json
import logging
import time
from typing import Any, Literal, Optional

from sdk.adapters import get_adapter
from sdk.adapters.base import LLMResponse

logger = logging.getLogger(__name__)


class EvaluationResult:
    """Result of a constitutional evaluation."""

    def __init__(
        self,
        compliant: bool,
        score: float,
        violations: list[dict],
        notes: str = "",
        constitution_version: str = "unknown",
        truncated: bool = False,
        status: str = "success",
        failure_reason: Optional[str] = None,
    ):
        self.compliant = compliant
        self.score = score
        self.violations = violations
        self.notes = notes
        self.constitution_version = constitution_version
        self.truncated = truncated
        self.status = status
        self.failure_reason = failure_reason

    def to_dict(self) -> dict:
        return {
            "compliant": self.compliant,
            "score": self.score,
            "violations": self.violations,
            "notes": self.notes,
            "constitution_version": self.constitution_version,
            "truncated": self.truncated,
            "status": self.status,
            "failure_reason": self.failure_reason,
        }


class Governance:
    """
    Constitutional AI governance wrapper.

    Usage:
        gov = Governance(api_key="...", mode="async")
        raw_response = anthropic_client.messages.create(...)
        response = gov.wrap(
            provider="anthropic",
            raw_response=raw_response,
            user_prompt=prompt,
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        constitution_path: str = "constitution/rules/default_v1.json",
        constitution_version: str = "latest",
        governance_service_url: str = "http://localhost:8000",
        mode: Literal["sync", "async", "fire-and-forget"] = "async",
        max_tokens_per_chunk: int = 8000,
    ):
        self.api_key = api_key
        self.constitution_path = constitution_path
        self.constitution_version = constitution_version
        self.governance_service_url = governance_service_url
        self.mode = mode
        self.max_tokens_per_chunk = max_tokens_per_chunk

        self._constitution: Optional[dict] = None
        self._load_constitution()

    def _load_constitution(self) -> None:
        """Load constitution from JSON file."""
        try:
            with open(self.constitution_path, "r") as f:
                self._constitution = json.load(f)
            logger.info(f"Loaded constitution v{self._get_constitution_version()}")
        except FileNotFoundError:
            logger.warning(f"Constitution file not found: {self.constitution_path}")
            self._constitution = {"version": "unknown", "rules": []}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in constitution: {e}")
            self._constitution = {"version": "error", "rules": []}

    def _get_constitution_version(self) -> str:
        """Safely get constitution version, handling None case."""
        if self._constitution is None:
            return "unknown"
        return self._constitution.get("version", "unknown")

    def _get_constitution_rules(self) -> list[dict]:
        """Safely get constitution rules list, handling None case."""
        if self._constitution is None:
            return []
        return self._constitution.get("rules", [])

    def _validate_input(self, llm_response: str) -> Optional[str]:
        """
        Validate inputs before evaluation. Returns skip reason or None.

        Validates:
        - Constitution exists and has rules
        - Output is not empty/whitespace
        """
        if not self._get_constitution_rules():
            return "no_constitution"

        stripped = llm_response.strip()
        if not stripped:
            return "empty_output"

        return None

    def _format_constitution_rules(self) -> str:
        """Format constitution rules for the interpreter prompt."""
        rules = self._get_constitution_rules()
        formatted = []
        for i, rule in enumerate(rules, 1):
            if not rule.get("enabled", True):
                continue
            severity = rule.get("severity", "info").upper()
            text = rule.get("text", "")
            formatted.append(f"{i}. [{severity}] {text}")
        return "\n".join(formatted)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count. Uses character approximation: 1 token ≈ 4 chars.

        For production, use tiktoken for accurate counting.
        """
        return len(text) // 4

    def _smart_chunk(self, text: str) -> list[str]:
        """
        Split text into chunks at paragraph boundaries, respecting max_tokens.

        Returns list of chunks, each under max_tokens.
        """
        if self._estimate_tokens(text) <= self.max_tokens_per_chunk:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk = ""
        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)
            chunk_tokens = self._estimate_tokens(current_chunk)

            if chunk_tokens + para_tokens <= self.max_tokens_per_chunk:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        if len(chunks) > 5:
            logger.warning(f"Output split into {len(chunks)} chunks — consider increasing max_tokens_per_chunk")

        return chunks

    def _build_interpreter_prompt(self, rules: str, user_prompt: str, llm_response: str) -> str:
        """Build the interpreter prompt for a single chunk."""
        return f"""SYSTEM: You are a constitutional AI evaluator. Your job is to evaluate LLM outputs against a set of principles. Be precise, fair, and explain your reasoning.

USER:

PRINCIPLES (evaluate against ALL of these):
{rules}

INPUT PROMPT (what was asked):
{user_prompt or '[not provided]'}

OUTPUT TO EVALUATE:
{llm_response}

Respond with a JSON object only:
{{
  "compliant": true/false,
  "overall_score": 0.0-1.0,
  "violations": [
    {{
      "rule_id": "rule_xyz",
      "rule_text": "...",
      "severity": "critical|high|medium|low|info",
      "explanation": "plain english explanation of the violation",
      "quote": "the specific text that violated the rule"
    }}
  ],
  "notes": "any additional observations"
}}"""

    def wrap(
        self,
        provider: str,
        raw_response: Any,
        user_prompt: str = "",
    ) -> Any:
        """
        Wrap an LLM call with constitutional governance.

        The caller makes the LLM call directly, passes the raw response object,
        and governance extracts text + model ID using the provider's adapter.

        Args:
            provider: LLM provider ('anthropic', 'openai', etc.)
            raw_response: The raw response object from the LLM call.
                          Must match the provider's response type.
            user_prompt: The original user prompt (for interpreter context).
                         Defaults to empty string.

        Returns:
            The original raw_response (unmodified by governance)
        """
        start = time.time()
        request_id = f"req_{int(start * 1000)}"

        adapter = get_adapter(provider)
        text = adapter.extract_text(raw_response)
        model = adapter.get_model_id(raw_response)

        skip_reason = self._validate_input(text)
        if skip_reason:
            logger.info(f"Skipping evaluation: {skip_reason}")
            self._log_evaluation(
                request_id=request_id,
                user_prompt=user_prompt,
                llm_response=text,
                model=model,
                provider=provider,
                result=EvaluationResult(
                    compliant=True,
                    score=1.0,
                    violations=[],
                    status="skipped",
                    constitution_version=self._get_constitution_version(),
                ),
                latency_ms=int((time.time() - start) * 1000),
            )
            return raw_response

        if self.mode == "fire-and-forget":
            logger.info(f"Fire-and-forget: captured {len(text)} chars, no evaluation")
            return raw_response

        if self.mode == "async":
            asyncio.create_task(
                self._evaluate_async(request_id, user_prompt, text, model, provider, start)
            ).add_done_callback(self._handle_task_exception)
            return raw_response

        result = self._evaluate_sync(user_prompt, text, model, provider)
        self._log_evaluation(
            request_id=request_id,
            user_prompt=user_prompt,
            llm_response=text,
            model=model,
            provider=provider,
            result=result,
            latency_ms=int((time.time() - start) * 1000),
        )
        return raw_response

    def _handle_task_exception(self, task: asyncio.Task) -> None:
        """Handle unhandled exceptions from background tasks."""
        try:
            task.result()
        except Exception as e:
            logger.exception(f"Background evaluation task failed: {e}")

    def _evaluate_sync(
        self,
        user_prompt: str,
        llm_response: str,
        model: str,
        provider: str,
    ) -> EvaluationResult:
        """
        Synchronous evaluation — calls the interpreter and waits for result.
        For MVP: calls interpreter LLM via anthropic adapter (default: Claude 3.5 Sonnet).
        """
        rules = self._format_constitution_rules()
        chunks = self._smart_chunk(llm_response)
        truncated = len(chunks) > 1

        try:
            all_violations = []
            interpreter_adapter = get_adapter("anthropic")

            for chunk in chunks:
                prompt = self._build_interpreter_prompt(rules, user_prompt, chunk)
                raw = interpreter_adapter.call(prompt)
                parsed = self._parse_interpreter_response(raw.text)
                if parsed:
                    all_violations.extend(parsed.get("violations", []))

            has_violations = len(all_violations) > 0

            return EvaluationResult(
                compliant=not has_violations,
                score=1.0 if not has_violations else 0.7,
                violations=all_violations,
                constitution_version=self._get_constitution_version(),
                truncated=truncated,
                status="success",
            )

        except Exception as e:
            return self._handle_evaluation_error(e, llm_response)

    def _handle_evaluation_error(self, error: Exception, llm_response: str) -> EvaluationResult:
        """
        Handle evaluation errors with specific exception types.

        Error categories:
        - AuthenticationError: Wrong API key — CRITICAL, no retry, alert
        - RateLimitError: Rate limited — retry with backoff (done by caller if sync)
        - APITimeoutError: Timeout — retry with backoff
        - Other: Generic failure, log and return
        """
        error_type = type(error).__name__

        if "AuthenticationError" in error_type or "auth" in str(error).lower():
            logger.critical(
                f"Authentication failure during evaluation: {error}. "
                f"Check ANTHROPIC_API_KEY. Evaluation skipped."
            )
            return EvaluationResult(
                compliant=True,
                score=0.0,
                violations=[],
                status="failed",
                failure_reason=f"auth_error: {error}",
            )

        if "RateLimitError" in error_type or "429" in str(error):
            logger.warning(f"Rate limited during evaluation: {error}. Consider reducing concurrency.")
            return EvaluationResult(
                compliant=True,
                score=0.0,
                violations=[],
                status="failed",
                failure_reason=f"rate_limited: {error}",
            )

        if "APITimeoutError" in error_type or "timeout" in str(error).lower():
            logger.warning(f"Timeout during evaluation: {error}")
            return EvaluationResult(
                compliant=True,
                score=0.0,
                violations=[],
                status="failed",
                failure_reason=f"timeout: {error}",
            )

        logger.error(f"Evaluation failed: {error}")
        return EvaluationResult(
            compliant=True,
            score=0.0,
            violations=[],
            status="failed",
            failure_reason=str(error),
        )

    def _parse_interpreter_response(self, raw_text: str) -> Optional[dict]:
        """
        Parse JSON from the interpreter LLM response.

        Handles:
        1. Clean JSON
        2. JSON wrapped in markdown code blocks
        3. Partial JSON with common fixes
        """
        import re

        text = raw_text.strip()

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            text = json_match.group(0)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            text = text.replace("```json", "").replace("```", "")
            text = text.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse interpreter JSON: {raw_text[:200]}")
                return None

    async def _evaluate_async(
        self,
        request_id: str,
        user_prompt: str,
        llm_response: str,
        model: str,
        provider: str,
        start: float,
    ) -> None:
        """Background evaluation task — runs in thread pool to avoid blocking."""
        try:
            result = await asyncio.to_thread(
                self._evaluate_sync, user_prompt, llm_response, model, provider
            )
        except Exception as e:
            result = self._handle_evaluation_error(e, llm_response)
        self._log_evaluation(
            request_id=request_id,
            user_prompt=user_prompt,
            llm_response=llm_response,
            model=model,
            provider=provider,
            result=result,
            latency_ms=int((time.time() - start) * 1000),
        )

    def _log_evaluation(
        self,
        request_id: str,
        user_prompt: str,
        llm_response: str,
        model: str,
        provider: str,
        result: EvaluationResult,
        latency_ms: int,
    ) -> None:
        """
        Log evaluation to the audit store.

        MVP: logs via standard logging. Production: sends to governance service.
        """
        audit_record = {
            "id": f"eval_{request_id}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": request_id,
            "model_provider": provider,
            "model_name": model,
            "constitution_version": result.constitution_version,
            "user_prompt": user_prompt,
            "llm_response": llm_response[:10000],
            "evaluation": result.to_dict(),
            "latency_ms": latency_ms,
            "status": result.status,
            "failure_reason": result.failure_reason,
        }

        logger.info(
            f"Evaluation {audit_record['id']}: "
            f"status={result.status}, compliant={result.compliant}, "
            f"violations={len(result.violations)}"
        )
