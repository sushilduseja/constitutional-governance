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
