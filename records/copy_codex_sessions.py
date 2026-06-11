#!/usr/bin/env python3
"""
Copy Codex session JSONL files for one project into a flat destination.

Codex stores sessions by date under ~/.codex/sessions and archived_sessions.
Project ownership is recorded inside each JSONL file at:
  session_meta.payload.cwd
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


DEFAULT_CODEX_HOME = Path.home() / ".codex"


def discover_session_files(codex_home):
    files = []
    sessions_dir = codex_home / "sessions"
    archived_dir = codex_home / "archived_sessions"
    if sessions_dir.exists():
        files.extend(sessions_dir.rglob("*.jsonl"))
    if archived_dir.exists():
        files.extend(archived_dir.glob("*.jsonl"))
    return sorted(set(files))


def read_session_cwd(path):
    """Return the first session_meta payload cwd from a Codex JSONL file."""
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("type") != "session_meta":
                    continue
                payload = record.get("payload", {})
                cwd = payload.get("cwd")
                return str(cwd) if cwd else None
    except OSError as exc:
        print(f"skipped unreadable: {path} ({exc})")
    return None


def normalize_path(path):
    return Path(path).expanduser().resolve(strict=False)


def is_same_or_child(path, parent):
    path = normalize_path(path)
    parent = normalize_path(parent)
    return path == parent or parent in path.parents


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_file_content(left, right):
    if not right.exists() or left.stat().st_size != right.stat().st_size:
        return False
    return file_hash(left) == file_hash(right)


def destination_for(source, dest_dir):
    target = dest_dir / source.name
    if not target.exists() or same_file_content(source, target):
        return target

    source_hash = file_hash(source)[:10]
    candidate = dest_dir / f"{source.stem}-{source_hash}{source.suffix}"
    if not candidate.exists() or same_file_content(source, candidate):
        return candidate

    counter = 2
    while True:
        candidate = dest_dir / f"{source.stem}-{source_hash}-{counter}{source.suffix}"
        if not candidate.exists() or same_file_content(source, candidate):
            return candidate
        counter += 1


def copy_project_sessions(codex_home, target_cwd, dest_dir, dry_run):
    matches = []
    for session_file in discover_session_files(codex_home):
        session_cwd = read_session_cwd(session_file)
        if session_cwd and is_same_or_child(session_cwd, target_cwd):
            matches.append((session_file, session_cwd))

    copied = 0
    unchanged = 0
    would_copy = 0

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    for source, session_cwd in matches:
        target = destination_for(source, dest_dir)
        if target.exists() and same_file_content(source, target):
            unchanged += 1
            status = "unchanged"
        elif dry_run:
            would_copy += 1
            status = "would-copy"
        else:
            shutil.copy2(source, target)
            copied += 1
            status = "copied"
        print(f"{status}: {source} -> {target} cwd={session_cwd}")

    skipped = unchanged
    print("")
    print(f"matched: {len(matches)}")
    print(f"copied: {copied}")
    print(f"skipped: {skipped}")
    if dry_run:
        print(f"would-copy: {would_copy}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Copy Codex session files for a project into a flat directory."
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Project path to match. Default: current working directory.",
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=DEFAULT_CODEX_HOME,
        help="Codex home directory. Default: ~/.codex.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("."),
        help="Destination directory. Default: current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be copied without writing files.",
    )
    args = parser.parse_args()

    return copy_project_sessions(
        codex_home=normalize_path(args.codex_home),
        target_cwd=normalize_path(args.cwd),
        dest_dir=normalize_path(args.dest),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
