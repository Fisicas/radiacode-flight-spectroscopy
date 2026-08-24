#!/usr/bin/env python3
"""Build Figure 01: cosmic-ray transport to RadiaCode observables.

The figure is deliberately drawn from simple vector primitives so the SVG
remains editable and the PNG can be regenerated without a browser.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import math
import tempfile
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


WIDTH = 3200
HEIGHT = 1800

BG = "#FBFCFE"
INK = "#162033"
MUTED = "#526173"
NAVY = "#12233F"
BLUE = "#246FB5"
BLUE_LIGHT = "#EAF4FB"
SKY_1 = "#E8F3FB"
SKY_2 = "#DCECF7"
SKY_3 = "#CFDFEC"
ORANGE = "#E87919"
ORANGE_LIGHT = "#FFF1E3"
PURPLE = "#7040AF"
PURPLE_LIGHT = "#F0EAF8"
TEAL = "#198F8B"
TEAL_LIGHT = "#E7F5F3"
TEAL_DARK = "#0B5A57"
GOLD = "#F2B134"
RED = "#C63E4E"
WHITE = "#FFFFFF"
LINE = "#B8C8D8"
GROUND = "#8E735B"


def font_file(*, bold: bool = False, italic: bool = False) -> str:
    windows = Path("C:/Windows/Fonts")
    names = {
        (False, False): ("arial.ttf", "DejaVuSans.ttf"),
        (True, False): ("arialbd.ttf", "DejaVuSans-Bold.ttf"),
        (False, True): ("ariali.ttf", "DejaVuSans-Oblique.ttf"),
        (True, True): ("arialbi.ttf", "DejaVuSans-BoldOblique.ttf"),
    }[(bold, italic)]
    for name in names:
        candidate = windows / name
        if candidate.exists():
            return str(candidate)
    return names[-1]


def points_text(points: Sequence[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


class Scene:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.image = Image.new("RGB", (width, height), BG)
        self.draw = ImageDraw.Draw(self.image, "RGBA")
        self.svg: list[str] = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
                'aria-labelledby="title desc">'
            ),
            '<title id="title">From cosmic rays to what RadiaCode records in flight</title>',
            (
                '<desc id="desc">A left-to-right scientific schematic showing a primary cosmic ray '
                'creating representative nucleon, electromagnetic, and muonic branches connected only by named '
                'collision, pion-decay, and photon-conversion events. One representative muon path continues '
                'through aircraft altitude to the ground. A ground-level callout notes that muons dominate the '
                'penetrating charged cosmic-ray component while neutrons, photons, electrons, positrons, and some '
                'protons also remain. '
                'The right side shows local aircraft '
                'geometry, the 10 millimeter CsI(Tl) cube, its gamma-calibrated visible-energy response, and '
                'recorded detector observables. A prominent '
                'boundary states that pulse height does not identify particle species or directly measure '
                'primary cosmic-ray flux.</desc>'
            ),
            f'<rect width="{width}" height="{height}" fill="{BG}"/>',
        ]

    @staticmethod
    def _rgba(color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
        value = color.lstrip("#")
        rgb = tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
        return (*rgb, int(round(255 * opacity)))

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str = "none",
        stroke: str = "none",
        sw: float = 1,
        radius: float = 0,
        opacity: float = 1.0,
    ) -> None:
        coords = (round(x), round(y), round(x + w), round(y + h))
        if fill != "none":
            rgba = self._rgba(fill, opacity)
            if radius:
                self.draw.rounded_rectangle(coords, radius=radius, fill=rgba)
            else:
                self.draw.rectangle(coords, fill=rgba)
        if stroke != "none" and sw > 0:
            rgba = self._rgba(stroke, opacity)
            if radius:
                self.draw.rounded_rectangle(coords, radius=radius, outline=rgba, width=round(sw))
            else:
                self.draw.rectangle(coords, outline=rgba, width=round(sw))
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'
        )

    def ellipse(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str,
        stroke: str = "none",
        sw: float = 1,
        opacity: float = 1.0,
    ) -> None:
        self.draw.ellipse(
            (round(x), round(y), round(x + w), round(y + h)),
            fill=self._rgba(fill, opacity),
            outline=None if stroke == "none" else self._rgba(stroke, opacity),
            width=round(sw),
        )
        self.svg.append(
            f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'
        )

    def line(
        self,
        points: Sequence[tuple[float, float]],
        *,
        color: str,
        sw: float = 4,
        opacity: float = 1.0,
        dash: str | None = None,
    ) -> None:
        self.draw.line(points, fill=self._rgba(color, opacity), width=round(sw), joint="curve")
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.svg.append(
            f'<polyline points="{points_text(points)}" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" '
            f'opacity="{opacity}"{dash_attr}/>'
        )

    def wave(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        color: str,
        sw: float = 5,
        amplitude: float = 9,
        wavelength: float = 42,
        opacity: float = 1.0,
    ) -> None:
        """Draw the conventional wavy photon notation between interactions."""
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        length = max(math.hypot(dx, dy), 1)
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        cycles = max(round(length / wavelength), 1)
        samples = max(int(length / 4), 24)
        points: list[tuple[float, float]] = []
        for index in range(samples + 1):
            t = index / samples
            offset = amplitude * math.sin(2 * math.pi * cycles * t)
            points.append((sx + dx * t + px * offset, sy + dy * t + py * offset))
        self.line(points, color=color, sw=sw, opacity=opacity)

    def polygon(
        self,
        points: Sequence[tuple[float, float]],
        *,
        fill: str,
        stroke: str = "none",
        sw: float = 1,
        opacity: float = 1.0,
    ) -> None:
        self.draw.polygon(points, fill=self._rgba(fill, opacity))
        if stroke != "none":
            self.draw.line([*points, points[0]], fill=self._rgba(stroke, opacity), width=round(sw), joint="curve")
        self.svg.append(
            f'<polygon points="{points_text(points)}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linejoin="round" opacity="{opacity}"/>'
        )

    def arrow(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        color: str,
        sw: float = 7,
        head: float = 20,
        opacity: float = 1.0,
    ) -> None:
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        length = max(math.hypot(dx, dy), 1)
        ux, uy = dx / length, dy / length
        bx, by = ex - ux * head, ey - uy * head
        px, py = -uy * head * 0.48, ux * head * 0.48
        self.line([(sx, sy), (bx, by)], color=color, sw=sw, opacity=opacity)
        self.polygon([(ex, ey), (bx + px, by + py), (bx - px, by - py)], fill=color, opacity=opacity)

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: int,
        color: str = INK,
        bold: bool = False,
        italic: bool = False,
        align: str = "left",
        opacity: float = 1.0,
    ) -> None:
        font = ImageFont.truetype(font_file(bold=bold, italic=italic), size)
        bbox = self.draw.textbbox((0, 0), value, font=font)
        text_w = bbox[2] - bbox[0]
        draw_x = x if align == "left" else x - text_w / 2 if align == "center" else x - text_w
        self.draw.text((round(draw_x), round(y)), value, font=font, fill=self._rgba(color, opacity))
        anchor = {"left": "start", "center": "middle", "right": "end"}[align]
        weight = "700" if bold else "400"
        style = "italic" if italic else "normal"
        escaped = html.escape(value)
        self.svg.append(
            f'<text x="{x}" y="{y}" dominant-baseline="hanging" text-anchor="{anchor}" '
            f'font-family="Arial, DejaVu Sans, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" font-style="{style}" fill="{color}" '
            f'opacity="{opacity}">{escaped}</text>'
        )

    def save(self, svg_path: Path, png_path: Path) -> None:
        self.svg.append("</svg>")
        svg_text = "\n".join(self.svg) + "\n"
        svg_path.write_text(svg_text, encoding="utf-8")
        png_info = PngImagePlugin.PngInfo()
        # Hash newline-normalized text so Git checkout settings cannot make the
        # PNG/SVG synchronization marker platform-dependent.
        normalized_svg = svg_path.read_text(encoding="utf-8")
        png_info.add_text(
            "figure_svg_sha256",
            hashlib.sha256(normalized_svg.encode("utf-8")).hexdigest(),
        )
        self.image.save(
            png_path,
            format="PNG",
            optimize=True,
            dpi=(180, 180),
            pnginfo=png_info,
        )


def stage_heading(scene: Scene, x: float, y: float, number: str, title: str, color: str) -> None:
    scene.ellipse(x, y, 62, 62, fill=color)
    scene.text(x + 31, y + 11, number, size=32, color=WHITE, bold=True, align="center")
    scene.text(x + 84, y + 7, title, size=37, color=INK, bold=True)


def particle(scene: Scene, x: float, y: float, label: str, color: str, radius: float = 29) -> None:
    scene.ellipse(x - radius, y - radius, 2 * radius, 2 * radius, fill=color, stroke=WHITE, sw=5)
    scene.text(x, y - 18, label, size=30, color=WHITE, bold=True, align="center")


def compact_particle_marker(
    scene: Scene,
    cx: float,
    cy: float,
    label: str,
    color: str,
    *,
    diameter: float,
    text_size: int,
) -> None:
    """Draw a small circular particle marker with optically centered text."""
    scene.ellipse(
        cx - diameter / 2,
        cy - diameter / 2,
        diameter,
        diameter,
        fill=color,
        stroke=WHITE,
        sw=3,
    )
    scene.text(
        cx,
        cy - text_size / 2,
        label,
        size=text_size,
        color=WHITE,
        bold=True,
        align="center",
    )


def decay_vertex(scene: Scene, x: float, y: float, radius: float = 13) -> None:
    """Mark a pion decay with a solid orange node."""
    scene.ellipse(
        x - radius,
        y - radius,
        2 * radius,
        2 * radius,
        fill=ORANGE,
        stroke=WHITE,
        sw=4,
    )


def conversion_vertex(scene: Scene, x: float, y: float, radius: float = 14) -> None:
    """Mark photon pair conversion in the field of an air nucleus."""
    scene.ellipse(
        x - radius,
        y - radius,
        2 * radius,
        2 * radius,
        fill=WHITE,
        stroke=PURPLE,
        sw=5,
    )
    scene.ellipse(x - 5, y - 5, 10, 10, fill=MUTED)


def draw_aircraft(scene: Scene, ox: float, oy: float, scale: float = 1.0, *, detector: bool = True) -> None:
    """Draw a clean top-view commercial-airliner silhouette.

    ``ox`` is the tail x-position and ``oy`` is the fuselage centerline.
    """
    pts = [
        (700, 0),
        (664, -18),
        (590, -32),
        (430, -40),
        (305, -170),
        (262, -170),
        (320, -38),
        (122, -27),
        (64, -96),
        (30, -96),
        (50, -22),
        (0, -12),
        (0, 12),
        (50, 22),
        (30, 96),
        (64, 96),
        (122, 27),
        (320, 38),
        (262, 170),
        (305, 170),
        (430, 40),
        (590, 32),
        (664, 18),
    ]
    points = [(ox + x * scale, oy + y * scale) for x, y in pts]
    scene.polygon(points, fill=WHITE, stroke=BLUE, sw=7 * scale)
    scene.line(
        [(ox + 108 * scale, oy), (ox + 625 * scale, oy)],
        color=LINE,
        sw=3 * scale,
    )
    # Wing-mounted engines and cockpit glazing make the silhouette read as an airliner.
    for engine_y in (-82, 82):
        scene.ellipse(
            ox + 342 * scale,
            oy + (engine_y - 18) * scale,
            94 * scale,
            36 * scale,
            fill=WHITE,
            stroke=BLUE,
            sw=4 * scale,
        )
    scene.ellipse(ox + 620 * scale, oy - 16 * scale, 28 * scale, 12 * scale, fill=NAVY)
    scene.ellipse(ox + 620 * scale, oy + 4 * scale, 28 * scale, 12 * scale, fill=NAVY)
    if detector:
        scene.rect(
            ox + 360 * scale,
            oy - 18 * scale,
            48 * scale,
            36 * scale,
            fill=TEAL,
            stroke=WHITE,
            sw=3 * scale,
            radius=6 * scale,
        )


def draw_figure(scene: Scene) -> None:
    # Title and thesis.
    scene.text(110, 76, "From cosmic rays to what RadiaCode records in flight", size=76, bold=True)
    scene.text(
        114,
        176,
        "The atmosphere creates a mixed secondary field; RadiaCode records pulse height reported as γ-calibrated visible energy.",
        size=34,
        color=MUTED,
    )

    # Atmospheric transport field.
    ax, ay, aw, ah = 100, 285, 1760, 1115
    left_scale = ah / 1050

    def sy(y: float) -> float:
        """Scale an original left-panel y coordinate into the taller panel."""
        return ay + (y - ay) * left_scale

    def spts(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(x, sy(y)) for x, y in points]

    scene.rect(ax, ay, aw, ah, fill=BLUE_LIGHT, stroke="#AFCBE1", sw=4, radius=34)
    scene.rect(ax + 4, sy(ay + 4), aw - 8, 194 * left_scale, fill=NAVY, radius=29)
    scene.rect(ax + 4, sy(ay + 168), aw - 8, 300 * left_scale, fill=SKY_1)
    scene.rect(ax + 4, sy(ay + 468), aw - 8, 305 * left_scale, fill=SKY_2)
    scene.rect(ax + 4, sy(ay + 773), aw - 8, 268 * left_scale, fill=SKY_3)
    scene.line(spts([(ax + 4, ay + 1040), (ax + aw - 4, ay + 1040)]), color=GROUND, sw=14)

    # Sparse stars support the space/atmosphere transition. Keep a generous
    # exclusion zone around the stage heading and the primary-particle label.
    for x, y, r in [(740, 430, 4), (1450, 345, 5), (1760, 350, 4)]:
        scene.ellipse(x - r, sy(y) - r, 2 * r, 2 * r, fill=WHITE, opacity=0.72)

    scene.ellipse(142, sy(326), 62, 62, fill=BLUE)
    scene.text(173, sy(337), "1", size=32, color=WHITE, bold=True, align="center")
    # Preserve a clear gap before the straight primary-particle path; the full
    # heading remains on one line without the final word touching the arrow.
    scene.text(226, sy(333), "ATMOSPHERIC DEPTH SETS THE BROAD FIELD", size=31, color=WHITE, bold=True)
    scene.text(1780, sy(414), "SPACE / UPPER ATMOSPHERE", size=22, color="#D9ECF7", bold=True, align="right")
    scene.line(spts([(1425, 447), (1780, 447)]), color="#9FC9E2", sw=2, opacity=0.64)

    # Depth guide.
    scene.text(180, sy(515), "LESS AIR ABOVE", size=28, color=BLUE, bold=True)
    scene.text(180, sy(552), "lower P • smaller X", size=27, color=BLUE)
    scene.text(180, sy(1112), "MORE AIR ABOVE", size=28, color=TEAL, bold=True)
    scene.text(180, sy(1149), "higher P • larger X", size=27, color=TEAL)
    scene.text(125, sy(1255), "GROUND", size=25, color=GROUND, bold=True)

    # Primary particle and first interaction. Every downstream split begins at
    # this common physical vertex or at another explicitly marked vertex.
    primary_vertex = (980, sy(550))
    scene.arrow((980, sy(365)), (980, sy(520)), color=GOLD, sw=13, head=34)
    scene.text(1030, sy(389), "primary proton or nucleus", size=31, color=WHITE, bold=True)

    # Representative nucleons emerge directly from the first hadronic
    # collision. Their paths remain straight because no later interaction is
    # drawn in this deliberately minimal topology.
    scene.arrow(primary_vertex, (650, sy(805)), color=ORANGE, sw=6, head=17, opacity=0.86)
    scene.arrow(primary_vertex, (820, sy(850)), color=ORANGE, sw=6, head=17, opacity=0.84)

    # One representative charged pion reaches a named decay. Only the
    # detector-relevant muon daughter is retained in this instrument-focused
    # schematic; the penetrating muon crosses flight altitude and reaches the
    # ground. A single μ± track represents either charge sign, not multiplicity.
    charged_pion_decay = (920, sy(730))
    muon_ground = (1820, sy(1305))
    scene.arrow(primary_vertex, charged_pion_decay, color=ORANGE, sw=6, head=17, opacity=0.88)
    scene.arrow(charged_pion_decay, muon_ground, color=BLUE, sw=7, head=20, opacity=0.78)

    # The electromagnetic component uses conventional wavy photon lines. A
    # short neutral-pion segment ends at a named decay; two photons originate
    # there. One interacts in the field of an air nucleus at a marked pair-
    # conversion vertex, from which straight electron and positron tracks
    # emerge. The other photon never bends.
    pi0_decay = (1100, sy(665))
    pair_conversion = (1260, sy(750))
    scene.arrow(primary_vertex, pi0_decay, color=ORANGE, sw=6, head=17, opacity=0.88)
    scene.wave(pi0_decay, pair_conversion, color=PURPLE, sw=5, amplitude=7, opacity=0.90)
    scene.wave(pi0_decay, (1515, sy(805)), color=PURPLE, sw=5, amplitude=8, opacity=0.88)
    scene.arrow(pair_conversion, (1350, sy(835)), color=PURPLE, sw=5, head=16, opacity=0.84)
    scene.arrow(pair_conversion, (1470, sy(890)), color=PURPLE, sw=5, head=16, opacity=0.82)

    # Distinct symbols prevent decay and conversion from reading as generic
    # decorative branch points.
    decay_vertex(scene, *charged_pion_decay)
    decay_vertex(scene, *pi0_decay)
    conversion_vertex(scene, *pair_conversion)

    # Redraw the first interaction over all outgoing paths to show their common
    # origin rather than several nearby, ambiguous starting points.
    scene.ellipse(951, sy(521), 58, 58, fill=GOLD, stroke=WHITE, sw=5)
    scene.text(980, sy(531), "×", size=34, color=NAVY, bold=True, align="center")

    # Labels are drawn after the trajectories so every word remains unobstructed.
    scene.text(1025, sy(548), "FIRST HADRONIC COLLISION IN AIR", size=22, color=NAVY, bold=True)
    scene.rect(260, sy(592), 600, 54, fill=WHITE, radius=14, opacity=0.92)
    scene.text(280, sy(602), "HADRONIC SECONDARIES: n, p, π±, π⁰", size=23, color=ORANGE, bold=True)
    scene.rect(180, sy(680), 560, 54, fill=WHITE, radius=14, opacity=0.92)
    scene.text(200, sy(691), "MUONIC: μ± FROM CHARGED-PION DECAY", size=22, color=BLUE, bold=True)
    scene.rect(1220, sy(592), 530, 54, fill=WHITE, radius=14, opacity=0.92)
    scene.text(1240, sy(602), "ELECTROMAGNETIC BRANCH", size=25, color=PURPLE, bold=True)

    # Each non-primary vertex is named locally; no generic vertex legend is
    # needed to infer what a ring or dot means.
    scene.rect(935, sy(690), 155, 38, fill=WHITE, radius=11, opacity=0.93)
    scene.text(950, sy(696), "π± decay", size=21, color=ORANGE, bold=True)
    scene.text(1100, sy(625), "π⁰", size=22, color=ORANGE, bold=True, align="center")
    scene.text(1100, sy(691), "decay", size=19, color=ORANGE, bold=True, align="center")
    scene.rect(1035, sy(765), 205, 40, fill=WHITE, radius=11, opacity=0.93)
    scene.text(1050, sy(773), "γ conversion in air", size=20, color=PURPLE, bold=True)

    particle(scene, 650, sy(805), "n", ORANGE)
    particle(scene, 820, sy(850), "p", ORANGE)
    # Place the muon marker on an unobstructed portion of its continuous track.
    particle(scene, 1600, sy(1164), "μ±", BLUE, radius=35)
    particle(scene, 1350, sy(835), "e−", PURPLE, radius=35)
    particle(scene, 1470, sy(890), "e+", PURPLE, radius=35)
    particle(scene, 1515, sy(805), "γ", PURPLE)

    # Cruise-altitude coordinate and aircraft interception.
    scene.line(spts([(350, 900), (1780, 900)]), color=BLUE, sw=3, opacity=0.34, dash="16 14")
    scene.rect(180, sy(875), 535, 118, fill=WHITE, stroke="#B9D3E6", sw=3, radius=18, opacity=0.96)
    scene.text(212, sy(898), "CRUISE LEVELS IN THIS STUDY", size=29, color=BLUE, bold=True)
    scene.text(212, sy(938), "≈9–11 km • lower P • smaller X", size=30, color=INK)
    draw_aircraft(scene, 840, sy(960), 0.78)
    scene.rect(760, sy(1100), 740, 98, fill=SKY_3, radius=18, opacity=0.94)
    scene.text(1130, sy(1115), "mixed field reaches the aircraft", size=31, color=INK, bold=True, align="center")
    scene.text(
        1130,
        sy(1157),
        "n • μ± • γ • e± • p • other secondaries",
        size=30,
        color=MUTED,
        align="center",
    )
    scene.text(
        1330,
        sy(1207),
        "Pressure is an atmospheric-depth proxy:  X ≈ P/g",
        size=29,
        color=TEAL,
        bold=True,
        align="center",
    )
    scene.text(
        1330,
        sy(1247),
        "The particle mix also depends on geomagnetic location and solar conditions.",
        size=23,
        color=MUTED,
        align="center",
    )

    # Muons dominate the charged cosmic-ray component near sea level, but the
    # atmospheric secondary field at ground is not exclusively muonic. Use a
    # compact categorical callout rather than relative bar sizes: composition
    # depends on energy threshold and response quantity, and RadiaCode does not
    # identify these species. The continuous blue path remains the representative
    # penetrating trajectory; the markers acknowledge other ground components.
    # Keep the callout inside its own compact lane at the lower left. The box
    # hugs the content, while larger type and balanced padding preserve the
    # claim's readability in the GitHub-scaled PNG.
    ground_box_x, ground_box_w = 270, 520
    scene.rect(ground_box_x, sy(1188), ground_box_w, 124, fill=WHITE, stroke="#B9D3E6", sw=2, radius=15, opacity=0.96)
    scene.text(ground_box_x + ground_box_w / 2, sy(1195), "GROUND-LEVEL SECONDARIES", size=22, color=NAVY, bold=True, align="center")

    # First row: the main sea-level charged component.
    compact_particle_marker(scene, 300, sy(1244), "μ±", BLUE, diameter=34, text_size=15)
    scene.text(326, sy(1219), "muons dominate the penetrating charged", size=22, color=BLUE, bold=True)
    scene.text(326, sy(1243), "cosmic-ray component at ground level", size=22, color=BLUE, bold=True)

    # Second row: particle markers precede the contiguous phrase "also reach
    # ground". The wavy photon symbol distinguishes gamma from a lowercase y.
    compact_particle_marker(scene, 356, sy(1282), "n", ORANGE, diameter=28, text_size=14)
    scene.wave((389, sy(1282)), (427, sy(1282)), color=PURPLE, sw=4, amplitude=4, opacity=0.92)
    scene.text(442, sy(1271), "γ", size=21, color=PURPLE, bold=True)
    compact_particle_marker(scene, 481, sy(1282), "e±", PURPLE, diameter=32, text_size=14)
    compact_particle_marker(scene, 529, sy(1282), "p", ORANGE, diameter=28, text_size=14)
    scene.text(555, sy(1273), "also reach ground", size=20, color=MUTED)
    scene.text(
        1330,
        sy(1280),
        "Selected detector-relevant branches shown; line count does not represent particle yield.",
        size=20,
        color=MUTED,
        align="center",
    )

    # Causal handoff from the atmospheric field to the instrument chain. Both
    # the tail and arrowhead sit entirely in the inter-panel gutter.
    scene.arrow((1880, 500), (1948, 500), color=INK, sw=9, head=28)

    # Stage 2: local aircraft and detector geometry (secondary to atmospheric depth).
    rx, rw = 1980, 1120
    stage2_y = 285
    stage3_y = 685
    stage4_y = 1075
    stage2_shift = stage2_y - 300
    stage3_shift = stage3_y - 660
    stage4_shift = stage4_y - 1010
    scene.rect(rx, stage2_y, rw, 310, fill=ORANGE_LIGHT, stroke="#E7B271", sw=4, radius=30)
    stage_heading(scene, rx + 50, 334 + stage2_shift, "2", "LOCAL AIRCRAFT + DETECTOR GEOMETRY", ORANGE)
    draw_aircraft(scene, rx + 105, 500 + stage2_shift, 0.34)
    # The same three particle-field colors used at the scintillator descend
    # onto the aircraft here, making the panel-to-panel handoff explicit.
    for xx, color, end_y in [
        (rx + 155, ORANGE, 460 + stage2_shift),
        (rx + 245, BLUE, 460 + stage2_shift),
        (rx + 335, PURPLE, 460 + stage2_shift),
    ]:
        scene.arrow((xx, 398 + stage2_shift), (xx, end_y), color=color, sw=6, head=17, opacity=0.82)
    scene.text(rx + 455, 427 + stage2_shift, "Aircraft structure, cabin contents, placement,", size=25, color=INK, bold=True)
    scene.text(rx + 455, 469 + stage2_shift, "and orientation also shape the field at the crystal.", size=25, color=INK, bold=True)
    scene.text(rx + 455, 526 + stage2_shift, "Atmospheric depth is the primary coordinate", size=25, color=BLUE, bold=True)
    scene.text(rx + 455, 562 + stage2_shift, "analyzed in this snapshot.", size=25, color=BLUE, bold=True)

    # Downward flow arrow with a visible tail in the enlarged gutter.
    scene.arrow((2540, 608), (2540, 672), color=INK, sw=8, head=24)

    # Stage 3: compact scintillator response and its identification limits.
    scene.rect(rx, stage3_y, rw, 300, fill=TEAL_LIGHT, stroke="#77BBB7", sw=4, radius=30)
    stage_heading(scene, rx + 50, 694 + stage3_shift, "3", "DETECTOR RESPONSE, NOT PARTICLE ID", TEAL)
    # The RC-103 specification gives a 10 x 10 x 10 mm CsI(Tl) scintillator.
    # Draw three visible faces so the icon reads as a cube rather than a slab.
    cube_x, cube_y = rx + 120, 775 + stage3_shift
    cube_w, cube_d, cube_h = 130, 32, 108
    scene.arrow((rx + 40, 826 + stage3_shift), (cube_x - 4, 826 + stage3_shift), color=ORANGE, sw=6, head=17)
    scene.arrow((rx + 40, 854 + stage3_shift), (cube_x - 4, 854 + stage3_shift), color=BLUE, sw=6, head=17)
    scene.arrow((rx + 40, 882 + stage3_shift), (cube_x - 4, 882 + stage3_shift), color=PURPLE, sw=6, head=17)
    scene.polygon(
        [(cube_x, cube_y + cube_d), (cube_x + cube_w, cube_y + cube_d),
         (cube_x + cube_w, cube_y + cube_d + cube_h), (cube_x, cube_y + cube_d + cube_h)],
        fill="#BFE9D5", stroke=TEAL, sw=5,
    )
    scene.polygon(
        [(cube_x, cube_y + cube_d), (cube_x + cube_d, cube_y),
         (cube_x + cube_w + cube_d, cube_y), (cube_x + cube_w, cube_y + cube_d)],
        fill="#DDF5E9", stroke=TEAL, sw=5,
    )
    scene.polygon(
        [(cube_x + cube_w, cube_y + cube_d), (cube_x + cube_w + cube_d, cube_y),
         (cube_x + cube_w + cube_d, cube_y + cube_h),
         (cube_x + cube_w, cube_y + cube_d + cube_h)],
        fill="#8FD1B6", stroke=TEAL, sw=5,
    )
    for px, py in [
        (cube_x + 34, cube_y + 58),
        (cube_x + 82, cube_y + 87),
        (cube_x + 53, cube_y + 119),
    ]:
        scene.ellipse(px - 9, py - 9, 18, 18, fill=GOLD)
    # Keep the side-face scintillation point clearly inset from every cube edge.
    side_px, side_py, side_pr = cube_x + 147, cube_y + 65, 7
    scene.ellipse(side_px - side_pr, side_py - side_pr, 2 * side_pr, 2 * side_pr, fill=GOLD)
    scene.text(
        cube_x + 80,
        920 + stage3_shift,
        "10×10×10 mm CsI(Tl) cube",
        size=22,
        color=TEAL,
        bold=True,
        align="center",
    )
    # Stylized scintillation pulse: quiet baseline, fast rise, then a smooth
    # exponential decay. This is schematic and does not imply a measured decay
    # constant for the device electronics.
    pulse_baseline_y = 862 + stage3_shift
    pulse_onset_x = rx + 500
    pulse_amplitude = 102
    pulse_tau = 58
    pulse = [(rx + 430, pulse_baseline_y), (pulse_onset_x, pulse_baseline_y)]
    pulse.append((pulse_onset_x, pulse_baseline_y - pulse_amplitude))
    pulse.extend(
        (
            pulse_onset_x + dx,
            pulse_baseline_y - pulse_amplitude * math.exp(-dx / pulse_tau),
        )
        for dx in range(10, 251, 10)
    )
    scene.line(pulse, color=RED, sw=8)
    scene.text(rx + 595, 886 + stage3_shift, "pulse height", size=25, color=RED, bold=True, align="center")
    scene.text(
        rx + 595,
        918 + stage3_shift,
        "→ γ-calibrated visible energy",
        size=21,
        color=TEAL,
        bold=True,
        align="center",
    )
    scene.text(rx + 790, 784 + stage3_shift, "Pulse height", size=29, color=INK, bold=True)
    scene.text(rx + 790, 824 + stage3_shift, "≠ particle identity", size=27, color=RED, bold=True)
    scene.text(rx + 790, 864 + stage3_shift, "≠ arrival direction", size=27, color=RED, bold=True)
    scene.text(rx + 790, 904 + stage3_shift, "particle-dependent light yield", size=22, color=MUTED)

    scene.arrow((2540, 998), (2540, 1062), color=INK, sw=8, head=24)

    # Stage 4: recorded observables.
    scene.rect(rx, stage4_y, rw, 325, fill=PURPLE_LIGHT, stroke="#A98ACB", sw=4, radius=30)
    stage_heading(scene, rx + 50, 1044 + stage4_shift, "4", "SOFTWARE RECORDS DETECTOR OBSERVABLES", PURPLE)
    # Mini spectrum with an explicit terminal/overflow bin.
    x0, y0, pw, ph = rx + 92, 1248 + stage4_shift, 470, 118
    scene.line([(x0, y0 - ph), (x0, y0), (x0 + pw, y0)], color=INK, sw=4)
    bars = [92, 73, 60, 52, 45, 39, 33, 27, 23, 20, 17, 14, 12, 138]
    bw = 24
    for idx, bh in enumerate(bars):
        color = RED if idx < len(bars) - 1 else PURPLE
        scene.rect(x0 + 16 + idx * 30, y0 - bh, bw, bh, fill=color, radius=3)
    scene.text(
        x0 + pw / 2,
        y0 + 12,
        "γ-calibrated visible energy / keV",
        size=22,
        color=MUTED,
        align="center",
    )
    scene.text(rx + 630, 1155 + stage4_shift, "PULSE-HEIGHT SPECTRUM", size=28, color=RED, bold=True)
    scene.text(rx + 630, 1202 + stage4_shift, "TOTAL COUNT RATE (CPS)", size=28, color=BLUE, bold=True)
    scene.text(rx + 630, 1249 + stage4_shift, "TERMINAL / OVERFLOW-BIN RATE", size=28, color=PURPLE, bold=True)
    scene.text(rx + 630, 1290 + stage4_shift, "catch-all channel; not a particle species", size=24, color=MUTED)

    # Strong interpretation boundary. Pull it close to the main panels so it
    # reads as their conclusion rather than a detached footer, and use a deep
    # teal distinct from the atmospheric panel's navy header.
    boundary_y = 1425
    scene.rect(100, boundary_y, 3000, 230, fill=TEAL_DARK, radius=30)
    scene.rect(100, boundary_y, 18, 230, fill=GOLD, radius=9)
    scene.text(160, boundary_y + 33, "INTERPRETATION BOUNDARY", size=27, color=GOLD, bold=True)
    scene.text(
        160,
        boundary_y + 77,
        "RadiaCode records pulse height as γ-calibrated visible energy — not particle identity, direction, or primary cosmic-ray flux.",
        size=33,
        color=WHITE,
        bold=True,
    )
    scene.text(
        160,
        boundary_y + 140,
        "Incident energy, particle fluence, or dose require a validated response + geometry model; the terminal bin is a catch-all channel.",
        size=28,
        color="#D9E4F0",
    )

    # Explicit references and scale note share one compact footer line.
    scene.text(
        108,
        1700,
        "Selected references and clickable source links: README Figure 01 caption • Device/output: RadiaCode 103 technical specifications and Spectrum Window documentation.",
        size=21,
        color=MUTED,
    )
    scene.text(3092, 1700, "Conceptual schematic • not to scale", size=21, color=MUTED, align="right")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "figures" / "presentation",
        help="Directory for the SVG and PNG outputs.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate in a temporary directory and verify the committed SVG/PNG pair.",
    )
    return parser.parse_args()


def render_figure(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "figure_01_physics_cascade_to_detector"
    scene = Scene(WIDTH, HEIGHT)
    draw_figure(scene)
    svg_path = output_dir / f"{stem}.svg"
    png_path = output_dir / f"{stem}.png"
    scene.save(svg_path, png_path)
    return svg_path, png_path


def check_committed_figure(output_dir: Path) -> None:
    stem = "figure_01_physics_cascade_to_detector"
    committed_svg = output_dir / f"{stem}.svg"
    committed_png = output_dir / f"{stem}.png"
    if not committed_svg.is_file() or not committed_png.is_file():
        raise SystemExit("Figure 01 check failed: committed PNG/SVG pair is incomplete.")

    with tempfile.TemporaryDirectory(prefix="figure-01-check-") as temp_dir:
        generated_svg, _ = render_figure(Path(temp_dir))
        if generated_svg.read_text(encoding="utf-8") != committed_svg.read_text(encoding="utf-8"):
            raise SystemExit(
                "Figure 01 check failed: committed SVG differs from scripts/build_figure_01.py output."
            )

    normalized_svg = committed_svg.read_text(encoding="utf-8")
    svg_sha256 = hashlib.sha256(normalized_svg.encode("utf-8")).hexdigest()
    with Image.open(committed_png) as image:
        if image.size != (WIDTH, HEIGHT):
            raise SystemExit(
                f"Figure 01 check failed: PNG dimensions are {image.size}, expected {(WIDTH, HEIGHT)}."
            )
        if image.info.get("figure_svg_sha256") != svg_sha256:
            raise SystemExit(
                "Figure 01 check failed: PNG metadata does not match the committed SVG. Regenerate both."
            )
    print("Figure 01 check passed: generator, SVG master, and PNG rendering are synchronized.")


def main() -> None:
    args = parse_args()
    if args.check:
        check_committed_figure(args.output_dir)
        return

    svg_path, png_path = render_figure(args.output_dir)
    print(f"Wrote {svg_path}")
    print(f"Wrote {png_path}")


if __name__ == "__main__":
    main()
