# Reproducibility and release checklist

## Inputs and consent

- [x] Four public detector files have SHA-256 checksums.
- [x] Public detector serial number and travel-date consent is recorded.
- [x] Third-party FlightAware KML files are omitted.
- [x] Flight identifiers, dates, routes, and original KML hashes are recorded.
- [x] FlightAware-derived tables, figures, and animations are excluded from MIT
      and CC BY 4.0 and carry the selected rights notice.
- [x] The author's decision to publish non-raw derivatives for noncommercial
      academic review, with possible modification or removal if requested, is
      recorded in `THIRD_PARTY_NOTICES.md`.
- [ ] Each future contribution contains explicit metadata-publication consent.
- [ ] Placement, orientation, aircraft, and cabin location are recorded or
      explicitly marked `not recorded`.

## Validation

- [x] Detector JSON parses and contains positive live time.
- [x] Detector timestamp ordering and duplicates are checked.
- [x] Optional local KML timestamps, duplicates, coordinates, and UTC overlap
      are checked.
- [x] Detector and derived-file hashes match their manifests.
- [x] `total CPS = non-overflow CPS + overflow CPS` within tolerance.
- [x] Pressure bins retain live exposure and contributing-flight counts.
- [x] Equal-flight and exposure-weighted summaries are labeled.

## Modeling and uncertainty

- [x] Pooled models are fitted and evaluated in the same CPS scale.
- [x] Figure 06 uses a Poisson count likelihood with live-time exposure.
- [x] AICc, deviance degrees of freedom, exact Poisson intervals, parameter
      intervals, and a fitted-mean band are reported.
- [x] Aggregation, serial dependence, overdispersion, and causal limitations are
      stated.
- [ ] Replicate the count-level model across all flights and devices.

## Calibration

- [x] Output and anchor-supported channel ranges are distinguished.
- [x] Low- and high-channel extrapolation is explicit.
- [x] Calibration exports can be checked deterministically.
- [x] Counting-statistical peak-centroid uncertainties and leave-one-peak-out
      validation results are reported; total systematic uncertainty and a
      sub-59.5-keV reference remain future work.

## Presentation and release

- [x] Figure 01 is publication-facing, linked to SVG, and has full Markdown
      references plus a scale/range caveat.
- [x] Figure 01 generator, SVG master, and PNG rendering pass the committed
      synchronization check.
- [x] Altitude, pressure, visible-energy, and terminal-channel terms are
      consistent.
- [x] README contains no links to a release that does not yet exist.
- [x] Citation metadata contains no premature release date.
- [x] Asset-specific license scope and third-party exclusions are documented.
- [x] Preferred personal author identity is recorded in the license, package,
      and citation metadata.
- [x] Final repository URL is recorded in citation and package metadata.
- [ ] Create and verify optional full-resolution GitHub Release media.
