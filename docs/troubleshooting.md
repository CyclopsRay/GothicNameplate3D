# Problems encountered and fixes

## One row unexpectedly shrinks

The original fitting guard silently switched a row from `stretch` to `preserve` when its scale ratio crossed a threshold. For `PUT YOUR / NAME HERE`, only the second row crossed it: the upper row remained 26 mm tall while the lower row became 9.28 mm instead of 27 mm. A small text change produced a large visual discontinuity.

The repository now respects the chosen fitting mode for every row. Default `stretch` fills both envelopes; `preserve` is an explicit user choice. Verify `layout` dimensions in `report.json` and inspect the front render when changing this behavior. This change does not affect the cleaned font cache.

## Empty glyph components and silent failed Booleans

In the original Bandosa conversion, a few unfilled points/edges became tiny “glyph” objects with 2–4 vertices and zero faces. Ordinary edge checks alone missed them because a zero-edge object has zero bad edges. Blender's MANIFOLD Boolean solver printed warnings and left the modifier unapplied; later operations could continue and even save files.

Clean the planar input by deleting vertices without filled faces before finding connected glyph components. Before every union, require nonempty faces, manifold edges, and no vertices without incident faces. After applying the Boolean, assert that its modifier was removed. Never use a render or Blender process exit 0 as the sole proof of success. The launcher supplies `--python-exit-code 1` and checks the final report.

Additional punctuation exposed point-contact contours during full-font preprocessing. Split independent face fans before caching. Keep all components with real filled area; do not delete a dot/apostrophe just because it is disconnected from the main letter.

## Export triangulation creates coincident opposite triangles

The original n-gon mesh passed Blender manifold checks, but re-importing its STL exposed two edges with four incident faces. Tessellation had introduced pairs of exactly coincident, oppositely oriented triangles near the base intersection. Their third vertices formed zero-volume fins.

`clean_shell()` triangulates explicitly, groups by the same three vertex IDs, and removes both faces only when a pair's orientations are opposite. Same-facing duplicates or more than two repeats stop the build for diagnosis. It removes resulting loose points and rechecks manifold topology. This is a narrow repair, not general permission to delete suspicious geometry.

Always run the independent STL read-back check after this cleanup: dimensions, one component, edge incidences, nonzero triangle areas, positive volume, bottom Z, and angle. Newly failed checks require investigation rather than broad mesh remeshing that erases typography.

## Scaling a finished triangulated mesh collapses points

An independent test of `MEI'S / GARDEN`, 180 mm long at 65°, exposed 14 nonmanifold edges and 21 zero-area triangles when the already-triangulated 150 mm mesh was scaled at the end. Float32 rounding made some intersection vertices identical and others collinear, especially near the base/platform junction. The default 150 mm example had passed, so testing only that example would have missed this failure.

The worker now scales all construction parts to their final size **before** Boolean unions and final tessellation. The same 180 mm / 65° case then passed exported-STL validation. Do not reintroduce final vertex scaling after cleanup. A broad weld/dissolve repair of the failed STL was tested and did not preserve manifold topology; fix the operation order instead.

## macOS Blender crashes before Python starts

On this machine, sandboxed Blender initialization crashed in the Metal GPU device check even for `-b`. The same command worked with an approved sandbox escalation. Headless mode did not avoid the issue.

If the crash happens before the script starts and the log/backtrace points to Metal initialization, run the same task-specific Blender invocation through the environment's supported escalation mechanism. Do not disable sandboxing globally, overwrite Blender preferences, or repeatedly rerun unchanged failing commands. An approval denial is a separate permission issue and should be reported accurately.

## Units and exports

Blender is modeled in millimeter coordinates with `scene.unit_settings.scale_length=0.001`. STL is exported with `use_scene_unit=False`, keeping numbers in millimeters. The GLB exporter in the tested version did not automatically honor the scene unit scale; export its node with scale 0.001 and restore object scale 1 before saving the Blender file. A 150 mm object must appear as 0.150 meters in a glTF viewer.

The worker exports only the selected print mesh. Keep studio floor, lamps, cameras, hidden font sources, and duplicate construction objects out of the STL. Pack the font in the `.blend` so the scene remains portable.

## Cache misses and unsupported text

A new font file, different Blender major/minor, or new cache recipe must not reuse an old cache. Examine the cache key and `converted_glyphs` in the report. If requested characters are absent from the font cmap, use a suitable font or obtain the user's intended substitution; do not silently delete them. The only automatic substitutions are recorded straight-quote equivalents described in `parameters.md`.
