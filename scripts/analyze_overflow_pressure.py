#!/usr/bin/env python3
"""Compare overflow CPS with pressure and atmospheric column depth.

The default inputs are the compact derived tables committed under
``data/derived``. The script deliberately treats pressure and column depth as
alternative coordinates: in this dataset X = 1.019716 * P, so fitting both
predictors would be redundant.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def least_squares(design: np.ndarray, response: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    coefficients = np.linalg.lstsq(design, response, rcond=None)[0]
    return coefficients, design @ coefficients


def fit_direct_exponential(
    predictor: np.ndarray, response: np.ndarray
) -> tuple[float, float, np.ndarray]:
    """Fit ``response = amplitude * exp(-predictor / scale)`` in CPS space."""

    best: tuple[float, float, float, np.ndarray] | None = None
    for scale in np.geomspace(10.0, 5000.0, 10000):
        exponential = np.exp(-predictor / scale)
        denominator = float(exponential @ exponential)
        amplitude = max(float(exponential @ response) / denominator, 0.0)
        prediction = amplitude * exponential
        sse = float(np.sum((response - prediction) ** 2))
        if best is None or sse < best[0]:
            best = (sse, scale, amplitude, prediction)
    assert best is not None
    _, scale, amplitude, prediction = best
    return amplitude, scale, prediction


def _fit_nonnegative_floor_amplitude(
    exponential: np.ndarray,
    response: np.ndarray,
) -> tuple[float, float, np.ndarray]:
    """Solve a two-parameter non-negative least-squares problem exactly."""

    design = np.column_stack((np.ones_like(exponential), exponential))
    candidates: list[np.ndarray] = []

    unconstrained = np.linalg.lstsq(design, response, rcond=None)[0]
    if np.all(unconstrained >= 0.0):
        candidates.append(unconstrained)

    candidates.append(np.array([max(float(response.mean()), 0.0), 0.0]))
    denominator = float(exponential @ exponential)
    amplitude = max(float(exponential @ response) / denominator, 0.0)
    candidates.append(np.array([0.0, amplitude]))

    coefficients = min(
        candidates,
        key=lambda values: float(np.sum((response - design @ values) ** 2)),
    )
    return float(coefficients[0]), float(coefficients[1]), design @ coefficients


def fit_direct_exponential_floor(
    predictor: np.ndarray, response: np.ndarray
) -> tuple[float, float, float, np.ndarray]:
    """Fit response = floor + amplitude * exp(-predictor / scale).

    The one-dimensional scale search keeps this script dependency-light. For
    each candidate scale, the floor and amplitude are solved linearly and
    constrained to be non-negative.
    """

    best: tuple[float, float, float, float, np.ndarray] | None = None
    for scale in np.geomspace(10.0, 5000.0, 10000):
        exponential = np.exp(-predictor / scale)
        floor, amplitude, prediction = _fit_nonnegative_floor_amplitude(
            exponential, response
        )
        sse = float(np.sum((response - prediction) ** 2))
        if best is None or sse < best[0]:
            best = (sse, scale, floor, amplitude, prediction)

    assert best is not None
    _, scale, floor, amplitude, prediction = best
    return floor, amplitude, scale, prediction


def fit_flight_amplitude_exponential(
    predictor: np.ndarray,
    response: np.ndarray,
    flight_indicators: np.ndarray,
) -> tuple[np.ndarray, float, np.ndarray]:
    """Fit a common exponential scale with a separate amplitude per flight."""

    best: tuple[float, float, np.ndarray, np.ndarray] | None = None
    for scale in np.geomspace(10.0, 5000.0, 10000):
        exponential = np.exp(-predictor / scale)
        design = flight_indicators * exponential[:, None]
        amplitudes = np.maximum(np.linalg.lstsq(design, response, rcond=None)[0], 0.0)
        prediction = design @ amplitudes
        sse = float(np.sum((response - prediction) ** 2))
        if best is None or sse < best[0]:
            best = (sse, scale, amplitudes, prediction)
    assert best is not None
    _, scale, amplitudes, prediction = best
    return amplitudes, scale, prediction


def metrics(response: np.ndarray, prediction: np.ndarray, parameter_count: int) -> dict[str, float]:
    residual = response - prediction
    sse = float(np.sum(residual**2))
    sample_size = len(response)
    aic = float(sample_size * np.log(sse / sample_size) + 2 * parameter_count)
    denominator = sample_size - parameter_count - 1
    aicc = aic + 2.0 * parameter_count * (parameter_count + 1) / denominator
    return {
        "rmse_cps": float(np.sqrt(np.mean(residual**2))),
        "r2": float(1.0 - sse / np.sum((response - response.mean()) ** 2)),
        "aic_gaussian": aic,
        "aicc_gaussian": float(aicc),
    }


def analyze(average_path: Path, by_flight_path: Path) -> None:
    average = pd.read_csv(average_path)
    by_flight = pd.read_csv(by_flight_path)

    common_column = "common_all_four_legs"
    if common_column not in average.columns:
        common_column = "common_all_four"
    common = average[average[common_column].astype(bool)].copy()
    pressure = common["pressure_center_hpa"].to_numpy(float)
    depth = common["column_depth_center_g_cm2"].to_numpy(float)
    response = common["overflow_cps_equal_flight"].to_numpy(float)

    print(f"common four-flight bins: {len(common)}")
    print(f"pressure range: {pressure.min():.1f}-{pressure.max():.1f} hPa")
    print(f"depth range: {depth.min():.1f}-{depth.max():.1f} g cm^-2")

    for name, design in (
        ("linear_pressure", np.column_stack((np.ones_like(pressure), pressure))),
        ("quadratic_pressure", np.column_stack((np.ones_like(pressure), pressure, pressure**2))),
    ):
        coefficients, prediction = least_squares(design, response)
        print(name, coefficients, metrics(response, prediction, len(coefficients)))

    amplitude, scale_hpa, exponential_prediction = fit_direct_exponential(pressure, response)
    print(
        "exponential_no_floor",
        {"amplitude_cps": amplitude, "scale_hpa": scale_hpa},
        metrics(response, exponential_prediction, 2),
    )

    floor, amplitude, scale_hpa, prediction = fit_direct_exponential_floor(pressure, response)
    scale_depth = scale_hpa * (depth[0] / pressure[0])
    print(
        "exponential_plus_floor",
        {
            "floor_cps": floor,
            "amplitude_cps": amplitude,
            "scale_hpa": scale_hpa,
            "scale_g_cm2": scale_depth,
        },
        metrics(response, prediction, 3),
    )

    # A common slope with a separate intercept for each flight is a useful
    # check against one flight dominating the pooled curve.
    common_min = float(pressure.min())
    common_max = float(pressure.max())
    subset = by_flight[
        (by_flight["pressure_center_hpa"] >= common_min)
        & (by_flight["pressure_center_hpa"] <= common_max)
        & (by_flight["overflow_cps"] > 0)
    ].copy()
    flights = sorted(subset["flight_key"].unique())
    flight_index = {flight: index for index, flight in enumerate(flights)}
    rows = np.arange(len(subset))
    fixed_intercepts = np.zeros((len(subset), len(flights)))
    fixed_intercepts[rows, subset["flight_key"].map(flight_index).to_numpy(int)] = 1.0
    fixed_pressure = subset["pressure_center_hpa"].to_numpy(float)
    fixed_response = subset["overflow_cps"].to_numpy(float)
    fixed_design = np.column_stack((fixed_intercepts, fixed_pressure))
    fixed_coefficients, fixed_prediction = least_squares(fixed_design, fixed_response)
    print(
        "flight_fixed_effects_linear",
        {"common_slope_cps_per_hpa": fixed_coefficients[-1]},
        metrics(fixed_response, fixed_prediction, len(fixed_coefficients)),
    )
    amplitudes, fixed_scale_hpa, fixed_exponential_prediction = fit_flight_amplitude_exponential(
        fixed_pressure, fixed_response, fixed_intercepts
    )
    print(
        "flight_amplitudes_exponential",
        {
            "flight_amplitudes_cps": amplitudes.tolist(),
            "effective_scale_hpa": fixed_scale_hpa,
        },
        metrics(
            fixed_response,
            fixed_exponential_prediction,
            len(amplitudes) + 1,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--average",
        type=Path,
        default=repo / "data" / "derived" / "pressure_overflow_average.csv",
    )
    parser.add_argument(
        "--by-flight",
        type=Path,
        default=repo / "data" / "derived" / "pressure_overflow_by_flight.csv",
    )
    args = parser.parse_args()
    analyze(args.average, args.by_flight)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
