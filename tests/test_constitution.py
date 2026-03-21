"""
Tests for constitution loading and validation.
"""

import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.governance import Governance


class TestConstitutionLoading:
    """Test constitution file loading."""

    def test_loads_valid_constitution(self):
        """Default constitution loads successfully."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        assert gov._constitution is not None
        assert gov._get_constitution_version() == "1.0.0"
        assert len(gov._get_constitution_rules()) == 5

    def test_loads_all_five_rules(self):
        """All 5 rules are present and enabled."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        rules = gov._get_constitution_rules()
        assert len(rules) == 5

        rule_ids = [r["id"] for r in rules]
        assert "rule_truth_001" in rule_ids
        assert "rule_harm_001" in rule_ids
        assert "rule_citation_001" in rule_ids
        assert "rule_uncertainty_001" in rule_ids
        assert "rule_bias_001" in rule_ids

    def test_all_rules_enabled_by_default(self):
        """All rules are enabled."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        for rule in gov._get_constitution_rules():
            assert rule["enabled"] is True

    def test_missing_constitution_file_returns_empty_rules(self):
        """Missing file is handled gracefully."""
        gov = Governance(
            constitution_path="constitution/rules/nonexistent.json"
        )
        assert gov._constitution is not None
        assert gov._get_constitution_version() == "unknown"
        assert len(gov._get_constitution_rules()) == 0

    def test_malformed_json_returns_empty_rules(self, tmp_path):
        """Malformed JSON is handled gracefully."""
        bad_file = tmp_path / "malformed.json"
        bad_file.write_text("{ this is not json")

        gov = Governance(constitution_path=str(bad_file))
        assert gov._get_constitution_version() == "error"
        assert len(gov._get_constitution_rules()) == 0


class TestConstitutionRules:
    """Test constitution rule formatting."""

    def test_format_rules_includes_severity(self):
        """Formatted rules include severity in brackets."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        formatted = gov._format_constitution_rules()

        assert "[CRITICAL]" in formatted
        assert "[HIGH]" in formatted
        assert "[LOW]" in formatted

    def test_format_rules_skips_disabled(self):
        """Disabled rules are not included."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        rules = gov._get_constitution_rules()
        rules[0]["enabled"] = False

        formatted = gov._format_constitution_rules()
        assert "truth" not in formatted.lower()
        assert "harm" in formatted.lower()

    def test_format_rules_includes_rule_text(self):
        """Formatted rules include the rule text."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        formatted = gov._format_constitution_rules()

        assert "verifiable false claims" in formatted
        assert "harm to individuals" in formatted

    def test_format_rules_empty_when_no_rules(self):
        """Empty string when constitution has no rules."""
        gov = Governance(
            constitution_path="constitution/rules/nonexistent.json"
        )
        formatted = gov._format_constitution_rules()
        assert formatted == ""


class TestConstitutionSchema:
    """Test constitution schema compliance."""

    def test_all_rules_have_required_fields(self):
        """Each rule has id, text, severity, enabled."""
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        for rule in gov._get_constitution_rules():
            assert "id" in rule
            assert "text" in rule
            assert "severity" in rule
            assert "enabled" in rule
            assert "created_at" in rule
            assert "updated_at" in rule

    def test_rule_severity_values(self):
        """Severity is one of the valid values."""
        valid_severities = {"critical", "high", "medium", "low", "info"}
        gov = Governance(
            constitution_path="constitution/rules/default_v1.json"
        )
        for rule in gov._get_constitution_rules():
            assert rule["severity"] in valid_severities
