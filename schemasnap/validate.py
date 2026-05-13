"""Schema validation: check a snapshot against a set of rules."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationRule:
    table_pattern: str          # fnmatch-style pattern, e.g. "users" or "*"
    required_columns: List[str] = field(default_factory=list)
    forbidden_columns: List[str] = field(default_factory=list)
    min_column_count: Optional[int] = None
    max_column_count: Optional[int] = None


@dataclass
class ValidationViolation:
    table: str
    rule_index: int
    message: str


@dataclass
class ValidationReport:
    snapshot_file: str
    violations: List[ValidationViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def summary(self) -> str:
        if self.passed:
            return f"OK  {self.snapshot_file} — all rules passed"
        lines = [f"FAIL {self.snapshot_file} — {len(self.violations)} violation(s)"]
        for v in self.violations:
            lines.append(f"  [{v.table}] rule#{v.rule_index}: {v.message}")
        return "\n".join(lines)


def load_rules(rules_path: str | Path) -> List[ValidationRule]:
    """Load validation rules from a JSON file."""
    data: List[Dict[str, Any]] = json.loads(Path(rules_path).read_text())
    rules = []
    for item in data:
        rules.append(ValidationRule(
            table_pattern=item["table_pattern"],
            required_columns=item.get("required_columns", []),
            forbidden_columns=item.get("forbidden_columns", []),
            min_column_count=item.get("min_column_count"),
            max_column_count=item.get("max_column_count"),
        ))
    return rules


def _matches(table: str, pattern: str) -> bool:
    import fnmatch
    return fnmatch.fnmatch(table, pattern)


def validate_snapshot(
    snapshot: Dict[str, Any],
    rules: List[ValidationRule],
) -> List[ValidationViolation]:
    """Return violations found in *snapshot* against *rules*."""
    schema: Dict[str, Any] = snapshot.get("schema", {})
    violations: List[ValidationViolation] = []

    for idx, rule in enumerate(rules):
        for table, cols in schema.items():
            if not _matches(table, rule.table_pattern):
                continue
            col_names = list(cols.keys()) if isinstance(cols, dict) else []
            for req in rule.required_columns:
                if req not in col_names:
                    violations.append(ValidationViolation(table, idx,
                        f"required column '{req}' is missing"))
            for forb in rule.forbidden_columns:
                if forb in col_names:
                    violations.append(ValidationViolation(table, idx,
                        f"forbidden column '{forb}' is present"))
            if rule.min_column_count is not None and len(col_names) < rule.min_column_count:
                violations.append(ValidationViolation(table, idx,
                    f"column count {len(col_names)} < min {rule.min_column_count}"))
            if rule.max_column_count is not None and len(col_names) > rule.max_column_count:
                violations.append(ValidationViolation(table, idx,
                    f"column count {len(col_names)} > max {rule.max_column_count}"))
    return violations


def validate_snapshot_file(
    snapshot_path: str | Path,
    rules: List[ValidationRule],
) -> ValidationReport:
    """Load a snapshot file and validate it, returning a ValidationReport."""
    p = Path(snapshot_path)
    snapshot = json.loads(p.read_text())
    violations = validate_snapshot(snapshot, rules)
    return ValidationReport(snapshot_file=str(p), violations=violations)
