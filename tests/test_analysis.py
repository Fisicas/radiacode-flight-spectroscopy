import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_featured_flight_overflow import exact_poisson_interval, fit_models
from scripts.analyze_overflow_pressure import (
    _fit_nonnegative_floor_amplitude,
    fit_direct_exponential,
    fit_direct_exponential_floor,
)
from calibration.validate_peak_centroids import energy_keV


class AnalysisRegressionTests(unittest.TestCase):
    def test_floor_amplitude_fit_refits_the_active_boundary(self):
        exponential = np.array([1.0, 0.5, 0.25])
        response = np.array([1.0, 2.0, 3.0])

        floor, amplitude, prediction = _fit_nonnegative_floor_amplitude(
            exponential, response
        )

        self.assertAlmostEqual(floor, 2.0)
        self.assertAlmostEqual(amplitude, 0.0)
        np.testing.assert_allclose(prediction, np.full(3, 2.0))

    def test_pooled_exponentials_use_comparable_cps_scale_fits(self):
        data = pd.read_csv(ROOT / "data" / "derived" / "pressure_overflow_average.csv")
        common = data[data["common_all_four_legs"].astype(bool)]
        pressure = common["pressure_center_hpa"].to_numpy(float)
        response = common["overflow_cps_equal_flight"].to_numpy(float)

        _, zero_scale, zero_prediction = fit_direct_exponential(pressure, response)
        _, _, floor_scale, floor_prediction = fit_direct_exponential_floor(pressure, response)
        zero_rmse = float(np.sqrt(np.mean((response - zero_prediction) ** 2)))
        floor_rmse = float(np.sqrt(np.mean((response - floor_prediction) ** 2)))

        self.assertLess(zero_rmse, 0.02)
        self.assertTrue(150.0 < zero_scale < 160.0)
        self.assertLess(floor_rmse, zero_rmse)
        self.assertTrue(125.0 < floor_scale < 140.0)

    def test_featured_flight_aicc_and_exact_tail_interval(self):
        data = pd.read_csv(ROOT / "data" / "derived" / "pressure_overflow_by_flight.csv")
        data = data[data.flight_key.eq("OMA_ATL-OMA")].sort_values("pressure_bin_id")
        fits, _ = fit_models(
            data["column_depth_center_g_cm2"].to_numpy(float),
            data["overflow_counts"].to_numpy(float),
            data["live_time_s"].to_numpy(float),
        )
        best = fits["exponential_plus_floor"]
        zero = fits["exponential_zero_floor"]
        self.assertLess(float(best["aicc"]), float(zero["aicc"]))
        self.assertAlmostEqual(float(zero["aicc"]) - float(best["aicc"]), 3.3126, places=3)

        low, high = exact_poisson_interval(25)
        self.assertAlmostEqual(low / 721.0, 0.0224392, places=6)
        self.assertAlmostEqual(high / 721.0, 0.0511858, places=6)

    def test_committed_peak_validation_limits(self):
        validation = ROOT / "calibration" / "validation"
        features = pd.read_csv(validation / "flight_feature_centroid_diagnostics.csv")
        held_out = pd.read_csv(validation / "held_out_peak_validation.csv")

        candidate = features[features["feature"].str.contains("511")].iloc[0]
        low_energy = features[features["feature"].str.contains("threshold")].iloc[0]
        nearby = held_out[held_out["near_511_context"].eq("yes")]

        self.assertAlmostEqual(float(candidate["centroid_working_energy_keV"]), 510.989638, places=6)
        self.assertEqual(low_energy["status"], "no precision centroid reported")
        self.assertAlmostEqual(
            nearby["residual_predicted_minus_assigned_keV"].abs().max(),
            4.358767,
            places=6,
        )
        self.assertAlmostEqual(energy_keV(201.8), 510.989638, places=6)
