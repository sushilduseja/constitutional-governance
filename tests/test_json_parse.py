"""
Tests for interpreter JSON response parsing.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.governance import Governance


class TestJsonParsing:
    """Test JSON parsing robustness."""

    def test_parses_clean_json(self):
        """Clean JSON is parsed correctly."""
        gov = Governance()
        raw = '{"compliant": true, "score": 1.0, "violations": []}'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["compliant"] is True
        assert result["score"] == 1.0

    def test_parses_markdown_wrapped_json(self):
        """JSON in markdown code blocks is parsed."""
        gov = Governance()
        raw = '```json\n{"compliant": false, "violations": [{"rule_id": "test"}]}\n```'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["compliant"] is False
        assert len(result["violations"]) == 1

    def test_parses_json_with_leading_text(self):
        """JSON after leading text is extracted."""
        gov = Governance()
        raw = 'Here is my analysis:\n{"compliant": true, "score": 0.9}'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["score"] == 0.9

    def test_parses_json_with_trailing_text(self):
        """JSON with trailing text is extracted."""
        gov = Governance()
        raw = '{"compliant": true, "score": 1.0}\n\nThis assessment is based on...'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["compliant"] is True

    def test_parses_nested_json(self):
        """Nested JSON structures are preserved."""
        gov = Governance()
        raw = '{"compliant": false, "violations": [{"rule_id": "rule_001", "severity": "high", "explanation": "The model claimed X"}]}'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert len(result["violations"]) == 1
        assert result["violations"][0]["severity"] == "high"

    def test_returns_none_on_invalid_json(self):
        """Invalid JSON returns None."""
        gov = Governance()
        raw = 'This is not JSON at all'
        result = gov._parse_interpreter_response(raw)
        assert result is None

    def test_returns_none_on_empty_string(self):
        """Empty string returns None."""
        gov = Governance()
        result = gov._parse_interpreter_response("")
        assert result is None

    def test_returns_none_on_whitespace_only(self):
        """Whitespace-only returns None."""
        gov = Governance()
        result = gov._parse_interpreter_response("   \n\n   ")
        assert result is None

    def test_strips_backticks(self):
        """Backticks are stripped."""
        gov = Governance()
        raw = '```\n{"compliant": true}\n```'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["compliant"] is True

    def test_handles_special_characters(self):
        """Special characters in strings are handled."""
        gov = Governance()
        raw = '{"notes": "The model said \\"I\\" with quotes"}'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert "I" in result["notes"]


class TestJsonParsingRealWorld:
    """Real-world interpreter response patterns."""

    def test_violation_format(self):
        """Violation structure is preserved."""
        gov = Governance()
        raw = """```json
{
  "compliant": false,
  "overall_score": 0.72,
  "violations": [
    {
      "rule_id": "rule_citation_001",
      "rule_text": "The AI must not fabricate sources...",
      "severity": "medium",
      "explanation": "The response claimed 'scientists at MIT discovered...' without a verifiable source.",
      "quote": "scientists at MIT discovered this effect"
    }
  ],
  "notes": "Good analogy for the target audience"
}
```"""
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["compliant"] is False
        assert result["overall_score"] == 0.72
        assert len(result["violations"]) == 1
        assert result["violations"][0]["rule_id"] == "rule_citation_001"

    def test_compliant_response(self):
        """Compliant response parses correctly."""
        gov = Governance()
        raw = '{"compliant": true, "overall_score": 1.0, "violations": [], "notes": "All rules satisfied"}'
        result = gov._parse_interpreter_response(raw)
        assert result is not None
        assert result["compliant"] is True
        assert result["overall_score"] == 1.0
        assert result["notes"] == "All rules satisfied"
