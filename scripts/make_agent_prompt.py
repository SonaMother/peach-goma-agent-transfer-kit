#!/usr/bin/env python3
"""make_agent_prompt.py - generate AGENT_PROMPT.txt for ANY project.

Templates the proven hand-off prompt (calibrate -> pick channel ->
anti-hallucination rules -> honest final report) with your repo's URLs,
part caps, and data-driven anchors, so it can never drift from reality.

Run AFTER make_simple_parts.py (it reads parts/ for the anchor numbers).

Usage:
  python3 make_agent_prompt.py --repo-dir /path/to/project \
      --gh-repo Owner/name [--branch main] [--project-name "My Project"] \
      [--fabrication-tell "a CRA-style index.html with %PUBLIC_URL% is WRONG"]
"""
import argparse
from pathlib import Path

LINE_CAP = 100      # keep in sync with make_simple_parts.py
BYTE_CAP = 4000


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo-dir", required=True, type=Path)
    p.add_argument("--gh-repo", required=True, metavar="OWNER/NAME")
    p.add_argument("--branch", default="main")
    p.add_argument("--project-name", default=None)
    p.add_argument("--install-cmd", default="npm install",
                   help="dependency install command shown in the guides")
    p.add_argument("--run-cmd", default="npm run dev",
                   help="build/run command shown in the guides")
    p.add_argument("--fabrication-tell", default="",
                   help="project-specific 'you fabricated it' symptom, "
                        "e.g. a wrong-style boilerplate file")
    return p.parse_args()


def main():
    args = parse_args()
    repo: Path = args.repo_dir
    project = args.project_name or args.gh_repo.split("/")[1]

    parts_dir = repo / "parts"
    part_files = sorted(parts_dir.glob("*.txt"))
    assert part_files, "no parts/ found - run make_simple_parts.py first"

    # gather data-driven anchor facts from the part headers
    files: dict[str, int] = {}
    for pf in part_files:
        header = pf.read_text(encoding="utf-8").splitlines()[0]
        rel = header.split(" | ", 1)[1][:-1]
        files[rel] = files.get(rel, 0) + 1
    n_files = len(files)
    total_bytes = sum((repo / rel).stat().st_size for rel in files)
    largest = max(files, key=lambda rel: (repo / rel).stat().st_size)
    largest_b = (repo / largest).stat().st_size
    has_npm = (repo / "package.json").exists()

    tell_lines = (
        [f"  5. Known fabrication trap from prior agents: {args.fabrication_tell}",
         "     If yours differs, you fabricated it - redo that file from its parts."]
        if args.fabrication_tell else
        ["  5. If any file's byte count differs from the anchors below, you",
         "     truncated or fabricated it: redo that file from its parts."])

    chan_a = (
        ["  A. npm works (BEST, one command, byte-exact):",
         f"       npm pack github:{args.gh_repo}",
         "     Extract the tarball. DONE. (npm install github:... also works;",
         "     files land under node_modules/<see package.json name>/)"]
        if has_npm else
        ["  A. (not applicable: this repo has no package.json - continue with B)"])

    L = []
    L.append("AGENT PROMPT - REBUILD THIS REPO EXACTLY")
    L.append("=========================================")
    L.append("")
    L.append(f'You reproduce the exact source tree of the "{project}" repository on')
    L.append("disk, byte for byte, so it builds and runs. Never write any file from")
    L.append('memory or from "understanding". Every byte must come from a channel')
    L.append("below.")
    L.append("")
    L.append("STEP 1 - CALIBRATE (one fetch)")
    L.append("Fetch PARTS_INDEX.md (repo root, plain text). Its STEP 0 has two probes.")
    L.append("They tell you whether your fetcher keeps tag-like text and newlines.")
    L.append("Then use the FIRST channel below that fits your toolset.")
    L.append("")
    L.append("CHANNELS - FIRST THAT APPLIES WINS")
    L.extend(chan_a)
    L.append("  B. shell + git: git clone")
    L.append(f"     https://github.com/{args.gh_repo}.git")
    L.append("     DONE.")
    L.append("  C. code execution + HTTP, no git: fetch each path via the GitHub")
    L.append("     Contents API and base64-decode. Tag-proof by construction.")
    L.append("     Details in the repo README.md, section on programmatic access.")
    L.append("  D. fetch-only, tags AND newlines survive: SIMPLE PARTS WALK.")
    L.append("     PARTS_INDEX.md - section THE LOOP. ONE part per fetch: fetch a")
    L.append(f"     tiny part (p001, p002, ... ; max {LINE_CAP} lines / {BYTE_CAP:,} bytes), then")
    L.append("     create-or-append its target file IMMEDIATELY, then fetch the")
    L.append("     next. Never fetch ahead of your writes. No JSON, no decoding.")
    L.append("     Recommended default for your toolset.")
    L.append("  E. fetch-only, tags stripped but newlines survive: same walk, but fetch")
    L.append("     the twin parts from parts-esc/ and after each completed file run")
    L.append("     three replace-alls (PARTS_INDEX.md, THE LOOP, rule 6).")
    L.append("  F. fetch-only, newlines collapsed: NO text channel survives you. Either")
    L.append("     get npm working (channel A) or fetch the single-line JSON bundle:")
    L.append("     bundle/INDEX.json (assembly protocol inside that file). Do not")
    L.append("     attempt the plain-text walk; it will be mangled.")
    L.append("")
    L.append("NON-NEGOTIABLE RULES")
    L.append("  1. Never claim a step succeeded without printing its verification value")
    L.append("     in the same message (byte count, anchor result, or command output).")
    L.append("  2. Never invent paths, part numbers, hashes, or file contents. If you")
    L.append("     are about to state a value you did not just fetch or compute, stop.")
    L.append("  3. A failed or suspicious fetch: re-fetch once, then stop and report the")
    L.append("     exact error. Never continue with partial or guessed data.")
    L.append("  4. Byte-exact copying only. No cleanup, no reformatting, no improvements.")
    L.extend(tell_lines)
    L.append("  6. One part in, one write out. Fetched text you have not written to")
    L.append("     disk can fall out of your context later. Never fetch ahead of writes.")
    L.append("")
    L.append("ANCHORS")
    L.append(f"  - Parts channel ships {n_files} files, about {total_bytes // 1024} KB of source.")
    L.append("  - The lockfile (package-lock.json) is intentionally not among them:")
    L.append(f"    {args.install_cmd} regenerates it.")
    L.append(f"  - {largest}: {largest_b:,} bytes - the largest file by far.")
    L.append(f"  - Build gate: {args.install_cmd}, then {args.run_cmd}.")
    L.append("")
    L.append("FINAL REPORT - PRINT EXACTLY THIS, FILLED IN")
    L.append("  files written: ...")
    L.append(f"  anchors checked ({largest}, file count vs PARTS_INDEX): ...")
    L.append("  install: OK or FAIL (with error text)")
    L.append("  run/build: OK or FAIL (with error text)")
    L.append("An honest failure report is more valuable than a fake success. Do not")
    L.append("narrate success you have not verified with the anchors above.")

    out = repo / "AGENT_PROMPT.txt"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"OK: {out.name} - {out.stat().st_size:,} bytes "
          f"({n_files} files, largest {largest} {largest_b:,} B)")


if __name__ == "__main__":
    main()
