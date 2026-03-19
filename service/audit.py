"""
SQLite Audit Log Store.

Append-only audit log for constitutional AI evaluations.
No UPDATE or DELETE operations — immutable by design.
"""

import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_RESPONSE_LENGTH = 64 * 1024
AUDIT_WRITE_RETRIES = 3
AUDIT_WRITE_RETRY_DELAY = 0.5


class AuditWriteError(Exception):
    """Raised when the audit log fails to write after all retries."""


@dataclass
class EvaluationRecord:
    """An evaluation audit record."""
    id: str
    timestamp: str
    request_id: str
    model_provider: str
    model_name: str
    constitution_version: str
    user_prompt: Optional[str]
    llm_response: str
    compliant: bool
    score: float
    violations: list
    notes: Optional[str]
    truncated: bool
    status: str
    failure_reason: Optional[str]
    latency_ms: int
    interpreter_model: str


class AuditStore:
    """
    Append-only SQLite audit log for evaluations.
    
    Design:
    - Append-only: No UPDATE or DELETE operations
    - Thread-safe: Uses connection per thread
    - Idempotent: Uses INSERT OR REPLACE for crash recovery
    - No PII: Stores only evaluation metadata
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS evaluations (
        id              TEXT PRIMARY KEY,
        timestamp       TEXT NOT NULL,
        request_id      TEXT NOT NULL,
        model_provider  TEXT NOT NULL,
        model_name      TEXT NOT NULL,
        constitution_version TEXT NOT NULL,
        user_prompt     TEXT,
        llm_response   TEXT NOT NULL,
        compliant       INTEGER NOT NULL,
        score           REAL NOT NULL,
        violations      TEXT NOT NULL,
        notes           TEXT,
        truncated       INTEGER NOT NULL,
        status          TEXT NOT NULL,
        failure_reason  TEXT,
        latency_ms      INTEGER NOT NULL,
        interpreter_model TEXT NOT NULL,
        interpreter_prompt_version TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_evaluations_timestamp ON evaluations(timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_evaluations_compliant ON evaluations(compliant);
    CREATE INDEX IF NOT EXISTS idx_evaluations_status ON evaluations(status);
    """

    def __init__(self, db_path: str = "audit.db"):
        self.db_path = Path(db_path)
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                timeout=5.0,
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._init_schema(self._local.conn)
        return self._local.conn

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(self.SCHEMA)
        conn.commit()

    def _generate_id(self) -> str:
        """Generate unique evaluation ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        uid = uuid.uuid4().hex[:8]
        return f"eval_{ts}_{uid}"

    def write(
        self,
        request_id: str,
        model_provider: str,
        model_name: str,
        constitution_version: str,
        user_prompt: Optional[str],
        llm_response: str,
        compliant: bool,
        score: float,
        violations: list,
        notes: Optional[str],
        truncated: bool,
        status: str,
        failure_reason: Optional[str],
        latency_ms: int,
        interpreter_model: str,
        interpreter_prompt_version: Optional[str] = None,
    ) -> str:
        """
        Write an evaluation record to the audit log.
        
        Returns the evaluation ID.
        """
        evaluation_id = self._generate_id()
        timestamp = datetime.now(timezone.utc).isoformat()

        response_truncated = llm_response[:MAX_RESPONSE_LENGTH]
        if len(llm_response) > MAX_RESPONSE_LENGTH:
            logger.warning(f"LLM response truncated from {len(llm_response)} to {MAX_RESPONSE_LENGTH} chars")

        violations_json = json.dumps(violations, ensure_ascii=False)

        conn = self._get_connection()
        last_error: Optional[Exception] = None

        for attempt in range(AUDIT_WRITE_RETRIES):
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO evaluations (
                        id, timestamp, request_id, model_provider, model_name,
                        constitution_version, user_prompt, llm_response,
                        compliant, score, violations, notes, truncated,
                        status, failure_reason, latency_ms,
                        interpreter_model, interpreter_prompt_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evaluation_id,
                        timestamp,
                        request_id,
                        model_provider,
                        model_name,
                        constitution_version,
                        user_prompt,
                        response_truncated,
                        int(compliant),
                        score,
                        violations_json,
                        notes,
                        int(truncated),
                        status,
                        failure_reason,
                        latency_ms,
                        interpreter_model,
                        interpreter_prompt_version,
                    ),
                )
                conn.commit()
                logger.info(
                    f"Audit: wrote {evaluation_id} "
                    f"status={status} compliant={compliant} violations={len(violations)}"
                )
                return evaluation_id

            except sqlite3.OperationalError as e:
                last_error = e
                if "locked" in str(e).lower() and attempt < AUDIT_WRITE_RETRIES - 1:
                    delay = AUDIT_WRITE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"DB locked, retrying in {delay:.1f}s (attempt {attempt + 1}/{AUDIT_WRITE_RETRIES})")
                    time.sleep(delay)
                else:
                    logger.critical(f"AUDIT FAILURE: {evaluation_id} lost after {attempt + 1} attempts — {e}")
                    raise AuditWriteError(f"Failed to write audit record after {attempt + 1} attempts: {e}") from last_error

            except Exception as e:
                last_error = e
                if attempt < AUDIT_WRITE_RETRIES - 1:
                    delay = AUDIT_WRITE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Audit write failed, retrying in {delay:.1f}s (attempt {attempt + 1}/{AUDIT_WRITE_RETRIES}): {e}")
                    time.sleep(delay)
                else:
                    logger.critical(f"AUDIT FAILURE: {evaluation_id} lost after {AUDIT_WRITE_RETRIES} attempts — {e}")
                    raise AuditWriteError(f"Failed to write audit record after {AUDIT_WRITE_RETRIES} attempts: {e}") from last_error

        raise AuditWriteError(f"Audit write failed: unhandled error path")

    def query(
        self,
        limit: int = 50,
        offset: int = 0,
        compliant: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """
        Query evaluation records.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            compliant: Filter by compliance status
            status: Filter by status (success, failed, skipped)
        
        Returns:
            List of evaluation records as dicts
        """
        conn = self._get_connection()

        query = "SELECT * FROM evaluations WHERE 1=1"
        params = []

        if compliant is not None:
            query += " AND compliant = ?"
            params.append(int(compliant))

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            record = dict(row)
            record["compliant"] = bool(record["compliant"])
            record["truncated"] = bool(record["truncated"])
            if record.get("violations"):
                try:
                    record["violations"] = json.loads(record["violations"])
                except json.JSONDecodeError:
                    record["violations"] = []
            results.append(record)

        return results

    def count(
        self,
        compliant: Optional[bool] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        Count evaluation records.
        
        Args:
            compliant: Filter by compliance status
            status: Filter by status
        
        Returns:
            Number of matching records
        """
        conn = self._get_connection()

        query = "SELECT COUNT(*) FROM evaluations WHERE 1=1"
        params = []

        if compliant is not None:
            query += " AND compliant = ?"
            params.append(int(compliant))

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        row = conn.execute(query, params).fetchone()
        return row[0] if row else 0

    def get_stats(self) -> dict:
        """
        Get aggregate statistics.
        
        Returns:
            Dict with total, compliant count, violation count, etc.
        """
        total = self.count()
        compliant_count = self.count(compliant=True)
        failed_count = self.count(compliant=False, status="success")

        return {
            "total_evaluations": total,
            "compliance_rate": round(compliant_count / total * 100, 1) if total > 0 else 0.0,
            "active_violations": failed_count,
        }
