# Save Games — transcript21.txt

| # | Save File | Location | Previous 5 Commands |
|---|-----------|----------|---------------------|
| 1 | wt71.sav | Shack | wait; enter dory; give silver coin to oarsman; s; enter door |
| 2 | wt72.sav | South of Reservoir | u; turn lantern off; n; s; d |
| 3 | wt73.sav | Base of Tower | wait; wait; wait; d; d |
| 4 | wt74.sav | Crossroads | d; save; sw; sw; sw |
| 5 | wt75.sav | Behind the Shed | d; s; s; s; s |

## Notes

- The transcript opens with a `restore wt17.sav` (line 15) rather than a fresh start.
- This is the New Mexico atomic-test area again, and the player dies repeatedly (atomic blast, MPs catching you on the ladder, the guard dog raising an alarm) while working out the safe route/timing. **14 restores** occur across the transcript; all are excluded from the table.
- **Save 4** (wt74.sav): Save 3's own `save` command (line 1212) falls inside Save 4's 5-command lookback window and is counted as one of the 5, per the "don't skip a save/restore inside the window" rule.
- One restore (line 950, `wt12.sav`) jumps to a completely different branch of the game — "Cottage", far from the tower area — where the player tries (and fails) to take a huge book, then restores `wt71.sav` (line 972) to abandon that detour and resume the tower/reservoir sequence. This is the "harmless" transcript gap referenced in `save_paths.md`/project memory: nothing gets saved during the Cottage detour before it's abandoned.
- A typo (`restire` at line 1097) is rejected by the parser and does not count as a real restore attempt.
- The transcript ends with `quit` → `yes` after Save 5, at "Behind the Shed".
