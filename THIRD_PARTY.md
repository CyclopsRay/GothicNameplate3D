# Third-party assets and tools

The GNU GPL v3 license covers this project's original code and documentation. It does not grant rights to third-party fonts, their complete glyph caches, or embedded copies in generated Blender scenes.

## Bandosa Regular

The example uses Bandosa Regular by **Blankids Studio**. The [distribution page](https://www.1001fonts.com/bandosa-font.html) describes it as personal-use-only and points to the [foundry product page](https://blankidsfonts.com/product/bandosa-a-handmade-blackletter-font/) for licensing. Obtain the font and any license appropriate to your use separately.

The repository includes a rendered example image, but **does not distribute the font binary or its complete derived glyph geometry**. `setup-font` copies a file supplied by the user into an ignored local folder and creates an ignored local cache. Generated Blender files pack their font and are ignored as well. Changing the font does not change that font's license.

## Runtime

- [Blender](https://www.blender.org/) is installed separately and provides its Python API, bmesh, and NumPy. No Blender binaries are redistributed here.
- The launcher uses Python's standard library. The optional standalone mesh tests use a separately installed [NumPy](https://numpy.org/).

No reference STL or other third-party model is bundled.
