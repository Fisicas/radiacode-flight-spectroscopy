"""Manifest loading and lightweight input validation.

This module deliberately validates the file contract without importing the
plotting stack. It is suitable for a dry run before the heavier analysis.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_COLUMNS = {
    "flight_key",
    "route",
    "detector_file",
    "track_file",
    "calibration_manifest_id",
    "analysis_config_version",
}


@dataclass(frozen=True)
class Issue:
    level: str
    flight_key: str
    message: str


def load_manifest(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"manifest missing required columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("manifest contains no flight rows")
    keys = [row.get("flight_key", "").strip() for row in rows]
    if any(not key for key in keys):
        raise ValueError("every manifest row needs a flight_key")
    if len(set(keys)) != len(keys):
        raise ValueError("flight_key values must be unique")
    return rows


def _resolve(value: str, root: Path) -> Path:
    candidate = Path(value.strip())
    return candidate if candidate.is_absolute() else (root / candidate).resolve()


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _epoch_ms(value: object) -> datetime:
    return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)


def _parse_kml(path: Path) -> tuple[datetime, datetime, int, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    whens = re.findall(r"<when>\s*(.*?)\s*</when>", text)
    coords = re.findall(r"<gx:coord>\s*(.*?)\s*</gx:coord>", text)
    if len(whens) != len(coords):
        raise ValueError(f"{len(whens)} <when> values but {len(coords)} <gx:coord> values")
    parsed = []
    for raw in whens:
        value = raw.strip().replace("Z", "+00:00")
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None:
            raise ValueError("KML timestamp has no UTC offset")
        parsed.append(stamp.astimezone(timezone.utc))
    if len(parsed) < 2:
        raise ValueError("KML track needs at least two points")
    warnings = []
    if parsed != sorted(parsed):
        warnings.append("KML timestamps are not sorted")
    if len(set(parsed)) != len(parsed):
        warnings.append("KML timestamps contain duplicates")
    for coord in coords:
        parts = coord.split()
        if len(parts) != 3:
            raise ValueError(f"invalid gx:coord: {coord!r}")
        lon, lat, alt = (float(part) for part in parts)
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(f"implausible coordinate: {coord!r}")
        if not (-1000 <= alt <= 100000):
            raise ValueError(f"implausible altitude in coordinate: {coord!r}")
    return min(parsed), max(parsed), len(parsed), warnings


def _parse_rcspg(path: Path) -> tuple[datetime, datetime, int, list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    spectra = payload.get("spectrums")
    if not isinstance(spectra, list) or not spectra:
        raise ValueError("spectrums must be a non-empty list")
    channel_count = int(payload.get("channelCount", 0))
    if channel_count <= 0:
        raise ValueError("channelCount must be positive")
    timestamps = []
    warnings = []
    for index, record in enumerate(spectra):
        if "timestamp" not in record:
            raise ValueError(f"spectrum {index} has no timestamp")
        timestamps.append(_epoch_ms(record["timestamp"]))
        live = float(record.get("collectTime", 0))
        if live <= 0:
            raise ValueError(f"spectrum {index} has non-positive collectTime")
        pulses = record.get("pulses", [])
        if len(pulses) > channel_count:
            raise ValueError(f"spectrum {index} has more pulse bins than channelCount")
    if timestamps != sorted(timestamps):
        warnings.append("detector timestamps are not sorted")
    if len(set(timestamps)) != len(timestamps):
        warnings.append("detector timestamps contain duplicates")
    return min(timestamps), max(timestamps), channel_count, warnings


def validate_manifest(manifest_path: str | Path, root: str | Path | None = None) -> list[Issue]:
    manifest_path = Path(manifest_path).resolve()
    root_path = Path(root).resolve() if root else manifest_path.parent.parent.resolve()
    rows = load_manifest(manifest_path)
    issues: list[Issue] = []
    for row in rows:
        key = row["flight_key"].strip()
        detector = _resolve(row["detector_file"], root_path)
        track_value = row.get("track_file", "").strip()
        track = _resolve(track_value, root_path) if track_value else None
        if not detector.is_file():
            issues.append(Issue("ERROR", key, f"missing detector file: {detector}"))
            continue
        if track is not None and not track.is_file():
            issues.append(Issue("ERROR", key, f"missing track file: {track}"))
            continue
        expected_detector = row.get("detector_sha256", "").strip()
        if expected_detector and expected_detector.lower() != sha256(detector):
            issues.append(Issue("ERROR", key, "detector SHA-256 does not match manifest"))
        expected_track = row.get("track_sha256", "").strip()
        if track is not None and expected_track and expected_track.lower() != sha256(track):
            issues.append(Issue("ERROR", key, "track SHA-256 does not match manifest"))
        try:
            detector_start, detector_end, channel_count, warnings = _parse_rcspg(detector)
            track_warnings: list[str] = []
            if track is None:
                issues.append(
                    Issue(
                        "WARNING",
                        key,
                        "track file omitted from this snapshot; obtain a permitted local copy to validate UTC overlap",
                    )
                )
            else:
                track_start, track_end, _, track_warnings = _parse_kml(track)
                if detector_end < track_start or track_end < detector_start:
                    issues.append(Issue("ERROR", key, "detector and KML timestamps do not overlap"))
            if channel_count != 1024:
                issues.append(Issue("WARNING", key, f"channelCount={channel_count}; current production layout is 1024"))
            for warning in warnings + track_warnings:
                issues.append(Issue("WARNING", key, warning))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            issues.append(Issue("ERROR", key, f"input parse/QA failure: {exc}"))
    return issues
