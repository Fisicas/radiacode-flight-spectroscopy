# Animation viewing guide

Each route has two presentation formats:

1. a full dashboard overview; and
2. three synchronized panel GIFs rendered from the same detector-record index
   sequence.

The panel GIFs are intentionally separate so a browser can display each graph
column at a readable width. Download the three files for a route from the
`v0.1-media` GitHub Release and open them together; they use the same frame
count, frame duration, elapsed-time cursor, and UTC timestamp in the header.
All three panels use a shared 1,588-pixel
height; the two middle spectrograms are expanded to occupy that full vertical
span rather than leaving unused space below the lower plot.

| Panel | What it shows |
|---|---|
| `spectrum_route.gif` | Accumulated spectrum with the cautious near-511-keV annotation and the geographic route |
| `spectrograms_overflow.gif` | 0-1000 keV spectrogram, final three calibrated bins including overflow, and shared log color scale |
| `diagnostics.gif` | Track-reported altitude, ISA-equivalent pressure, non-overflow CPS, and overflow CPS |

The PNG frame beside each GIF is the static fallback for browsers or document
readers that do not animate GIFs. The detailed GIFs are distributed as
`v0.1-media` GitHub Release assets; the landing-page featured animation remains
in the main repository. The CSV/JSON products remain the numerical record; animations are
synchronized explanatory views.

For the quantitative response analysis associated with the featured ATL-to-OMA
flight, see the [single-flight overflow report](../docs/featured_flight_overflow_analysis.md),
the [Figure 06 static visualization](../figures/presentation/figure_06_oma_atl_overflow_depth_response.png),
and the [reproducible notebook](../notebooks/atl_oma_overflow_depth_analysis.ipynb).
The publication-facing [Figure 01 schematic](../figures/presentation/figure_01_physics_cascade_to_detector.svg)
provides the conceptual atmospheric-field-to-detector interpretation boundary.

To rebuild the landing-page featured animation from the prepared release-media
bundle:

```text
python scripts/build_featured_animation.py --source-root ../github_repository_release_assets_v0.1-media
```

The default output is a 1400-pixel-wide, 50-frame, 56-color GIF with a static
PNG fallback beside it.

The frame schedule is recorded in
[`panel_animation_metadata.json`](panels/panel_animation_metadata.json).

To verify that each synchronized set still has matching panel heights and
frame counts, run:

```text
python scripts/check_panel_sizes.py
```

To verify that the featured animation has no map-disposal or basemap-continuity
artifact, run:

```text
python scripts/check_featured_animation.py
```

## Rights and attribution

The route and altitude layers were derived from FlightAware website data used
in the local analysis. No downloaded KML is included. These non-raw derivative
animations are displayed for noncommercial academic review and are excluded
from the repository's MIT and CC BY 4.0 licenses; see
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

> Contains FlightAware data © FlightAware LLC 2026. FlightAware data and
> trademarks are excluded from the repository’s MIT and CC BY 4.0 licenses.
> This independent project is not affiliated with or endorsed by FlightAware.

The geographic background was rendered from public-domain Natural Earth data:
“Made with Natural Earth.”
