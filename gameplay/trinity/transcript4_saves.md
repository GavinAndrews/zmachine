# Save Games — transcript4.txt

| # | Save File | Location | Previous 5 Commands |
|---|-----------|----------|---------------------|
| 1 | wt4.sav | Underground | take all; w; take walkie; examine walkie; examine numbered slider |
| 2 | wt4.sav (overwrite) | Bottom of Stairs | e; e; turn lantern off; drop lantern; drop walkie |
| 3 | wt6.sav | Earth Orbit, in a soap bubble | wait; enter dish; s; sw; enter door |
| 4 | wt7.sav | Earth Orbit, on a satellite | wait; restore; examine moon; take skink; kill skink |
| 5 | wt8.sav | Waterfall | kill skink; save; look; wait; burst bubble with umbrella |
| 6 | wt9.sav | Bottom of Stairs | put dead skink in pocket; e; e; drop umbrella; i |

## Notes

- The transcript opens already at Bottom of Stairs with no explicit `restore` printed — a silent mid-session log split continuing directly from `transcript3.txt`.
- **Save 2** overwrites the file from Save 1 (both named `wt4.sav`).
- **Save 4** (wt7.sav): the satellite blast kills the player twice in this transcript. The first death (line 670, "the satellite's blast incinerates you") leads to a `restore wt5.sav` attempt that fails (file not found), then a successful `restore wt6.sav`. The second death (line 805, "your internal organs begin to rupture") leads straight to a successful `restore wt6.sav`. Only the second, successful restore (line 842) falls within Save 4's 5-command lookback window and is counted as one of the 5, per the "don't skip a save/restore inside the window" rule; the failed restore attempt and the first restore are both further back and excluded.
- **Save 5** (wt8.sav): Save 4's own `save` command falls inside Save 5's 5-command lookback window and is counted as one of the 5, again per the "don't skip" rule.
- Three restores occur in this transcript total (lines 707 — failed, `wt5.sav` not found; 716 — succeeded, `wt6.sav`; 843 — succeeded, `wt6.sav` again); all are excluded from the table itself, though two are referenced above where they fall inside a save's lookback window.
- The transcript ends with `quit` → `yes` after Save 6.
