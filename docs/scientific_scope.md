# Scientific scope

## Working objective

This repository studies what compact RadiaCode scintillation spectrometers
record when carried through changing atmospheric depth and changing local
environments. The first demonstration consists of four commercial flight legs,
but the intended dataset includes comparable aircraft, open-sea, and ground
measurements from many devices and contributors.

The central research question is:

> Which energy-dependent detector observables are reproducible across devices,
> flights, altitudes, routes, and environments, and can a distributed collection
> of those observations add useful context to established cosmic-ray and
> aviation-radiation measurements?

## What is measured

The primary observables are:

- time-resolved energy spectra in the device's calibrated channel grid;
- live-time-normalized total and non-overflow count rate;
- the final calibrated detector bins, including the terminal/overflow bin;
- recurring spectral features or broad shape descriptors;
- route, altitude, UTC time, and modeled ISA pressure/atmospheric depth;
- metadata describing detector model, calibration, placement, orientation,
  aircraft, cabin location, and acquisition settings.

These are detector-system observables. They are influenced by atmospheric
secondary-particle production and transport, geomagnetic and solar conditions,
aircraft/vessel materials and shielding, and the detector's own scintillator,
photodetector, electronics, threshold, dead-time, saturation, and calibration.

## What this project does not claim

The v0.1 snapshot does not claim:

- direct incident cosmic-ray flux, fluence, or species-resolved flux;
- particle identification from a single compact scintillation detector;
- a universal altitude law from four flights;
- a calibrated dose or dose-equivalent result without a response and geometry
  model;
- a definitive isotope assignment for the 511-keV annotation;
- a definitive elemental assignment for the low-energy feature near 17–20 keV;
- equivalence between RadiaCode measurements and gLOWCOST muon counts,
  neutron-monitor data, or aviation dosimeters.

The current four-flight pressure summary shows an exponential-like decrease in
overflow CPS with increasing atmospheric depth. A floor-plus-exponential has
the lowest residual error among four descriptive fits, but the zero-floor
exponential also follows the curve closely. This is a useful detector-response
comparison, not evidence that the measured overflow channel is direct cosmic-ray
flux or that the fitted scale is a universal atmospheric attenuation length.

The first complete single-flight count-level case study is documented in the
[featured ATL-to-OMA flight overflow analysis](featured_flight_overflow_analysis.md).
It uses overflow counts with live-time exposure in a Poisson likelihood and
uses atmospheric depth as the physical predictor.

The terminal/overflow bin deserves separate treatment. RadiaCode's spectrum
documentation describes the most recent channel as containing its own events
plus data outside the displayed energy range. A terminal-bin excess is
therefore an endpoint detector-response observable. It may be sensitive to the
high-energy secondary field, local materials and shielding, pulse pile-up, or
upper-range electronics behavior, but it is not by itself a cosmic-ray flux or
particle-identification measurement.

## Why aircraft, open sea, and ground controls belong together

Aircraft provide a large change in atmospheric depth over a few hours. Open-sea
measurements reduce the contribution from soil, rock, buildings, and other
nearby terrestrial sources, while ground measurements help characterize the
detector and local environment. Comparing these environments can test whether
the recurring spectrum is primarily associated with an attenuated atmospheric
secondary field, a local material response, or a mixture of both.

The open-sea comparison currently comes from a community [RadiaCode 110
report](https://www.reddit.com/r/Radiacode/comments/1vogqn6/rc_110_background_measurement_at_sea_during_a/),
not from a calibrated reference campaign. It is therefore a useful
hypothesis-forming observation and a reason to collect standardized sea, ship,
and ground controls—not a standalone proof of spectral origin.

A second community comparison is the 26-day lead-castle background reported by
[Beerbrewing](https://www.reddit.com/user/Beerbrewing/), which shows both a
candidate 511-keV feature and terminal-bin activity. A lead castle is not a
passive cosmic-ray filter: it changes attenuation and interaction geometry, and
the long integration accumulates rare events into the terminal channel. This
observation should be analyzed as a shielding-and-detector-response control,
not as a direct measurement of the unmodified cosmic field.

## Relationship to existing work

The [gLOWCOST project at Georgia State
University](https://cosmic.gsu.edu/) is developing a distributed network of
low-cost muon detectors for cosmic-ray and space-weather monitoring. This
project is complementary rather than interchangeable: gLOWCOST targets a
particle-counting observable, while RadiaCode measurements provide a portable,
energy-resolved detector response.

The work also sits downstream of established atmospheric transport, aviation
radiation, and dosimetry programs. Comparisons with [NASA's NAIRAS
model](https://ccmc.gsfc.nasa.gov/models/NAIRAS~2.0/) or instruments such as
those described in the [RaD-X overview](https://science.larc.nasa.gov/rad-x/about/)
must be made only after matching the measured quantities, detector response,
geometry, shielding, and uncertainty model.

## Initial validation ladder

1. Reproduce the four-flight parser, UTC alignment, live-time normalization,
   and energy-rebinning results.
2. Establish whether broad spectral features recur across flights and pressure
   bins within the same device.
3. Add open-sea and controlled ground measurements with the same device,
   orientation, acquisition settings, and calibration provenance.
4. Compare multiple RadiaCode models and devices to separate environmental
   variation from instrument response.
5. Add solar, geomagnetic, and model covariates only after the detector-level
   observables are stable.
6. Where possible, make paired measurements with a reference detector or a
   gLOWCOST site before interpreting correlations as physical relationships.

## Specific open questions

The route context uses FlightAware-reported track altitude. Its altitude type
is not independently verified; ISA-equivalent pressure and depth are modeled
coordinates rather than measured cabin pressure.

The overall spectral shape, threshold-adjacent low-energy structure, candidate
511-keV feature, and overflow response are all open questions. A four-flight
Gaussian-plus-background diagnostic places the broad higher-energy feature at
510.99 keV with an approximate counting-statistical 68% interval of
508.54–513.31 keV, but it assumes stable same-detector raw-channel response
across acquisitions. Nearby held-out calibration residuals reach 4.36 keV and
the physical identity remains unestablished. The low-energy structure is
especially constrained by calibration, model choice, and threshold behavior:
its descriptive maxima and
fit variants span about 15–20 keV, entirely below the lowest 59.5-keV anchor.
For context, aluminum K-alpha fluorescence is near 1.486 keV, while common
RadiaCode 102/103
models have a published lower energy range near 20 keV. The feature should
therefore be treated as threshold-adjacent until controlled measurements show
otherwise.
