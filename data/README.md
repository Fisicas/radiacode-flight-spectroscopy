# Data policy and track acquisition

## What this snapshot includes

The repository includes four original RadiaCode `.rcspg` spectrograms under
`data/raw/`. The project author has explicitly chosen to publish the detector
serial number and acquisition/travel dates contained in these files. Their
SHA-256 checksums are recorded in `config/four_flights.csv` and
`data/raw/SHA256SUMS.txt`.

The corresponding FlightAware `.kml` tracks were used in the local analysis
but are **not redistributed**. Their flight identifiers, dates, routes, and
original KML checksums are recorded in
[`config/flight_track_sources.csv`](../config/flight_track_sources.csv). The
derived tables, figures, and animations are included for noncommercial academic
review but remain excluded from the repository's MIT and CC BY 4.0 licenses.

## Access a FlightAware track for permitted local use

These steps document how the original inputs were obtained; they are not a
license or a grant of downstream rights. For each flight listed below:

1. Open [FlightAware](https://www.flightaware.com/) and search the flight
   designator.
2. Open the history entry matching the date and route.
3. Scroll to the **Flight Track Log**.
4. Click **`+GoogleEarth`** below the track log to download the KML file.
5. Keep the downloaded file outside the public repository, or place it under
   ignored `data/private/`, and reference it from a local manifest.
6. Review [FlightAware's current Terms of Use](https://www.flightaware.com/about/terms-of-use)
   before using the downloaded data, and do not commit or share the raw KML.

| Flight key | Flight | FlightAware date | Route |
|---|---|---:|---|
| `MSP_MSP-ATL` | DAL1052 | 2026-06-21 | KMSP → KATL |
| `LGA_ATL-LGA` | AAL4605 | 2026-07-03 | KATL → KLGA |
| `LGA_LGA-ATL` | DAL342 | 2026-07-06 | KLGA → KATL |
| `OMA_ATL-OMA` | DAL2707 | 2026-08-07 | KATL → KOMA |

Historical access may depend on FlightAware account level and retention. A
fresh download may not be byte-identical to the file used in this analysis;
compare it with the recorded SHA-256 when exact reproduction matters.

## Expected KML structure

The validator expects a Google Earth KML track containing paired UTC timestamps
and coordinates:

```xml
<when>2026-08-08T02:53:36Z</when>
<gx:coord>-84.42 33.64 300.0</gx:coord>
```

There must be at least two points, timestamps must include a UTC offset, and
longitude, latitude, and altitude must be plausible. The validator reports
unsorted or duplicate timestamps and checks UTC overlap with detector records.

FlightAware's field is described here as **track-reported altitude** because
this snapshot does not independently establish whether it is GPS/geometric or
pressure altitude. ISA-equivalent pressure and column depth are modeled from
that reported altitude; neither is measured cabin pressure.

## Contributor consent

Contributors must make an explicit, informed decision about publication. A
submitted detector file may expose device serial number, acquisition timestamps,
and other metadata; a submitted track may expose detailed travel. Contributions
should state whether those fields may be public. Do not commit a third-party
track unless its license or terms permit redistribution.

The synthetic files in `data/example/` exist so parser and overlap tests can run
without flight data. Private or unreviewed inputs belong under ignored
`data/private/` or outside the repository.

## Licensing boundary

The root MIT license covers original code and workflow-documentation text, but
not embedded third-party or track-derived material. The four project-owned
detector files are covered by the repository's
[CC BY 4.0 data license](../LICENSE-DATA.md). That license does not extend to
FlightAware data or to the pressure/depth tables, figures, and animations that
derive from FlightAware-reported track altitude.

The included non-raw derivative products carry this notice:

> Contains FlightAware data © FlightAware LLC 2026. FlightAware data and
> trademarks are excluded from the repository’s MIT and CC BY 4.0 licenses.
> This independent project is not affiliated with or endorsed by FlightAware.

Each future contribution must document its source, consent, applicable terms,
and the contributor's authority to license the submitted detector data.
