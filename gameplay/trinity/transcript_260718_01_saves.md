# Save Games — transcript_260718_01.txt

Table of save games, the location the save was made at, and the previous 5 commands leading up to each save. Generated with `.claude/skills/transcript-saves/extract_saves.py`.

| # | Save File | Location | Previous 5 Commands |
|---|-----------|----------|----------------------|
| 1 | save_260718_01.sav | Tower Landing | drop cardboard, w, u, d, look |
| 2 | save_260718_02.sav | Base of Tower | climb ropes, restore (→save_260718_01), d, take ruby, put ruby in red boot |
| 3 | save_260718_03.sav | Front Deck | w, sw, look, s, u |
| 4 | save_260718_04.sav | Assembly Room | open cage, open door, s, move paper, take screwdriver |
| 5 | save_260718_05.sav | Behind the Shed | w, s, s, examine thin man, examine bunker with binoculars |
| 6 | save_260718_06.sav | Behind the Shed | take key, i, put knife in pocket, put screwdriver in pocket, take key |
| 7 | save_260718_07.sav | Base of Tower | open box, i, drop padlock, look, examine control panel |
| 8 | save_260718_08.sav | Jeep | raise antenna, set walkie to 51, toggle walkie, turn walkie on, score |

Notes:
- This transcript starts with `restore wt81.sav` at Palace Gate (line 16), not a fresh start.
- This transcript has no `[Obj#NNN: ...]` tags — locations were resolved from the bare room-name footer line that precedes each prompt (see SKILL.md's newer-format note).
- 6 restores are excluded from the table by default: the opening `restore wt81.sav`; `restore save_260718_01.sav` right before save #2 (undoes a death after `climb ropes`); two death-triggered restores of `save_260718_07.sav` between save #7 and save #8; and two further restores of `save_260718_08.sav` after the final save (post-save reloads, no later save follows them).
- Save #2's previous-5 window includes the `restore (→save_260718_01)` that undid a death right before it, per the "don't skip a save/restore inside the window" rule.