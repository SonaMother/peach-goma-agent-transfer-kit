#!/usr/bin/env python3
"""bundle v3 ("parts-v3"): exact-reconstruction bundle for AI agents whose web
fetcher (a) strips HTML/JSX-like tags even inside JSON bodies, (b) collapses
newlines in text responses, and (c) truncates large responses (observed: raw
58KB file truncated; Contents-API base64 OK <= ~5KB files, truncated ~8KB+;
a 14KB single-line JSON parsed fine once).

v3 changes vs v2:
- ZERO raw angle brackets / ampersands: all <, >, & escaped as \u003c \u003e
  \u0026 in the final JSON text -> tag-strippers have literally nothing to match.
- Single-line compact JSON -> newline-collapsers have nothing to join.
- Shards <= 8KB on the wire (under every cap observed so far).

Usage:
  python3 make_json_shards_v2.py --repo-dir /path/to/project \
      --gh-repo Owner/name [--branch main] [--project-name "My Project"]
"""
import argparse
import hashlib
import json
import subprocess
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path


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
SLUG = "-".join(s for s in
                "".join(c if c.isalnum() else "-" for c in PROJECT.lower()).split("-")
                if s) or "recreate"
BUNDLE = REPO / "bundle"
BUNDLE.mkdir(exist_ok=True)
COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()

EXCLUDE = {"gameproject.zip", "RECREATE_PROJECT.md", "AGENT_PROMPT.txt",
           "PARTS_INDEX.md"}
SHARD_CAP = 8 * 1024       # max bytes of any shard file on the wire
TEXT_BUDGET = 7_300        # max escaped-chars of part text per part

def tag_safe(s: str) -> str:
    """Escape <, >, & so the JSON text contains zero tag-like sequences."""
    return (s.replace("<", r"\u003c")
             .replace(">", r"\u003e")
             .replace("&", r"\u0026"))

def dumps(obj) -> str:
    return tag_safe(json.dumps(obj, ensure_ascii=True, separators=(",", ":")))

def esc_len(s: str) -> int:
    return len(json.dumps(s, ensure_ascii=True)) - 2

def cumulative_esc(text: str):
    cum = [0]
    for ch in text:
        add = len(json.dumps(ch, ensure_ascii=True)) - 2
        if ch in "<>&":          # tag_safe expands these 1-char to 6-char escapes
            add += 5
        cum.append(cum[-1] + add)
    return cum

# ---- slice every tracked file into parts ---------------------------------
tracked = sorted(p for p in subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True).splitlines()
                 if p not in EXCLUDE and not p.startswith(("bundle/", "parts/", "parts-esc/")))

parts, files_meta = [], []
for rel in tracked:
    raw = (REPO / rel).read_bytes()
    text = raw.decode("utf-8")
    cum = cumulative_esc(text)
    n = len(text)
    slices, i = [], 0
    while i < n:
        j = bisect_right(cum, cum[i] + TEXT_BUDGET) - 1
        if j <= i:
            raise RuntimeError(f"slice failed at {rel}:{i}")
        slices.append(text[i:j])
        i = j
    of = len(slices)
    for seq, chunk in enumerate(slices, 1):
        b = chunk.encode("utf-8")
        parts.append({"path": rel, "seq": seq, "of": of, "bytes": len(b),
                      "sha256": hashlib.sha256(b).hexdigest(), "text": chunk})
    files_meta.append({"path": rel, "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest(), "parts": of})

# ---- pack parts into shard files, measuring real wire size ----------------
shards, cur = [], []
for p in parts:
    trial = cur + [p]
    wire = len(dumps({"shard": "x", "parts": trial}).encode("utf-8")) + 450
    if cur and wire > SHARD_CAP:
        shards.append(cur)
        cur = [p]
    else:
        cur = trial
if cur:
    shards.append(cur)

for k, plist in enumerate(shards, 1):
    name = f"shard-{k:02d}.json"
    for p in plist:
        p["shard"] = name
    obj = {"bundle": f"{SLUG}-recreate",
           "layout": "parts-v3",
           "commit": COMMIT, "shard": name, "parts": plist}
    out = BUNDLE / name
    out.write_text(dumps(obj), encoding="utf-8")
    size = out.stat().st_size
    assert size <= SHARD_CAP, f"{name} is {size} bytes (> cap)"
    print(f"{name:16} {size:>7,} bytes  {len(plist)} parts")

part_index = [{"shard": p["shard"], "path": p["path"], "seq": p["seq"], "of": p["of"],
               "bytes": p["bytes"], "sha256": p["sha256"]} for p in parts]

# NOTE: parts[] mapping is NOT stored in INDEX (it would double its size past the
# 8KB cap). Every shard entry already carries path/seq/of/bytes/sha256, so agents
# group shard entries by path themselves. INDEX stays a single <=8KB file.

index = {
    "bundle": f"{SLUG}-recreate",
    "layout": "parts-v3",
    "repo": args.gh_repo,
    "commit": COMMIT,
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    "why": ("Fetch-only agents: every bundle file contains ZERO raw < > & characters "
            "(escaped) and is single-line JSON, so tag-stripping, newline-collapsing "
            "and truncating fetch converters cannot alter them. Parse as JSON."),
    "integrity_check_for_fetcher":
        "After fetching, confirm no raw '<' '>' '&' appear (only backslash-u escapes).",
    "how_to_reconstruct": [
        "1. Fetch every bundle/shard-NN.json in shards[] (each <= 8,192 bytes; one URL per call is fine).",
        "2. Group each shard's parts by 'path', sort by 'seq' (entries carry path/seq/of/bytes/sha256/text).",
        "3. File content = concat of part 'text' in seq order; \\u003c-style escapes decode via your JSON parser.",
        "   No shell: Write part seq=1, then Edit-append each next part (old_str = current last line).",
        "4. Verify sha256(utf8(text)) per part and per file against files[]. Quote real hash strings.",
        "5. npm install && npm run dev",
    ],
    "totals": {"files": len(files_meta), "content_bytes": sum(f["bytes"] for f in files_meta),
               "shards": len(shards), "parts": len(parts), "max_shard_bytes": SHARD_CAP},
    "regenerable": {"package-lock.json": "npm install regenerates it; skip its parts if capped"},
    "alternate_channels": {
        "npm_as_transport": (f"BEST if npm works: npm install github:{args.gh_repo}"
                             " -> repo lands byte-exact in node_modules/<see package.json name>/"),
        "shell": f"git clone https://github.com/{args.gh_repo}.git",
        "unzip": f"https://github.com/{args.gh_repo}/raw/{args.branch}/gameproject.zip (byte-exact archive, if present)",
        "code_exec": ("Contents API JSON+base64, tag-proof, per file: "
                      f"https://api.github.com/repos/{args.gh_repo}/contents/<path>?ref={args.branch}"),
        "human": "RECREATE_PROJECT.md in repo root (only if your fetcher does NOT strip tags)",
    },
    "files": files_meta,
    "shards": [{"file": f"shard-{k:02d}.json"} for k in range(1, len(shards) + 1)],
}
(BUNDLE / "INDEX.json").write_text(dumps(index))
print(f"INDEX.json      {(BUNDLE / 'INDEX.json').stat().st_size:>7,} bytes")
print(f"total: {len(files_meta)} files, {len(parts)} parts, {len(shards)} shards")
