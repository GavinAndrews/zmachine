---
name: score-path
description: Reconstruct every point-scoring event (what earned each point, where, and the running total) along the real playthrough path to a save, correctly skipping abandoned restore-branches. Use when the user asks how they got to a score, wants a breakdown/history of all points earned, wants to know where/how they scored, or asks to redo this after new transcripts or saves were added.
---

# Score path reconstruction

Given a game's `gameplay/<game>/transcript*.txt` files, produce an ordered
table of every point-scoring event on the **true** path to a save: the
transcript line, points gained, running total, the command that earned it,
and the in-game location.

The hard part isn't finding `[Your score just went up...]` lines (a plain
grep does that) -- it's that a raw grep also picks up score events from
**abandoned branches**: stretches of play the user later undid with
`restore` to try something else. Those show up as scores that jump around
non-monotonically when scanned naively. This skill reuses the save-graph
skill's transcript-ordering/restore-pruning engine (`rebuild_save_artifacts.py`,
in the sibling `save-graph` skill directory) to get the actual surviving
command sequence first, then only scans the transcript text *between
consecutive on-path commands* for score messages -- so an abandoned
branch's score events are never visited, because both commands bracketing
it survive on the true path and the branch sits (restored away) in between.

## Running it

```
python .claude/skills/score-path/score_path.py --game trinity
```

- `--game NAME` -- defaults to `trinity`. Resolves to `gameplay/<name>/`.
- `--save NAME` -- analyze the path to a specific `.sav` file instead of the
  auto-picked one. Default is the reachable save with the longest
  reconstructed command chain (same "furthest progress" heuristic save-graph
  uses for its default goal save) -- in practice this is also the
  highest-scoring save, since score is monotonic along any one true path.
- `--out PATH` -- output markdown path (default `gameplay/<game>/score_path.md`).

Prints the table to stdout and also writes it to `score_path.md`. Also
prints a **WARNING** if the running total doesn't add up (previous total +
this event's delta != the game's own reported total) -- that would mean the
reconstructed path still has an off-path event in it, so treat the output as
suspect and investigate rather than trusting the numbers.

## Repeatable use

Whenever new transcripts or saves are added and the user's peak score
changes, just rerun the command above -- it re-discovers every
`transcript*.txt` in the directory the same way save-graph does, so there's
nothing to update by hand.

## Limitation

Only works for games that emit the V4+-style per-pickup announcement
("Your score just went up by N points. The total is now M out of 100.") --
Trinity does this. Status-line-only V1-3 games (Zork I/II/III) never print
this message per point, so this script correctly reports zero events for
them; reconstructing their score history would need diffing periodic
"[Your score is N...]" checkpoints instead, which isn't implemented here.

## History

Built after manually reconstructing the path to a 91/100 Trinity score by
hand (in a subagent) once; this generalizes that one-off into a rerunnable
tool built on save-graph's existing, already-correct branch-pruning replay
rather than re-deriving it.
