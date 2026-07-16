# Trinity — World Clock (G99/G41) and the Winged Boots

Derived from disassembly of TRINITY.DAT (TRINITY.txt). Extends the Blockhouse writeup (`data/trinity_dog_puzzle.md`), which found the dog-recall event gated on `G99 == 27`. This document covers the clock mechanism itself and how the boots interact with it.

## The clock: G41:G99:G43 = HH:MM:SS

`G99` (Global #154, declared initial value `0x1E` = 30) is not a per-turn counter — it's reused as a **local scene clock**, reset to a specific starting minute value whenever a new "reality"/chapter/vignette is entered, then counted upward as the scene progresses. `G41` accompanies it as an hour counter (0–23).

This is confirmed by a generic clock-display routine at `0x102D0` (called from a "consult watch"-type handler at `0x29108`/`0x35CCC`), which formats `G41:G99:G43` as a literal `H:MM:SS am/pm` string (12-hour, zero-padded minutes/seconds, am/pm from `G41`). So **`G43` is not a separate mystery counter — it's the seconds field of the same clock**, which resolves the earlier open question about its `SUB G43 0x0F -> G67` wraparound (that's just seconds rolling over past 59, mirrored the same way minutes roll into hours).

### The tick-advance routine chain

```
0x17D10  — loop: calls 0x17D30 exactly L00 times (L00 = "how many minutes to advance", passed in by the caller)
0x17D30  — the actual per-tick body:
             JZ G4A [TRUE] → (G4A set) just clear G4A and return — one tick silently suppressed
             ... walks a scheduled-event/daemon table (G2A) ...
             INC G85                          ; total-elapsed-turns-ish counter
             JZ G74 [TRUE] → RET               ; G74 set suppresses the clock entirely (skips G99/G41 update)
             ADD G43 0x0F -> G67; JG G43 0x3B ...  ; a parallel counter, not traced further
             INC G99
             JG G99 0x3B [FALSE] → skip wrap    ; wraps past 59
               SUB G99 0x3C -> G153            ; overflow handling (not fully traced — see caveats)
             INC G41
             JG G41 0x17 [FALSE] → skip wrap    ; wraps past 23 (hour rollover)
               STORE G41 0x00
```

So **the clock only advances when something explicitly calls `0x17D10` with a tick count** — it is not a blanket "every turn" increment. Two flags (`G4A`, `G74`) can each suppress a tick/the whole update, which is presumably used elsewhere in the game to give "free" actions that don't cost story time.

### What calls the tick-advance chain

`0x17D30`'s callers: `0x0FE54`, `0x17478`, `0x17D10` (self, via the loop). `0x17D10`'s own callers: `0x17218`, `0x17318`, `0x26868`. Of these, **`0x17318` is the desert-wander dispatcher** — its caller list is the ~40 conditional desert direction-exit routines already catalogued in `data/trinity_routine_analysis.txt` / the "Desert Navigation" section of the memory reference. `0x17218` (detailed below) is the routine that actually computes how many minutes a desert move costs, including the boots check. `0x0FE54`, `0x17478`, and `0x26868` were not traced in this pass — they may drive the clock during other travel systems (e.g. other chapters' equivalent of "wandering"), but that's unconfirmed.

**Practical implication:** most ordinary room-to-room movement in the game (the Blockhouse, the Wabe, etc.) does *not* appear to run through this specific chain — the Blockhouse's own `G99` gate advances via whatever drives its local scene (not traced here), separately from the desert-wander system. Treat the tick-cost numbers below as specific to **desert wandering**, not universal per-move costs.

## Known scene resets (STORE G99 <value>)

Every place the code does `STORE G99 <value>` marks entry into a new scene with its own local clock, paired with a `G41` (hour) reset alongside it where present. All eight resets found in the disassembly are now identified:

| Address | G99 reset | G41 (hour) reset | Scene |
|---|---|---|---|
| `0x1C0F1` | `0x01` (1 min) | `0x0B` (11am) | **Nagasaki.** Flying scene: "soars high over the city... rhythmic pump of its great wings... the drone of approaching [aircraft]" — the aircraft's vocab includes "BOCK'S AIR" (**Bockscar**, the B-29 that dropped the bomb). Reached by flight (winged boots) over the city. 11:01am is one minute before the actual historical detonation (11:02am local time, Aug 9 1945) — a near-exact match. |
| `0x24BE8` (via `0x24BBC`) | `0x3A` (58 min) | `0x04` (4am) | **New Mexico/Trinity.** "Islet" (#5, Parent #88) → IN → **Shack** (#507) — the same Shack referenced in the Blockhouse guard-chase text ("crawl over to the exit, peek around the [309]..."). 4:58am, just before the historical 5:29:45am Trinity detonation. |
| `0x22D48` (via `0x22D28`) | `0x34` (52 min) | `0x04` (4am) | **New Mexico/Trinity.** "Mesa" (#76, Parent #88) → IN, past a door (object #524) — "squeeze through / cross the brink of [it]." 4:52am, same pre-dawn Trinity timeline as the Shack entry above. |
| `0x22BFD` | `0x32` (50 min) | `0x11` (17 = 5pm) | **New Mexico area, different visit.** "Ossuary" (#522, Parent #88) → door → **Underground** (#131, home of the lantern #357) — "You explore the door's edge with a timid foot." 5:50pm — much later in the day than the Mesa/Shack/dawn-detonation timeline; likely a separate, earlier (in-story) exploration of the same physical desert region before the actual test night. |
| `0x2304F` | `0x29` (41 min) | `0x0E` (2pm) | **New Mexico/Cottage area.** Herb Garden (#417) → IN through the white door (#356, from the lemming puzzle) once open. 2:41pm — same "different visit, different time of day" pattern as the Ossuary entry. |
| `0x2CD2A` | `0x3B` (59 min) | `0x0F` (3pm) | **Transition into The Wabe** (`STORE GAE 0x79`). Also sets `G74 = 1` (suppresses the next clock tick) and inserts the parrot's umbrella (#549) directly into the player's inventory (#103) — a scripted "arrival" cutscene, likely the payoff of a giant-garden/Wonderland puzzle (nearby text: "...isn't long enough to reach ... Nice try. Unfortunately, your arm isn't long enough to reach ..."). 3:59pm. |
| `0x3B0B1` | `0x1E` (30 min) | `0x0F` (3pm) | **Present-day Kensington Gardens reset.** A large state-reset routine: clears/repositions the old woman (#567, owner of the umbrella), Lancaster Gate-area objects (#41, #531, #93, #45, #342 — all part of the real Kensington Gardens gate names catalogued elsewhere), clears an attribute on the player's own hand (#10), and sets `G74 = 0` (un-suppresses the clock). 3:30pm — matches the global's declared *default* value, confirming this is a "return to (or start of) the present-day frame story" reset rather than a historical vignette. |

## Known significant thresholds (JE/JG/JL against G99)

The full list of distinct comparison values seen against `G99` in the disassembly (72 total references): `0x00, 0x01, 0x02, 0x09, 0x0A, 0x0F, 0x18(24), 0x1B(27), 0x1C(28), 0x1D(29), 0x1E(30), 0x28(40), 0x29(41), 0x31(49), 0x32(50), 0x34(52), 0x36(54), 0x37(55), 0x38(56), 0x39(57), 0x3A(58), 0x3B(59)`. These now sort into four scene clusters plus one purely generic routine:

### New Mexico / Trinity test countdown (the big one)

This is not just the Blockhouse dog recall — it's one large, multi-room countdown sequence, all sharing the same clock:

- **`G99 == 0x1B (27)`** — the dog is `REMOVE_OBJ`'d ("It's time, Wolf!"), and the Blockhouse `SW` exit opens (`G99 > 27`). Full detail in `data/trinity_dog_puzzle.md`.
- **`0x18(24)`, `0x1C(28)`, `0x1D(29)`** (routine `0x1D390`, right next to the tick-27 event) — a short run of narrated flare/signal beats leading up to and past the dog recall.
- **`0x09(9)`, `0x1B(27)`, `0x1C(28)`, `0x1D(29)`** (routine `0x1D6E0`/`0x1D90C` area) — an in-fiction radio countdown: *"Ninety seconds to auto-sequencer. Mark."* — the real 1945 Trinity test used an automatic countdown timer, and this is that timer being called out over the radio. The same routine also handles a distant gunshot near object #387 and walkie-talkie (#60) chatter ("Looks like a no-go without X").
- **`< 0x1D (29)`** (routine `0x3683C`, objects **white wire (#7), blue wire (#192), striped wire (#338), red wire (#265)**) — a colored-wire puzzle, hinted by "[You] must refer to the wires by their color." Given the "auto-sequencer" framing elsewhere in the same cluster, this reads as the player handling the actual detonator wiring of the historical device during the final countdown, not a modern bomb-disposal scene.
- **`< 0x1D (29)`** (routine `0x39335`, near object #270/#251/#245) — more countdown radio chatter: *"X just woke up again... sounds like a wet line somewhere... the kid's keepin' an eye on it. If it dies again before the sequencer takes over, we're gonna have to scrub. Roger... lotta crossed fingers up here."* — technicians worried a bad connection will force an abort ("scrub") before the automatic sequencer fires.
- **`< 0x1C (28)`** (routine `0x21E64`, object **"GIs" (#59)**) — soldiers waiting nearby getting increasingly tense as the tick approaches 28: "obviously under a lot of strain... fingers drum impatiently on their steering wheels... eyes dart back and forth..."
- **`> 0x31 (49)`** (routine `0x24E9C`, the white door **#356** from the lemming puzzle) — "Numb with cold, you leap across the jamb of the [door]" instead of the plain version — a flavor variant for having lingered too long (fits the pre-dawn desert cold).
- **`0x00`, `0x01`** (routine `0x1E928`/`0x1E985`) — an MP (military police) shoving a rifle barrel into the player's back ("Before you can move, an MP is shoving a barrel into the small of your back"), touching Shack (#507) and room #158.

### Nagasaki schoolyard (tied to the `0x1C0F1` reset)

- **`0x00`, `0x01`, `0x02`** — the "girl" (#155, the child later shielded from the blast), "teachers" (#169), and "children" (#553) are all "watching the sky apprehensively" at this exact tick, versus their normal playful/working behavior (`0x35961`–`0x35A65` cluster). At `0x200A8`/`0x205D6` the same girl object reacts "urgently"/"desperately" instead of "playfully"/"cheerfully" specifically at tick 1.
- **`0x38 (56)`** (routine `0x1B7F0`, called from the aircraft object #566's own handler) — the flash of light itself: *"[The area] is lit by a terrifying flash of light. You dive to cover the screaming [girl]... and feel the earth shudder beneath a crushing blast wave. Your body absorbs much of the deadly radiation that might otherwise have reached the child. Years later, she recalls to her grandchildren the tale of a mysterious stranger who shielded her life..."* — a heroic self-sacrifice death, then `CALL 0x28C40` (the shared death handler).

### Tropical thermonuclear test (likely Bikini Atoll / Castle Bravo)

Routine `0x1B328` and onward (`0x36`–`0x3B`, i.e. 54–59): *"Your tropical vacation is cut short by a multimegaton thermonuclear detonation, centered in the nearby [maze of plumbing]."* "Multimegaton" points to a hydrogen-bomb-scale test rather than the ~20kt Trinity/Nagasaki devices — Castle Bravo (Bikini Atoll, 1954, ~15 megatons) is the obvious real-world match. The sequence is a rising-tide countdown: a floating object (#283) drifts away and eventually vanishes, "Five. Four. Three. Two. One." plays over some broadcast (gated on object #25's state), and a spoken countdown ("...minutes.~" / "ninety seconds.~" / "forty-five seconds.~" / "thirty seconds.~") plays via `PRINT_PADDR G94` as the ticks climb toward `0x3B`. Ends the same way as the others: `CALL 0x28C40`.

### Not clearly scene-specific

- **`0x102FC`** — this is a **generic clock-display routine** (`0x102D0`), not a narrative event: it just prints `G41:G99:G43` as `H:MM:SS am/pm`, with the `G99`-vs-`0x0A` check only there to decide whether to zero-pad the minutes. Confirms `G43` = seconds (see above).
- **`0x1863A`** — ties `G99 == 0x39 (57)` to `PUT_PROP OBJECT41 PROPERTY43 ... "yellow"`, gated by a separate, unrelated countdown global (`G6C`, decremented 10→0). Object #41 is one of the Kensington Gardens gate-area objects touched by the big present-day reset (`0x3B0B1`) above — likely a minor cosmetic detail (something changing color/ripening at a specific time of day) rather than a major plot beat. Not confidently attributed beyond that.

## The boots: how they affect ticks

Two objects: **red boot (#172)** and **green boot (#294)**, found on a corpse (#582, vocab "WABEWALKER" — implying a previous, unsuccessful traveler) near the Wabe. Each boot has an `ATTRIBUTE34` ("worn") and, separately, an `ATTRIBUTE4` flag that gets set only after a specific ritual: pressing a jewel into the boot's toe recess (`GDD`=boot, `G6D`=jewel) —

> "You press the [jewel] into the toe of the [boot]. As you watch, the leather closes around the jewel and absorbs it like melting wax. A shudder of ecstasy ripples up and down the length of the boot. It begins to glow with raw energy, brighter and brighter, until you shield your eyes from the glare. When you peek again, a tiny pair of wings has sprouted out of the heel."

So `ATTRIBUTE4` = "has been activated/winged," distinct from and in addition to `ATTRIBUTE34` = "currently worn." Both boots need **both** flags for flight to work.

### The desert-wander cost, with and without wings (`0x17218`)

This routine only applies to desert-to-desert movement (both current and destination rooms have `ATTRIBUTE20`, inside zone object #88 — the documented "Desert Navigation" system). It computes how many minutes (`L01`) the move costs, then calls `CALL_2S 0x17D10 (L01)`:

```
Normal (missing worn+winged on either boot):
  RUN/JOG verb, terrain ATTRIBUTE3 set     → L01 = 0x13 (19 minutes)
  RUN/JOG verb, terrain ATTRIBUTE3 unset   → L01 = 0x09 ( 9 minutes)
  WALK (anything else), terrain ATTR3 set  → L01 = 0x1D (29 minutes)
  WALK, terrain ATTR3 unset                → L01 = 0x13 (19 minutes)
  ... CALL_2S 0x17D10 (L01)                ; clock advances by L01 minutes

Both boots WORN (ATTRIBUTE34) *and* WINGED (ATTRIBUTE4):
  TEST_ATTR OBJECT172 ATTRIBUTE34 [FALSE] → normal path above
  TEST_ATTR OBJECT172 ATTRIBUTE4  [FALSE] → normal path above
  TEST_ATTR OBJECT294 ATTRIBUTE34 [FALSE] → normal path above
  TEST_ATTR OBJECT294 ATTRIBUTE4  [FALSE] → normal path above
  STORE G17 0x02                           ; "flight" indicator
  PRINT "You put one boot forward... [scenery] streaks past in a dizzy rush of color"
  RTRUE                                     ; returns WITHOUT ever calling 0x17D10
```

**Running roughly halves the cost of walking (9–19 vs. 19–29 minutes), but flying with both activated, worn boots skips the clock call entirely — desert-wander moves cost zero minutes on the world clock while flying.** Given that scripted events (like the Blockhouse dog recall at tick 27) are gated on this same clock, doing your desert travel while winged effectively "freezes" story time during those moves, buying much more slack against any time-based deadline than even running would.

(Global `G17` is also referenced in unrelated-looking code near the roadrunner/dog logic around `0x1C8D7`–`0x1C93D`, decrementing a counter with similar "skip checks while this is nonzero" semantics. It's unclear whether this is the same "flight in progress" concept reused, or an unrelated reuse of the same global slot — flagging as uncertain rather than asserting a link.)

## Caveats

- All 8 scene-reset addresses and all but 2 of the distinct threshold values are now attributed to a specific scene (New Mexico/Trinity countdown, Nagasaki, the tropical thermonuclear test, or the two Kensington Gardens transitions). `0x1863A` remains only loosely attributed (minor cosmetic detail, gated by an unrelated countdown global `G6C`); the exact object/scene for the "Ossuary"/"Mesa" *time-of-day* discrepancy (New Mexico rooms resetting to both ~4-5am *and* ~2-5pm) wasn't resolved — plausibly two separate in-story visits to the same physical desert region, but that's inference, not confirmed text.
- The exact semantics of the `G99`/`G43` overflow (`SUB G99 0x3C -> G153`, `ADD G43 0x0F -> G67`) weren't fully resolved at the byte level; they don't appear to reset `G99`/`G43` themselves, which is odd for a wraparound and wasn't chased down further. This no longer matters much for narrative purposes now that `0x102D0` confirms `G41:G99:G43` is just a conventional `H:MM:SS` clock — the wraparound almost certainly works correctly for display purposes, only the exact overflow bookkeeping is unresolved.
- The tick-cost analysis (9/19/29 minutes, zero while flying) is specific to the **desert-wander system** (`0x17218`/`0x17318`). Whether the same boots have any effect on movement cost in other travel systems (`0x0FE54`, `0x17478`, `0x26868` — the other callers of the tick-advance chain) was not checked.
- The New Mexico "auto-sequencer" countdown cluster (wire puzzle, GI chatter, walkie-talkie, MP capture) spans many routines across a wide address range; individual branch-level behavior within that cluster was not traced exhaustively — only enough to confirm scene identity and rough sequencing.
