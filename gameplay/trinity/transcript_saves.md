# Save Games — transcript.txt

| # | Save File | Location | Previous 5 Commands |
|---|-----------|----------|---------------------|
| 1 | a.sav | Palace Gate | i; examine watch |
| 2 | a.sav (overwrite) | Broad Walk | n; enter pram; open umbrella; push pram s; look |
| 3 | b.sav | Meadow | examine watch; look; enter door; e; e |
| 4 | c.sav | Barrow | ne; nw; s; give ruby to wight; i |
| 5 | d.sav | North Bog | look; s; examine flytrap; i; look inside flytrap |
| 6 | tuesday | Summit | n; se; sw; ne; sw |

## Notes

- This transcript is a separate, older, unrelated session from the `transcript{1,2,3,4,5,6,7,10,21,31}.txt` continuous-session group — it uses a different location-tag format (`[236: Palace Gate]` vs. the numbered `[Obj#NNN: Location Name]` seen in later transcripts, though functionally the same) and produces the legacy saves `a`/`b`/`c`/`d`/`tuesday` referenced in `save_paths.md`.
- **Save 1** (a.sav) happens at the very start of the session (the 3rd player input overall), so only 2 commands precede it instead of 5.
- **Save 2** overwrites the file from Save 1 (both named `a`) — noted as "(overwrite)" per the skill's convention rather than merged or dropped.
- **Save 3** (b.sav) lands immediately after the toadstool/white-door dimensional transition from Wading into Meadow — this transition prints ~20 blank padding lines (not counted as commands) between `e` (into the door) and the new-location banner.
- A `restore` immediately follows Save 1 (line 31, restoring `a` right after saving it) — excluded from the table per the default skill behavior.
- Several blank/empty player inputs occur elsewhere in the transcript (e.g. lines 848, 1566, 1816, 1820 — each producing `[What?]`), but none fall within any save's 5-command lookback window, so none appear in the table.
- The session ends with `quit` → `yes` at line 2239, after Save 6; no further saves occur.
