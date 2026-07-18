---
name: save-graph
description: Regenerate save_paths.md (reconstructed command sequences for every .sav file) and saves.html (an interactive vis-network graph of the save tree) for a game from its gameplay/<game>/ transcripts. Use when the user asks to rebuild/regenerate/update the save graph or save-path reconstructions, says these files are stale/out of date, or asks to redo what was previously done for saves.html/save_paths.md after new transcripts or saves were added.
---

# Save graph reconstruction

`gameplay/<game>/save_paths.md` and `gameplay/<game>/saves.html` are derived
artifacts: for every `.sav` file with transcript evidence, the full sequence
of player commands needed to reach that exact save state, and an interactive
graph of how all the saves relate (which one branches from which, and what
commands sit on each branch). Both are regenerated from scratch by one
script — `rebuild_save_artifacts.py`, next to this SKILL.md.

## Running it

```
python .claude/skills/save-graph/rebuild_save_artifacts.py --game trinity
```

- `--game <name>` — defaults to `trinity`. Resolves to `gameplay/<name>/`.
- `--goal <savename>` — override the auto-picked "goal" save (the orange
  highlighted node / default in saves.html's "Route to" filter). Default is
  whichever reachable save has the longest reconstructed command chain
  (furthest progress). Only needed if you want to highlight a specific
  save (e.g. a particular ending) instead.
- `--paths-only` / `--html-only` — write just one of the two output files.

The script auto-discovers every `transcript*.txt` in `gameplay/<game>/` —
there is no file list to maintain. Just drop new transcripts in that
directory and rerun.

## How it figures out transcript order

No manual ordering list. Each transcript file is classified by how it opens:

1. **Restores a save** (`restore <name>` appears before any real gameplay,
   ignoring restores of saves the file *itself* already produced earlier —
   those are just ordinary mid-session save-scumming after a death, not a
   cross-file link) → depends on whichever transcript(s) produced `<name>`.
2. **Fresh-start banner** (the copyright text, or the `[RNG seeded ...]`
   debug line, near the top) and no restore → a genuine fresh game start.
3. **Neither** → the game process just kept running while transcript
   logging was toggled off/on (`#transcript`), so the file is a raw
   continuation of whichever other transcript's *ending* location matches
   this file's *opening* location.

Files are grouped into independent play-session trees by this dependency
graph; each group replays as one continuous stream (so state carries across
a raw mid-session file split, but never leaks between unrelated sessions).
Two groups currently exist for Trinity: the main story chain rooted at
`transcript1.txt`, and an unrelated old legacy session rooted at
`transcript.txt` (produces `a.sav`–`d.sav`).

## Location parsing

Same rule as the `transcript-saves` skill: transcripts recorded with `#loc`
on have `[Obj#NNN: Location Name]` tags; transcripts recorded with `#loc`
off have none, so location falls back to the bare room-name line some turns
echo immediately above the next prompt. This is decided per-file (a file
either has tags throughout or not at all, matching that `#loc` is a
session-wide toggle), not by transcript naming/date.

## What "keep all the concepts in saves.html" means in practice

`saves.html` is regenerated **from its own current content**, not from
`map.html` (which is a different, independently-evolving room-map graph
that happens to share the same vis-network scaffold). The script only
regex-replaces four things in the existing file:

- `NODES_DATA` / `EDGES_DATA` / `PATHS` (the graph data)
- the `<option>` list inside the `#dest-filter` "Route to" dropdown
- the "N saves unreachable (hover)" badge text/tooltip

Everything else — physics-off-after-settle, drag-to-reposition with
localStorage autosave, JPEG/PDF export, the goal-save orange highlight
baked into `NODES_DATA`, the destination filter that limits the displayed
subgraph to one save's path — survives untouched because it's simply not
touched. If you ever need to change any of that scaffolding, edit
`saves.html` directly; the next regeneration will preserve your edit.

## Unreachable saves

The "N saves unreachable" badge and the `## Unreachable saves` section in
`save_paths.md` are computed dynamically: every `.sav` file physically
present in `gameplay/<game>/` that no transcript ever shows being *saved*
(not restored — a restore of a name nobody saved is logged separately per
group as "could not be resolved", which usually means a transcript that
produced it no longer exists on disk). No hardcoded list to maintain.

## History

This script replaces `infocomm/reconstruct_save_paths.py` and
`infocomm/build_saves_graph.py` (deleted), which hardcoded an explicit
transcript file list and a fixed goal save name, and broke once transcripts
moved out of `infocomm/` into `gameplay/<game>/`.
