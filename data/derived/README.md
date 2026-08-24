# Derived pressure-response tables

These compact CSVs summarize the current four-flight processing pass for the
overflow channel. They are derived from the included raw `.rcspg` files and
local user-supplied FlightAware KML tracks. The KML files are not redistributed;
their identifiers and original hashes are recorded in
[`config/flight_track_sources.csv`](../../config/flight_track_sources.csv).
The tables make the pressure/depth response analysis inspectable without
committing the much larger intermediate spectra.

These tables derive their pressure and depth coordinates from FlightAware
website data. They are included for noncommercial academic review but excluded
from the repository's MIT and CC BY 4.0 licenses. See
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md).

- [`pressure_overflow_by_flight.csv`](pressure_overflow_by_flight.csv) contains
  pressure-bin counts, live time, total/non-overflow/overflow CPS, and Poisson
  rate uncertainties for each flight.
- [`pressure_overflow_average.csv`](pressure_overflow_average.csv) contains
  equal-flight and exposure-weighted summaries, including the common bins
  supported by all four flights.

The pressure coordinate is modeled ISA-equivalent pressure calculated from
FlightAware-reported track altitude; the source altitude type is not independently
verified. The
column-depth coordinate is `X[g cm^-2] = 1.019716 × P[hPa]`; it is therefore an
equivalent predictor, not an independent measurement. Raw counts must be
converted to rates using live time before comparing flights or pressure bins.

The reproducible model comparison is in
[`scripts/analyze_overflow_pressure.py`](../../scripts/analyze_overflow_pressure.py).
The single-flight case study is documented in
[`docs/featured_flight_overflow_analysis.md`](../../docs/featured_flight_overflow_analysis.md)
and reproduced by
[`scripts/analyze_featured_flight_overflow.py`](../../scripts/analyze_featured_flight_overflow.py).
Its model, prediction, and JSON summary files are included beside these tables.
The checksums are recorded in [`SHA256SUMS.txt`](SHA256SUMS.txt).

The publication-facing visualization for the single-flight analysis is
[`Figure 06`](../../figures/presentation/figure_06_oma_atl_overflow_depth_response.png).
It should be read together with the report because the fitted floor and depth
scale are detector-level, flight-specific descriptors rather than direct
cosmic-ray flux parameters. The conceptual
[Figure 01](../../figures/presentation/figure_01_physics_cascade_to_detector.svg)
states the detector-response interpretation boundary and is not a quantitative
transport calculation.
