# PARTS INDEX - rebuild this repo by reading tiny text parts

Goal: recreate every source file on disk (by hand, from these parts)
so the project builds and runs. No JSON, no decoding, no special tools.

## STEP 0 - calibrate yourself (one fetch, already done if you read this)
Probe 1 (tags): the next line contains a test tag:
<tag-probe-12345>
If you can see "<tag-probe-12345>" above, your fetcher keeps tags:
use parts/. If it vanished or looks mangled, your fetcher strips
tag-like text: use parts-esc/ instead (same parts, but < > & are
stored as backslash-u escape sequences).
Probe 2 (newlines): PROBE-A and PROBE-B are on separate lines:
PROBE-A
PROBE-B
If they arrive joined on one line ("PROBE-A PROBE-B"), your fetcher
collapses newlines: no plain-text channel can work for you. Stop and
use npm (see AGENT_PROMPT.txt) or the JSON bundle bundle/INDEX.json.

## THE LOOP (your whole job)
1. Run npm install once now. It regenerates package-lock.json, which
   is intentionally not shipped here.
2. Process parts strictly in order: p001, p002, p003, ...
   ONE part per fetch: write it (step 4) BEFORE fetching the next.
   Never fetch ahead of your writes. Part filenames follow one rule:
   pNNN__<file path, with / written as __>__partKKofNN.txt
   Example: p008__src__character__Cat.tsx__part01of17.txt holds the start of src/character/Cat.tsx.
   Cannot list a folder? https://ungh.cc/repos/SonaMother/peach-goma-skyhop-3d-cat-platformer/files/main
   lists every file path (plain JSON, no headers needed).
   If a fetch fails or a part looks cut off, re-fetch that part
   once; never guess lines. raw.githubusercontent.com blocked?
   Same files, no rate limit, at:
   https://cdn.jsdelivr.net/gh/SonaMother/peach-goma-skyhop-3d-cat-platformer@main/parts/FILE.txt
3. Line 1 of each part is a header [PART k of n | path].
   It is a label only - NEVER copy it into the target file.
4. Write as you read: part k=1 -> create the file with the remaining
   lines exactly as they are; parts k>1 -> append to the same file.
   Write immediately after each fetch: text you have not written down
   can fall out of your context later. Never hold whole files in
   memory; never rewrite from memory; never stack up unwritten parts.
   If a hard tool-step budget makes one-at-a-time impossible, fetch
   at most one file's parts ahead, and still write each part as it
   arrives.
5. When you consume the part whose header shows k equal to n, that
   file is complete. Move to the next part number.
6. parts-esc only: right after a file is complete, replace-all three
   sequences in it: \u003c with the less-than sign, \u003e with the
   greater-than sign, \u0026 with the ampersand.
7. After the last part: npm run dev. Done.

## PART TABLE (34 files, 223,453 bytes of source)
raw = parts/, esc = parts-esc/. Byte sizes refer to the real files.

| file | bytes | raw parts | esc parts |
|---|---|---|---|
| .gitignore | 334 | p001 (1) | p001 (1) |
| README.md | 8,363 | p002-p004 (3) | p002-p004 (3) |
| index.html | 783 | p005 (1) | p005 (1) |
| package.json | 784 | p006 (1) | p006 (1) |
| src/App.tsx | 3,143 | p007 (1) | p007 (1) |
| src/character/Cat.tsx | 58,242 | p008-p023 (16) | p008-p024 (17) |
| src/character/Part.tsx | 1,234 | p024 (1) | p025 (1) |
| src/character/README.md | 3,887 | p025 (1) | p026 (1) |
| src/character/expressions.ts | 8,337 | p026-p028 (3) | p027-p029 (3) |
| src/character/materials.ts | 3,982 | p029-p030 (2) | p030-p031 (2) |
| src/character/palettes.ts | 1,473 | p031 (1) | p032 (1) |
| src/character/poses.ts | 11,818 | p032-p035 (4) | p033-p036 (4) |
| src/character/springs.ts | 3,524 | p036-p037 (2) | p037-p038 (2) |
| src/game/sfx.ts | 6,504 | p038-p039 (2) | p039-p040 (2) |
| src/game/store.ts | 3,826 | p040-p041 (2) | p041-p042 (2) |
| src/game/useInput.ts | 3,901 | p042-p043 (2) | p043-p044 (2) |
| src/game/world.ts | 8,483 | p044-p046 (3) | p045-p047 (3) |
| src/index.css | 2,471 | p047 (1) | p048 (1) |
| src/main.tsx | 230 | p048 (1) | p049 (1) |
| src/scenes/GameOverScene.tsx | 4,821 | p049-p050 (2) | p050-p051 (2) |
| src/scenes/GameScene.tsx | 21,329 | p051-p057 (7) | p052-p058 (7) |
| src/scenes/LabScene.tsx | 3,505 | p058 (1) | p059 (1) |
| src/scenes/MenuScene.tsx | 4,572 | p059-p060 (2) | p060-p061 (2) |
| src/three-jsx.d.ts | 164 | p061 (1) | p062 (1) |
| src/ui/Overlays.tsx | 19,065 | p062-p066 (5) | p063-p068 (6) |
| src/ui/Sky.tsx | 1,066 | p067 (1) | p069 (1) |
| src/utils/cn.ts | 169 | p068 (1) | p070 (1) |
| src/world/Backdrop.tsx | 6,887 | p069-p070 (2) | p071-p072 (2) |
| src/world/Items.tsx | 8,770 | p071-p073 (3) | p073-p075 (3) |
| src/world/Particles.tsx | 6,631 | p074-p075 (2) | p076-p077 (2) |
| src/world/Platform.tsx | 10,904 | p076-p078 (3) | p078-p081 (4) |
| src/world/geometries.ts | 3,032 | p079 (1) | p082 (1) |
| tsconfig.json | 681 | p080 (1) | p083 (1) |
| vite.config.ts | 538 | p081 (1) | p084 (1) |

Totals: raw 81 parts, esc 84 parts. Every part is <= 100 lines and <= 4000 bytes.

## Sanity anchors (check these instead of trusting yourself)
- src/main.tsx is 230 bytes and starts with: import { StrictMode }
- index.html is 783 bytes and references /src/main.tsx (Vite, not CRA;
  any %PUBLIC_URL% means you fabricated it - redo that file)
- src/character/Cat.tsx is 58,242 bytes, the largest file
- The game builds with: npm install && npm run dev
