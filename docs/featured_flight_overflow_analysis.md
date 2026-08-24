# Single-flight overflow response: ATL to OMA

## Purpose

This is the first comprehensive count-level analysis of the flight used in the
featured animation. It asks how the RadiaCode terminal/overflow response
changes with atmospheric overburden during one flight, while keeping the
measured quantity explicit: overflow counts recorded by the detector per unit
live time.

The analysis is deliberately detector-centered. It does not interpret overflow
CPS as a direct cosmic-ray flux, particle fluence, or particle-identification
measurement.

## Data and provenance

The flight is identified in the repository as `OMA_ATL-OMA` (ATL to OMA). The
compact input table contains 16 pressure bins derived from the raw
[RCSPG detector file](../data/raw/OMA_ATL-OMA.rcspg) and the local FlightAware
track identified in the [track-source table](../config/flight_track_sources.csv).
The KML itself is not redistributed. The analysis-ready table is
[`pressure_overflow_by_flight.csv`](../data/derived/pressure_overflow_by_flight.csv).

Because the table's pressure/depth coordinates derive from the FlightAware
track, the table, model products, and figures are excluded from the repository's
MIT and CC BY 4.0 licenses and carry the selected FlightAware notice. See
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

The flight contributes 6,590 s of live time and 5,290 overflow counts. The
pressure-bin centers span 225–975 hPa, corresponding to 229.4–994.2 g cm⁻² in
the current ISA depth coordinate.

## Statistical model

For bin `i`, let `n_i` be overflow counts and `T_i` be detector live time. The
count-level model is:

```text
n_i ~ Poisson(T_i R(X_i))
```

where `R(X_i)` is overflow CPS and `X_i` is atmospheric column depth. This is
equivalent to using `log(T_i)` as the exposure offset in a log-rate model. The
physical predictor is depth, not pressure; pressure is retained for display and
for comparison with the flight record. In this data product:

```text
X [g cm^-2] = 1.019716 × P [hPa]
```

Four response families were fit:

```text
linear:                 R = b0 + b1 (X / 1000)
quadratic:              R = b0 + b1 (X / 1000) + b2 (X / 1000)^2
zero-floor exponential: R = A exp(-X / Lambda)
floor + exponential:    R = B + A exp(-X / Lambda)
```

The linear and quadratic models use a non-negative identity-link Poisson fit.
The exponential models profile the depth scale by likelihood search and keep
the amplitude and floor non-negative. The reproducible implementation is
[`analyze_featured_flight_overflow.py`](../scripts/analyze_featured_flight_overflow.py).
Because there are only 16 bins, model comparison emphasizes AICc rather than
uncorrected AIC. Absolute AIC/AICc values omit the shared `log(n!)` constant;
only within-dataset differences are interpreted.

## Results

| Model | ΔAICc | Poisson deviance | Deviance df | Pearson residual RMSE | Rate RMSE (CPS) |
|---|---:|---:|---:|---:|---:|
| Linear | 535.140 | 556.856 | 14 | 5.261 | 0.2926 |
| Quadratic | 65.192 | 83.830 | 13 | 2.204 | 0.1005 |
| Zero-floor exponential | 3.313 | 25.028 | 14 | 1.288 | 0.0416 |
| Floor-plus-exponential | 0.000 | 18.639 | 13 | 1.061 | 0.0366 |

The best of the requested descriptions is the floor-plus-exponential:

```text
B       = 0.0182 CPS     (approximate 95% interval 0.0079–0.0422)
A       = 6.207 CPS      (approximate 95% interval 5.210–7.394)
Lambda  = 151.1 g cm^-2  (approximate 95% interval 136.8–166.9)
```

The zero-floor exponential remains plausible: its ΔAICc is 3.31 and the
single-flight tail is sparse. The result is therefore evidence for an
exponential-like falloff plus a possible detector-level floor, not a decisive
identification of a physical floor component.

The parameter intervals are local, Hessian-based likelihood approximations.
They quantify curvature of this fitted model but do not account for binning,
serial correlation, model-selection uncertainty, or between-flight variation.

The fitted curves and Poisson-aware residuals are shown in
[`figure_06_oma_atl_overflow_depth_response.png`](../figures/presentation/figure_06_oma_atl_overflow_depth_response.png).
The complete prediction table and machine-readable summary are:

- [`OMA_ATL-OMA_overflow_depth_models.csv`](../data/derived/OMA_ATL-OMA_overflow_depth_models.csv)
- [`OMA_ATL-OMA_overflow_depth_predictions.csv`](../data/derived/OMA_ATL-OMA_overflow_depth_predictions.csv)
- [`OMA_ATL-OMA_overflow_depth_analysis.json`](../data/derived/OMA_ATL-OMA_overflow_depth_analysis.json)
- [`atl_oma_overflow_depth_analysis.ipynb`](../notebooks/atl_oma_overflow_depth_analysis.ipynb)

## High-depth floor inspection

The high-depth tail is defined here as bins with lower pressure edge `P ≥ 750
hPa`, or approximately `X ≥ 764.8 g cm⁻²`. It contains 25 overflow counts in
721 s:

```text
observed tail rate = 0.0347 CPS
Poisson standard error = 0.0069 CPS
exact 95% Poisson interval = 0.0224–0.0512 CPS
```

The exposure-weighted tail predictions are 0.0348 CPS for the floor-plus-
exponential and 0.0246 CPS for the zero-floor exponential. The observed tail
is therefore consistent with the fitted floor, but the count total is small
enough that this should be treated as a useful hypothesis for replication.

## Interpretation

The nonlinear shape is physically reasonable as a detector-level response. A
single attenuating component can produce an exponential-like term with depth,
but the atmospheric secondary field is a cascade rather than a single beam.
Production, decay, energy loss, geomagnetic selection, aircraft shielding,
detector geometry, thresholds, pulse processing, and the terminal-bin
definition can all change the observed curve. The fitted `Lambda` is therefore
an effective response scale for this flight and setup, not a universal
atmospheric attenuation length.

The tail `B` term can include a mixture of residual atmospheric secondaries,
local aircraft/material response, detector electronics or overflow behavior,
and unmodeled geometry or orientation. The lead-castle and open-sea examples
described in the main README make this separation especially important:
shielding changes the interaction field and does not provide a clean switch
that turns the cosmic component off.

## Limitations and next analysis

This is one flight from one detector and one aircraft environment. The pressure
bins are aggregated, and the tail has only 25 counts. The analysis does not
yet include detector orientation, cabin location, temperature, geomagnetic
coordinates, solar conditions, aircraft material, route direction, or a
paired reference detector.

Aggregation also combines ascent, descent, time, and geographic position within
pressure bins. Residual serial dependence and unmodeled overdispersion are not
estimated, so the fitted pressure association is descriptive rather than
causal.

The next steps are:

1. run the same Poisson count/exposure models on every demonstration flight;
2. add flight-specific intercepts or a hierarchical model before estimating a
   shared depth response;
3. compare the overflow response with non-overflow and total CPS using the same
   live-time and depth conventions;
4. replicate the model across devices, open-sea voyages, ground controls, and
   controlled shielding states; and
5. only then test associations with geomagnetic, solar, and established
   aviation-radiation model products.

This sequence keeps the contribution scientifically useful within the larger
cosmic-ray measurement framework: it establishes what a widely available
portable spectrometer records before asking how a distributed network might be
calibrated or compared with dedicated particle counters such as gLOWCOST.
