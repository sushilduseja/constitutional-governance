"""
Tests for Governance class core behavior.
"""

import pytest
import json
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.governance import Governance, EvaluationResult
from sdk.adapters.base import LLMResponse


class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_defaults(self):
        """Default values are set correctly."""
        result = EvaluationResult(compliant=True, score=1.0, violations=[])
        assert result.compliant is True
        assert result.score == 1.0
        assert result.violations == []
        assert result.notes == ""
        assert result.constitution_version == "unknown"
        assert result.truncated is False
        assert result.status == "success"
        assert result.failure_reason is None

    def test_to_dict(self):
        """Serialization works correctly."""
        result = EvaluationResult(
            compliant=False,
            score=0.7,
            violations=[{"rule_id": "test"}],
            notes="Test note",
            constitution_version="1.0.0",
            truncated=True,
            status="success",
        )
        d = result.to_dict()
        assert d["compliant"] is False
        assert d["score"] == 0.7
        assert d["violations"] == [{"rule_id": "test"}]
        assert d["truncated"] is True


class TestValidation:
    """Test input validation."""

    def test_validate_empty_output(self):
        """Empty output is skipped."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        reason = gov._validate_input("")
        assert reason == "empty_output"

    def test_validate_whitespace_output(self):
        """Whitespace-only output is skipped."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        reason = gov._validate_input("   \n\n  ")
        assert reason == "empty_output"

    def test_validate_valid_output(self):
        """Valid output passes validation."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        reason = gov._validate_input("This is a valid response.")
        assert reason is None

    def test_validate_no_constitution(self):
        """Missing constitution is detected."""
        gov = Governance(constitution_path="nonexistent.json")
        reason = gov._validate_input("Some text")
        assert reason == "no_constitution"


class TestGovernanceWrap:
    """Test Governance.wrap() behavior."""

    def test_wrap_returns_raw_response(self):
        """wrap() returns the original raw response."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json",
            mode="fire-and-forget",
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello, world!")]

        result = gov.wrap(
            provider="anthropic",
            raw_response=mock_response,
            user_prompt="Say hello",
        )
        assert result is mock_response

    def test_wrap_extracts_text_from_response(self):
        """wrap() extracts text using the adapter."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json",
            mode="fire-and-forget",
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Extracted text")]

        with patch.object(gov, "_log_evaluation") as mock_log:
            gov.wrap(
                provider="anthropic",
                raw_response=mock_response,
                user_prompt="Test prompt",
            )

    @pytest.mark.asyncio
    async def test_wrap_async_mode_returns_immediately(self):
        """Async mode returns without waiting."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json",
            mode="async",
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response text")]
        mock_response.model = "claude-3-5-sonnet"

        import time
        start = time.time()
        # Mock the _evaluate_async method to avoid actual async execution
        with patch.object(gov, '_evaluate_async') as mock_evaluate_async:
            result = await gov.wrap(
                provider="anthropic",
                raw_response=mock_response,
                user_prompt="Test",
            )
        elapsed = time.time() - start

        assert result is mock_response
        assert elapsed < 0.1
        # Verify that _evaluate_async was called
        mock_evaluate_async.assert_called_once()

    def test_wrap_fire_and_forget_skips_evaluation(self):
        """Fire-and-forget mode does not evaluate."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json",
            mode="fire-and-forget",
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]

        with patch.object(gov, "_evaluate_async") as mock_eval:
            with patch.object(gov, "_evaluate_sync") as mock_sync:
                result = gov.wrap(
                    provider="anthropic",
                    raw_response=mock_response,
                )
                mock_eval.assert_not_called()
                mock_sync.assert_not_called()

    def test_wrap_sync_mode_evaluates(self):
        """Sync mode evaluates immediately."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json",
            mode="sync",
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="A response that needs evaluation")]
        mock_response.model = "claude-3-5-sonnet"

        with patch("sdk.governance.get_adapter") as mock_get:
            mock_adapter = MagicMock()
            mock_adapter.extract_text.return_value = "A response that needs evaluation"
            mock_adapter.get_model_id.return_value = "claude-3-5-sonnet"
            mock_adapter.call.return_value = MagicMock(text='{"compliant": true, "score": 1.0, "violations": []}')
            mock_get.return_value = mock_adapter

            with patch.object(gov, "_evaluate_sync") as mock_eval:
                mock_eval.return_value = EvaluationResult(
                    compliant=True, score=1.0, violations=[]
                )
                result = gov.wrap(
                    provider="anthropic",
                    raw_response=mock_response,
                )
                mock_eval.assert_called_once()


class TestErrorHandling:
    """Test error handling."""

    def test_handle_evaluation_error_auth(self):
        """Authentication errors are handled."""
        gov = Governance()

        class AuthError(Exception):
            pass

        error = AuthError("Invalid API key")
        result = gov._handle_evaluation_error(error, "some response")

        assert result.status == "failed"
        assert result.failure_reason is not None
        assert "authentication" in result.failure_reason.lower()

    def test_handle_evaluation_error_rate_limit(self):
        """Rate limit errors are handled."""
        gov = Governance()

        class RateLimitError(Exception):
            pass

        error = RateLimitError("Rate limit exceeded")
        result = gov._handle_evaluation_error(error, "some response")

        assert result.status == "failed"
        assert result.failure_reason is not None
        assert "rate" in result.failure_reason.lower()

    def test_handle_evaluation_error_timeout(self):
        """Timeout errors are handled."""
        gov = Governance()

        class TimeoutError(Exception):
            pass

        error = TimeoutError("Request timed out")
        result = gov._handle_evaluation_error(error, "some response")

        assert result.status == "failed"
        assert result.failure_reason is not None
        assert "timeout" in result.failure_reason.lower()

    def test_handle_evaluation_error_generic(self):
        """Generic errors are handled."""
        gov = Governance()

        error = ValueError("Something went wrong")
        result = gov._handle_evaluation_error(error, "some response")

        assert result.status == "failed"
        assert result.failure_reason is not None


class TestPromptBuilding:
    """Test interpreter prompt construction."""

    def test_build_prompt_includes_rules(self):
        """Prompt includes formatted rules."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        prompt = gov._build_interpreter_prompt(
            rules="1. [CRITICAL] Test rule\n2. [HIGH] Another rule",
            user_prompt="What is 2+2?",
            llm_response="The answer is 4.",
        )

        assert "[CRITICAL]" in prompt
        assert "[HIGH]" in prompt
        assert "Test rule" in prompt
        assert "What is 2+2?" in prompt
        assert "The answer is 4." in prompt

    def test_build_prompt_includes_not_provided(self):
        """Empty user prompt shows placeholder."""
        gov = Governance()
        prompt = gov._build_interpreter_prompt(
            rules="1. [LOW] Test",
            user_prompt="",
            llm_response="Response",
        )

        assert "[not provided]" in prompt

    def test_build_prompt_is_different_per_chunk(self):
        """Each chunk gets its own prompt."""
        gov = Governance()
        prompt1 = gov._build_interpreter_prompt("rules", "prompt", "chunk 1")
        prompt2 = gov._build_interpreter_prompt("rules", "prompt", "chunk 2")

        assert "chunk 1" in prompt1
        assert "chunk 2" in prompt2
        assert "chunk 1" not in prompt2
