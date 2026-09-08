# Inputs and layout

The main entry point is `python3 generate.py "PUT YOUR" "NAME HERE"`. Run `setup-font` once to configure a local default font; the wrapper creates a new timestamped output directory automatically.

The table below describes the advanced `scripts/nameplate.py build` interface, which accepts one or two text rows and an explicit output directory. Its font default is `assets/fonts/bandosa.regular.ttf`; it does not read the wrapper's local default configuration. No font is distributed in this repository.

| Control | Default | Behavior |
| --- | --- | --- |
| `--text` | none | Single row; no implicit second row |
| `--top`, `--bottom` | none | Two explicit rows; top and bottom order preserved |
| `--font` | Bandosa Regular | Individual TTF/OTF; no system installation needed |
| `--length` | 150 | Overall X length in mm; other dimensions scale proportionally |
| `--angle` | 70 | Degrees above horizontal; validated range 45–85 |
| `--spacing` | 1.08 | Blender-style tracking control; supported 0.5–3 |
| `--fit` | stretch | Fits each row to the template; use preserve for original aspect ratio |
| `--steps` | 96 | Arc segments, accepted 32–192 |
| `--views` | beauty,side,top | Comma-separated view names; also front and back |
| `--no-render` | false | Export/check only; useful for secondary mechanical tests |
| `--cache-dir` | output parent's `.nameplate-font-cache` | Shared writable cache for custom fonts |

At 150 mm length, the base is 3.2 mm thick, the overall footprint is 150 × 65 mm, the display platform has a 56 mm outer diameter and 52 mm clear interior, its surface is at Z=4.9 mm, and the lip rises 1.6 mm above that surface. Its center is X=120, Y=29.5 mm. The circular extension fits inside the left base's Y=-3…62 mm bounds. A two-row 70° model is about 56 mm tall; one row and other angles have different heights.

The text envelope is X=4…91 mm. Two rows use radii 2.2…29.2 mm and 30.8…56.8 mm; a single row uses 2.2…47.2 mm. A point `(x,r)` follows `(x, r*cos(theta), 2.7+r*sin(theta))` for theta from 0 to the requested angle. Starting at Z=2.7 mm overlaps the 3.2 mm base. The terminal plane is common to all letters, and punctuation has its own path down to the base.

`stretch` matches the accepted template by allowing independent horizontal and vertical scaling. Both rows fill their assigned height even when their text lengths differ. Very short/long strings can look unusually wide or narrow; explicitly choose `preserve` to keep the original proportions and center each row horizontally. Preserve mode can leave vertical space in a row's fixed envelope. The worker never switches fitting modes for just one row, wraps, truncates, or changes case. Actual row dimensions and fitting modes are recorded in `report.json`.

## JSON jobs

Create the JSON as data, then run `python3 scripts/nameplate.py build --config examples/job.json` from the repository root. Relative paths are resolved against the current working directory, not the JSON file's directory:

```json
{
  "rows": ["PUT YOUR", "NAME HERE"],
  "output": "outputs/json-example",
  "font": "assets/fonts/bandosa.regular.ttf",
  "cache_dir": "assets/font-cache",
  "length": 150,
  "angle": 70,
  "fit": "stretch",
  "views": ["beauty", "front", "side", "top"]
}
```

Optional keys are `font`, `cache_dir`, `spacing`, and `steps`. Do not add embedded line breaks/tabs to a row. Other config keys are rejected. The output folder must be empty or new.

## Text coverage and typography

Bandosa provides 90 printable characters, all in the ASCII range. It does not cover Chinese, accented Latin, emoji, or every ASCII punctuation mark. Missing glyphs produce a clear error, not tofu boxes. If a typographic quote is absent but its straight counterpart exists, curly apostrophes/quotes are mapped to straight ones and the substitution is recorded in the report. No other character replacement is performed.

Other fonts can supply additional Unicode glyphs through cmap formats 4/12. The cached layout uses hmtx advances and legacy kern pairs. This is suitable for ordinary Latin names and independent glyphs; the implementation does not apply OpenType GPOS/GSUB shaping, ligatures, joining, or bidirectional text. For scripts requiring those features, use a shaping-capable outline source and adapt the layout step instead of claiming faithful typography. TTC/WOFF font collections need an individual TTF/OTF extracted first.
