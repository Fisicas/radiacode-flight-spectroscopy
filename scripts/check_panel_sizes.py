"""Verify synchronized panel dimensions and animation frame counts."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PANEL_ROOT = ROOT / "animations" / "panels"
PANEL_NAMES = ("spectrum_route", "spectrograms_overflow", "diagnostics")


def gif_size_frames_duration(path: Path) -> tuple[tuple[int, int], int, int | None]:
    with Image.open(path) as image:
        image.seek(0)
        return image.size, getattr(image, "n_frames", 1), image.info.get("duration")


def main() -> int:
    errors: list[str] = []
    route_summaries: list[str] = []
    route_heights: set[int] = set()

    for route_dir in sorted(path for path in PANEL_ROOT.iterdir() if path.is_dir()):
        panel_sizes: dict[str, tuple[int, int]] = {}
        panel_frames: dict[str, int] = {}
        panel_durations: dict[str, int | None] = {}
        present_gifs = 0
        missing_gifs = 0

        for panel_name in PANEL_NAMES:
            gif_path = route_dir / f"{panel_name}.gif"
            frame_path = route_dir / f"{panel_name}_frame.png"
            if not frame_path.exists():
                errors.append(f"{route_dir.name}: missing {panel_name} PNG fallback")
                continue

            with Image.open(frame_path) as frame_image:
                frame_size = frame_image.size

            panel_sizes[panel_name] = frame_size
            if gif_path.exists():
                present_gifs += 1
                gif_size, frame_count, duration_ms = gif_size_frames_duration(gif_path)
                if gif_size != frame_size:
                    errors.append(
                        f"{route_dir.name}/{panel_name}: GIF {gif_size} != PNG {frame_size}"
                    )
                panel_frames[panel_name] = frame_count
                panel_durations[panel_name] = duration_ms
            else:
                missing_gifs += 1

        if len(panel_sizes) != len(PANEL_NAMES):
            continue
        if present_gifs and missing_gifs:
            errors.append(f"{route_dir.name}: only some release GIFs are present")

        heights = {height for _, height in panel_sizes.values()}
        route_heights.update(heights)
        if len(heights) != 1:
            errors.append(f"{route_dir.name}: panel heights differ: {panel_sizes}")

        size_text = ", ".join(
            f"{name}={panel_sizes[name][0]}x{panel_sizes[name][1]}"
            for name in PANEL_NAMES
        )
        if panel_frames:
            frame_counts = set(panel_frames.values())
            if len(frame_counts) != 1:
                errors.append(
                    f"{route_dir.name}: panel frame counts differ: {panel_frames}"
                )

            durations = set(panel_durations.values())
            if len(durations) != 1:
                errors.append(
                    f"{route_dir.name}: panel frame durations differ: {panel_durations}"
                )
            route_summaries.append(
                f"{route_dir.name}: {size_text}; frames={next(iter(frame_counts))}; "
                f"duration_ms={next(iter(durations))}"
            )
        else:
            route_summaries.append(
                f"{route_dir.name}: {size_text}; release GIFs not in main tree"
            )

    if len(route_heights) != 1:
        errors.append(f"panel heights differ across routes: {sorted(route_heights)}")

    metadata_path = PANEL_ROOT / "panel_animation_metadata.json"
    if metadata_path.exists() and route_heights:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected_height = metadata.get("panel_height_px")
        actual_height = next(iter(route_heights))
        if expected_height is not None and expected_height != actual_height:
            errors.append(
                f"metadata panel_height_px={expected_height} != actual {actual_height}"
            )
        expected_frame_count = metadata.get("frame_count")
        expected_duration_ms = metadata.get("frame_duration_ms")
        actual_frame_counts: set[int] = set()
        actual_durations: set[int | None] = set()
        for route_dir in sorted(path for path in PANEL_ROOT.iterdir() if path.is_dir()):
            reference_gif = route_dir / f"{PANEL_NAMES[0]}.gif"
            if reference_gif.exists():
                _, frame_count, duration_ms = gif_size_frames_duration(reference_gif)
                actual_frame_counts.add(frame_count)
                actual_durations.add(duration_ms)
        if expected_frame_count is not None and actual_frame_counts and actual_frame_counts != {expected_frame_count}:
            errors.append(
                f"metadata frame_count={expected_frame_count} != actual {sorted(actual_frame_counts)}"
            )
        if expected_duration_ms is not None and actual_durations and actual_durations != {expected_duration_ms}:
            errors.append(
                f"metadata frame_duration_ms={expected_duration_ms} != actual {sorted(actual_durations)}"
            )

    for summary in route_summaries:
        print(summary)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Panel size check passed: all three synchronized panels share the same height.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
