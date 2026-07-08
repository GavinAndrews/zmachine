# Save Games — transcript31.txt

| # | Save File | Location | Previous 5 Commands |
|---|-----------|----------|---------------------|
| 1 | wt81.sav | Bottom of Stairs | w; take lantern; sw; w; se |
| 2 | wt82.sav | Base of Tower | d; d; feed roadrunner; take ruby; put ruby in red boot |
| 3 | wt83.sav | Under the Windmill | take all; turn lantern off; u; s; ne |
| 4 | wt84.sav | North of Reservoir | u; nw; take all; drop shroud; take walkie |
| 5 | wt85.sav | Kitchen | take knife (failed); i; drop cage; wear binoculars; take knife |
| 6 | wt86.sav | Crossroads | nw; w; w; sw; sw |
| 7 | wt87.sav | Behind the Shed | binoculars look in shed; binoculars shed; look through binoculars at shed; examine shed with binoculars; look |
| 8 | wt88.sav | Outside Blockhouse | wake dog; restore (wt84.sav); restore (wt85.sav); restore (wt86.sav); sw |
| 9 | wt89.sav | Behind the Shed | restore (wt85.sav); restore (wt86.sav); se; se; s |

## Notes

- The transcript opens at "Cottage" (a `restore wt12.sav` from `transcript21.txt`, per the project's `save_paths.md`). The player dies twice in a row testing the cauldron puzzle (garlic → explosion, both times staying too close), restoring `wt12.sav` each time, then a third attempt at line 271 restores `wt17.sav` instead — a completely different branch (Bottom of Stairs, boot/tower gear) — and from there re-solves the cauldron puzzle correctly (leave the room before it detonates) before continuing into the tower/reservoir/windmill sequence that produces Saves 1–7.
- **Save 3** (wt83.sav): two blank inputs at lines 949 and 953 each produce `[Undone.]` — these are `undo` meta-commands whose typed text isn't echoed into the transcript the way ordinary commands are (this interpreter's meta-command handling intercepts them before the normal input-echo path), similar to the async map-notification quirk noted in `transcript10_saves.md`. Neither falls inside the save's 5-command lookback window.
- **Save 8** (wt88.sav) and **Save 9** (wt89.sav) sit inside the German-shepherd/blockhouse puzzle, which the player dies at repeatedly (waking the dog, feeding it the roadrunner, being spotted by the GI with binoculars, being overheard by the thin man). Save 8's window includes a death (`wake dog`) followed immediately by **three restores in a row** (wt84.sav → wt85.sav → wt86.sav, walking back up the save chain to a common point), and Save 9's window includes the last two of those same restores — both counted per the "don't skip a save/restore inside the window" rule.
- The transcript ends mid-death-loop: the last event is `quit` (line 2643) answering the "restart, restore, or quit" prompt after yet another blockhouse death, with the file ending immediately after (no confirmation `yes` captured). No further saves occur after Save 9.
