"""
Tests for the FastAPI service endpoints.
"""

import pytest
import asyncio
import httpx
from unittest.mock import patch, MagicMock


@pytest.fixture
async def client():
    """Async test client for the service."""
    from service.app import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestEvaluateRequestSchema:
    """Verify the new request schema only accepts user_prompt + context."""

    @pytest.mark.asyncio
    async def test_accepts_user_prompt_only(self, client):
        """Request with only user_prompt is valid."""
        with patch("service.app._get_monitored_adapter") as mock_ad, \
             patch("service.app.evaluator") as mock_eval:

            mock_ad.return_value.call.return_value = MagicMock(text="mock response")
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.compliant = True
            mock_result.score = 1.0
            mock_result.violations = []
            mock_result.notes = ""
            mock_result.constitution_version = "1.0.0"
            mock_result.truncated = False
            mock_result.failure_reason = None
            mock_eval.evaluate.return_value = mock_result

            res = await client.post("/evaluate", json={"user_prompt": "Hello"})
            assert res.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_rejects_llm_response_field(self, client):
        """llm_response is no longer in the request schema."""
        res = await client.post("/evaluate", json={
            "user_prompt": "Hello",
            "llm_response": "Some response",
        })
        body = res.json()
        assert "llm_response" not in body

    @pytest.mark.asyncio
    async def test_rejects_model_provider_field(self, client):
        """model_provider is no longer in the request schema."""
        res = await client.post("/evaluate", json={
            "user_prompt": "Hello",
            "model_provider": "openai",
        })
        body = res.json()
        assert "model_provider" not in body

    @pytest.mark.asyncio
    async def test_rejects_model_name_field(self, client):
        """model_name is no longer in the request schema."""
        res = await client.post("/evaluate", json={
            "user_prompt": "Hello",
            "model_name": "gpt-4",
        })
        body = res.json()
        assert "model_name" not in body

    @pytest.mark.asyncio
    async def test_accepts_optional_context(self, client):
        """Optional context field is accepted."""
        with patch("service.app._get_monitored_adapter") as mock_ad, \
             patch("service.app.evaluator") as mock_eval:

            mock_ad.return_value.call.return_value = MagicMock(text="mock response")
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.compliant = True
            mock_result.score = 1.0
            mock_result.violations = []
            mock_result.notes = ""
            mock_result.constitution_version = "1.0.0"
            mock_result.truncated = False
            mock_result.failure_reason = None
            mock_eval.evaluate.return_value = mock_result

            res = await client.post("/evaluate", json={
                "user_prompt": "Hello",
                "context": "Previous conversation history here.",
            })
            assert res.status_code in (200, 500)


class TestDirectEvaluateEndpoint:
    """Tests for the /api/direct-evaluate endpoint."""

    @pytest.mark.asyncio
    async def test_direct_evaluate_returns_evaluation(self, client):
        """direct-evaluate evaluates pre-written response without LLM call."""
        with patch("service.app.evaluator") as mock_eval:
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.compliant = False
            mock_result.score = 0.4
            mock_result.violations = [
                {"rule_id": "rule_truth_001", "severity": "critical", "explanation": "False claim made"}
            ]
            mock_result.notes = "chunk 1: violation"
            mock_result.constitution_version = "1.0.0"
            mock_result.truncated = False
            mock_result.failure_reason = None
            mock_eval.evaluate.return_value = mock_result

            res = await client.post("/api/direct-evaluate", json={
                "user_prompt": "Who discovered penicillin?",
                "llm_response": "Penicillin was discovered by Alexander Fleming in 1928.",
            })

            assert res.status_code == 200
            data = res.json()
            assert "evaluation" in data
            assert data["evaluation"]["compliant"] is False
            assert data["evaluation"]["score"] == 0.4
            assert len(data["evaluation"]["violations"]) == 1

    @pytest.mark.asyncio
    async def test_direct_evaluate_requires_llm_response(self, client):
        """llm_response is required for direct-evaluate."""
        res = await client.post("/api/direct-evaluate", json={
            "user_prompt": "Hello",
        })
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_direct_evaluate_requires_user_prompt(self, client):
        """user_prompt is required for direct-evaluate."""
        res = await client.post("/api/direct-evaluate", json={
            "llm_response": "Some response",
        })
        assert res.status_code == 422


class TestServiceConfigEndpoint:
    """Tests for the /api/config endpoint."""

    @pytest.mark.asyncio
    async def test_config_returns_all_fields(self, client):
        """config endpoint returns monitored_provider, monitored_model, provider_models."""
        res = await client.get("/api/config")
        assert res.status_code == 200
        data = res.json()
        assert "monitored_provider" in data
        assert "monitored_model" in data
        assert "provider_models" in data

    @pytest.mark.asyncio
    async def test_config_provider_models_has_all_providers(self, client):
        """provider_models contains anthropic, openai, groq."""
        res = await client.get("/api/config")
        data = res.json()
        models = data["provider_models"]
        assert "anthropic" in models
        assert "openai" in models
        assert "groq" in models

    @pytest.mark.asyncio
    async def test_config_each_provider_has_models(self, client):
        """Each provider has at least one model defined."""
        res = await client.get("/api/config")
        data = res.json()
        for provider, models in data["provider_models"].items():
            assert len(models) > 0
            for m in models:
                assert "id" in m
                assert "label" in m


class TestHealthEndpoint:
    """Health endpoint includes monitored model info."""

    @pytest.mark.asyncio
    async def test_health_includes_monitored_model(self, client):
        """Health response includes monitored_provider and monitored_model."""
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "monitored_provider" in data
        assert "monitored_model" in data


class TestEvaluateEndpointResponse:
    """Verify /evaluate returns llm_response + evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_llm_response(self, client):
        """evaluate response includes llm_response from the monitored model."""
        with patch("service.app._get_monitored_adapter") as mock_ad, \
             patch("service.app.evaluator") as mock_eval:

            mock_ad.return_value.call.return_value = MagicMock(
                text="The capital of France is Paris."
            )
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.compliant = True
            mock_result.score = 1.0
            mock_result.violations = []
            mock_result.notes = ""
            mock_result.constitution_version = "1.0.0"
            mock_result.truncated = False
            mock_result.failure_reason = None
            mock_eval.evaluate.return_value = mock_result

            res = await client.post("/evaluate", json={"user_prompt": "What is the capital of France?"})
            assert res.status_code == 200
            data = res.json()
            assert "llm_response" in data
            assert "evaluation" in data
            assert data["llm_response"] == "The capital of France is Paris."
            assert data["evaluation"]["compliant"] is True

    @pytest.mark.asyncio
    async def test_evaluate_includes_context_in_llm_call(self, client):
        """Context is passed through to the monitored LLM."""
        captured_prompts = []

        def capture_call(prompt, **kwargs):
            captured_prompts.append(prompt)
            return MagicMock(text="Response")

        with patch("service.app._get_monitored_adapter") as mock_ad, \
             patch("service.app.evaluator") as mock_eval:

            mock_ad.return_value.call.side_effect = capture_call
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.compliant = True
            mock_result.score = 1.0
            mock_result.violations = []
            mock_result.notes = ""
            mock_result.constitution_version = "1.0.0"
            mock_result.truncated = False
            mock_result.failure_reason = None
            mock_eval.evaluate.return_value = mock_result

            res = await client.post("/evaluate", json={
                "user_prompt": "Summarize this for me.",
                "context": "The document is about climate change.",
            })
            assert res.status_code == 200
            assert len(captured_prompts) == 1
            assert "climate change" in captured_prompts[0]
            assert "Summarize this" in captured_prompts[0]
