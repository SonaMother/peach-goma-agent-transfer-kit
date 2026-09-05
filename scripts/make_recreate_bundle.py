#!/usr/bin/env python3
"""Generate a single-file reconstruction bundle (RECREATE_PROJECT.md) from the
git-tracked files of ANY repo, so any AI/tool that can read one text URL can
rebuild the exact directory tree (paths + byte-exact contents + sha256 manifest).

Usage:
  python3 make_recreate_bundle.py --repo-dir /path/to/project \
      --gh-repo Owner/name [--branch main] [--project-name "My Project"]
"""
import argparse
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXCLUDE_META = {"RECREATE_PROJECT.md", "AGENT_PROMPT.txt", "PARTS_INDEX.md"}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo-dir", required=True, type=Path)
    p.add_argument("--gh-repo", required=True, metavar="OWNER/NAME")
    p.add_argument("--branch", default="main")
    p.add_argument("--project-name", default=None,
                   help="human-readable name; default = name part of --gh-repo")
    return p.parse_args()


args = parse_args()
REPO: Path = args.repo_dir
PROJECT = args.project_name or args.gh_repo.split("/")[1]
OUT = REPO / "RECREATE_PROJECT.md"


def sh(*a: str) -> str:
    return subprocess.check_output(a, cwd=REPO, text=True).strip()


zips = sorted(p.name for p in REPO.glob("*.zip"))
files = [p for p in sh("git", "ls-files").splitlines()
         if p not in EXCLUDE_META
         and not p.startswith(("bundle/", "parts/", "parts-esc/"))
         and not ("/" not in p and p.endswith(".zip"))]
commit = sh("git", "rev-parse", "HEAD")

rows, blocks = [], []
total_bytes = 0
for rel in sorted(files):
    data = (REPO / rel).read_bytes()
    total_bytes += len(data)
    sha = hashlib.sha256(data).hexdigest()
    lines = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    rows.append(f"| `{rel}` | {len(data):,} | {lines:,} | `{sha[:12]}` |")
    blocks.append(
        f"<<<<< BEGIN FILE: {rel} ({len(data)} bytes) >>>>>\n"
        f"{data.decode('utf-8')}\n"
        f"<<<<< END FILE: {rel} >>>>>"
    )

if len(zips) == 1:
    zip_note = (f"- `{zips[0]}` (binary, byte-exact archive of these sources) is NOT "
                f"inlined here; it sits in the repo root if you prefer `unzip` / `git clone`.")
else:
    zip_note = "- Binary archives are not inlined; use `git clone` if you have a shell."

header = f"""# RECREATE_PROJECT.md - exact one-file reconstruction bundle

This single file contains **every source file** of **{PROJECT}** with its
exact repository path and byte-exact contents, so the complete directory tree can be
recreated 1:1 from one URL - no shell, no zip tool, nothing but the ability to read text.

- Source commit: `{commit}`
- Generated (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
- Files: {len(files)} | Total: {total_bytes:,} bytes
{zip_note}

## How to reconstruct the directory exactly

1. Create the folder structure: for each block below, `mkdir -p` the directory part of
   the path (e.g. `src/character`), then write the text between that block's
   `BEGIN FILE` and `END FILE` markers into the file named in the marker - verbatim,
   byte-for-byte (the byte count in the marker lets you verify).
2. Root-level files (`index.html`, `package.json`, ...) go directly in the project root.
3. Optional verification: the **Manifest** below lists each file's size and SHA-256;
   check with `sha256sum` or any equivalent.
4. Then install and run the project as usual.

> Parsing note for AI agents: file boundaries are the lines starting with
> `<<<<< BEGIN FILE:` / `<<<<< END FILE:`. Paths never contain newlines, and this
> marker sequence never occurs inside file contents. Content is UTF-8.
>
> If your web fetcher strips HTML/JSX-like tags (symptom: fetched source files
> arrive missing `<div>`, `<Canvas>`, ...), this file WILL be mutilated too. Use the
> JSON shards instead - `bundle/INDEX.json` + `bundle/shard-*.json` - JSON bodies
> survive such converters. Verify every file against the SHA-256 manifest either way.

## Manifest

| Path | Bytes | Lines | SHA-256 (first 12) |
|---|---|---|---|
{chr(10).join(rows)}

## File blocks ({len(files)} files, in alphabetical order)
"""

OUT.write_text(header + "\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
print(f"OK: {OUT.name} - {len(files)} files, {total_bytes:,} src bytes, "
      f"{OUT.stat().st_size:,} bundle bytes")
