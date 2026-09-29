#!/usr/bin/env python3
"""Mirror a built site into the repository without overwriting author-owned files."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

MANIFEST = '.site-root.json'
PROTECTED = {'content', 'templates', 'scripts', 'tests', 'docs', 'legacy', 'archive', 'examples', '.git', '.github', '.venv', '_site'}
SKIP = {'.site-build.json', MANIFEST, '.DS_Store'}


class PublishError(ValueError):
    """The mirror would overwrite or remove a file it does not safely own."""


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def validate_path(value):
    if not isinstance(value, str) or not value or '\\' in value or any(ord(char) < 32 for char in value):
        raise PublishError(f'Unsafe root-mirror path: {value!r}')
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or path.as_posix() != value or '..' in path.parts or path.parts[0] in PROTECTED:
        raise PublishError(f'Unsafe root-mirror path: {value}')
    if any(part.startswith('.') for part in path.parts) and value != '.nojekyll':
        raise PublishError(f'Unsafe hidden root-mirror path: {value}')
    return Path(*path.parts)


def read_manifest(root):
    path = Path(root) / MANIFEST
    if path.is_symlink():
        raise PublishError(f'Refusing symlink root-mirror manifest: {path}')
    if not path.exists():
        return {'version': 1, 'files': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise PublishError(f'{path}: invalid mirror manifest: {exc}') from exc
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('files'), dict):
        raise PublishError(f'{path}: expected version 1 and a files mapping')
    for relative, checksum in data['files'].items():
        validate_path(relative)
        if not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise PublishError(f'{path}: invalid content hash for {relative}')
    return data


def safe_destination(root, relative):
    path = root / validate_path(relative)
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise PublishError(f'Refusing root-mirror symlink: {parent}')
        if parent != path and parent.exists() and not parent.is_dir():
            raise PublishError(f'Root-mirror directory conflicts with an author-owned file: {parent}')
    if not path.resolve().is_relative_to(root):
        raise PublishError(f'Root-mirror path leaves the repository: {relative}')
    return path


def preserved_original_matches(root, relative, checksum):
    if Path(relative).suffix.lower() != '.html':
        return False
    for archive in (root / 'legacy', root / 'archive/legacy-pages'):
        original = archive / relative
        if (original.is_file()
                and not any(parent.is_symlink() for parent in (original, *original.parents) if parent.is_relative_to(root))
                and original.resolve().is_relative_to(archive) and digest(original) == checksum):
            return True
    return False


def plan_sync(root, site):
    """Validate the entire operation before writing or deleting any root files."""
    root, site = Path(root).resolve(), Path(site).resolve()
    if root == site or root.is_relative_to(site) or not site.is_dir():
        raise PublishError(f'Unsafe or missing built-site directory: {site}')
    previous = read_manifest(root)['files']
    for relative, checksum in previous.items():
        target = safe_destination(root, relative)
        if target.exists() and (not target.is_file() or digest(target) != checksum):
            raise PublishError(f'Protected edited generated file: {relative}. Preserve your edit before rebuilding the root mirror.')
    files, writes, shared = {}, [], []
    for source in sorted(site.rglob('*')):
        if source.is_symlink():
            raise PublishError(f'Refusing built-site symlink: {source}')
        if not source.is_file() or source.name in SKIP:
            continue
        relative = source.relative_to(site).as_posix()
        target = safe_destination(root, relative)
        checksum = digest(source)
        if target.exists() and not target.is_file():
            raise PublishError(f'Root-mirror file conflicts with an existing directory: {relative}')
        if relative in previous:
            files[relative] = checksum
            if not target.exists() or digest(target) != checksum:
                writes.append(relative)
            continue
        if target.exists():
            current = digest(target)
            if preserved_original_matches(root, relative, current):
                # First adoption is authorized only after preserving these exact
                # old page bytes in a source archive, including index and 404.
                files[relative] = checksum
                if current != checksum:
                    writes.append(relative)
            elif current == checksum:
                # Existing source assets stay author-owned. Future output may
                # omit them without deleting the source file from the workspace.
                shared.append(relative)
            else:
                raise PublishError(f'Protected author-owned file conflicts with generated output: {relative}')
        else:
            files[relative] = checksum
            writes.append(relative)
    deletes = sorted(set(previous) - set(files))
    return {'files': files, 'writes': writes, 'deletes': deletes, 'shared': shared}


def atomic_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix='.site-root-', dir=target.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        shutil.copy2(source, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def sync_root(root, site):
    """Publish new output and remove only unchanged files owned by our manifest."""
    root, site = Path(root).resolve(), Path(site).resolve()
    plan = plan_sync(root, site)
    for relative in plan['writes']:
        atomic_copy(site / relative, safe_destination(root, relative))
    for relative in plan['deletes']:
        target = safe_destination(root, relative)
        target.unlink(missing_ok=True)
        parent = target.parent
        while parent != root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    descriptor, name = tempfile.mkstemp(prefix='.site-root-manifest-', dir=root)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(json.dumps({'version': 1, 'files': plan['files']}, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        temporary.replace(root / MANIFEST)
    finally:
        temporary.unlink(missing_ok=True)
    return {'written': len(plan['writes']), 'removed': len(plan['deletes']), 'shared': len(plan['shared'])}
