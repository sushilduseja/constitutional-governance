"""
Tests for the GoldenSetChecker.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from service.analytics import GoldenSetChecker
from service.evaluator import EvaluationResult


class TestGoldenSetChecker:
    """Tests for the golden set consistency checker."""

    def test_check_missing_file(self):
        """Returns error status when golden set file doesn't exist."""
        mock_evaluator = MagicMock()
        checker = GoldenSetChecker(mock_evaluator, "nonexistent.json")
        result = checker.check()

        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert result["drift_count"] == 0
        assert result["total"] == 0

    def _build_all_pass_mock(self):
        """Returns a mock that matches all golden set expected outcomes."""
        from collections import defaultdict
        mock = MagicMock()
        results = {
            "golden_golden_001": EvaluationResult(
                compliant=False, score=0.4,
                violations=[{"rule_id": "rule_citation_001", "severity": "high"}],
                notes="", status="success"),
            "golden_golden_002": EvaluationResult(
                compliant=False, score=0.3,
                violations=[
                    {"rule_id": "rule_bias_001", "severity": "high"},
                    {"rule_id": "rule_harm_001", "severity": "critical"},
                ],
                notes="", status="success"),
            "golden_golden_003": EvaluationResult(
                compliant=False, score=0.2,
                violations=[{"rule_id": "rule_truth_001", "severity": "critical"}],
                notes="", status="success"),
            "golden_golden_004": EvaluationResult(
                compliant=True, score=1.0, violations=[], notes="", status="success"),
            "golden_golden_005": EvaluationResult(
                compliant=True, score=1.0, violations=[], notes="", status="success"),
            "golden_golden_006": EvaluationResult(
                compliant=False, score=0.5,
                violations=[{"rule_id": "rule_uncertainty_001", "severity": "low"}],
                notes="", status="success"),
            "golden_golden_007": EvaluationResult(
                compliant=True, score=1.0, violations=[], notes="", status="success"),
            "golden_golden_008": EvaluationResult(
                compliant=True, score=1.0, violations=[], notes="", status="success"),
        }

        def mock_eval(**kwargs):
            rid = kwargs.get("request_id", "")
            return results.get(rid, EvaluationResult(compliant=True, score=1.0, violations=[], notes="", status="success"))

        mock.evaluate.side_effect = mock_eval
        return mock

    def test_check_all_pass(self):
        """Returns pass status when all golden cases match expected."""
        golden_path = Path(__file__).parent / "golden_set.json"
        checker = GoldenSetChecker(self._build_all_pass_mock(), str(golden_path))
        result = checker.check()

        assert result["status"] == "pass"
        assert result["drift_count"] == 0
        assert result["total"] == 8
        assert result["passed"] == 8
        assert result["cases"] == []

    def test_check_drift_compliance(self):
        """Detects drift when compliant flag doesn't match expected."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            compliant=False,
            score=0.5,
            violations=[{"rule_id": "rule_truth_001", "severity": "critical"}],
            notes="",
            status="success",
        )
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check()

        assert result["status"] == "drift_detected"
        assert result["drift_count"] > 0

    def test_check_verbose_includes_pass_cases(self):
        """verbose=True includes passing cases in output."""
        golden_path = Path(__file__).parent / "golden_set.json"
        checker = GoldenSetChecker(self._build_all_pass_mock(), str(golden_path))
        result = checker.check(verbose=True)

        assert result["status"] == "pass"
        assert len(result["cases"]) == 8

    def test_check_handles_evaluation_error(self):
        """Returns drift on evaluation failure without crashing."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.side_effect = RuntimeError("API unavailable")
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check()

        assert result["drift_count"] == 8
        for case in result["cases"]:
            assert case["status"] == "error"
            assert "evaluation_error" in case["drift_reason"]

    def test_check_unexpected_violation(self):
        """Detects unexpected violation rule IDs."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            compliant=False,
            score=0.4,
            violations=[
                {"rule_id": "rule_truth_001", "severity": "critical"},
                {"rule_id": "rule_uncertainty_001", "severity": "low"},
            ],
            notes="",
            status="success",
        )
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check(verbose=True)

        golden_003 = next(c for c in result["cases"] if c["id"] == "golden_003")
        assert golden_003["drift"] is True
        assert "unexpected_violations" in golden_003["drift_reason"]

    def test_check_missing_violation(self):
        """Detects expected violation rule IDs that are missing."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            compliant=False,
            score=0.5,
            violations=[],
            notes="",
            status="success",
        )
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check(verbose=True)

        golden_001 = next(c for c in result["cases"] if c["id"] == "golden_001")
        assert golden_001["drift"] is True
        assert "missing_violations" in golden_001["drift_reason"]

    def test_check_severity_threshold(self):
        """Detects when actual severity is below expected minimum."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            compliant=False,
            score=0.3,
            violations=[{"rule_id": "rule_bias_001", "severity": "info"}],
            notes="",
            status="success",
        )
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check(verbose=True)

        golden_002 = next(c for c in result["cases"] if c["id"] == "golden_002")
        assert golden_002["drift"] is True
        assert "severity_too_low" in golden_002["drift_reason"]

    def test_check_includes_metadata(self):
        """Includes golden model and prompt version in report."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            compliant=True,
            score=1.0,
            violations=[],
            notes="",
            status="success",
        )
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check()

        assert result["interpreter_prompt_version"] == "v1"
        assert result["golden_model"] == "claude-3-5-sonnet-20260220"

    def test_case_result_structure(self):
        """Each case includes expected and actual comparisons."""
        golden_path = Path(__file__).parent / "golden_set.json"
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = EvaluationResult(
            compliant=True,
            score=1.0,
            violations=[],
            notes="",
            status="success",
        )
        checker = GoldenSetChecker(mock_evaluator, str(golden_path))
        result = checker.check(verbose=True)

        for case in result["cases"]:
            assert "id" in case
            assert "description" in case
            assert "drift" in case
            assert "drift_reason" in case
            assert "expected" in case
            assert "actual" in case
            assert "status" in case
            assert "compliant" in case["expected"]
            assert "violation_rule_ids" in case["expected"]
            assert "compliant" in case["actual"]
            assert "violation_count" in case["actual"]
            assert "status" in case["actual"]
