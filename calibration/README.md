# Calibration verification bundle

This directory contains a compact, reproducible calibration check for the
RadiaCode-103 spectra used in the flight workflow. The source spectra were
provided by the project author and are preserved as XML inputs. The derived CSV
files apply the working manual-primary energy calibration; they are verification
products, not dose or fluence calibrations.

## Source spectra

| File | Material/source | Role in the check |
|---|---|---|
| [`source_spectra/Am-241.xml`](source_spectra/Am-241.xml) | Am-241 | Clean low-energy gamma anchor near 59.5409 keV |
| [`source_spectra/Ra-226.xml`](source_spectra/Ra-226.xml) | Radium-series source | Low- and mid-energy anchors from the Ra-226/Pb-214/Bi-214 series |
| [`source_spectra/Th-232.xml`](source_spectra/Th-232.xml) | Thorium-series source | Mid- and high-energy anchors, including Tl-208 at 2614.511 keV |
| [`source_spectra/U-238-U-235-FiestaWare.xml`](source_spectra/U-238-U-235-FiestaWare.xml) | Uranium-bearing Fiestaware | Independent spectral check across the low/mid-energy range |

The selected primary anchors and fitted channel centroids are listed in
[`manual_primary_peaks.csv`](manual_primary_peaks.csv). Counting-statistical
centroid uncertainties and leave-one-peak-out checks are in the
[`validation/`](validation/) products. The source names are
descriptive sample labels; they should not be read as a claim of secular
equilibrium or source-activity certification.

## Working energy conversion

For zero-based RadiaCode XML channel `c`, the current working calibration is:

```text
E_keV(c) = 5.151420584 + 2.431018093*c + 0.000374694301*c^2
```

The selected-anchor fit has an approximately 1.24 keV RMS residual and a 2.57
keV maximum absolute residual in the working notes. The high-energy curvature
is sensitive to the fitted centroid of the weak Tl-208 2614.5-keV peak, so this
calibration remains explicitly marked as working rather than final.

The nine fitted anchors span channels 22.21–937.81 (approximately
59.5–2614.5 keV). The exported 0–1023 channel axis therefore extrapolates below
the lowest anchor and above the highest anchor, including the threshold-adjacent
region and the terminal channel. The manifest distinguishes the output range
from this anchor-supported range; neither should be interpreted as an
efficiency or dose-response validation.

## Centroid uncertainty and held-out checks

[`validate_peak_centroids.py`](validate_peak_centroids.py) uses fixed,
documented windows around the nine primary peaks. It estimates a linear
sideband, calculates a background-subtracted peak width and area, and applies a
4,000-replicate Poisson bootstrap. The manual fitted centroids remain the point
estimates; the background-subtracted moment bootstrap supplies a documented
counting-statistical uncertainty scale. The resulting one-standard-deviation
counting-statistical centroid uncertainties range from 0.013 keV for the strong
Am-241 59.5-keV peak to 3.16 keV for the weak Tl-208 2614.5-keV peak. These are
not total uncertainties: they exclude background/window choice, unresolved
lines, source characterization, detector drift, and response-model error.

Each leave-one-peak-out fold refits the quadratic curve to the other eight
anchors. The two folds closest to the 511-keV region give residuals of +3.93
keV at 583.187 keV and -4.36 keV at 609.312 keV. The 2614.511-keV fold misses
by +25.67 keV, confirming that the high-energy curvature is not independently
constrained by the lower-energy anchors.

For the summed raw-channel spectra from the four public flights, a Gaussian
plus linear-background description places the broad feature at 510.99 keV with
an approximate counting-statistical 68% profile interval of 508.54–513.31 keV.
The aggregation uses one detector and assumes stable raw-channel response
across acquisition dates. The interval does not include the nearby held-out
disagreement or detector-response systematics, and it does not establish
annihilation radiation or isotope identity.

No precision centroid is reported for the threshold-adjacent low-energy
structure. Its per-flight channel maxima map to 14.88–19.75 keV under the
working calibration, and simple window/background choices move a fitted
centroid across 15.67–19.93 keV. The entire structure is below the lowest
59.5-keV anchor, so the earlier “~19 keV” wording remains descriptive rather
than a calibrated line-energy claim.

The auditable products are:

- [`anchor_centroid_uncertainties.csv`](validation/anchor_centroid_uncertainties.csv)
- [`held_out_peak_validation.csv`](validation/held_out_peak_validation.csv)
- [`flight_feature_centroid_diagnostics.csv`](validation/flight_feature_centroid_diagnostics.csv)
- [`peak_validation_summary.json`](validation/peak_validation_summary.json)
- [`calibration_peak_validation.ipynb`](../notebooks/calibration_peak_validation.ipynb)

The machine-readable provenance is in
[`manual_primary_calibration.yml`](manual_primary_calibration.yml). The
energy-converted spectra in
[`energy_converted_spectra/`](energy_converted_spectra/) are generated by
[`recalibrate_spectra.py`](recalibrate_spectra.py) and retain the original XML
calibration in their commented metadata. File checksums are in
[`SHA256SUMS.txt`](SHA256SUMS.txt).

From the repository root, verify the committed deterministic outputs without
replacing them:

```powershell
python calibration/recalibrate_spectra.py --check
python calibration/validate_peak_centroids.py --check
```

To intentionally regenerate either set of canonical files, use `--force` with
the corresponding script.

The output energy axis is a channel-to-energy mapping for spectral comparison.
It does not provide detector efficiency, dose response, particle fluence, or
isotope identification by itself.

The project-owned calibration measurements and their data products are licensed
under [CC BY 4.0](../LICENSE-DATA.md). The calibration scripts and documentation
remain under the root [MIT License](../LICENSE).
