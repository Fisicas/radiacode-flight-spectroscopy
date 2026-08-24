#!/usr/bin/env python3
"""Run release-facing checks that do not depend on the private analysis tree."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def check_sha256_manifest(path: Path) -> list[str]:
    issues: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line.strip())
        if not match:
            continue
        expected, relative = match.groups()
        target = path.parent / relative
        if not target.is_file():
            issues.append(f"missing checksum target: {target.relative_to(REPO)}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            issues.append(f"checksum mismatch: {target.relative_to(REPO)}")
    return issues


def check_markdown_links() -> list[str]:
    issues: list[str] = []
    for markdown in sorted(REPO.rglob("*.md")):
        text = markdown.read_text(encoding="utf-8", errors="replace")
        for raw in LINK.findall(text):
            target = raw.strip().strip("<>").split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (markdown.parent / target).exists():
                issues.append(
                    f"broken Markdown path in {markdown.relative_to(REPO)}: {target}"
                )

    text = (REPO / "README.md").read_text(encoding="utf-8")
    figure_stem = "figures/presentation/figure_01_physics_cascade_to_detector"
    linked_figure = re.search(
        rf"\[!\[[^\]]*\]\({re.escape(figure_stem)}\.png\)\]"
        rf"\({re.escape(figure_stem)}\.svg\)",
        text,
    )
    if not linked_figure:
        issues.append("README Figure 01 PNG is not linked to the SVG master")
    if "**Figure 01 sources:**" not in text:
        issues.append("README Figure 01 source caption is missing")
    return issues


def main() -> int:
    issues: list[str] = []
    for required in ("LICENSE", "LICENSE-DATA.md", "THIRD_PARTY_NOTICES.md"):
        if not (REPO / required).is_file():
            issues.append(f"missing required rights file: {required}")
    for manifest in REPO.rglob("SHA256SUMS.txt"):
        issues.extend(check_sha256_manifest(manifest))
    issues.extend(check_markdown_links())

    redistributed = sorted((REPO / "data" / "raw").glob("*.kml"))
    for path in redistributed:
        issues.append(f"third-party KML present in public raw directory: {path.name}")

    stale_phrases = {
        "Reproducible measurement pipeline": "Figure 03 overstates portability",
        "GPS geometric altitude": "altitude source type is unverified",
        "intentionally deferred": "Figure 01 is now publication-facing",
        "pre-publication staging tree": "public snapshot wording is required",
    }
    public_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in [REPO / "README.md", *sorted((REPO / "docs").glob("*.md"))]
    )
    normalized_public_text = re.sub(r"\s+", " ", public_text)
    if not re.search(
        r"not\s+affiliated with or endorsed by RADIACODE LTD or FlightAware",
        public_text,
    ):
        issues.append("README independent-project trademark disclaimer is missing")
    if "LICENSE-DATA.md" not in public_text or "THIRD_PARTY_NOTICES.md" not in public_text:
        issues.append("README asset-specific licensing links are missing")
    flightaware_notice = (
        "Contains FlightAware data © FlightAware LLC 2026. FlightAware data and "
        "trademarks are excluded from the repository’s MIT and CC BY 4.0 licenses. "
        "This independent project is not affiliated with or endorsed by FlightAware."
    )
    if flightaware_notice not in normalized_public_text:
        issues.append("README FlightAware rights notice is missing or incomplete")
    for phrase, message in stale_phrases.items():
        if phrase in public_text:
            issues.append(f"stale phrase {phrase!r}: {message}")

    # Split the spelling so this repository-wide check does not flag itself.
    legacy_ui_term = "he" + "ro"
    for path in sorted(REPO.rglob("*")):
        if legacy_ui_term in path.name.lower():
            issues.append(
                f"legacy UI term remains in path: {path.relative_to(REPO)}"
            )
    searchable_suffixes = {".md", ".py", ".ipynb", ".yml", ".yaml", ".toml"}
    for path in sorted(REPO.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in searchable_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(rf"\b{legacy_ui_term}\b", text, flags=re.IGNORECASE):
            issues.append(
                f"legacy UI term remains in text: {path.relative_to(REPO)}"
            )

    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    print(
        "Repository checks passed: checksums, local Markdown links, KML policy, "
        "terminology, and release wording."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
