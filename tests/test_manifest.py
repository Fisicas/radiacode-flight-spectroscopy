import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from radiacode_flight.manifest import _parse_kml, validate_manifest


ROOT = Path(__file__).parents[1]


class ManifestTests(unittest.TestCase):
    def test_example_manifest_has_no_errors(self):
        issues = validate_manifest(ROOT / "config" / "example_manifest.csv")
        self.assertFalse([issue for issue in issues if issue.level == "ERROR"])

    def test_example_manifest_warns_for_small_fixture_channel_count(self):
        issues = validate_manifest(ROOT / "config" / "example_manifest.csv")
        self.assertTrue(any(issue.level == "WARNING" and "channelCount" in issue.message for issue in issues))

    def test_public_snapshot_manifest_validates_detectors_without_tracks(self):
        issues = validate_manifest(ROOT / "config" / "four_flights.csv")
        self.assertFalse([issue for issue in issues if issue.level == "ERROR"])
        omitted = [issue for issue in issues if "track file omitted" in issue.message]
        self.assertEqual(len(omitted), 4)

    def test_kml_parser_reports_unsorted_and_duplicate_timestamps(self):
        body = """<?xml version="1.0"?>
<kml xmlns:gx="http://www.google.com/kml/ext/2.2"><Document><Placemark><gx:Track>
<when>2026-01-01T00:00:02Z</when><when>2026-01-01T00:00:01Z</when><when>2026-01-01T00:00:01Z</when>
<gx:coord>-84 33 1000</gx:coord><gx:coord>-84 33 1001</gx:coord><gx:coord>-84 33 1002</gx:coord>
</gx:Track></Placemark></Document></kml>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "track.kml"
            path.write_text(body, encoding="utf-8")
            start, end, count, warnings = _parse_kml(path)
        self.assertLess(start, end)
        self.assertEqual(count, 3)
        self.assertTrue(any("not sorted" in warning for warning in warnings))
        self.assertTrue(any("duplicates" in warning for warning in warnings))

    def test_bad_detector_hash_is_an_error(self):
        columns = [
            "flight_key", "route", "detector_file", "track_file",
            "detector_sha256", "track_sha256", "calibration_manifest_id",
            "analysis_config_version",
        ]
        row = {
            "flight_key": "BAD_HASH",
            "route": "fixture",
            "detector_file": str(ROOT / "data" / "example" / "example.rcspg"),
            "track_file": "",
            "detector_sha256": "0" * 64,
            "track_sha256": "",
            "calibration_manifest_id": "embedded_example",
            "analysis_config_version": "0.1.0",
        }
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                writer.writerow(row)
            issues = validate_manifest(manifest, root=ROOT)
        self.assertTrue(any(issue.level == "ERROR" and "SHA-256" in issue.message for issue in issues))


if __name__ == "__main__":
    unittest.main()
