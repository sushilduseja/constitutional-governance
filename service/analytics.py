"""
Analytics and stats aggregation from the audit store.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from service.audit import AuditStore

logger = logging.getLogger(__name__)


class Analytics:
    """
    Analytics engine for violation patterns and compliance metrics.
    
    Queries the audit store and computes aggregate statistics.
    """

    def __init__(self, audit_store: AuditStore):
        self.audit_store = audit_store

    def get_stats(self) -> dict:
        """
        Get overall statistics.
        
        Returns:
            Dict with total, compliance rate, violation count
        """
        total = self.audit_store.count()
        compliant_count = self.audit_store.count(compliant=True)
        failed_count = self.audit_store.count(compliant=False, status="success")

        return {
            "total_evaluations": total,
            "compliance_rate": round(compliant_count / total * 100, 1) if total > 0 else 0.0,
            "active_violations": failed_count,
        }

    def get_violations_by_rule(self, limit: int = 10) -> dict:
        """
        Get violation counts grouped by rule ID.
        
        Args:
            limit: Maximum number of rules to return
            
        Returns:
            Dict mapping rule_id to violation count
        """
        records = self.audit_store.query(limit=500)
        
        rule_counts = defaultdict(int)
        for record in records:
            if record.get("compliant", True):
                continue
            violations = record.get("violations", [])
            if isinstance(violations, list):
                for v in violations:
                    rule_id = v.get("rule_id", "unknown")
                    rule_counts[rule_id] += 1

        sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_rules[:limit])

    def get_violations_by_severity(self) -> dict:
        """
        Get violation counts grouped by severity.
        
        Returns:
            Dict mapping severity to count
        """
        records = self.audit_store.query(limit=500)
        
        severity_counts = defaultdict(int)
        for record in records:
            if record.get("compliant", True):
                continue
            violations = record.get("violations", [])
            if isinstance(violations, list):
                for v in violations:
                    severity = v.get("severity", "unknown")
                    severity_counts[severity] += 1

        return dict(severity_counts)

    def get_compliance_trend(self, days: int = 7) -> list[dict]:
        """
        Get daily compliance rate for the past N days.
        
        Args:
            days: Number of days to include
            
        Returns:
            List of dicts with date, total, compliant, rate
        """
        records = self.audit_store.query(limit=1000)
        
        daily_stats = defaultdict(lambda: {"total": 0, "compliant": 0})
        
        for record in records:
            timestamp = record.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                date = dt.date().isoformat()
            except (ValueError, TypeError):
                date = "unknown"
            
            daily_stats[date]["total"] += 1
            if record.get("compliant", True):
                daily_stats[date]["compliant"] += 1
        
        trend = []
        for date in sorted(daily_stats.keys()):
            stats = daily_stats[date]
            rate = round(stats["compliant"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0
            trend.append({
                "date": date,
                "total": stats["total"],
                "compliant": stats["compliant"],
                "rate": rate,
            })
        
        return trend[-days:]

    def get_violations_by_model(self) -> dict:
        """
        Get violation counts grouped by model name.
        
        Returns:
            Dict mapping model_name to violation count
        """
        records = self.audit_store.query(limit=500)
        
        model_counts = defaultdict(lambda: {"total": 0, "violations": 0})
        for record in records:
            model = record.get("model_name", "unknown")
            model_counts[model]["total"] += 1
            if not record.get("compliant", True):
                violations = record.get("violations", [])
                model_counts[model]["violations"] += len(violations) if isinstance(violations, list) else 0

        result = {}
        for model, stats in model_counts.items():
            rate = round(stats["violations"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0
            result[model] = {
                "total": stats["total"],
                "violations": stats["violations"],
                "violation_rate": rate,
            }
        
        return result

    def get_failure_stats(self) -> dict:
        """
        Get statistics about evaluation failures.
        
        Returns:
            Dict with failure counts by type
        """
        total = self.audit_store.count()
        failed = self.audit_store.count(status="failed")
        skipped = self.audit_store.count(status="skipped")
        
        records = self.audit_store.query(status="failed", limit=100)
        failure_reasons = defaultdict(int)
        for record in records:
            reason = record.get("failure_reason", "unknown")
            if len(reason) > 50:
                reason = reason[:50] + "..."
            failure_reasons[reason] += 1

        return {
            "total_failures": failed,
            "total_skipped": skipped,
            "failure_rate": round(failed / total * 100, 1) if total > 0 else 0.0,
            "skip_rate": round(skipped / total * 100, 1) if total > 0 else 0.0,
            "top_failure_reasons": dict(sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:5]),
        }

    def get_full_report(self) -> dict:
        """
        Get a comprehensive analytics report.
        
        Returns:
            Dict with all analytics
        """
        return {
            "stats": self.get_stats(),
            "violations_by_rule": self.get_violations_by_rule(),
            "violations_by_severity": self.get_violations_by_severity(),
            "compliance_trend": self.get_compliance_trend(),
            "violations_by_model": self.get_violations_by_model(),
            "failure_stats": self.get_failure_stats(),
        }


class GoldenSetChecker:
    """
    Consistency checker for the golden test set.

    Re-evaluates each golden test case against the current constitution
    and interpreter prompt, then compares actual results to expected.
    Alerts when the interpreter drifts from known correct behavior.
    """

    def __init__(self, evaluator, golden_set_path: str = "tests/golden_set.json"):
        self.evaluator = evaluator
        self.golden_set_path = golden_set_path

    def check(self, verbose: bool = False) -> dict:
        """
        Run the golden set consistency check.

        Args:
            verbose: Include per-case details even when passing.

        Returns:
            Dict with overall pass/fail, drift count, and per-case results.
        """
        import json
        from pathlib import Path

        path = Path(self.golden_set_path)
        if not path.exists():
            return {
                "status": "error",
                "message": f"Golden set not found at {self.golden_set_path}",
                "drift_count": 0,
                "total": 0,
                "cases": [],
            }

        with open(path, encoding="utf-8") as f:
            golden = json.load(f)

        cases = golden.get("test_cases", [])
        results = []
        drift_count = 0

        for tc in cases:
            result = self._evaluate_case(tc)
            results.append(result)
            if result["drift"]:
                drift_count += 1

        total = len(cases)
        passed = total - drift_count

        report = {
            "status": "pass" if drift_count == 0 else "drift_detected",
            "message": f"{passed}/{total} cases matched expected behavior" if drift_count == 0 else f"{drift_count}/{total} cases drifted from expected behavior",
            "total": total,
            "passed": passed,
            "drift_count": drift_count,
            "interpreter_prompt_version": golden.get("interpreter_prompt_version"),
            "golden_model": golden.get("model"),
            "cases": results,
        }

        if not verbose:
            report["cases"] = [r for r in results if r["drift"]]

        return report

    def _evaluate_case(self, tc: dict) -> dict:
        """
        Evaluate a single golden test case and compare to expected.
        """
        tc_id = tc.get("id", "unknown")
        description = tc.get("description", "")
        user_prompt = tc.get("user_prompt", "")
        llm_response = tc.get("llm_response", "")
        expected = tc.get("expected", {})

        try:
            eval_result = self.evaluator.evaluate(
                user_prompt=user_prompt,
                llm_response=llm_response,
                model_provider="golden_set",
                model_name="consistency_check",
                request_id=f"golden_{tc_id}",
            )
        except Exception as e:
            return {
                "id": tc_id,
                "description": description,
                "drift": True,
                "drift_reason": f"evaluation_error: {e}",
                "expected": expected,
                "actual": None,
                "status": "error",
            }

        actual_compliant = eval_result.compliant
        actual_violations = eval_result.violations or []
        actual_rule_ids = {v.get("rule_id") for v in actual_violations}
        expected_rule_ids = set(expected.get("violation_rule_ids", []))
        expected_compliant = expected.get("compliant", True)

        drift = False
        drift_reasons = []

        if actual_compliant != expected_compliant:
            drift = True
            drift_reasons.append(
                f"compliant={actual_compliant}, expected={expected_compliant}"
            )

        unexpected = actual_rule_ids - expected_rule_ids
        missing = expected_rule_ids - actual_rule_ids
        if unexpected:
            drift = True
            drift_reasons.append(f"unexpected_violations: {sorted(unexpected)}")
        if missing:
            drift = True
            drift_reasons.append(f"missing_violations: {sorted(missing)}")

        severity_min = expected.get("severity_min")
        if severity_min and actual_violations:
            severity_order = ["info", "low", "medium", "high", "critical"]
            try:
                actual_min_idx = min(
                    severity_order.index(v.get("severity", "info"))
                    for v in actual_violations
                    if v.get("severity", "info") in severity_order
                )
                expected_idx = severity_order.index(severity_min)
                if actual_min_idx < expected_idx:
                    drift = True
                    drift_reasons.append(
                        f"severity_too_low: got {actual_violations[0].get('severity')}, expected {severity_min}+"
                    )
            except ValueError:
                pass

        notes_contains = expected.get("notes_contains")
        if notes_contains and not llm_response.strip():
            pass
        elif notes_contains and notes_contains.lower() not in (eval_result.notes or "").lower():
            if not drift:
                drift = True
                drift_reasons.append(f"notes_missing: expected '{notes_contains}'")

        return {
            "id": tc_id,
            "description": description,
            "drift": drift,
            "drift_reason": "; ".join(drift_reasons) if drift_reasons else "",
            "expected": {
                "compliant": expected_compliant,
                "violation_rule_ids": sorted(expected_rule_ids),
                "severity_min": severity_min,
            },
            "actual": {
                "compliant": actual_compliant,
                "score": eval_result.score,
                "violation_rule_ids": sorted(actual_rule_ids),
                "violation_count": len(actual_violations),
                "status": eval_result.status,
                "notes": eval_result.notes,
            },
            "status": "drift" if drift else "ok",
        }
