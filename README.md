# AI-Agent Repo Transfer Kit

Ship **any** code repository through fragile AI-agent web fetchers - agents
that cannot `git clone`, cannot unzip, cannot run code, and whose only
capability is: *fetch a URL, read the text, hand-write files*.

Project-agnostic by design: the scripts take your repo as arguments and
contain no project references. Point, run, push - done.

Proven in production: after 3 failed transfer attempts (mangled JSX, collapsed
newlines, silent truncation, and fabricated success reports), a 4th agent
rebuilt the target repo **byte-exact, 34/34 files**, using the guides this kit
generated (see `examples/peach-goma-skyhop/` for that real output).

- Worked example target repo:
  https://github.com/SonaMother/peach-goma-skyhop-3d-cat-platformer
- Hand-off URL that was given to the agent:
  `https://raw.githubusercontent.com/SonaMother/peach-goma-skyhop-3d-cat-platformer/main/AGENT_PROMPT.txt`

## The problem, in one paragraph

Web-only AI agents fetch URLs through a lossy pipeline. Observed damage across
agents: (a) HTML-like tag stripping - every `<div>`, `<Canvas>`, even `&&`
disappears, also inside JSON bodies; (b) newline collapsing - lines merge, so
indentation and line structure are destroyed; (c) size truncation - responses
cut off around 4-8 KB; (d) no HTTP headers - custom `Accept:` headers cannot be
sent; (e) no base64 decoder. None of this is visible to the agent, which is
why the worst failure mode is not breakage but **confident fabrication**
(invented hashes, invented files, claimed success).

## Use it on a NEW project (the whole workflow)

```bash
# from inside your project's git working tree:
python3 /path/to/this-kit/scripts/new_project.py \
    --repo-dir . \
    --gh-repo YourName/your-project \
    [--project-name "My Project"] \
    [--install-cmd "npm install"] [--run-cmd "npm run dev"] \
    [--fabrication-tell "a CRA-style index.html with %PUBLIC_URL% is WRONG"] \
    [--exclude some_big_binary.bin]
```

That one command generates everything into your repo, verifies it locally,
and prints the publish checklist:

| Generated | Purpose |
|---|---|
| `parts/` + `parts-esc/` | tiny plain-text part files (raw / tag-escaped), the fetch-only channel |
| `PARTS_INDEX.md` | self-calibrating walk instructions (probes + THE LOOP + part table + anchors) |
| `AGENT_PROMPT.txt` | the single file agents read first: calibrate, pick channel, anti-hallucination rules |
| `RECREATE_PROJECT.md` | single-file bundle for fetchers that do NOT strip tags |
| `bundle/INDEX.json` + `bundle/shard-*.json` | single-line tag-proof JSON shards (<= 8 KB wire) for newline-collapsing fetchers |

After committing and pushing, re-run the verifiers in `remote` mode (the
checklist prints the exact commands), then give agents **one URL, nothing
else**:

```
https://raw.githubusercontent.com/YourName/your-project/main/AGENT_PROMPT.txt
```

Notes:

- Non-node project? Pass `--install-cmd` / `--run-cmd` (e.g. `pip install -r
  requirements.txt` / `python main.py`). Channel A auto-disables when the repo
  has no `package.json`.
- `--fabrication-tell` injects a project-specific "you fabricated it"
  symptom (e.g. wrong-era boilerplate) into the agent's rules.
- `package-lock.json` and root-level `*.zip` files are excluded from the
  parts automatically; add more via repeatable `--exclude`.
- **Regenerate after every source change** - a stale part table silently
  corrupts reconstructions.

## Repo map

| Path | What it is |
|---|---|
| `scripts/new_project.py` | One-command orchestrator: generate all, verify locally, print publish checklist |
| `scripts/make_simple_parts.py` | Generator: `parts/` + `parts-esc/` + `PARTS_INDEX.md` (100 lines / 4,000 B caps per part) |
| `scripts/make_agent_prompt.py` | Generator: `AGENT_PROMPT.txt` from data-driven anchors and your URLs |
| `scripts/make_recreate_bundle.py` | Generator: single-file markdown bundle |
| `scripts/make_json_shards_v2.py` | Generator: bundle v3 JSON shards (<= 8 KB, zero raw `< > &`, single-line) |
| `scripts/verify_parts.py` | Verifier: reassembles both part sets, byte-compares (`local` / `remote`) |
| `scripts/verify_bundle_v3.py` | Verifier: reassembles the JSON bundle, byte-compares (`local` / `remote`) |
| `examples/peach-goma-skyhop/` | Real generated `AGENT_PROMPT.txt` + `PARTS_INDEX.md` from the proven transfer |

## The channels, in the order agents are told to try

| Channel | Requires | Exact? |
|---|---|---|
| A. `npm pack github:user/repo` | npm/shell | byte-exact, one command (auto-skipped without `package.json`) |
| B. `git clone` | git | byte-exact |
| C. Contents API + base64 decode | code execution | byte-exact (fetch-only agents: unusable - needs header or decoder) |
| D. `parts/` walk | fetcher keeps `< > &` and newlines | byte-exact |
| E. `parts-esc/` walk | fetcher strips tags but keeps newlines | byte-exact after 3 replace-alls |
| F. `bundle/INDEX.json` shards | fetcher collapses newlines too | byte-exact after JSON parse |

## Design rules (the part that actually matters)

1. **Calibrate before trusting.** `PARTS_INDEX.md` STEP 0 embeds a tag probe
   and a newline probe. The agent measures its own fetcher and routes itself
   to the right channel - we never assume which lane works.
2. **Escape, don't avoid.** `parts-esc/` stores `< > &` as `\u003c \u003e
   \u0026`, so tag-strippers find nothing to strip. The generator asserts no
   source file already contains those literal sequences (ambiguity guard).
3. **Cap in bytes AND lines.** Every part is <= 100 lines and <= 4,000 bytes
   *on the wire* (UTF-8). Byte caps dominate character caps (bytes >= chars
   for UTF-8), so the limit holds whether a fetcher counts bytes or
   characters; the line cap exists because some pipelines are line-oriented.
4. **Write as you read.** One fetch = one part = create-or-append, BEFORE the
   next fetch. The agent never holds whole files in memory, never rewrites
   from memory, never stacks unwritten parts (unwritten text falls out of
   agent context).
5. **Verification is separate code.** Verifiers re-parse part headers,
   re-assemble, and byte-compare against the working tree - locally and again
   from the live remote. Builders are never trusted.
6. **Anchors instead of trust.** Anchors are *computed* from your real files
   (file count, total bytes, largest file, a tag-safe preview line), so they
   can never drift. Any mismatch = the agent truncated or fabricated.
7. **Honest failure beats fake success.** The rules forbid claiming success
   without printing a verification value, and the final report template forces
   explicit OK/FAIL per gate.

## Historical note

`make_json_shards.py` (v1, plain-JSON shards up to 123 KB) is intentionally
not included: agent #2 proved single responses get truncated far below that
size, and v3 (shards <= 8 KB, zero raw `< > &`, single-line) superseded it.
Keep only what survived contact with real fetchers.
