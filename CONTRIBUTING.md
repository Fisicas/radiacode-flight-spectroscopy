# Contributing

Contributions are welcome, especially detector observations accompanied by a
locally obtained flight track and enough metadata for comparison.

Before sharing a dataset, review travel metadata, detector identifiers,
privacy, calibration provenance, and the licensing or terms of the associated
flight track. FlightAware KML files must not be committed to this repository.

Contributors must explicitly confirm whether their detector serial number,
acquisition timestamps, and travel dates may be public. The current project
author has opted in for the four v0.1 detector files; that choice is not assumed
for anyone else. Keep an `.rcspg` private unless its contributor has opted in.

For a proposed matched flight pair, include the route, UTC date, detector
configuration, calibration identifier, analysis configuration, and checksums.
Record placement, orientation, aircraft, and cabin location as `not recorded`
when unavailable rather than leaving their status ambiguous. Provide the track
source and retrieval identifiers, but contribute the KML itself only when its
terms expressly allow redistribution.
Keep numerical products and explanatory figures clearly separated from raw
inputs, and preserve the cautious language used for the near-511-keV feature
and detector overflow channel.

Code and original documentation-text contributions are submitted under the
root MIT License, excluding any embedded third-party or track-derived material.
Detector-data contributors must explicitly confirm that they created or control
the submitted measurements and agree to the CC BY 4.0 terms in
`LICENSE-DATA.md`, unless a different compatible license is documented before
the contribution is accepted. No contributor may apply the project data license
to a third-party track or to an artifact incorporating that track unless the
source terms expressly permit sublicensing under those terms.
