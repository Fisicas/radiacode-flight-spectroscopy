#!/usr/bin/env python3
"""Fit live-time-normalized overflow counts for the featured flight.

The response is modeled at the count level as

    n_i ~ Poisson(T_i * R(X_i))

where ``n_i`` is the overflow count in a pressure/depth bin, ``T_i`` is live
time, and ``X_i`` is atmospheric column depth.  The four requested rate
families are fit with the Poisson likelihood while retaining only non-negative
rates over the observed range.

The script has no SciPy dependency so that the analysis can be reproduced from
the compact CSV files with the repository's minimal runtime.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


DEPTH_PER_HPA = 1.019716
MODEL_ORDER = [
    "linear",
    "quadratic",
    "exponential_zero_floor",
    "exponential_plus_floor",
]
MODEL_COLORS = {
    "linear": "#2678B8",
    "quadratic": "#D95F02",
    "exponential_zero_floor": "#6A3D9A",
    "exponential_plus_floor": "#1B9E77",
}


def poisson_nll(counts: np.ndarray, exposure: np.ndarray, rate: np.ndarray) -> float:
    """Return Poisson negative log-likelihood, omitting log(n!) constants."""

    safe_rate = np.maximum(rate, 1e-12)
    return float(np.sum(exposure * safe_rate - counts * np.log(exposure * safe_rate)))


def poisson_deviance(
    counts: np.ndarray, exposure: np.ndarray, rate: np.ndarray
) -> float:
    """Return the Poisson deviance for predicted counts."""

    mu = np.maximum(exposure * rate, 1e-12)
    terms = np.where(
        counts > 0,
        counts * np.log(np.maximum(counts, 1e-12) / mu) - (counts - mu),
        mu,
    )
    return float(2.0 * np.sum(terms))


def poisson_cdf(k: int, mean: float) -> float:
    """Return P(N <= k) for a Poisson mean without a SciPy dependency."""

    if k < 0:
        return 0.0
    if mean < 0:
        raise ValueError("Poisson mean must be nonnegative")
    term = math.exp(-mean)
    total = term
    for value in range(1, k + 1):
        term *= mean / value
        total += term
    return min(max(total, 0.0), 1.0)


def poisson_mean_for_cdf(k: int, target: float) -> float:
    """Invert the Poisson CDF in its mean using monotone bisection."""

    if not 0.0 < target < 1.0:
        raise ValueError("target must lie strictly between zero and one")
    lo = 0.0
    hi = max(1.0, float(k + 1))
    while poisson_cdf(k, hi) > target:
        hi *= 2.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if poisson_cdf(k, mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def exact_poisson_interval(count: float, confidence: float = 0.95) -> tuple[float, float]:
    """Return the two-sided Garwood interval for an integer Poisson count."""

    integer_count = int(round(count))
    if abs(count - integer_count) > 1e-9 or integer_count < 0:
        raise ValueError("Exact Poisson intervals require a nonnegative integer count")
    alpha = 1.0 - confidence
    lower = 0.0
    if integer_count > 0:
        lower = poisson_mean_for_cdf(integer_count - 1, 1.0 - alpha / 2.0)
    upper = poisson_mean_for_cdf(integer_count, alpha / 2.0)
    return lower, upper


def aicc(aic: float, observations: int, parameters: int) -> float:
    """Return the small-sample corrected Akaike information criterion."""

    denominator = observations - parameters - 1
    if denominator <= 0:
        return float("inf")
    return aic + 2.0 * parameters * (parameters + 1) / denominator


def numerical_hessian(
    function: Callable[[np.ndarray], float], point: np.ndarray
) -> np.ndarray:
    """Finite-difference Hessian for approximate log-parameter uncertainty."""

    point = np.asarray(point, dtype=float)
    size = len(point)
    steps = 1e-4 * np.maximum(1.0, np.abs(point))
    result = np.zeros((size, size), dtype=float)
    center = function(point)
    for i in range(size):
        ei = np.zeros(size)
        ei[i] = steps[i]
        result[i, i] = (function(point + ei) - 2.0 * center + function(point - ei)) / steps[i] ** 2
        for j in range(i + 1, size):
            ej = np.zeros(size)
            ej[j] = steps[j]
            value = (
                function(point + ei + ej)
                - function(point + ei - ej)
                - function(point - ei + ej)
                + function(point - ei - ej)
            ) / (4.0 * steps[i] * steps[j])
            result[i, j] = value
            result[j, i] = value
    return result


def _newton_identity_rate(
    design: np.ndarray,
    counts: np.ndarray,
    exposure: np.ndarray,
    initial: np.ndarray | None = None,
    nonnegative_parameters: bool = False,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fit ``rate = design @ beta`` by Poisson-likelihood Newton steps.

    This is an identity-link Poisson model.  It is used for the requested
    linear and quadratic rate curves, and for the floor/amplitude subproblem
    at a fixed exponential scale.  Backtracking keeps fitted rates positive;
    the floor and amplitude subproblem also keeps both parameters nonnegative.
    """

    observed_rate = counts / np.maximum(exposure, 1e-12)
    if initial is None:
        weights = np.sqrt(np.maximum(exposure, 1.0))
        beta = np.linalg.lstsq(design * weights[:, None], observed_rate * weights, rcond=None)[0]
    else:
        beta = np.asarray(initial, dtype=float).copy()

    if not np.all(np.isfinite(beta)):
        beta = np.zeros(design.shape[1], dtype=float)
    if nonnegative_parameters:
        beta = np.maximum(beta, 1e-8)
    rate = design @ beta
    if np.any(rate <= 0) or not np.all(np.isfinite(rate)):
        beta = np.zeros(design.shape[1], dtype=float)
        beta[0] = max(float(np.sum(counts) / np.sum(exposure)), 1e-6)
        if nonnegative_parameters:
            beta = np.maximum(beta, 1e-8)
        rate = design @ beta
    if np.any(rate <= 0):
        beta = np.linalg.lstsq(design, np.maximum(observed_rate, 1e-8), rcond=None)[0]
        if nonnegative_parameters:
            beta = np.maximum(beta, 1e-8)
        rate = np.maximum(design @ beta, 1e-8)

    current = poisson_nll(counts, exposure, rate)
    for _ in range(120):
        safe_rate = np.maximum(rate, 1e-12)
        gradient = design.T @ (exposure - counts / safe_rate)
        hessian = design.T @ ((counts / safe_rate**2)[:, None] * design)
        try:
            step = np.linalg.solve(hessian + np.eye(hessian.shape[0]) * 1e-10, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        if not np.all(np.isfinite(step)) or np.linalg.norm(step) < 1e-9:
            break

        accepted = False
        for fraction in 0.5 ** np.arange(0, 24):
            candidate = beta - fraction * step
            if nonnegative_parameters and np.any(candidate < 0):
                continue
            candidate_rate = design @ candidate
            if np.any(candidate_rate <= 0) or not np.all(np.isfinite(candidate_rate)):
                continue
            candidate_nll = poisson_nll(counts, exposure, candidate_rate)
            if candidate_nll <= current + 1e-10:
                beta, rate, current = candidate, candidate_rate, candidate_nll
                accepted = True
                break
        if not accepted:
            break
        if np.linalg.norm(fraction * step) < 1e-8 * (1.0 + np.linalg.norm(beta)):
            break
    return beta, np.maximum(rate, 1e-12), current


def _golden_minimize(function: Callable[[float], float], lo: float, hi: float) -> float:
    """Minimize a scalar function on a bounded interval."""

    golden = (math.sqrt(5.0) - 1.0) / 2.0
    c = hi - golden * (hi - lo)
    d = lo + golden * (hi - lo)
    fc, fd = function(c), function(d)
    for _ in range(50):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - golden * (hi - lo)
            fc = function(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + golden * (hi - lo)
            fd = function(d)
    return (lo + hi) / 2.0


def _scale_candidates(depth: np.ndarray) -> np.ndarray:
    span = max(float(depth.max() - depth.min()), 1.0)
    lo = max(1.0, span / 100.0)
    hi = max(10_000.0, span * 100.0)
    return np.geomspace(lo, hi, 1800)


def fit_zero_floor_exponential(
    depth: np.ndarray, counts: np.ndarray, exposure: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fit ``R = A exp(-X/Lambda)`` with a one-dimensional scale search."""

    def fit_at_scale(scale: float) -> tuple[float, float]:
        z = np.exp(-depth / scale)
        amplitude = float(np.sum(counts) / np.sum(exposure * z))
        rate = amplitude * z
        return poisson_nll(counts, exposure, rate), amplitude

    candidates = _scale_candidates(depth)
    values = np.array([fit_at_scale(scale)[0] for scale in candidates])
    index = int(np.argmin(values))
    lo = math.log(candidates[max(0, index - 1)])
    hi = math.log(candidates[min(len(candidates) - 1, index + 1)])
    log_scale = _golden_minimize(lambda value: fit_at_scale(math.exp(value))[0], lo, hi)
    scale = math.exp(log_scale)
    _, amplitude = fit_at_scale(scale)
    rate = amplitude * np.exp(-depth / scale)
    return np.array([amplitude, scale]), rate


def fit_floor_plus_exponential(
    depth: np.ndarray, counts: np.ndarray, exposure: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fit ``R = B + A exp(-X/Lambda)`` with nonnegative B and A."""

    def fit_at_scale(scale: float) -> tuple[float, np.ndarray, np.ndarray]:
        z = np.exp(-depth / scale)
        initial_rate = counts / np.maximum(exposure, 1e-12)
        floor = max(float(np.min(initial_rate) * 0.3), 1e-8)
        amplitude = max(float(np.max(initial_rate) - floor), 1e-8)
        beta, rate, nll = _newton_identity_rate(
            np.column_stack((np.ones_like(z), z)),
            counts,
            exposure,
            initial=np.array([floor, amplitude]),
            nonnegative_parameters=True,
        )
        return nll, beta, rate

    candidates = _scale_candidates(depth)
    values = np.array([fit_at_scale(scale)[0] for scale in candidates])
    index = int(np.argmin(values))
    lo = math.log(candidates[max(0, index - 1)])
    hi = math.log(candidates[min(len(candidates) - 1, index + 1)])
    log_scale = _golden_minimize(lambda value: fit_at_scale(math.exp(value))[0], lo, hi)
    scale = math.exp(log_scale)
    _, beta, rate = fit_at_scale(scale)
    return np.array([beta[0], beta[1], scale]), rate


def fit_models(
    depth: np.ndarray, counts: np.ndarray, exposure: np.ndarray
) -> tuple[dict[str, dict[str, object]], pd.DataFrame]:
    """Fit all requested models and return model metadata plus predictions."""

    x = depth / 1000.0
    fits: dict[str, dict[str, object]] = {}

    linear_design = np.column_stack((np.ones_like(x), x))
    beta, rate, _ = _newton_identity_rate(linear_design, counts, exposure)
    fits["linear"] = {
        "parameters": beta,
        "rate": rate,
        "equation": "R = b0 + b1 * (X / 1000)",
    }

    quadratic_design = np.column_stack((np.ones_like(x), x, x**2))
    beta, rate, _ = _newton_identity_rate(quadratic_design, counts, exposure)
    fits["quadratic"] = {
        "parameters": beta,
        "rate": rate,
        "equation": "R = b0 + b1 * (X / 1000) + b2 * (X / 1000)^2",
    }

    parameters, rate = fit_zero_floor_exponential(depth, counts, exposure)
    fits["exponential_zero_floor"] = {
        "parameters": parameters,
        "rate": rate,
        "equation": "R = A * exp(-X / Lambda)",
    }

    parameters, rate = fit_floor_plus_exponential(depth, counts, exposure)
    fits["exponential_plus_floor"] = {
        "parameters": parameters,
        "rate": rate,
        "equation": "R = B + A * exp(-X / Lambda)",
    }

    prediction_rows: list[dict[str, float | str]] = []
    for model_name in MODEL_ORDER:
        model = fits[model_name]
        predicted = np.asarray(model["rate"], dtype=float)
        mu = exposure * predicted
        observed_rate = counts / exposure
        pearson = (counts - mu) / np.sqrt(np.maximum(mu, 1e-12))
        parameter_count = len(model["parameters"])
        model_aic = 2.0 * parameter_count + 2.0 * poisson_nll(counts, exposure, predicted)
        model.update(
            {
                "n_parameters": parameter_count,
                "nll": poisson_nll(counts, exposure, predicted),
                "aic": model_aic,
                "aicc": aicc(model_aic, len(counts), parameter_count),
                "deviance": poisson_deviance(counts, exposure, predicted),
                "deviance_df": len(counts) - parameter_count,
                "pearson_chi2": float(np.sum(pearson**2)),
                "pearson_rmse": float(np.sqrt(np.mean(pearson**2))),
                "rate_rmse_cps": float(np.sqrt(np.mean((observed_rate - predicted) ** 2))),
                "max_abs_pearson": float(np.max(np.abs(pearson))),
            }
        )
        if model_name in {"exponential_zero_floor", "exponential_plus_floor"}:
            parameters = np.asarray(model["parameters"], dtype=float)
            log_parameters = np.log(parameters)

            def nll_from_log(candidate: np.ndarray) -> float:
                values = np.exp(candidate)
                if model_name == "exponential_zero_floor":
                    candidate_rate = values[0] * np.exp(-depth / values[1])
                else:
                    candidate_rate = values[0] + values[1] * np.exp(-depth / values[2])
                return poisson_nll(counts, exposure, candidate_rate)

            hessian = numerical_hessian(nll_from_log, log_parameters)
            covariance = np.linalg.pinv(hessian)
            standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
            model["log_parameter_covariance"] = covariance
            model["parameter_ci95"] = np.column_stack(
                (
                    np.exp(log_parameters - 1.96 * standard_errors),
                    np.exp(log_parameters + 1.96 * standard_errors),
                )
            )
        for i, residual in enumerate(pearson):
            prediction_rows.append(
                {
                    "model": model_name,
                    "bin_index": int(i),
                    "predicted_overflow_cps": float(predicted[i]),
                    "predicted_overflow_counts": float(mu[i]),
                    "pearson_residual": float(residual),
                }
            )

    return fits, pd.DataFrame(prediction_rows)


def high_depth_summary(
    data: pd.DataFrame, fits: dict[str, dict[str, object]], threshold_hpa: float = 750.0
) -> dict[str, object]:
    tail = data[data["pressure_lo_hpa"] >= threshold_hpa].copy()
    counts = float(tail["overflow_counts"].sum())
    exposure = float(tail["live_time_s"].sum())
    rate = counts / exposure
    standard_error = math.sqrt(counts) / exposure
    exact_low_count, exact_high_count = exact_poisson_interval(counts)
    result: dict[str, object] = {
        "threshold_pressure_hpa": threshold_hpa,
        "threshold_depth_g_cm2": threshold_hpa * DEPTH_PER_HPA,
        "bins": int(len(tail)),
        "counts": counts,
        "live_time_s": exposure,
        "rate_cps": rate,
        "poisson_se_cps": standard_error,
        "exact_95_low_cps": exact_low_count / exposure,
        "exact_95_high_cps": exact_high_count / exposure,
    }
    for model_name in MODEL_ORDER:
        predicted = np.asarray(fits[model_name]["rate"], dtype=float)
        tail_index = data["pressure_lo_hpa"].to_numpy(float) >= threshold_hpa
        result[f"{model_name}_exposure_weighted_rate_cps"] = float(
            np.sum(predicted[tail_index] * data.loc[tail_index, "live_time_s"].to_numpy(float))
            / exposure
        )
    return result


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _draw_axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    draw.line((left, top, left, bottom), fill="#3A3A3A", width=2)
    draw.line((left, bottom, right, bottom), fill="#3A3A3A", width=2)


def _draw_vertical_label(
    image: Image.Image,
    text: str,
    center: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
) -> None:
    """Draw a centered vertical label without entering the plotting region."""

    bounds = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font)
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    scratch = Image.new("RGBA", (text_width + 16, text_height + 16), (255, 255, 255, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    scratch_draw.text((8 - bounds[0], 8 - bounds[1]), text, font=font, fill=fill)
    rotated = scratch.rotate(90, expand=True)
    image.paste(
        rotated,
        (center[0] - rotated.width // 2, center[1] - rotated.height // 2),
        rotated,
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    top_y: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
) -> None:
    """Draw text with its visual center aligned to ``center_x``."""

    bounds = draw.textbbox((0, 0), text, font=font)
    text_width = bounds[2] - bounds[0]
    draw.text((center_x - text_width // 2, top_y), text, font=font, fill=fill)


def make_figure(
    data: pd.DataFrame,
    fits: dict[str, dict[str, object]],
    output_path: Path,
    title: str = "Featured ATL → OMA flight: overflow response versus atmospheric depth",
) -> None:
    """Create a clean static figure without requiring Matplotlib."""

    width, height = 1800, 1100
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(34, bold=True)
    subtitle_font = _font(20)
    axis_font = _font(18)
    label_font = _font(21, bold=True)
    legend_font = _font(17)

    _draw_centered_text(draw, width // 2, 38, title, title_font, "#20252B")
    _draw_centered_text(
        draw,
        width // 2,
        86,
        "Overflow counts / live time; Poisson count likelihood; pressure retained as a display coordinate",
        subtitle_font,
        "#66717B",
    )

    left_box = (120, 185, 870, 880)
    right_box = (1010, 185, 1760, 880)
    _draw_axes(draw, left_box)
    _draw_axes(draw, right_box)

    depth = data["column_depth_center_g_cm2"].to_numpy(float)
    pressure = data["pressure_center_hpa"].to_numpy(float)
    observed = data["overflow_cps"].to_numpy(float)
    counts = data["overflow_counts"].to_numpy(float)
    exposure = data["live_time_s"].to_numpy(float)
    count_intervals = np.array([exact_poisson_interval(value) for value in counts])
    observed_low = count_intervals[:, 0] / exposure
    observed_high = count_intervals[:, 1] / exposure
    x_min, x_max = 200.0, 1020.0
    y_min, y_max = 0.0, max(1.4, float(np.max(observed_high) * 1.08))

    def map_x(value: float, box: tuple[int, int, int, int]) -> int:
        return int(box[0] + (value - x_min) / (x_max - x_min) * (box[2] - box[0]))

    def map_y(value: float, box: tuple[int, int, int, int], lo: float, hi: float) -> int:
        value = min(max(value, lo), hi)
        return int(box[3] - (value - lo) / (hi - lo) * (box[3] - box[1]))

    # Grid, depth ticks, and the pressure display coordinate.
    for tick in [250, 500, 750, 1000]:
        x = map_x(tick, left_box)
        draw.line((x, left_box[1], x, left_box[3]), fill="#E6E9EC", width=1)
        draw.text((x - 20, left_box[3] + 12), f"{tick}", font=axis_font, fill="#495057")
        p = tick / DEPTH_PER_HPA
        draw.text((x - 26, left_box[1] - 31), f"{p:.0f}", font=axis_font, fill="#6A3D9A")
    for tick in [0.0, 0.4, 0.8, 1.2]:
        y = map_y(tick, left_box, y_min, y_max)
        draw.line((left_box[0], y, left_box[2], y), fill="#E6E9EC", width=1)
        draw.text((left_box[0] - 58, y - 10), f"{tick:.1f}", font=axis_font, fill="#495057")

    # High-depth tail shading in both panels.
    tail_start = map_x(750 * DEPTH_PER_HPA, left_box)
    draw.rectangle((tail_start, left_box[1], left_box[2], left_box[3]), fill="#FFF4D6")
    draw.line((tail_start, left_box[1], tail_start, left_box[3]), fill="#D9A441", width=2)
    draw.text((tail_start + 8, left_box[1] + 10), "high-depth tail", font=legend_font, fill="#8A6419")

    for i, value in enumerate(observed):
        x = map_x(depth[i], left_box)
        y = map_y(value, left_box, y_min, y_max)
        y_lo = map_y(observed_low[i], left_box, y_min, y_max)
        y_hi = map_y(observed_high[i], left_box, y_min, y_max)
        draw.line((x, y_hi, x, y_lo), fill="#20252B", width=2)
        draw.line((x - 5, y_hi, x + 5, y_hi), fill="#20252B", width=2)
        draw.line((x - 5, y_lo, x + 5, y_lo), fill="#20252B", width=2)
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#20252B")

    grid_depth = np.linspace(x_min, x_max, 300)
    grid_x = grid_depth / 1000.0
    best_model = fits["exponential_plus_floor"]
    best_parameters = np.asarray(best_model["parameters"], dtype=float)
    best_covariance = np.asarray(best_model["log_parameter_covariance"], dtype=float)
    best_exponential = np.exp(-grid_depth / best_parameters[2])
    best_curve = best_parameters[0] + best_parameters[1] * best_exponential
    best_gradient = np.column_stack(
        (
            np.full_like(grid_depth, best_parameters[0]),
            best_parameters[1] * best_exponential,
            best_parameters[1] * best_exponential * grid_depth / best_parameters[2],
        )
    )
    best_variance = np.einsum("ij,jk,ik->i", best_gradient, best_covariance, best_gradient)
    best_standard_error = np.sqrt(np.maximum(best_variance, 0.0))
    band_low = np.maximum(0.0, best_curve - 1.96 * best_standard_error)
    band_high = best_curve + 1.96 * best_standard_error
    band_points = [
        (map_x(float(xv), left_box), map_y(float(yv), left_box, y_min, y_max))
        for xv, yv in zip(grid_depth, band_high)
    ] + [
        (map_x(float(xv), left_box), map_y(float(yv), left_box, y_min, y_max))
        for xv, yv in zip(grid_depth[::-1], band_low[::-1])
    ]
    draw.polygon(band_points, fill="#DDEFE5")
    for model_name in MODEL_ORDER:
        parameters = np.asarray(fits[model_name]["parameters"], dtype=float)
        if model_name == "linear":
            curve = parameters[0] + parameters[1] * grid_x
        elif model_name == "quadratic":
            curve = parameters[0] + parameters[1] * grid_x + parameters[2] * grid_x**2
        elif model_name == "exponential_zero_floor":
            curve = parameters[0] * np.exp(-grid_depth / parameters[1])
        else:
            curve = parameters[0] + parameters[1] * np.exp(-grid_depth / parameters[2])
        points = [
            (map_x(float(xv), left_box), map_y(float(yv), left_box, y_min, y_max))
            for xv, yv in zip(grid_depth, curve)
        ]
        draw.line(points, fill=MODEL_COLORS[model_name], width=4)

    _draw_centered_text(draw, (left_box[0] + left_box[2]) // 2, 920, "Atmospheric depth X (g cm⁻²)", label_font, "#20252B")
    _draw_centered_text(draw, (left_box[0] + left_box[2]) // 2, 120, "Pressure P (hPa)", axis_font, "#6A3D9A")
    _draw_vertical_label(image, "Overflow CPS", (48, (left_box[1] + left_box[3]) // 2), label_font, "#20252B")

    legend_items = [
        ("observed 95% exact Poisson CI", "#20252B"),
        ("linear", MODEL_COLORS["linear"]),
        ("quadratic", MODEL_COLORS["quadratic"]),
        ("zero-floor exponential", MODEL_COLORS["exponential_zero_floor"]),
        ("floor + exponential (95% mean band)", MODEL_COLORS["exponential_plus_floor"]),
    ]
    legend_y = 975
    legend_gap = 38
    legend_widths = []
    for label, _ in legend_items:
        bounds = draw.textbbox((0, 0), label, font=legend_font)
        legend_widths.append(28 + 12 + bounds[2] - bounds[0])
    total_legend_width = sum(legend_widths) + legend_gap * (len(legend_items) - 1)
    legend_x = (width - total_legend_width) // 2
    for (label, color), item_width in zip(legend_items, legend_widths):
        lx = legend_x
        ly = legend_y
        draw.line((lx, ly + 10, lx + 28, ly + 10), fill=color, width=4)
        if label.startswith("observed"):
            draw.ellipse((lx + 9, ly + 4, lx + 19, ly + 14), fill=color)
        draw.text((lx + 38, ly), label, font=legend_font, fill="#394047")
        legend_x += item_width + legend_gap

    # Residual panel.
    tail_start_right = map_x(750 * DEPTH_PER_HPA, right_box)
    draw.rectangle((tail_start_right, right_box[1], right_box[2], right_box[3]), fill="#FFF4D6")
    draw.line((tail_start_right, right_box[1], tail_start_right, right_box[3]), fill="#D9A441", width=2)
    residual_arrays: dict[str, np.ndarray] = {}
    for model_name in MODEL_ORDER:
        parameters = np.asarray(fits[model_name]["parameters"], dtype=float)
        if model_name == "linear":
            predicted = parameters[0] + parameters[1] * (depth / 1000.0)
        elif model_name == "quadratic":
            x = depth / 1000.0
            predicted = parameters[0] + parameters[1] * x + parameters[2] * x**2
        elif model_name == "exponential_zero_floor":
            predicted = parameters[0] * np.exp(-depth / parameters[1])
        else:
            predicted = parameters[0] + parameters[1] * np.exp(-depth / parameters[2])
        residual_arrays[model_name] = (counts - exposure * predicted) / np.sqrt(np.maximum(exposure * predicted, 1e-12))
    residual_limit = max(3.0, float(max(np.max(np.abs(v)) for v in residual_arrays.values()) * 1.12))
    for tick in [-2, 0, 2]:
        y = map_y(tick, right_box, -residual_limit, residual_limit)
        draw.line((right_box[0], y, right_box[2], y), fill="#E6E9EC" if tick else "#9299A0", width=1 if tick else 2)
        draw.text((right_box[0] - 42, y - 10), f"{tick}", font=axis_font, fill="#495057")
    for tick in [250, 500, 750, 1000]:
        x = map_x(tick, right_box)
        draw.line((x, right_box[1], x, right_box[3]), fill="#E6E9EC", width=1)
        draw.text((x - 20, right_box[3] + 12), f"{tick}", font=axis_font, fill="#495057")
    for model_name in MODEL_ORDER:
        values = residual_arrays[model_name]
        points = [(map_x(depth[i], right_box), map_y(float(values[i]), right_box, -residual_limit, residual_limit)) for i in range(len(depth))]
        draw.line(points, fill=MODEL_COLORS[model_name], width=3)
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=MODEL_COLORS[model_name])
    _draw_centered_text(draw, (right_box[0] + right_box[2]) // 2, 920, "Depth X (g cm⁻²)", label_font, "#20252B")
    _draw_centered_text(draw, (right_box[0] + right_box[2]) // 2, right_box[1] + 10, "Poisson-aware residuals", legend_font, "#495057")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)


def run_analysis(
    input_path: Path,
    output_dir: Path,
    figure_path: Path,
    flight_key: str = "OMA_ATL-OMA",
) -> dict[str, object]:
    data = pd.read_csv(input_path)
    data = data[data["flight_key"].eq(flight_key)].copy().sort_values("pressure_bin_id")
    if data.empty:
        raise ValueError(f"No rows found for flight_key={flight_key!r}")

    depth = data["column_depth_center_g_cm2"].to_numpy(float)
    counts = data["overflow_counts"].to_numpy(float)
    exposure = data["live_time_s"].to_numpy(float)
    if np.any(counts < 0) or np.any(exposure <= 0):
        raise ValueError("Counts must be nonnegative and live time must be positive")

    fits, predictions = fit_models(depth, counts, exposure)
    base = data[
        [
            "flight_key",
            "flight_label",
            "pressure_bin_id",
            "pressure_lo_hpa",
            "pressure_hi_hpa",
            "pressure_center_hpa",
            "column_depth_center_g_cm2",
            "live_time_s",
            "n_records",
            "overflow_counts",
            "overflow_cps",
            "overflow_cps_se_poisson",
        ]
    ].reset_index(drop=True)
    prediction_table = base.copy()
    for model_name in MODEL_ORDER:
        subset = predictions[predictions.model.eq(model_name)].sort_values("bin_index")
        prediction_table[f"{model_name}_predicted_overflow_cps"] = subset["predicted_overflow_cps"].to_numpy()
        prediction_table[f"{model_name}_predicted_overflow_counts"] = subset["predicted_overflow_counts"].to_numpy()
        prediction_table[f"{model_name}_pearson_residual"] = subset["pearson_residual"].to_numpy()

    model_rows = []
    for model_name in MODEL_ORDER:
        model = fits[model_name]
        params = np.asarray(model["parameters"], dtype=float)
        row: dict[str, object] = {
            "flight_key": flight_key,
            "model": model_name,
            "equation": model["equation"],
            "n_parameters": int(model["n_parameters"]),
            "nll": float(model["nll"]),
            "aic": float(model["aic"]),
            "aicc": float(model["aicc"]),
            "deviance": float(model["deviance"]),
            "deviance_df": int(model["deviance_df"]),
            "pearson_chi2": float(model["pearson_chi2"]),
            "pearson_rmse": float(model["pearson_rmse"]),
            "rate_rmse_cps": float(model["rate_rmse_cps"]),
            "max_abs_pearson": float(model["max_abs_pearson"]),
        }
        for index, value in enumerate(params):
            row[f"parameter_{index + 1}"] = float(value)
        if model_name == "exponential_zero_floor":
            row["amplitude_cps"] = float(params[0])
            row["scale_g_cm2"] = float(params[1])
            row["floor_cps"] = 0.0
            intervals = np.asarray(model["parameter_ci95"], dtype=float)
            row["amplitude_ci95_low_cps"] = float(intervals[0, 0])
            row["amplitude_ci95_high_cps"] = float(intervals[0, 1])
            row["scale_ci95_low_g_cm2"] = float(intervals[1, 0])
            row["scale_ci95_high_g_cm2"] = float(intervals[1, 1])
        elif model_name == "exponential_plus_floor":
            row["floor_cps"] = float(params[0])
            row["amplitude_cps"] = float(params[1])
            row["scale_g_cm2"] = float(params[2])
            intervals = np.asarray(model["parameter_ci95"], dtype=float)
            row["floor_ci95_low_cps"] = float(intervals[0, 0])
            row["floor_ci95_high_cps"] = float(intervals[0, 1])
            row["amplitude_ci95_low_cps"] = float(intervals[1, 0])
            row["amplitude_ci95_high_cps"] = float(intervals[1, 1])
            row["scale_ci95_low_g_cm2"] = float(intervals[2, 0])
            row["scale_ci95_high_g_cm2"] = float(intervals[2, 1])
        model_rows.append(row)
    model_table = pd.DataFrame(model_rows)
    model_table["delta_aic"] = model_table["aic"] - model_table["aic"].min()
    model_table["delta_aicc"] = model_table["aicc"] - model_table["aicc"].min()

    tail = high_depth_summary(data, fits)
    summary = {
        "flight_key": flight_key,
        "flight_label": str(data["flight_label"].iloc[0]),
        "source": str(input_path),
        "bins": int(len(data)),
        "pressure_range_hpa": [float(data["pressure_center_hpa"].min()), float(data["pressure_center_hpa"].max())],
        "depth_range_g_cm2": [float(depth.min()), float(depth.max())],
        "total_live_time_s": float(exposure.sum()),
        "total_overflow_counts": float(counts.sum()),
        "models": model_table.to_dict(orient="records"),
        "high_depth_tail": tail,
        "depth_per_hpa": DEPTH_PER_HPA,
        "aic_note": "AIC and AICc omit the shared log(n!) constant; compare deltas only within this dataset.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    model_table.to_csv(
        output_dir / "OMA_ATL-OMA_overflow_depth_models.csv",
        index=False,
        float_format="%.10g",
        lineterminator="\n",
    )
    prediction_table.to_csv(
        output_dir / "OMA_ATL-OMA_overflow_depth_predictions.csv",
        index=False,
        float_format="%.10g",
        lineterminator="\n",
    )
    with (output_dir / "OMA_ATL-OMA_overflow_depth_analysis.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(summary, handle, indent=2)
    make_figure(data, fits, figure_path)
    return {
        "data": data,
        "fits": fits,
        "model_table": model_table,
        "prediction_table": prediction_table,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--input",
        type=Path,
        default=repo / "data" / "derived" / "pressure_overflow_by_flight.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo / "data" / "derived",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=repo / "figures" / "presentation" / "figure_06_oma_atl_overflow_depth_response.png",
    )
    parser.add_argument("--flight-key", default="OMA_ATL-OMA")
    args = parser.parse_args()
    result = run_analysis(args.input, args.output_dir, args.figure, args.flight_key)
    table = result["model_table"]
    print(table[["model", "aic", "aicc", "delta_aicc", "deviance", "deviance_df", "pearson_rmse", "rate_rmse_cps"]].to_string(index=False))
    print(json.dumps(result["summary"]["high_depth_tail"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
