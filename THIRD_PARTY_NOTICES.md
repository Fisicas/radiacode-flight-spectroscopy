# Third-party notices and rights boundaries

This file records third-party sources and terms relevant to the repository. It
does not replace those terms or grant rights in third-party material.
The project's license files allocate only rights the project author controls;
they do not override contractual restrictions attached to a data source.

## FlightAware

The local analysis used tracks downloaded interactively from FlightAware. No
downloaded FlightAware KML file is included in this repository. Nevertheless,
`data/derived/`, Figures 02 and 04–06, and the route/altitude animation products
incorporate or derive from FlightAware website data.

The project author has elected to publish those non-raw derivative artifacts
for noncommercial academic review while keeping all FlightAware material
outside the repository's open licenses. The following notice applies:

> Contains FlightAware data © FlightAware LLC 2026. FlightAware data and
> trademarks are excluded from the repository’s MIT and CC BY 4.0 licenses.
> This independent project is not affiliated with or endorsed by FlightAware.

This notice identifies the source and prevents the repository licenses from
being read as a sublicense of FlightAware material. It does not itself grant or
evidence a FlightAware license. The project author accepts that FlightAware may
request modification or removal of affected material.

As reviewed on 2026-08-23, FlightAware's website Terms of Use characterize its
no-charge web products and data as licensed solely for personal use and restrict
public display, distribution, and derivative works unless specifically
permitted. Educational, scientific, or noncommercial labeling does not by
itself supply that permission.

FlightAware separately publishes an AeroAPI Personal License that describes
certain academic uses and publication of non-raw data within a bona fide
academic setting. The inputs in this project were obtained from the interactive
website rather than under that AeroAPI license, so this project does not claim
that agreement as the source license for these artifacts.

- Terms of Use: <https://www.flightaware.com/about/terms-of-use>
- AeroAPI Personal License (January 2025):
  <https://www.flightaware.com/commercial/aeroapi/AeroAPI_Personal_License_Jan2025.pdf>
- Commercial and data licensing: <https://www.flightaware.com/commercial/>

FlightAware and its marks belong to their respective owner. This project is not
affiliated with or endorsed by FlightAware.

## RadiaCode

The detector and calibration measurements were created by the project author
using a personally controlled RadiaCode-103. The repository does not contain
RadiaCode application code, application screenshots, or vendor documentation.
It links to vendor documentation for technical context.

RadiaCode is a trademark of RADIACODE LTD. This independent project is not
affiliated with or endorsed by RADIACODE LTD.

- End-User License Agreement: <https://www.radiacode.com/legal/eula>
- Documentation: <https://radiacode.com/docs/en/100-series/>

## Natural Earth

The geographic backgrounds rendered in the route panels use Natural Earth map
data through Cartopy. Natural Earth states that its raster and vector map data
are in the public domain and that attribution is optional.

Made with Natural Earth. Free vector and raster map data at
<https://www.naturalearthdata.com/>.

## Python dependencies and GitHub Actions

The repository references, but does not vendor, NumPy, pandas, Pillow,
setuptools, pytest, `actions/checkout`, and `actions/setup-python`. Their own
distributions and repositories contain the controlling license notices.

- NumPy: BSD-3-Clause and permissive licenses for bundled components
- pandas: BSD-3-Clause and permissive licenses for bundled components
- Pillow: MIT-CMU license
- setuptools, pytest, `actions/checkout`, and `actions/setup-python`: MIT

## Scientific literature and vendor documentation

External papers and documentation are cited or linked. Their text, figures, and
PDFs are not redistributed by this repository. Those works remain subject to
their respective copyrights and terms.
