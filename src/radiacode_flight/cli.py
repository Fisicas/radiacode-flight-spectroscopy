"""Command-line entry points for the portable repository."""
from __future__ import annotations

import argparse
from pathlib import Path

from .manifest import validate_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radiacode-flight")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate a manifest and its input files")
    validate.add_argument("--manifest", required=True, type=Path)
    validate.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command == "validate":
        issues = validate_manifest(args.manifest, args.root)
        for issue in issues:
            print(f"{issue.level}: {issue.flight_key}: {issue.message}")
        errors = sum(issue.level == "ERROR" for issue in issues)
        warnings = sum(issue.level == "WARNING" for issue in issues)
        print(f"Validation complete: {errors} error(s), {warnings} warning(s)")
        return 1 if errors else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
