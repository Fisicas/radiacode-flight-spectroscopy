# Claims status

## Supported by the current workflow

- A RadiaCode `.rcspg` spectrogram can be synchronized to a locally obtained UTC
  KML by absolute timestamps when the files overlap.
- Live-time-normalized detector count rates and overflow-channel rates can be
  derived consistently from the current four-flight files.
- FlightAware-reported track altitude can be transformed into a modeled
  ISA-equivalent pressure and atmospheric column-depth coordinate for exploratory
  comparison; the source altitude type is not independently verified.
- Spectra from different embedded calibration grids can be redistributed by
  calibrated-energy interval overlap while preserving counts numerically.
- The summed four-flight raw-channel spectrum has a broad fitted feature at
  510.99 keV with an approximate counting-statistical 68% profile interval of
  508.54–513.31 keV. The diagnostic assumes stable same-detector raw-channel
  response across acquisitions. Nearby 583/609-keV leave-one-peak-out residuals
  reach 4.36 keV, so this remains a descriptive detector-spectrum feature.
- The project can be positioned as a detector-response study that preserves
  energy-dependent observables without claiming direct incident-particle flux.

## Requires additional validation

- Whether the near-511-keV feature is stable across flights, pressure bins,
  calibration choices, and control regions.
- Whether it is appropriate to call the feature an annihilation feature rather
  than a detector-spectrum feature near 511 keV.
- Whether the near-511-keV centroid remains stable under alternative
  backgrounds, time/pressure selections, calibration models, and independent
  reference-source acquisitions.
- Any detector-specific barometric coefficient or response correction.
- Any high-energy interpretation that depends on the weak Tl-208 2614.5-keV
  calibration anchor.
- Whether the recurring spectral shape is shared by aircraft, open-sea, and
  ground-control measurements after detector model, calibration, geometry, and
  exposure are accounted for.
- Whether terminal-bin excess in a long lead-shielded exposure is dominated by
  the penetrating atmospheric secondary field, interactions and secondary
  production in the surrounding high-Z shield, or detector/electronics response
  at the upper end of the measurement range.
- Whether the threshold-adjacent low-energy enhancement is a reproducible
  physical response, a threshold/calibration effect, or a composite
  environmental and instrument background. No precision centroid is supported:
  its maxima and simple fit variants span roughly 15–20 keV below the lowest
  calibration anchor.
- Whether any RadiaCode observable can be usefully compared with gLOWCOST muon
  count-rate data or aviation-radiation models after the measured quantities and
  response assumptions are matched.
- Whether the current floor-plus-exponential description of overflow CPS versus
  atmospheric depth remains stable across devices, routes, pressure ranges,
  shielding geometries, and control environments.

## Explicitly out of scope for the v0.1 snapshot

- Direct incident cosmic-ray flux or species-resolved flux.
- Particle identification from a single compact scintillation detector.
- Calibrated dose, dose equivalent, or fluence without a response/geometry model.
- A universal altitude law based on four flights.
- A measured cabin-pressure result from track-altitude-derived ISA-equivalent pressure.
- A claim that the open-sea Reddit observation independently establishes the
  origin of the flight spectrum; it is a community observation that motivates
  controlled testing, not a calibrated reference measurement.
- A claim that a visible terminal/overflow-bin excess is itself a direct
  measurement of cosmic-ray flux or a particle-identification signal.
