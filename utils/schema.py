"""Utilities for JSON schema assertions used by the test suite.

Provides a single helper `assert_json_schema(instance, schema)` which raises
AssertionError when validation fails. Uses the `jsonschema` library.
"""
from typing import Any

try:
    from jsonschema import Draft7Validator
except Exception:  # pragma: no cover - handled at runtime when package missing
    Draft7Validator = None


def assert_json_schema(instance: Any, schema: dict) -> bool:
    """Validate `instance` against `schema` (JSON Schema). Raise AssertionError on failure.

    Returns True when validation passes.
    """
    if Draft7Validator is None:
        raise AssertionError(
            "jsonschema library is required for assert_json_schema; install 'jsonschema'"
        )

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        parts = []
        for e in errors:
            path = ".".join(str(p) for p in e.path) if e.path else "<root>"
            parts.append(f"{path}: {e.message}")
        msg = "JSON schema validation errors: " + "; ".join(parts)
        raise AssertionError(msg)
    return True
