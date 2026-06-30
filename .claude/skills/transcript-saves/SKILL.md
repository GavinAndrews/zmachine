---
name: transcript-saves
description: Build a markdown table of save games from an Infocomm interpreter transcript (transcriptN.txt) — each save's location and the 5 player commands preceding it. Use when the user asks to find/list/table the save games (or save points) in a transcript file, or to do "the same thing" done previously for transcript5.txt on a new transcript.
---

# Transcript save-game table

Given an Infocomm interpreter transcript file (e.g. `transcript5.txt`, `transcript6.txt` in the `infocomm/` directory), produce a markdown table of every save event: the in-game location at the time of the save, and the 5 player commands immediately preceding the `save` command.

## Transcript format

Each player turn looks like:

```
[Obj#NNN: Location Name]
> command
... game output ...
```

A **save** event looks like:

```
> save
Save to file: 
> filename.sav

[SAVE completed.]
```

A **restore** event looks similar but with `restore` / `Restore from file:` / `[RESTORE completed.]` — exclude restores from the table unless the user explicitly asks for them too.

## Steps

1. Read the transcript file. If it's large, use `Grep` first to find all save events in one pass:
   ```
   pattern: Save to file:|^> save$
   ```
   This gives line numbers for every actual save (a `> save` command followed two lines later by `Save to file:` and the `.sav` filename). Don't confuse this with `restore` events, which have their own `Restore from file:` marker — only count lines that precede a `Save to file:` line.
2. For each save event, read enough surrounding context (`Read` with `offset`/`limit`, or just re-read the relevant page) to find:
   - **Location**: the `[Obj#NNN: Location Name]` tag immediately above the `> save` line (or the room-name footer printed just before the `>` prompt — either works, they match).
   - **Previous 5 commands**: walk backwards through the `> ` input lines preceding `> save` and collect the 5 most recent player commands (not the `save` command itself). If a prior `save`/`restore` command appears within that window, count it as one of the 5 — don't skip it.
3. If a save overwrites a `.sav` file that was already used earlier in the transcript, note it as "(overwrite)" in the table — don't merge or drop duplicate filenames.
4. Output a markdown table with columns: `#`, `Save File`, `Location`, `Previous 5 Commands`.
5. Write the table to a new file named `<transcript-basename>_saves.md` next to the transcript (e.g. `transcript5_saves.md`), using the `Write` tool. Include a short notes section below the table covering any edge cases hit (e.g. a save occurring right after a scenery-only room transition with few preceding commands, or restores excluded by default).

## Notes from prior runs

- Transcripts can be several thousand lines; `Read` truncates around ~2000 lines per call — use `offset`/`limit` to page through, or `Grep` to jump straight to save/restore markers instead of reading the whole file linearly.
- Room-transition teleports (e.g. stepping through a "white door") print ~20-30 blank lines before the new location — don't count blank lines as commands.