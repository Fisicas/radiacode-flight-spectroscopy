"""Check the featured animation for GIF compositing and map continuity issues."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FEATURED_ANIMATION = ROOT / "animations" / "previews" / "ATL-OMA_dashboard_preview.gif"
EXPECTED_SIZE = (1400, 734)
MIN_MAP_NONWHITE_PIXELS = 7000


def main() -> int:
    errors: list[str] = []
    with Image.open(FEATURED_ANIMATION) as image:
        if image.size != EXPECTED_SIZE:
            errors.append(f"featured-animation size {image.size} != expected {EXPECTED_SIZE}")
        if getattr(image, "n_frames", 1) < 40:
            errors.append(
                f"featured animation has too few frames: {getattr(image, 'n_frames', 1)}"
            )
        if image.info.get("transparency") is not None:
            errors.append("featured animation contains a transparency index")

        map_counts: list[int] = []
        map_box = (0, round(image.height * 350 / 734), round(image.width * 444 / 1400), image.height)
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            frame = image.convert("RGB").crop(map_box)
            nonwhite = sum(1 for pixel in frame.get_flattened_data() if min(pixel) < 225)
            map_counts.append(nonwhite)

    if map_counts and min(map_counts) < MIN_MAP_NONWHITE_PIXELS:
        errors.append(
            f"map continuity failed: minimum non-white pixels={min(map_counts)} "
            f"(< {MIN_MAP_NONWHITE_PIXELS})"
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        f"Featured-animation check passed: {len(map_counts)} frames; "
        f"map non-white pixels={min(map_counts)}..{max(map_counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
