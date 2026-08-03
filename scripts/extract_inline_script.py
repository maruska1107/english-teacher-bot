#!/usr/bin/env python3
"""Extract a top-level literal string assignment from a Python source file."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


class InlineScriptError(ValueError):
    """Raised when an inline script cannot be extracted safely."""


def extract_literal_string(source_path: Path, variable_name: str = "SCRIPT") -> str:
    """Return a top-level string literal without importing or executing the module."""
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InlineScriptError(f"cannot read {source_path}: {exc}") from exc

    try:
        module = ast.parse(source, filename=str(source_path))
    except SyntaxError as exc:
        raise InlineScriptError(f"cannot parse {source_path}: {exc}") from exc

    matches: list[ast.expr] = []
    for statement in module.body:
        if isinstance(statement, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == variable_name for target in statement.targets):
                matches.append(statement.value)
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == variable_name
            and statement.value is not None
        ):
            matches.append(statement.value)

    if not matches:
        raise InlineScriptError(f"{variable_name} assignment not found in {source_path}")
    if len(matches) != 1:
        raise InlineScriptError(f"multiple {variable_name} assignments found in {source_path}")

    value = matches[0]
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        raise InlineScriptError(f"{variable_name} in {source_path} must be a plain string literal")
    return value.value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a top-level literal inline JavaScript assignment without importing its module."
    )
    parser.add_argument("source", type=Path, help="Python source containing the assignment")
    parser.add_argument("variable", nargs="?", default="SCRIPT", help="assignment name (default: SCRIPT)")
    args = parser.parse_args()

    try:
        script = extract_literal_string(args.source, args.variable)
    except InlineScriptError as exc:
        print(f"inline script extraction error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(script)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
