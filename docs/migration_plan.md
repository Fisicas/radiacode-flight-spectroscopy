# Public roadmap

## v0.1: data, methods, and derived-results snapshot

The candidate release preserves the evidence needed to review the current
four-flight result without claiming a fully portable analysis package.
FlightAware-derived products are included for noncommercial academic review,
carry the repository's FlightAware rights notice, and remain outside its MIT
and CC BY 4.0 licenses.

Completed in v0.1:

- four original RadiaCode detector spectrograms with SHA-256 hashes;
- FlightAware retrieval identifiers and original KML hashes without
  redistribution of the third-party track files;
- a manifest and validator for detector files and optional local KML tracks;
- calibration source spectra, anchor table, supported/extrapolated ranges, and
  deterministic export verification;
- counting-statistical centroid uncertainties, leave-one-peak-out calibration
  checks, and explicit feature-centroid limits;
- compact derived pressure/depth tables and count-level model outputs;
- publication figures, animation previews, tests, and a reproducible
  single-flight notebook; and
- explicit limits on particle identification, flux, dose, altitude-source
  terminology, and causal interpretation.

## v0.2: portable analysis package

Refactor the local parser, UTC merge, normalization, energy redistribution,
plotting, and animation logic into `src/radiacode_flight/`. The target commands
are:

```text
radiacode-flight validate
radiacode-flight analyze
radiacode-flight normalize
radiacode-flight figures
radiacode-flight animate
```

Each run should write machine-readable metadata containing input hashes,
configuration, calibration identifier, output paths, warnings, software
versions, and count-conservation checks.

## Scientific validation priorities

1. Replicate the Poisson count/exposure analysis across all flights and devices.
2. Add flight-specific or hierarchical effects before estimating a shared depth
   response.
3. Record detector placement, orientation, aircraft, and cabin location.
4. Add an independent reference acquisition below 59.5 keV and repeat the
   calibration validation across devices and acquisition dates.
5. Obtain controlled ground, sea, shielding, and paired reference-detector
   measurements.
6. Add geomagnetic, solar, and atmospheric-transport model comparisons only
   after the detector-level response is stable.

## Release policy

Raw detector data require contributor consent for serial number and travel
metadata. Third-party tracks are referenced by source and retrieval identifiers
but are not committed unless their terms explicitly permit redistribution.
Derived tables, figures, and animations also require terms that permit the
intended publication; omitting a raw track does not by itself clear those
products. Presentation products remain subordinate to the numeric CSV/JSON
record.
