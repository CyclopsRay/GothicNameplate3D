# Cached font preparation

`scripts/font_cache.py` is the maintained implementation. Run `python3 generate.py setup-font /path/to/bandosa.regular.ttf` once. It copies the user-provided font unchanged into the ignored local `assets/fonts/` directory and prepares the reusable cache under `assets/font-cache/`. The cache contains glyph coordinates and geometry, not a modified font or a whole model for one name. Font binaries and full glyph caches are not distributed by this public repository.

The cached record includes font SHA-256, SFNT Unicode coverage, hmtx advances, available legacy kerning pairs, Blender-measured advance normalization and tracking, cleaned planar vertices, triangulated caps, boundary edges, connected components, and cleaning counts. Glyph coordinates use Blender text size 10. The normal build loads this data, lays out new text, fits the rows, and sweeps the existing boundaries through the requested angle.

Cache filenames combine font SHA-256, Blender major/minor, `RECIPE`, and `RESOLUTION`. Increment the recipe when changing geometry extraction or cleanup. The loading path verifies the signature before reuse. The wrapper shares the repository's local cache across output directories. Advanced callers can specify a separate `--cache-dir`, with the repository cache serving as a fallback. Rebuilding a cache must not require overwriting previous model versions.

## Preprocessing implemented

1. Read SFNT metadata as data and confirm glyph coverage.
2. Convert each needed glyph through Blender at resolution 6, without a 3D extrusion.
3. Weld nearly identical planar vertices at 0.00001 font-space units and triangulate the cap.
4. Remove zero-area triangles and any points/edges not belonging to filled faces. Bandosa conversion produced these invisible artifacts; sweeping them created empty “letters” and failed solid Boolean operations.
5. Split independent face fans at point contacts. Some additional punctuation contours meet only at a single point; separating their topological vertices preserves the visible outline while giving each swept component a closed boundary. Do not weld the split contacts back together.
6. Validate planar edges and boundary vertex degrees, then serialize closed components. Legitimate dots, accents, and disconnected ornamental shapes with filled area are retained and swept independently.

Spacing is calibrated from a single glyph, a repeated pair, and a tracked pair in Blender. Do not equate Blender size 10 with `10 / units_per_em`: Bandosa's Blender normalization was about 2.049 times that naive value. Likewise, `space_character` adds tracking rather than multiplying every advance. A naive cache layout made neighboring glyphs overlap and caused many invalid STL triangles. Recipe 2 records the measured scales and reproduces Blender's spacing without converting whole words each time.

The reference Bandosa preparation covered 90 printable glyphs, removed 102 loose vertices, and split 27 point contacts. Those are counts from that exact font and cache recipe, not assumptions about other fonts. Each local preparation writes a report under `assets/font-cache/preprocess-runs/run-*/report.json`. The original long iteration included diagnosis, retries, Boolean unions and renders; preprocessing the now-correct font alone is much shorter.

## Reuse and incremental coverage

Normal builds request only the characters in their text. After initial Bandosa setup, a cache hit should show zero converted glyphs. New custom fonts process only missing glyphs, then reuse them on later names when the same shared cache directory is used. `setup-font` uses `preprocess --all-supported` by default, intended for small fonts; it stops above 2048 printable characters rather than needlessly processing a large CJK font. `--chars` selects the needed subset.

Do not cache only YUQI/REALM or only the completed STL and call it reusable font preprocessing. A meaningful check uses different names, punctuation or digits and inspects cache hits, generated glyphs, and the exported STL.

The boundary/cap cache does not cache the final 3D Boolean union, bevels, lights, or rendered images. Timing comparisons should separate `cache.seconds`, `build_and_export_seconds`, and `total_seconds` in the report; avoid promising immediate complete models from a cache hit.
