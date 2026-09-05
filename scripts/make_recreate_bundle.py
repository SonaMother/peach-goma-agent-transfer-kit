#!/usr/bin/env python3
"""Generate a single-file reconstruction bundle (RECREATE_PROJECT.md) from the
git-tracked files of the repo, so any AI/tool that can read one text URL can
rebuild the exact directory tree (paths + byte-exact contents + sha256 manifest).
"""
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/z/my-project/peach-goma-project")
OUT = REPO / "RECREATE_PROJECT.md"
EXCLUDE = {"gameproject.zip", "RECREATE_PROJECT.md", "AGENT_PROMPT.txt", "PARTS_INDEX.md"}  # binary + self + agent meta

def sh(*args: str) -> str:
    return subprocess.check_output(args, cwd=REPO, text=True).strip()

files = [p for p in sh("git", "ls-files").splitlines()
         if p not in EXCLUDE and not p.startswith(("bundle/", "parts/", "parts-esc/"))]
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

header = f"""# RECREATE_PROJECT.md — exact one-file reconstruction bundle

This single file contains **every source file** of **Peach & Goma: SkyHop** with its
exact repository path and byte-exact contents, so the complete directory tree can be
recreated 1:1 from one URL — no shell, no zip tool, nothing but the ability to read text.

- Source commit: `{commit}`
- Generated (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
- Files: {len(files)} | Total: {total_bytes:,} bytes
- `gameproject.zip` (binary, byte-exact archive of these sources) is NOT inlined here;
  it sits in the repo root if you prefer `unzip` / `git clone`.

## How to reconstruct the directory exactly

1. Create the folder structure: for each block below, `mkdir -p` the directory part of
   the path (e.g. `src/character`), then write the text between that block's
   `BEGIN FILE` and `END FILE` markers into the file named in the marker — verbatim,
   byte-for-byte (the byte count in the marker lets you verify).
2. Root-level files (`index.html`, `package.json`, …) go directly in the project root.
3. Optional verification: the **Manifest** below lists each file's size and SHA-256;
   check with `sha256sum` or any equivalent.
4. Then `npm install && npm run dev` as usual.

> Parsing note for AI agents: file boundaries are the lines starting with
> `<<<<< BEGIN FILE:` / `<<<<< END FILE:`. Paths never contain newlines, and this
> marker sequence never occurs inside file contents. Content is UTF-8.
>
> ⚠️ If your web fetcher strips HTML/JSX-like tags (symptom: fetched `.tsx` files
> arrive missing `<Canvas>`, `<div>`, …), this file WILL be mutilated too. Use the
> JSON shards instead — `bundle/INDEX.json` + `bundle/shard-*.json` — JSON bodies
> survive such converters. Verify every file against the SHA-256 manifest either way.

## Manifest

| Path | Bytes | Lines | SHA-256 (first 12) |
|---|---|---|---|
{chr(10).join(rows)}

## File blocks ({len(files)} files, in alphabetical order)
"""

OUT.write_text(header + "\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
print(f"OK: {OUT.name} — {len(files)} files, {total_bytes:,} src bytes, "
      f"{OUT.stat().st_size:,} bundle bytes")
