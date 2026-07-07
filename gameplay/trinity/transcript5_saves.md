# Save Games in transcript5.txt

Table of save games, the location the save was made at, and the previous 5 commands leading up to each save.

| # | Save File | Location | Previous 5 Commands |
|---|-----------|----------|----------------------|
| 1 | wt10.sav | South Beach | toggle switch, press toggle switch, press red button, s, wait |
| 2 | wt11.sav | Cottage | take garlic, w, read map, i, open coconut with axe |
| 3 | wt12.sav | Cottage | e, ne, e, put honey in cauldron, put hand in cauldron |
| 4 | wt13.sav | Cottage | save (→wt12), i, take skink, put skink in cauldron, put garlic in cauldron |
| 5 | wt12.sav (overwrite) | Cottage | i, drop coconut, cut coconut with axe, take cracked coconut, pour coconut milk into cauldron |
| 6 | wt12.sav (overwrite) | Cottage | put skink in cauldron, i, drop garlic, look, take cage |
| 7 | wt14.sav | Platform | e, look, enter door, enter white door (plus an earlier `e`) |
| 8 | wt16.sav | Moor | d, d, i, e, e |
| 9 | wt16.sav (overwrite) | Bottom of Stairs | enter bird, enter door, i, w, w |
| 10 | wt17.sav | Bottom of Stairs | drop boots, i, take cage, look, i |
| 11 | wt19.sav | Shack | look, examine cardboard, read poetry, look, open enclosure |
| 12 | wt21.sav | Northwest Room | enter, open screen door, e, read map, s |

Notes:
- `restore` operations (wt9, repeated restores of wt11/wt12/wt16/wt19/wt21) are excluded — this table covers only save events.
- wt9.sav was only restored within this transcript, never saved, so it does not appear above.
- Save #7 (wt14) occurred immediately after a scenery-only teleport (white door transition), so its 5th prior command falls just before the location change.
