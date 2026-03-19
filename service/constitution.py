"""
Constitution Store.

Loads and caches constitution rules from JSON files.
Supports hot-reload and version tracking.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"id", "text", "severity", "enabled"}
VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}


class ConstitutionStore:
    """
    Loads and caches constitution rules.
    
    Design:
    - In-memory cache after first load
    - Hot-reload via explicit reload() call
    - Schema validation on load
    - Graceful degradation on errors
    """

    def __init__(self, constitution_path: str = "constitution/rules/default_v1.json"):
        self.constitution_path = Path(constitution_path)
        self._constitution: Optional[dict] = None
        self._version: str = "unknown"
        self._load()

    def _load(self) -> None:
        """Load constitution from JSON file."""
        try:
            if not self.constitution_path.exists():
                logger.warning(f"Constitution file not found: {self.constitution_path}")
                self._constitution = {"version": "unknown", "rules": []}
                self._version = "unknown"
                return

            with open(self.constitution_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.error("Constitution must be a JSON object")
                self._constitution = {"version": "error", "rules": []}
                self._version = "error"
                return

            rules = data.get("rules", [])
            if not isinstance(rules, list):
                logger.error("Constitution 'rules' must be a list")
                self._constitution = {"version": "error", "rules": []}
                self._version = "error"
                return

            valid_rules = []
            for i, rule in enumerate(rules):
                validated_rule = self._validate_rule(rule, i)
                if validated_rule:
                    valid_rules.append(validated_rule)
                else:
                    logger.warning(f"Skipping invalid rule at index {i}")

            self._constitution = {
                "version": data.get("version", "unknown"),
                "rules": valid_rules,
                "metadata": data.get("metadata", {}),
            }
            self._version = self._constitution["version"]

            logger.info(
                f"Loaded constitution v{self._version} "
                f"with {len(valid_rules)} rules"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in constitution: {e}")
            self._constitution = {"version": "error", "rules": []}
            self._version = "error"

        except Exception as e:
            logger.error(f"Failed to load constitution: {e}")
            self._constitution = {"version": "error", "rules": []}
            self._version = "error"

    def _validate_rule(self, rule: dict, index: int) -> Optional[dict]:
        """Validate a single rule."""
        if not isinstance(rule, dict):
            logger.warning(f"Rule at index {index} is not a dict")
            return None

        missing = REQUIRED_FIELDS - set(rule.keys())
        if missing:
            logger.warning(f"Rule at index {index} missing fields: {missing}")
            return None

        severity = rule.get("severity", "").lower()
        if severity not in VALID_SEVERITIES:
            logger.warning(
                f"Rule {rule.get('id')} has invalid severity: {severity}. "
                f"Valid: {VALID_SEVERITIES}"
            )
            return None

        return {
            "id": str(rule["id"]),
            "text": str(rule["text"]),
            "severity": severity,
            "enabled": bool(rule.get("enabled", True)),
            "tags": rule.get("tags", []),
            "created_at": rule.get("created_at"),
            "updated_at": rule.get("updated_at"),
        }

    def reload(self) -> None:
        """Hot-reload constitution from disk."""
        logger.info("Reloading constitution...")
        self._load()

    def get_rules(self, enabled_only: bool = True) -> list[dict]:
        """
        Get constitution rules.
        
        Args:
            enabled_only: If True, return only enabled rules
        
        Returns:
            List of rule dictionaries
        """
        if self._constitution is None:
            return []

        rules = self._constitution.get("rules", [])
        if enabled_only:
            rules = [r for r in rules if r.get("enabled", True)]

        return rules

    def get_version(self) -> str:
        """Get constitution version string."""
        return self._version

    def get_metadata(self) -> dict:
        """Get constitution metadata."""
        if self._constitution is None:
            return {}
        return self._constitution.get("metadata", {})

    def get_formatted_rules(self) -> str:
        """
        Get rules formatted for the interpreter prompt.
        
        Returns:
            Numbered list of rules as a string
        """
        rules = self.get_rules(enabled_only=True)
        if not rules:
            return ""

        formatted = []
        for i, rule in enumerate(rules, 1):
            severity = rule.get("severity", "info").upper()
            text = rule.get("text", "")
            formatted.append(f"{i}. [{severity}] {text}")

        return "\n".join(formatted)

    def to_dict(self) -> dict:
        """Get full constitution as a dictionary."""
        if self._constitution is None:
            return {"version": "unknown", "rules": []}
        return self._constitution.copy()

    def get_interpreter_prompt(self, version: str = "v1") -> str:
        """
        Load interpreter prompt from file.
        
        Args:
            version: Prompt version (e.g., 'v1', 'v2'). Maps to
                     constitution/interpreter_prompts/{version}.md
        
        Returns:
            The prompt text (stripped of markdown header), or empty string if file not found.
        """
        base_dir = self.constitution_path.parent.parent
        prompt_path = base_dir / "interpreter_prompts" / f"{version}.md"
        
        try:
            if not prompt_path.exists():
                logger.warning(f"Interpreter prompt not found: {prompt_path}")
                return ""
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self._strip_prompt_header(content)
        except Exception as e:
            logger.error(f"Failed to load interpreter prompt: {e}")
            return ""

    def _strip_prompt_header(self, content: str) -> str:
        """Strip markdown header (lines starting with # or >) before the prompt body."""
        lines = content.split("\n")
        body_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("SYSTEM:") or stripped.startswith("{"):
                body_start = i
                break
        return "\n".join(lines[body_start:]).strip()

    def get_interpreter_prompt_version(self) -> str:
        """
        Get the interpreter prompt version that corresponds to the constitution version.
        
        MVP: Uses constitution version to derive prompt version.
        e.g., constitution v1.0.0 → prompt v1.md
        """
        ver = self._version
        if ver == "unknown" or ver == "error":
            return "v1"
        major = ver.split(".")[0] if "." in ver else ver
        return f"v{major}"
