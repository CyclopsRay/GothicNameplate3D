# Bring your own font

Bandosa Regular by **Blankids Studio** is the original typeface used by this project.
The font file is **not distributed** in this public repository, and the code license
does not grant rights to it. Its published download terms describe personal use;
check the foundry's terms for your intended use.

- [Bandosa product page](https://blankidsfonts.com/product/bandosa-a-handmade-blackletter-font/)
- [Foundry licensing information](https://blankidsfonts.com/licensing/)
- [Bandosa download/usage notice](https://www.1001fonts.com/bandosa-font.html)

After obtaining a suitable font, configure it once:

```bash
python3 generate.py setup-font /path/to/bandosa.regular.ttf
```

This copies the font into this local directory, preprocesses its glyphs, and saves
the local default. Fonts, glyph caches, and local settings are ignored by Git.
You can also use another individual TTF/OTF file or pass `--font` for one build.

For fonts with more than 2048 printable characters, cache a chosen subset:

```bash
python3 generate.py setup-font /path/to/font.ttf --chars "ALICEWORLD0123456789"
```
