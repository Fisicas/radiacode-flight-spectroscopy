# Optional release media

The main repository contains the landing-page featured animation and static PNG fallbacks.
Full-resolution synchronized GIFs are prepared separately to avoid adding their
binary history to ordinary clones.

The route and altitude layers derive from FlightAware website data. Do not
include downloaded KML files in either release. The non-raw derivative media
are published for noncommercial academic review, excluded from MIT and CC BY
4.0, and covered by the notice in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

For an optional media release:

1. Confirm that the FlightAware rights notice appears in the release notes.
2. Create the GitHub tag/release `v0.1-media`.
3. Upload the files from the sibling
   `github_repository_release_assets_v0.1-media` directory.
4. Verify that every uploaded asset matches that bundle's `SHA256SUMS.txt`.
5. Add release links to the README only after the assets resolve.

The media bundle contains presentation products only. It must not contain
FlightAware KML files, private contributor inputs, temporary frames, or local
manifests. Public availability does not place FlightAware-derived material
under the repository's open licenses. Figure 01, Figure 06, their source
scripts, and the numeric case-study outputs remain in the main repository.
