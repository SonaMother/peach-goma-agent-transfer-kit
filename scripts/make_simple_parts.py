#!/usr/bin/env python3
"""make_simple_parts.py - the "simple parts" channel (project-agnostic).

Splits every tracked source file of ANY git repo into tiny plain-text part
files:

  parts/          raw content, byte-identical, NO transformation
  parts-esc/      same split, but < > & escaped as \\u003c \\u003e \\u0026
                  (for agents whose fetcher strips tag-like sequences)

Usage (all args required except noted):
  python3 make_simple_parts.py --repo-dir /path/to/project \\
      --gh-repo Owner/name [--branch main] [--project-name "My Project"] \\
      [--install-cmd "npm install"] [--run-cmd "npm run dev"] \\
      [--exclude extra_file.bin] [--exclude dir/]

Outputs (into --repo-dir): parts/, parts-esc/, PARTS_INDEX.md
"""
import argparse
import subprocess
from pathlib import Path

LINE_CAP = 100                      # max content lines per part
BYTE_CAP = 4000                     # max part file size on the wire (bytes)
# 4000 chosen for the fewest fetches while staying far under every raw
# truncation cap observed (raw fetches survived 14-21KB; ~6KB was API-only).
# NOTE: a Contents-API/base64 lane was considered and DROPPED - the target
# agents cannot decode base64, and the API's only plain-text mode needs a
# custom Accept header that URL-only fetchers cannot send.

META_FILES = {"PARTS_INDEX.md", "AGENT_PROMPT.txt", "RECREATE_PROJECT.md"}
META_PREFIXES = ("parts/", "parts-esc/", "bundle/")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo-dir", required=True, type=Path,
                   help="local git working clone of the project to transfer")
    p.add_argument("--gh-repo", required=True, metavar="OWNER/NAME",
                   help="GitHub repo the transfer files will be pushed to")
    p.add_argument("--branch", default="main")
    p.add_argument("--install-cmd", default="npm install",
                   help="dependency install command shown in the guides")
    p.add_argument("--run-cmd", default="npm run dev",
                   help="build/run command shown in the guides")
    p.add_argument("--exclude", action="append", default=[], metavar="NAME",
                   help="extra tracked file to exclude (repeatable)")
    return p.parse_args()


def esc(s: str) -> str:
    return (s.replace("<", r"\u003c")
             .replace(">", r"\u003e")
             .replace("&", r"\u0026"))


def chunk_lines(lines: list[str], header_budget: int) -> list[str]:
    """Group whole lines into chunks respecting LINE_CAP and byte budget."""
    chunks, cur, cur_bytes = [], [], 0
    for line in lines:
        lb = len(line.encode("utf-8"))
        if lb + 16 > BYTE_CAP - header_budget:
            raise RuntimeError(f"single line too big ({lb} B)")
        if cur and (len(cur) >= LINE_CAP or cur_bytes + lb > BYTE_CAP - header_budget):
            chunks.append("".join(cur))
            cur, cur_bytes = [], 0
        cur.append(line)
        cur_bytes += lb
    if cur:
        chunks.append("".join(cur))
    return chunks


def build_set(files: list[tuple[str, Path]], out_dir: Path, escape: bool):
    """files = [(relpath_string, absolute_path)] in transfer order."""
    out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob("*.txt"):
        old.unlink()
    rows, seq = [], 0
    for rel, abspath in files:
        text = abspath.read_bytes().decode("utf-8")
        # the esc set's unescape (3 replace-alls) is only lossless if no
        # source file already contains literal backslash-u escape sequences
        for lit in (r"\u003c", r"\u003e", r"\u0026"):
            assert lit not in text, (
                f"{rel} contains literal {lit}; esc set would be ambiguous. "
                f"Reword the source file in words instead.")
        body = esc(text) if escape else text
        lines = body.splitlines(keepends=True)
        hdr_budget = len(rel) + 32
        chunks = chunk_lines(lines, hdr_budget)
        n = len(chunks)
        first_seq = seq + 1
        for k, chunk in enumerate(chunks, 1):
            seq += 1
            header = f"[PART {k} of {n} | {rel}]\n"
            part = header + chunk
            data = part.encode("utf-8")
            assert len(data) <= BYTE_CAP, f"{rel} part {k}: {len(data)} B > cap"
            assert len(chunk.splitlines()) <= LINE_CAP
            name = f"p{seq:03d}__{rel.replace('/', '__')}__part{k:02d}of{n:02d}.txt"
            (out_dir / name).write_bytes(data)
        rows.append((rel, abspath.stat().st_size, first_seq, seq, n))
    return rows, seq


def safe_preview(files) -> tuple[str, str, bool]:
    """(rel, line, escaped) of the alphabetically-first file's first line that
    contains no < > & (so the preview survives every fetcher unchanged).
    If no such line exists, returns the first line esc()-escaped with
    escaped=True so the index can label it honestly."""
    for rel, abspath in files:
        for line in abspath.read_text(encoding="utf-8").splitlines():
            if line.strip() and not any(c in line for c in "<>&"):
                return rel, line.strip()[:60], False
    rel, abspath = files[0]
    first = abspath.read_text(encoding="utf-8").splitlines()[0][:60]
    return rel, esc(first), True


def index_md(rows_raw, rows_esc, n_raw, n_esc, args) -> str:
    total_bytes = sum(r[1] for r in rows_raw)
    # worked filename example, computed from real rows so it can never drift
    ex_rel, _, ex_first, _, ex_n = max(rows_esc, key=lambda r: r[1])
    ex_name = f"p{ex_first:03d}__{ex_rel.replace('/', '__')}__part01of{ex_n:02d}.txt"
    largest = max(rows_raw, key=lambda r: r[1])
    pv_rel, pv_line, pv_esc = safe_preview(
        [(r[0], args.repo_dir / r[0]) for r in rows_raw])
    L = []
    L.append("# PARTS INDEX - rebuild this repo by reading tiny text parts\n")
    L.append("Goal: recreate every source file on disk (by hand, from these parts)")
    L.append("so the project builds and runs. No JSON, no decoding, no special tools.\n")
    L.append("## STEP 0 - calibrate yourself (one fetch, already done if you read this)")
    L.append("Probe 1 (tags): the next line contains a test tag:")
    L.append("<tag-probe-12345>")
    L.append('If you can see "<tag-probe-12345>" above, your fetcher keeps tags:')
    L.append("use parts/. If it vanished or looks mangled, your fetcher strips")
    L.append("tag-like text: use parts-esc/ instead (same parts, but < > & are")
    L.append("stored as backslash-u escape sequences).")
    L.append("Probe 2 (newlines): PROBE-A and PROBE-B are on separate lines:")
    L.append("PROBE-A")
    L.append("PROBE-B")
    L.append('If they arrive joined on one line ("PROBE-A PROBE-B"), your fetcher')
    L.append("collapses newlines: no plain-text channel can work for you. Stop and")
    L.append("use npm (see AGENT_PROMPT.txt) or the JSON bundle bundle/INDEX.json.\n")
    L.append("## THE LOOP (your whole job)")
    L.append(f"1. Run `{args.install_cmd}` once now; it regenerates the lockfile,")
    L.append("   which is intentionally not shipped here.")
    L.append("2. Process parts strictly in order: p001, p002, p003, ...")
    L.append("   ONE part per fetch: write it (step 4) BEFORE fetching the next.")
    L.append("   Never fetch ahead of your writes. Part filenames follow one rule:")
    L.append("   pNNN__<file path, with / written as __>__partKKofNN.txt")
    L.append(f"   Example: {ex_name} holds the start of {ex_rel}.")
    L.append(f"   Cannot list a folder? https://ungh.cc/repos/{args.gh_repo}/files/{args.branch}")
    L.append("   lists every file path (plain JSON, no headers needed).")
    L.append("   If a fetch fails or a part looks cut off, re-fetch that part")
    L.append("   once; never guess lines. raw.githubusercontent.com blocked?")
    L.append("   Same files, no rate limit, at:")
    L.append(f"   https://cdn.jsdelivr.net/gh/{args.gh_repo}@{args.branch}/parts/FILE.txt")
    L.append("3. Line 1 of each part is a header [PART k of n | path].")
    L.append("   It is a label only - NEVER copy it into the target file.")
    L.append("4. Write as you read: part k=1 -> create the file with the remaining")
    L.append("   lines exactly as they are; parts k>1 -> append to the same file.")
    L.append("   Write immediately after each fetch: text you have not written down")
    L.append("   can fall out of your context later. Never hold whole files in")
    L.append("   memory; never rewrite from memory; never stack up unwritten parts.")
    L.append("   If a hard tool-step budget makes one-at-a-time impossible, fetch")
    L.append("   at most one file's parts ahead, and still write each part as it")
    L.append("   arrives.")
    L.append("5. When you consume the part whose header shows k equal to n, that")
    L.append("   file is complete. Move to the next part number.")
    L.append('6. parts-esc only: right after a file is complete, replace-all three')
    L.append('   sequences in it: \\u003c with the less-than sign, \\u003e with the')
    L.append('   greater-than sign, \\u0026 with the ampersand.')
    L.append(f"7. After the last part: {args.run_cmd}. Done.\n")
    L.append(f"## PART TABLE ({len(rows_raw)} files, {total_bytes:,} bytes of source)")
    L.append("raw = parts/, esc = parts-esc/. Byte sizes refer to the real files.")
    L.append("")
    L.append("| file | bytes | raw parts | esc parts |")
    L.append("|---|---|---|---|")
    for (rel, b, a1, a2, an), (_, _, b1, b2, bn) in zip(rows_raw, rows_esc):
        rs = f"p{a1:03d}-p{a2:03d}" if an > 1 else f"p{a1:03d}"
        es = f"p{b1:03d}-p{b2:03d}" if bn > 1 else f"p{b1:03d}"
        L.append(f"| {rel} | {b:,} | {rs} ({an}) | {es} ({bn}) |")
    L.append("")
    L.append(f"Totals: raw {n_raw} parts, esc {n_esc} parts. Every part is "
             f"<= {LINE_CAP} lines and <= {BYTE_CAP} bytes.")
    L.append("")
    L.append("## Sanity anchors (check these instead of trusting yourself)")
    L.append(f"- The project ships {len(rows_raw)} files, {total_bytes:,} bytes of source in total.")
    L.append(f"- {largest[0]} is {largest[1]:,} bytes - the largest file. If yours")
    L.append("  is smaller, you truncated it: redo that file, never guess lines.")
    if pv_esc:
        L.append(f"- {pv_rel} starts with (its < > & written as backslash-u escapes):")
        L.append(f"  {pv_line}")
    else:
        L.append(f"- {pv_rel} contains the line: {pv_line}")
    L.append("- Any file whose size or contents differ from the table above means")
    L.append("  you fabricated or truncated it - redo that file from its parts.")
    L.append(f"- The project builds with: {args.install_cmd} && {args.run_cmd}")
    return "\n".join(L) + "\n"


def main():
    args = parse_args()
    repo: Path = args.repo_dir
    assert (repo / ".git").exists(), f"{repo} is not a git working tree"
    assert "/" in args.gh_repo and args.gh_repo.count("/") == 1, \
        "--gh-repo must be OWNER/NAME"

    excluded = META_FILES | set(args.exclude)
    tracked: list[tuple[str, Path]] = []
    for p in subprocess.check_output(
            ["git", "ls-files"], cwd=repo, text=True).splitlines():
        if p.startswith(META_PREFIXES) or p in excluded:
            continue
        if p == "package-lock.json":      # regenerable via npm install
            continue
        if "/" not in p and p.endswith(".zip"):   # binary archives
            continue
        tracked.append((p, repo / p))

    rows_raw, n_raw = build_set(tracked, repo / "parts", escape=False)
    rows_esc, n_esc = build_set(tracked, repo / "parts-esc", escape=True)
    assert [r[0] for r in rows_raw] == [r[0] for r in rows_esc]

    (repo / "PARTS_INDEX.md").write_text(
        index_md(rows_raw, rows_esc, n_raw, n_esc, args), encoding="utf-8")

    idx = repo / "PARTS_INDEX.md"
    print(f"files: {len(tracked)}   raw parts: {n_raw}   esc parts: {n_esc}")
    print(f"PARTS_INDEX.md: {idx.stat().st_size:,} bytes")
    biggest_raw = max((repo / "parts" / f).stat().st_size
                      for f in [p.name for p in (repo / "parts").glob("*.txt")])
    biggest_esc = max((repo / "parts-esc" / f).stat().st_size
                      for f in [p.name for p in (repo / "parts-esc").glob("*.txt")])
    print(f"largest raw part: {biggest_raw:,} B   largest esc part: {biggest_esc:,} B")


if __name__ == "__main__":
    main()
