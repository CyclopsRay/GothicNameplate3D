#!/usr/bin/env python3
"""Two text rows in, checked 3D model out. One-time local font setup is supported."""
from pathlib import Path
from datetime import datetime
import argparse
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LOCAL_CONFIG = ROOT / '.nameplate-local.json'


def run(command):
    return subprocess.run(command, check=False).returncode


def local_defaults():
    if LOCAL_CONFIG.is_file():
        data = json.loads(LOCAL_CONFIG.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Local configuration must be a JSON object.')
        return data
    return {}


def resolve_default_font():
    configured = local_defaults().get('font')
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else ROOT / path
    return ROOT / 'assets/fonts/bandosa.regular.ttf'


def next_output_directory(parent=None):
    parent = Path(parent) if parent else ROOT / 'outputs'
    stem = datetime.now().strftime('%Y%m%d-%H%M%S')
    candidate = parent / stem
    serial = 1
    while candidate.exists():
        candidate = parent / f'{stem}-{serial:02d}'
        serial += 1
    return candidate


def setup_font(arguments):
    parser = argparse.ArgumentParser(description='Configure a locally owned font and cache its cleaned glyphs once.')
    parser.add_argument('font', type=Path)
    parser.add_argument('--chars', help='Only cache these characters; useful for large fonts.')
    parser.add_argument('--blender', help='Path to the Blender executable.')
    args = parser.parse_args(arguments)
    original = args.font.expanduser().resolve()
    if not original.is_file() or original.suffix.lower() not in ('.ttf', '.otf'):
        raise ValueError('Provide an existing individual .ttf or .otf font.')
    destination = ROOT / 'assets/fonts' / original.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if original != destination.resolve():
        if destination.exists() and destination.read_bytes() != original.read_bytes():
            raise ValueError(f'A different font already exists at {destination}; use a distinct filename.')
        shutil.copy2(original, destination)
    command = [sys.executable, str(ROOT / 'scripts/nameplate.py'), 'preprocess',
               '--font', str(destination), '--cache-dir', str(ROOT / 'assets/font-cache')]
    command += ['--chars=' + args.chars] if args.chars is not None else ['--all-supported']
    if args.blender:
        command += ['--blender', args.blender]
    code = run(command)
    if code:
        return code
    LOCAL_CONFIG.write_text(json.dumps({'font': str(destination.relative_to(ROOT))}, indent=2), encoding='utf-8')
    print(f'Default font configured locally: {destination.name}')
    print('Font, cache, and local configuration are excluded by .gitignore.')
    return 0


def generation_command(args):
    font = Path(args.font).expanduser().resolve() if args.font else resolve_default_font()
    if not font.is_file():
        raise ValueError('Configure a font once:\n  python3 generate.py setup-font /path/to/bandosa.regular.ttf\n'
                         'Or supply --font /path/to/font.ttf. See assets/fonts/README.md.')
    output = Path(args.output).expanduser().resolve() if args.output else next_output_directory()
    command = [sys.executable, str(ROOT / 'scripts/nameplate.py'), 'build',
               '--top=' + args.top, '--bottom=' + args.bottom,
               '--output', str(output), '--font', str(font),
               '--cache-dir', str(ROOT / 'assets/font-cache'),
               '--length', str(args.length), '--angle', str(args.angle), '--fit', args.fit,
               '--views', args.views]
    if args.no_render:
        command.append('--no-render')
    if args.blender:
        command += ['--blender', args.blender]
    return command


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == 'setup-font':
        return setup_font(argv[1:])
    parser = argparse.ArgumentParser(description='Generate a gothic nameplate from two text rows.')
    parser.add_argument('top', help='First/top text row; spelling and capitalization are preserved.')
    parser.add_argument('bottom', help='Second/bottom text row.')
    parser.add_argument('--output', help='New or empty output directory; default: outputs/<timestamp>.')
    parser.add_argument('--font', help='Override the locally configured default TTF/OTF font.')
    parser.add_argument('--length', type=float, default=150, help='Overall length in mm (default: 150).')
    parser.add_argument('--angle', type=float, default=70, help='Text angle above the base (default: 70).')
    parser.add_argument('--fit', choices=['stretch', 'preserve'], default='stretch')
    parser.add_argument('--views', default='beauty,side,top')
    parser.add_argument('--no-render', action='store_true')
    parser.add_argument('--blender', help='Path to the Blender executable.')
    args = parser.parse_args(argv)
    return run(generation_command(args))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
