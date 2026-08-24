#!/usr/bin/env python3
"""Export RadiaCode XML spectra with the working manual-primary calibration.

The script batch-converts the ``source_spectra`` XML files to CSV using:

    E_keV(c) = 5.151420584 + 2.431018093*c + 0.000374694301*c^2

where c is the zero-based RadiaCode channel index.

By default, each CSV contains the two plotting columns ``Energy_keV`` and
``Counts``. Setting ``INCLUDE_DIAGNOSTIC_COLUMNS`` to ``True`` also exports
``Channel``, ``Original_XML_Energy_keV``, and ``Energy_Shift_keV``.

The XML channel index is the source of truth. The OPUS +4 label correction is
not applied because it was an artifact of the spreadsheet export. ``--check``
verifies the committed outputs without replacing them; ``--force`` explicitly
replaces the canonical files.
"""

from __future__ import annotations

import argparse
import csv
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Optional


# Working manual-primary calibration and export settings.
# E_keV(c) = A + B*c + Q*c^2
CAL_A = 5.151420584
CAL_B = 2.431018093
CAL_Q = 0.000374694301

INPUT_FOLDER_NAME = "source_spectra"
OUTPUT_FOLDER_NAME = "energy_converted_spectra"

# True: export diagnostic columns in addition to Energy_keV and Counts.
# False: export only Energy_keV and Counts.
INCLUDE_DIAGNOSTIC_COLUMNS = False

# Number of digits after the decimal point for energy values.
ENERGY_DECIMALS = 6


# XML parsing helpers.

def strip_namespace(tag: str) -> str:
    """Return an XML tag name without namespace."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def iter_elements_by_local_name(root: ET.Element, local_name: str) -> Iterable[ET.Element]:
    """Yield all elements whose local tag name matches local_name, ignoring namespaces."""
    for elem in root.iter():
        if strip_namespace(elem.tag) == local_name:
            yield elem


def first_text_by_local_name(root: ET.Element, local_name: str) -> Optional[str]:
    """Return the text of the first matching local-name element, or None."""
    for elem in iter_elements_by_local_name(root, local_name):
        return elem.text
    return None


def find_first_by_local_name(root: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Return the first matching local-name element, or None."""
    for elem in iter_elements_by_local_name(root, local_name):
        return elem
    return None


def parse_spectrum_counts(root: ET.Element) -> list[int]:
    """
    Extract the spectrum counts from the first <Spectrum> element.

    RadiaCode XML spectrum files typically store counts as:

        <EnergySpectrum>
            ...
            <Spectrum>
                <DataPoint>...</DataPoint>
                ...
            </Spectrum>
        </EnergySpectrum>

    This function looks for the first local-name Spectrum element that contains
    DataPoint children.
    """
    for spectrum_elem in iter_elements_by_local_name(root, "Spectrum"):
        datapoints = [
            dp.text for dp in spectrum_elem
            if strip_namespace(dp.tag) == "DataPoint"
        ]
        if datapoints:
            counts = []
            for value in datapoints:
                if value is None:
                    counts.append(0)
                else:
                    counts.append(int(float(value.strip())))
            return counts

    raise ValueError("No <Spectrum> element with <DataPoint> children was found.")


def parse_original_xml_calibration(root: ET.Element) -> Optional[tuple[float, float, float]]:
    """
    Extract the original XML quadratic calibration coefficients, if present.

    Returns (a, b, q) for E = a + b*c + q*c^2.
    If fewer than 3 coefficients are present, returns None.
    """
    energy_cal = find_first_by_local_name(root, "EnergyCalibration")
    if energy_cal is None:
        return None

    coefficients = []
    for elem in energy_cal.iter():
        if strip_namespace(elem.tag) == "Coefficient" and elem.text is not None:
            try:
                coefficients.append(float(elem.text.strip()))
            except ValueError:
                pass

    if len(coefficients) >= 3:
        return coefficients[0], coefficients[1], coefficients[2]

    return None


def parse_metadata(root: ET.Element) -> dict[str, str]:
    """Extract a few useful metadata fields if present."""
    metadata = {}
    for key in [
        "Name",
        "SpectrumName",
        "SerialNumber",
        "StartTime",
        "EndTime",
        "MeasurementTime",
        "NumberOfChannels",
    ]:
        value = first_text_by_local_name(root, key)
        if value is not None:
            metadata[key] = value.strip()
    return metadata


# Calibration and output helpers.

def recommended_energy_keV(channel: int) -> float:
    """Current working manual-primary calibration."""
    c = float(channel)
    return CAL_A + CAL_B * c + CAL_Q * c * c


def polynomial_energy_keV(channel: int, coeffs: tuple[float, float, float]) -> float:
    """Evaluate E = a + b*c + q*c^2."""
    a, b, q = coeffs
    c = float(channel)
    return a + b * c + q * c * c


def canonical_output_path(output_dir: Path, xml_path: Path) -> Path:
    """Return the deterministic output path for one XML source spectrum."""

    return output_dir / f"{xml_path.stem}_energy_calibrated.csv"


def write_csv(
    csv_path: Path,
    counts: list[int],
    original_coeffs: Optional[tuple[float, float, float]],
    metadata: dict[str, str],
) -> None:
    """Write the recalibrated spectrum to CSV."""
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")

        # Metadata as commented rows. Excel will still open these, and OPUS/other
        # software can ignore or skip them if needed.
        writer.writerow(["# RadiaCode XML energy-recalibrated spectrum"])
        writer.writerow(["# Calibration", f"E_keV = {CAL_A} + {CAL_B}*c + {CAL_Q}*c^2"])
        writer.writerow(["# Channel indexing", "zero-based RadiaCode XML channel index"])
        for key, value in metadata.items():
            writer.writerow([f"# {key}", value])

        if original_coeffs is not None:
            a, b, q = original_coeffs
            writer.writerow(["# Original_XML_Calibration", f"E_keV = {a} + {b}*c + {q}*c^2"])
        else:
            writer.writerow(["# Original_XML_Calibration", "not found"])

        writer.writerow([])

        if INCLUDE_DIAGNOSTIC_COLUMNS:
            writer.writerow([
                "Energy_keV",
                "Counts",
                "Channel",
                "Original_XML_Energy_keV",
                "Energy_Shift_keV",
            ])
        else:
            writer.writerow(["Energy_keV", "Counts"])

        for channel, count in enumerate(counts):
            e_new = recommended_energy_keV(channel)

            if INCLUDE_DIAGNOSTIC_COLUMNS:
                if original_coeffs is not None:
                    e_old = polynomial_energy_keV(channel, original_coeffs)
                    shift = e_new - e_old
                    writer.writerow([
                        f"{e_new:.{ENERGY_DECIMALS}f}",
                        count,
                        channel,
                        f"{e_old:.{ENERGY_DECIMALS}f}",
                        f"{shift:.{ENERGY_DECIMALS}f}",
                    ])
                else:
                    writer.writerow([
                        f"{e_new:.{ENERGY_DECIMALS}f}",
                        count,
                        channel,
                        "",
                        "",
                    ])
            else:
                writer.writerow([f"{e_new:.{ENERGY_DECIMALS}f}", count])


def process_xml_file(xml_path: Path, output_dir: Path, *, overwrite: bool = False) -> Path:
    """Parse one XML file and write the recalibrated CSV."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    counts = parse_spectrum_counts(root)
    original_coeffs = parse_original_xml_calibration(root)
    metadata = parse_metadata(root)

    # Basic consistency warning only; do not stop processing.
    number_of_channels_text = metadata.get("NumberOfChannels")
    if number_of_channels_text:
        try:
            expected_n = int(float(number_of_channels_text))
            if expected_n != len(counts):
                print(
                    f"  Warning: {xml_path.name}: XML says NumberOfChannels={expected_n}, "
                    f"but found {len(counts)} DataPoint values."
                )
        except ValueError:
            pass

    csv_path = canonical_output_path(output_dir, xml_path)
    if csv_path.exists() and not overwrite:
        raise FileExistsError(f"{csv_path.name} exists; use --force to replace or --check to verify")
    write_csv(csv_path, counts, original_coeffs, metadata)
    return csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    script_dir = Path(__file__).resolve().parent
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir / OUTPUT_FOLDER_NAME,
        help="Destination for deterministic energy-calibrated CSV files.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--force", action="store_true", help="Replace canonical output files.")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Regenerate in a temporary directory and compare with committed outputs.",
    )
    args = parser.parse_args()
    input_dir = script_dir / INPUT_FOLDER_NAME
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_files = sorted(
        p for p in input_dir.glob("*.xml")
        if p.is_file()
    )

    if not xml_files:
        print(f"No .xml files found in: {input_dir}")
        return 0

    print(f"Found {len(xml_files)} XML file(s) in: {input_dir}")
    print(f"{'Checking' if args.check else 'Writing'} recalibrated CSV files in: {output_dir}")
    print()

    success_count = 0
    failure_count = 0

    temporary = tempfile.TemporaryDirectory() if args.check else None
    work_dir = Path(temporary.name) if temporary is not None else output_dir
    try:
        for xml_path in xml_files:
            print(f"Processing: {xml_path.name}")
            try:
                csv_path = process_xml_file(xml_path, work_dir, overwrite=args.force)
                if args.check:
                    committed = canonical_output_path(output_dir, xml_path)
                    if not committed.is_file():
                        raise FileNotFoundError(f"committed output missing: {committed.name}")
                    if csv_path.read_bytes() != committed.read_bytes():
                        raise ValueError(f"committed output differs: {committed.name}")
                    print(f"  Verified: {committed.name}")
                else:
                    print(f"  Wrote: {csv_path.name}")
                success_count += 1
            except Exception as exc:
                print(f"  ERROR: {exc}")
                failure_count += 1
    finally:
        if temporary is not None:
            temporary.cleanup()

    print()
    print(f"Done. Successful: {success_count}; Failed: {failure_count}")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
