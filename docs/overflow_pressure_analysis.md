# Overflow response versus atmospheric pressure and depth

## Question

The terminal/overflow channel is a detector-response observable. The useful
question is therefore not whether it is a direct cosmic-ray flux, but whether
its live-time-normalized rate changes reproducibly with atmospheric overburden
and what response family is a reasonable first description.

The analysis uses the four-flight pressure summaries in
[`data/derived/`](../data/derived/) and the reproducible model comparison in
[`scripts/analyze_overflow_pressure.py`](../scripts/analyze_overflow_pressure.py).
The primary comparison uses the equal-flight mean in pressure bins supported by
all four flights, avoiding an unequal-flight low-altitude comparison.

The pressure and depth coordinates in those summaries derive from FlightAware
website data. The summaries are included for noncommercial academic review but
excluded from the repository's MIT and CC BY 4.0 licenses; see
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

## Coordinate choice

For the current ISA conversion:

```text
X [g cm^-2] = 1.019716 × P [hPa]
```

Pressure `P` and atmospheric column depth `X` are therefore linearly equivalent
coordinates in this dataset. A model should use one or the other, not both as
independent predictors. Depth is the better physical coordinate because it
represents atmospheric mass above the detector.

## Current four-flight result

The common comparison contains 14 bins spanning 325–975 hPa, or approximately
331–994 g cm^-2. Overflow CPS falls rapidly as pressure/depth increases, but the
high-pressure end approaches a small noisy floor rather than continuing as a
clean straight line.

All four models below are fitted and evaluated in the original CPS scale, so
their residual metrics are directly comparable. With only 14 common-support
bins, AICc is reported alongside fit error.

| Model | RMSE (CPS) | R² | AICc |
|---|---:|---:|---:|
| Linear in pressure | 0.09497 | 0.721 | -60.83 |
| Quadratic in pressure | 0.03685 | 0.958 | -84.03 |
| Exponential, zero floor | 0.01778 | 0.990 | -107.75 |
| Exponential plus floor | 0.00984 | 0.997 | -121.00 |

The best descriptive fit in this small comparison is:

```text
R_overflow(X) ≈ B + A exp(-X / Lambda_eff)
B             ≈ 0.030 CPS
A             ≈ 7.22 CPS
Lambda_eff    ≈ 135 g cm^-2
```

The equivalent pressure scale is approximately 132 hPa. This is an empirical
response scale for this detector, flight geometry, calibration, and pressure
range. It must not be called a universal atmospheric attenuation length or
interpreted as a direct cosmic-ray interaction length.

The zero-floor exponential is substantially closer to the floor model than an
earlier log-CPS fit suggested. The floor model remains the best of these four
descriptions, but the comparison is exploratory: it gives equal weight to each
flight-balanced pressure bin, does not model heteroskedasticity or serial
correlation, and contains only 14 observations.

## Why an exponential can appear, and why it is not guaranteed

For one component that only survives passage through an overburden, a simple
transport approximation is:

```text
F(X) = F0 exp(-X / Lambda)
```

That is the intuition behind an exponential depth dependence. It is not the
full model for an atmospheric cosmic-ray cascade. Atmospheric secondaries are
produced, lose energy, decay, and feed other particle and photon populations.
The response can show a broad maximum, saturation, or multiple characteristic
scales rather than a single exponential. The detector also integrates over
energy, direction, particle type, shielding, aircraft materials, and its own
threshold, live time, pulse processing, and terminal-bin behavior.

The appropriate detector-level model is closer to:

```text
R_overflow(X) = B_detector
              + integral[ detector_response(E, direction, geometry)
                          × secondary_field(E, X, geomagnetic, solar)
                        ] dE
              + local_material_response(X)
```

The observed exponential-like curve may mean that one effective component
dominates over the sampled range. It does not demonstrate that all cosmic-ray
or secondary-particle fluence follows that same law.

## How to analyze this going forward

1. Use overflow counts divided by live time, not raw overflow counts. For a
   count-level model, use a Poisson likelihood with `log(live_time)` as the
   exposure offset.
2. Use atmospheric depth `X` as the physical predictor and retain pressure as
   a display coordinate. Do not fit both in the same model here.
3. Fit at least a linear, quadratic, zero-floor exponential, and floor-plus-
   exponential model. Compare residuals with Poisson-aware weights and inspect
   the high-depth floor separately.
4. Include flight-specific intercepts or random effects. The current four
   flights have different baseline rates and slightly different empirical
   slopes; a pooled curve without flight effects can hide that structure.
5. Treat the terminal bin, non-overflow spectrum, and total CPS as separate
   response channels. Their depth dependences need not be identical.
6. Add open-sea, ground, shielding, detector-orientation, geomagnetic, and
   solar covariates only after the single-device response is stable.

The present result supports a pressure/depth-dependent, non-linear detector
response with an exponential-like falloff and a high-depth floor. It does not
yet support a particle-flux law, a universal scale, or a causal decomposition
between atmospheric secondaries and local aircraft/material response.
