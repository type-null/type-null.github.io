#!/usr/bin/env python3
"""Verify that archived originals and all timeline artwork remain intact locally."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def verify(root: Path) -> tuple[int, int]:
    root = root.resolve()
    manifest_path = root / 'archive/original-assets/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    seen, total = set(), 0
    for item in manifest['files']:
        relative = Path(item['archived'])
        path = root / relative
        if relative.is_absolute() or not path.resolve().is_relative_to(root / 'archive/original-assets'):
            raise ValueError(f'Unsafe archive path: {relative}')
        if relative in seen:
            raise ValueError(f'Duplicate archive entry: {relative}')
        seen.add(relative)
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError(f'Archive content changed: {relative}')
        total += len(data)
    if len(seen) != manifest['total_files'] or total != manifest['total_bytes']:
        raise ValueError('Archive totals do not match the manifest')
    records = json.loads((root / 'content/_data/card-sets.json').read_text(encoding='utf-8'))['sets']
    for record in records:
        image = root / record['image'].lstrip('/')
        if not image.is_file() or not image.resolve().is_relative_to(root / 'assets'):
            raise ValueError(f'Timeline original is missing: {record["image"]}')
    print(f'Archive verified: {len(seen)} originals, {total:,} bytes; '
          f'all {len(records)} timeline originals remain in assets/.')
    return len(seen), total


if __name__ == '__main__':
    try:
        verify(Path(__file__).resolve().parents[1])
    except (OSError, ValueError, KeyError) as exc:
        print(f'Archive verification failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
