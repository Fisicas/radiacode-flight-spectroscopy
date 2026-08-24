"""Build the GitHub landing-page featured animation from synchronized panel GIFs.

The featured animation is rendered from the ATL-to-OMA panel GIFs. Those source GIFs are
prepared as Release assets rather than committed to the main repository, so a
local rebuild can pass their bundle with ``--source-root``. The script samples
a shorter loop, resizes the three panels together, and quantizes the result for
fast inline GitHub playback.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
PANEL_NAMES = ("spectrum_route", "spectrograms_overflow", "diagnostics")


def _rooted(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _sample_indices(frame_count: int, target_count: int) -> list[int]:
    if target_count < 1:
        raise ValueError("target frame count must be positive")
    if frame_count < 1:
        raise ValueError("source animation contains no frames")
    if target_count == 1:
        return [0]
    return [round(i * (frame_count - 1) / (target_count - 1)) for i in range(target_count)]


def _read_panel_metadata(panel_paths: list[Path]) -> tuple[int, int, int, list[tuple[int, int]]]:
    frame_count: int | None = None
    duration_ms: int | None = None
    source_size: tuple[int, int] | None = None
    sizes: list[tuple[int, int]] = []

    for path in panel_paths:
        with Image.open(path) as image:
            current_count = getattr(image, "n_frames", 1)
            current_duration = image.info.get("duration")
            current_size = image.size
            if frame_count is None:
                frame_count = current_count
                duration_ms = current_duration
                source_size = current_size
            elif (current_count, current_duration) != (frame_count, duration_ms):
                raise ValueError(f"panel animation metadata differ: {path}")
            sizes.append(current_size)

    assert frame_count is not None
    assert duration_ms is not None
    assert source_size is not None
    if any(size[1] != source_size[1] for size in sizes):
        raise ValueError(f"panel heights differ: {sizes}")
    return frame_count, duration_ms, source_size[1], sizes


def _load_resized_frames(
    path: Path,
    indices: list[int],
    target_width: int,
    target_height: int,
) -> dict[int, Image.Image]:
    wanted = set(indices)
    frames: dict[int, Image.Image] = {}
    with Image.open(path) as source:
        for index, frame in enumerate(ImageSequence.Iterator(source)):
            if index in wanted:
                frames[index] = frame.convert("RGB").resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                )
    return frames


def _compose_frames(
    panel_frames: list[dict[int, Image.Image]],
    indices: list[int],
    target_width: int,
    target_height: int,
    target_widths: list[int],
) -> list[Image.Image]:
    composites: list[Image.Image] = []
    for index in indices:
        canvas = Image.new("RGB", (target_width, target_height), "white")
        x = 0
        for frames, panel_width in zip(panel_frames, target_widths):
            canvas.paste(frames[index], (x, 0))
            x += panel_width
        composites.append(canvas)
    return composites


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", default="OMA_ATL-OMA")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="flat release bundle or repository root containing panel GIFs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("animations/previews/ATL-OMA_dashboard_preview.gif"),
    )
    parser.add_argument(
        "--frame-output",
        type=Path,
        default=Path("animations/previews/ATL-OMA_dashboard_preview_frame.png"),
    )
    parser.add_argument("--width", type=int, default=1400)
    parser.add_argument("--frames", type=int, default=50)
    parser.add_argument("--colors", type=int, default=56)
    parser.add_argument("--duration-ms", type=int, default=100)
    args = parser.parse_args()

    if args.source_root is None:
        panel_paths = [
            ROOT / "animations" / "panels" / args.route / f"{name}.gif"
            for name in PANEL_NAMES
        ]
    else:
        source_root = _rooted(args.source_root)
        panel_paths = [source_root / f"{args.route}_{name}.gif" for name in PANEL_NAMES]
        if not all(path.exists() for path in panel_paths):
            panel_paths = [
                source_root / "animations" / "panels" / args.route / f"{name}.gif"
                for name in PANEL_NAMES
            ]
    missing = [path for path in panel_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("missing source panel GIFs: " + ", ".join(map(str, missing)))

    source_count, source_duration, source_height, source_sizes = _read_panel_metadata(panel_paths)
    if args.width < 600:
        raise ValueError("featured-animation width is too small; use at least 600 pixels")
    if args.colors < 2 or args.colors > 256:
        raise ValueError("colors must be between 2 and 256")

    scale = args.width / sum(width for width, _ in source_sizes)
    target_height = round(source_height * scale)
    target_widths = [round(width * scale) for width, _ in source_sizes]
    target_widths[-1] += args.width - sum(target_widths)
    indices = _sample_indices(source_count, args.frames)

    resized_panels = [
        _load_resized_frames(path, indices, width, target_height)
        for path, width in zip(panel_paths, target_widths)
    ]
    composites = _compose_frames(
        resized_panels,
        indices,
        args.width,
        target_height,
        target_widths,
    )

    # Use one palette for the complete animation. Quantizing each frame to a
    # separate palette can make Pillow/GIF readers reinterpret light basemap
    # pixels as white when the frame palettes change.
    thumb_width = max(1, args.width // 5)
    thumb_height = max(1, round(target_height * thumb_width / args.width))
    columns = min(5, len(composites))
    rows = math.ceil(len(composites) / columns)
    palette_sheet = Image.new(
        "RGB",
        (columns * thumb_width, rows * thumb_height),
        "white",
    )
    for sheet_index, composite in enumerate(composites):
        thumbnail = composite.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        palette_sheet.paste(
            thumbnail,
            ((sheet_index % columns) * thumb_width, (sheet_index // columns) * thumb_height),
        )
    palette = palette_sheet.quantize(
        colors=args.colors,
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    )
    frames = [
        composite.quantize(palette=palette, dither=Image.Dither.NONE)
        for composite in composites
    ]

    output = _rooted(args.output)
    frame_output = _rooted(args.frame_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame_output.parent.mkdir(parents=True, exist_ok=True)
    fallback_index = len(frames) // 2
    frames[fallback_index].convert("RGB").save(frame_output, format="PNG", optimize=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=args.duration_ms,
        loop=0,
        # Keep each frame as a complete canvas. GIF delta-frame optimization
        # can dispose unchanged map pixels and make the basemap stutter in
        # browsers even when the source panel is stable.
        optimize=False,
        disposal=1,
    )

    print(
        f"Featured animation -> {output} ({output.stat().st_size / 1e6:.2f} MB, "
        f"{args.width}x{target_height}, {len(frames)} frames, "
        f"{args.duration_ms} ms/frame, {args.colors} colors)"
    )
    print(
        f"Static fallback -> {frame_output} ({frame_output.stat().st_size / 1e6:.2f} MB, "
        f"frame {fallback_index})"
    )
    print(f"Source panels: {args.route}; source frames={source_count}; source duration_ms={source_duration}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
