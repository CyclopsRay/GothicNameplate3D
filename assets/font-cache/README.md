# Local glyph cache

Cleaned glyph outlines, caps, boundaries, font spacing calibration and font metadata
are saved here as compressed JSON after `setup-font` or the first use of a font.
The cache key includes the font SHA-256, Blender major/minor version, geometry recipe,
and curve resolution. Subsequent names reuse cached glyphs; only missing glyphs are
processed.

Full font-outline caches are not committed to this public repository. This directory
is ignored by Git except for this README. The original local Bandosa cache contains
90 printable characters; see [preprocessing details](../../docs/font-preprocessing.md).
