"""Restore only this UI redesign, preserving the pre-existing uncommitted work."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def restore(root, apply=False):
    root = root.resolve()
    backup = root / '.local/ui-redesign-20261020'
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    conflicts = []
    pending = []
    for entry in manifest:
        target = (root / entry['path']).resolve()
        source = (backup / entry['path']).resolve()
        if not target.is_relative_to(root) or not source.is_relative_to(backup):
            raise ValueError('Invalid backup path')
        current = digest(target)
        if entry['before'] is not None and digest(source) != entry['before']:
            raise ValueError('Backup is missing or damaged: ' + entry['path'])
        if current == entry['before']:
            continue
        if current != entry['after']:
            conflicts.append(entry['path'])
        else:
            pending.append((entry, target, source))
    if conflicts:
        print('Stopped: files changed after the redesign. No files were restored:')
        print('\n'.join(conflicts))
        return 1
    print(f'{len(pending)} UI files can be restored; existing work is preserved.')
    if apply:
        for entry, target, source in pending:
            if entry['before'] is None:
                target.unlink()
            else:
                shutil.copy2(source, target)
        print('Previous UI restored. Refresh the portal with Ctrl+F5.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Restore the previous UI')
    parser.add_argument('--check', action='store_true', help='Validate without changing files (default)')
    args = parser.parse_args()
    sys.exit(restore(Path(__file__).resolve().parents[1], apply=args.apply))
