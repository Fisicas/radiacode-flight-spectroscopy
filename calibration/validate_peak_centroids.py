#!/usr/bin/env python3
"""Quantify centroid precision and held-out energy-scale checks.

The calibration anchors retain the manually fitted centroids used for the
working quadratic channel-to-energy conversion. This script adds an explicitly
limited counting-statistical uncertainty estimate for each centroid, performs
leave-one-peak-out calibration checks, and records cautious diagnostics for the
flight-spectrum structures near 511 keV and the lower threshold.

The uncertainty estimates do not include source certification, line blending,
window/background choice, detector drift, or response-model systematics.
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    from .recalibrate_spectra import (
        CAL_A,
        CAL_B,
        CAL_Q,
        parse_spectrum_counts,
    )
except ImportError:  # Direct execution from the calibration directory.
    from recalibrate_spectra import (  # type: ignore
        CAL_A,
        CAL_B,
        CAL_Q,
        parse_spectrum_counts,
    )


CALIBRATION_DIR = Path(__file__).resolve().parent
REPO = CALIBRATION_DIR.parent
ANCHOR_TABLE = CALIBRATION_DIR / "manual_primary_peaks.csv"
VALIDATION_DIR = CALIBRATION_DIR / "validation"
BOOTSTRAP_REPLICATES = 4_000

# Inclusive channel windows selected around the manually fitted primary peaks.
# They are intentionally stored here so the uncertainty calculation is
# inspectable and exactly repeatable.
ANCHOR_WINDOWS: dict[tuple[str, float], tuple[int, int]] = {
    ("Am-241.xml", 59.5409): (14, 31),
    ("Ra-226.xml", 186.211): (64, 82),
    ("Ra-226.xml", 241.995): (87, 104),
    ("Ra-226.xml", 295.224): (107, 127),
    ("Ra-226.xml", 351.932): (128, 151),
    ("Ra-226.xml", 609.312): (224, 253),
    ("Th-232.xml", 238.632): (84, 106),
    ("Th-232.xml", 583.187): (216, 245),
    ("Th-232.xml", 2614.511): (920, 955),
}

OUTPUT_NAMES = (
    "anchor_centroid_uncertainties.csv",
    "held_out_peak_validation.csv",
    "flight_feature_centroid_diagnostics.csv",
    "peak_validation_summary.json",
)


def energy_keV(channel: float) -> float:
    """Evaluate the working manual-primary energy conversion."""

    return CAL_A + CAL_B * channel + CAL_Q * channel * channel


def energy_slope_keV_per_channel(channel: float) -> float:
    """Return dE/dc for propagation of a local channel uncertainty."""

    return CAL_B + 2.0 * CAL_Q * channel


def _background_subtracted_moments(
    counts: np.ndarray,
    low: int,
    high: int,
) -> tuple[float, float, float]:
    """Return centroid, effective sigma, and net area for one peak window."""

    x = np.arange(low, high + 1, dtype=float)
    y = np.asarray(counts[low : high + 1], dtype=float)
    side_count = max(3, int(round(0.20 * len(x))))
    side_index = np.r_[0:side_count, len(x) - side_count : len(x)]
    slope, intercept = np.polyfit(x[side_index], y[side_index], 1)
    background = intercept + slope * x
    signal = np.clip(y - background, 0.0, None)
    net = float(signal.sum())
    if net <= 0.0:
        raise ValueError(f"non-positive background-subtracted area in channels {low}-{high}")
    centroid = float(np.dot(x, signal) / net)
    sigma = float(np.sqrt(np.dot((x - centroid) ** 2, signal) / net))
    return centroid, sigma, net


def _bootstrap_centroid_uncertainty(
    counts: np.ndarray,
    low: int,
    high: int,
    seed: int,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> float:
    """Poisson-bootstrap the background-subtracted moment centroid."""

    x = np.arange(low, high + 1, dtype=float)
    y = np.asarray(counts[low : high + 1], dtype=float)
    side_count = max(3, int(round(0.20 * len(x))))
    side_index = np.r_[0:side_count, len(x) - side_count : len(x)]
    design = np.column_stack([np.ones(len(side_index)), x[side_index]])
    design_pinv = np.linalg.pinv(design)

    simulated = np.random.default_rng(seed).poisson(y, size=(replicates, len(y)))
    coefficients = simulated[:, side_index] @ design_pinv.T
    background = coefficients[:, :1] + coefficients[:, 1:] * x[None, :]
    signal = np.clip(simulated - background, 0.0, None)
    net = signal.sum(axis=1)
    valid = net > 0.0
    centroids = (signal[valid] @ x) / net[valid]
    if len(centroids) < 0.99 * replicates:
        raise ValueError(f"too many invalid bootstrap fits in channels {low}-{high}")
    return float(np.std(centroids, ddof=1))


def _read_anchor_rows() -> list[dict[str, str]]:
    with ANCHOR_TABLE.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_source_counts(rows: Iterable[dict[str, str]]) -> dict[str, np.ndarray]:
    counts: dict[str, np.ndarray] = {}
    for row in rows:
        relative = row["source_file"]
        if relative in counts:
            continue
        root = ET.parse(CALIBRATION_DIR / relative).getroot()
        counts[relative] = np.asarray(parse_spectrum_counts(root), dtype=float)
    return counts


def compute_anchor_uncertainties() -> list[dict[str, object]]:
    """Return one uncertainty record for every working calibration anchor."""

    rows = _read_anchor_rows()
    spectra = _load_source_counts(rows)
    output: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        source_name = Path(row["source_file"]).name
        assigned = float(row["assigned_energy_keV"])
        low, high = ANCHOR_WINDOWS[(source_name, assigned)]
        moment, width, net = _background_subtracted_moments(
            spectra[row["source_file"]], low, high
        )
        uncertainty_channel = _bootstrap_centroid_uncertainty(
            spectra[row["source_file"]],
            low,
            high,
            seed=20260821 + index,
        )
        fitted = float(row["fitted_channel"])
        output.append(
            {
                "source_file": row["source_file"],
                "nuclide_or_line": row["nuclide_or_line"],
                "assigned_energy_keV": assigned,
                "fitted_channel": fitted,
                "fit_window_channels": f"{low}-{high}",
                "background_subtracted_moment_channel": round(moment, 6),
                "moment_minus_fitted_channel": round(moment - fitted, 6),
                "effective_sigma_channel": round(width, 6),
                "estimated_net_counts": round(net, 1),
                "centroid_counting_stat_1sigma_channel": round(uncertainty_channel, 6),
                "centroid_counting_stat_1sigma_keV": round(
                    uncertainty_channel * energy_slope_keV_per_channel(fitted), 6
                ),
                "uncertainty_scope": "Poisson counting statistics only",
            }
        )
    return output


def compute_held_out_validation(
    anchors: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Perform leave-one-peak-out checks of the quadratic energy conversion."""

    channels = np.asarray([float(row["fitted_channel"]) for row in anchors])
    energies = np.asarray([float(row["assigned_energy_keV"]) for row in anchors])
    uncertainties = np.asarray(
        [float(row["centroid_counting_stat_1sigma_channel"]) for row in anchors]
    )
    rng = np.random.default_rng(20260821)
    output: list[dict[str, object]] = []

    for held_out in range(len(anchors)):
        keep = np.arange(len(anchors)) != held_out
        coefficients = np.polyfit(channels[keep], energies[keep], 2)
        predicted = float(np.polyval(coefficients, channels[held_out]))

        simulations = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
        for replicate in range(BOOTSTRAP_REPLICATES):
            sampled_channels = rng.normal(channels, uncertainties)
            sampled_coefficients = np.polyfit(
                sampled_channels[keep], energies[keep], 2
            )
            simulations[replicate] = np.polyval(
                sampled_coefficients, sampled_channels[held_out]
            )

        assigned = energies[held_out]
        output.append(
            {
                "held_out_source_file": anchors[held_out]["source_file"],
                "held_out_line": anchors[held_out]["nuclide_or_line"],
                "assigned_energy_keV": assigned,
                "predicted_energy_keV": round(predicted, 6),
                "residual_predicted_minus_assigned_keV": round(predicted - assigned, 6),
                "counting_stat_prediction_1sigma_keV": round(
                    float(np.std(simulations, ddof=1)), 6
                ),
                "calibration_fit_anchor_count": int(keep.sum()),
                "near_511_context": "yes" if 500.0 <= assigned <= 700.0 else "no",
                "validation_scope": (
                    "line excluded from this fold; statistical centroid uncertainty only"
                ),
            }
        )
    return output


def _load_aggregate_flight_counts() -> tuple[np.ndarray, list[dict[str, object]], str]:
    aggregate = np.zeros(1024, dtype=float)
    flight_maxima: list[dict[str, object]] = []
    device_ids: set[str] = set()
    for path in sorted((REPO / "data" / "raw").glob("*.rcspg")):
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        device_ids.add(str(document["deviceId"]))
        flight = np.zeros(int(document["channelCount"]), dtype=float)
        for spectrum in document["spectrums"]:
            pulses = np.asarray(spectrum["pulses"], dtype=float)
            flight[: len(pulses)] += pulses
        aggregate[: len(flight)] += flight
        maximum_channel = int(np.argmax(flight[:13]))
        flight_maxima.append(
            {
                "flight": path.stem,
                "maximum_channel_0_to_12": maximum_channel,
                "working_energy_keV": round(energy_keV(maximum_channel), 6),
            }
        )
    if len(device_ids) != 1:
        raise ValueError(f"candidate-feature aggregation spans device IDs: {device_ids}")
    return aggregate, flight_maxima, next(iter(device_ids))


def _profile_gaussian_plus_linear(
    counts: np.ndarray,
    low: int,
    high: int,
    centroid_grid: np.ndarray,
    sigma_grid: np.ndarray,
) -> dict[str, float]:
    """Profile a Gaussian peak over a linear background with Pearson chi-square."""

    x = np.arange(low, high + 1, dtype=float)
    y = np.asarray(counts[low : high + 1], dtype=float)
    weight = 1.0 / np.sqrt(np.maximum(y, 1.0))
    centered_x = x - x.mean()
    profile: list[tuple[float, float, float, float]] = []

    for centroid in centroid_grid:
        best = (float("inf"), float("nan"), float("nan"))
        for sigma in sigma_grid:
            gaussian = np.exp(-0.5 * ((x - centroid) / sigma) ** 2)
            design = np.column_stack([np.ones(len(x)), centered_x, gaussian])
            coefficients = np.linalg.lstsq(
                design * weight[:, None], y * weight, rcond=None
            )[0]
            model = design @ coefficients
            if coefficients[2] <= 0.0 or np.any(model <= 0.0):
                continue
            statistic = float(np.sum((y - model) ** 2 / np.maximum(model, 1.0)))
            if statistic < best[0]:
                best = (statistic, float(sigma), float(coefficients[2]))
        profile.append((best[0], float(centroid), best[1], best[2]))

    best = min(profile)
    interval = [entry[1] for entry in profile if entry[0] <= best[0] + 1.0]
    null_design = np.column_stack([np.ones(len(x)), centered_x])
    null_coefficients = np.linalg.lstsq(
        null_design * weight[:, None], y * weight, rcond=None
    )[0]
    null_model = null_design @ null_coefficients
    null_statistic = float(
        np.sum((y - null_model) ** 2 / np.maximum(null_model, 1.0))
    )
    return {
        "centroid_channel": best[1],
        "sigma_channel": best[2],
        "amplitude_counts_per_channel": best[3],
        "profile_68_low_channel": min(interval),
        "profile_68_high_channel": max(interval),
        "peak_statistic": best[0],
        "linear_background_statistic": null_statistic,
        "delta_statistic": null_statistic - best[0],
    }


def _low_energy_model_sensitivity(counts: np.ndarray) -> tuple[float, float]:
    """Return the centroid envelope across simple low-energy peak descriptions."""

    estimates: list[float] = []
    variants = ((0, 12, 0), (0, 12, 1), (0, 14, 0), (0, 14, 1),
                (0, 16, 0), (0, 16, 1), (1, 14, 0), (1, 14, 1),
                (2, 14, 0), (2, 14, 1))
    for low, high, background_degree in variants:
        x = np.arange(low, high + 1, dtype=float)
        y = np.asarray(counts[low : high + 1], dtype=float)
        weight = 1.0 / np.sqrt(np.maximum(y, 1.0))
        best = (float("inf"), float("nan"))
        for centroid in np.linspace(3.0, 9.0, 241):
            for sigma in np.linspace(1.0, 6.0, 101):
                background = np.column_stack(
                    [x ** degree for degree in range(background_degree + 1)]
                )
                gaussian = np.exp(-0.5 * ((x - centroid) / sigma) ** 2)
                design = np.column_stack([background, gaussian])
                coefficients = np.linalg.lstsq(
                    design * weight[:, None], y * weight, rcond=None
                )[0]
                model = design @ coefficients
                if coefficients[-1] <= 0.0 or np.any(model <= 0.0):
                    continue
                statistic = float(
                    np.sum((y - model) ** 2 / np.maximum(model, 1.0))
                )
                if statistic < best[0]:
                    best = (statistic, float(centroid))
        estimates.append(best[1])
    return min(estimates), max(estimates)


def compute_flight_feature_diagnostics(
    held_out: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return cautious centroid diagnostics for the two named flight features."""

    counts, flight_maxima, device_id = _load_aggregate_flight_counts()
    near_511 = _profile_gaussian_plus_linear(
        counts,
        175,
        225,
        np.linspace(195.0, 209.0, 281),
        np.linspace(3.0, 18.0, 151),
    )
    centroid = near_511["centroid_channel"]
    lower_channel = near_511["profile_68_low_channel"]
    upper_channel = near_511["profile_68_high_channel"]
    local_validation = [
        abs(float(row["residual_predicted_minus_assigned_keV"]))
        for row in held_out
        if row["near_511_context"] == "yes"
    ]

    low_model_min, low_model_max = _low_energy_model_sensitivity(counts)
    maximum_channels = [int(row["maximum_channel_0_to_12"]) for row in flight_maxima]
    return [
        {
            "feature": "four-flight broad feature near 511 keV",
            "status": "descriptive candidate; physical identity not established",
            "scope": f"four public flights; one detector ({device_id})",
            "method": "Gaussian plus linear background; raw channels summed before applying working calibration",
            "centroid_channel": round(centroid, 6),
            "centroid_working_energy_keV": round(energy_keV(centroid), 6),
            "counting_stat_profile_68_low_keV": round(energy_keV(lower_channel), 6),
            "counting_stat_profile_68_high_keV": round(energy_keV(upper_channel), 6),
            "nearby_held_out_max_abs_residual_keV": round(max(local_validation), 6),
            "model_sensitivity_energy_span_keV": "",
            "descriptive_maximum_energy_span_keV": "",
            "delta_pearson_chi_square_vs_linear_background": round(
                near_511["delta_statistic"], 6
            ),
            "caveat": (
                "Approximate statistical interval excludes calibration/model "
                "systematics and assumes stable raw-channel response across "
                "acquisitions; a centroid near 511 keV does not identify "
                "annihilation radiation."
            ),
        },
        {
            "feature": "threshold-adjacent low-energy structure (previously described as ~19 keV)",
            "status": "no precision centroid reported",
            "scope": f"four public flights; one detector ({device_id})",
            "method": "per-flight channel maxima plus simple Gaussian/background sensitivity scan",
            "centroid_channel": "",
            "centroid_working_energy_keV": "",
            "counting_stat_profile_68_low_keV": "",
            "counting_stat_profile_68_high_keV": "",
            "nearby_held_out_max_abs_residual_keV": "",
            "model_sensitivity_energy_span_keV": (
                f"{energy_keV(low_model_min):.6f}-{energy_keV(low_model_max):.6f}"
            ),
            "descriptive_maximum_energy_span_keV": (
                f"{energy_keV(min(maximum_channels)):.6f}-"
                f"{energy_keV(max(maximum_channels)):.6f}"
            ),
            "delta_pearson_chi_square_vs_linear_background": "",
            "caveat": (
                "The structure is threshold-adjacent, below the 59.5-keV lowest "
                "anchor, and its fitted centroid changes with window/background choice."
            ),
        },
    ]


def build_validation_products() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    anchors = compute_anchor_uncertainties()
    held_out = compute_held_out_validation(anchors)
    features = compute_flight_feature_diagnostics(held_out)
    near_511_residuals = [
        abs(float(row["residual_predicted_minus_assigned_keV"]))
        for row in held_out
        if row["near_511_context"] == "yes"
    ]
    summary = {
        "calibration_id": "manual_primary_quadratic_2026-08-21",
        "status": "working_not_final",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "anchor_count": len(anchors),
        "anchor_energy_range_keV": [
            min(float(row["assigned_energy_keV"]) for row in anchors),
            max(float(row["assigned_energy_keV"]) for row in anchors),
        ],
        "leave_one_peak_out": {
            "fold_count": len(held_out),
            "near_511_context_lines_keV": [583.187, 609.312],
            "near_511_context_max_absolute_residual_keV": round(
                max(near_511_residuals), 6
            ),
        },
        "interpretation": {
            "near_511_keV": (
                "A four-flight detector-spectrum centroid can be described with a "
                "counting-statistical interval, but the nearby held-out residual and "
                "unmodeled response systematics preclude isotope identification. "
                "The raw-channel aggregation assumes stable detector response across "
                "the four acquisitions."
            ),
            "low_energy_structure": (
                "No precision centroid is reported: the structure is below the lowest "
                "anchor, threshold-adjacent, and model-dependent."
            ),
        },
    }
    return anchors, held_out, features, summary


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_validation_products(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    anchors, held_out, features, summary = build_validation_products()
    _write_csv(output_dir / OUTPUT_NAMES[0], anchors)
    _write_csv(output_dir / OUTPUT_NAMES[1], held_out)
    _write_csv(output_dir / OUTPUT_NAMES[2], features)
    summary_path = output_dir / OUTPUT_NAMES[3]
    with summary_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--force", action="store_true", help="Replace committed validation products.")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Regenerate in a temporary directory and compare with committed products.",
    )
    args = parser.parse_args()

    if args.check:
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary)
            write_validation_products(generated)
            failures: list[str] = []
            for name in OUTPUT_NAMES:
                committed = VALIDATION_DIR / name
                if not committed.is_file():
                    failures.append(f"missing committed output: {committed.relative_to(REPO)}")
                elif committed.read_bytes() != (generated / name).read_bytes():
                    failures.append(f"committed output differs: {committed.relative_to(REPO)}")
            if failures:
                for failure in failures:
                    print(f"ERROR: {failure}")
                return 1
        print(f"Peak validation check passed: {len(OUTPUT_NAMES)} deterministic products.")
        return 0

    existing = [VALIDATION_DIR / name for name in OUTPUT_NAMES if (VALIDATION_DIR / name).exists()]
    if existing and not args.force:
        print("ERROR: validation outputs already exist; use --force to replace or --check to verify")
        return 1
    write_validation_products(VALIDATION_DIR)
    print(f"Wrote {len(OUTPUT_NAMES)} peak-validation products to {VALIDATION_DIR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
