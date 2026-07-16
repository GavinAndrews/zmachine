# Trinity — Blockhouse: Guard Dog & Escape Route Analysis

Derived from disassembly of TRINITY.DAT (TRINITY.txt).

## TL;DR — does subduing the dog open the route around the blockhouse?

**No — not causally.** The `SOUTHWEST` exit from Outside Blockhouse (#174) that lets you go around the building is gated purely by the global game clock, **G99**:

```
26EC9 JG G99 0x1B [FALSE] 0x26ED7      ; if G99 > 27, exit succeeds (goes to room 529)
26ED7 PRINT "Another look at the shepherd encourages you not to go that way."
26EFF RFALSE
```

Nothing about the dog's attributes, sleep state, or attention is ever tested here — only `G99 > 0x1B (27)`. The flavor text blames the shepherd, but mechanically the block is a clock check.

Separately, at the *exact* moment **G99 == 0x1B (27)**, a scripted event fires (routine `0x1D390`, guarded by `JE G99 0x18 0x1B 0x1C`) that narrates a flare/signal going up and has the dog's handler call it away — `"...{It's }time{, }Wolf!~ calls a voice"` — followed by `REMOVE_OBJ OBJECT391`: the dog is unconditionally deleted from the room, regardless of anything the player has done to it.

So the dog leaving and the SW route opening are **both side effects of the same clock tick (27)**, not one causing the other. Any attempt to "subdue" the dog directly (petting past the wake-check, feeding it, sicing the roadrunner on it, attacking it) either has no lasting effect or actively risks the same guard/searchlight capture sequence as accidentally waking it — none of it changes whether SW is open. If it looked like subduing the dog opened the path, that's because both events lined up at the same in-game time.

**But this only applies to the movement gate, not to the whole location.** The three "Blockhouse" objects aren't uniformly related to each other:

| Pair | Related? |
|---|---|
| Dog (#391) ↔ Blockhouse (#73) | **No.** The blockhouse's own handler (`0x3B224`) only does generic "no windows/doors visible" and enter/climb checks — it never references the dog. It's just the building the dog happens to be chained to. |
| Dog (#391) ↔ Searchlight (#570) | **Yes.** Waking the dog triggers the searchlight/capture chain, and — as detailed below — the searchlight's own "break it" interaction checks the dog's presence to decide the outcome. |
| Dog (#391) ↔ SW exit | **No** (see above) — purely the G99 clock. |

## Object References

| Object | Description | Notes |
|--------|-------------|-------|
| #391   | German shepherd | vocab: dog, watchdog, shepherd, mutt, pooch, canine, animal, hellhound, alexis, wolf; Attributes 16, 26, 46, 47 |
| #174   | Outside Blockhouse | the room; New Mexico Trinity-test-site prologue area |
| #73    | blockhouse | dog is chained to this ("a chain of the type used to moor ocean liners") |
| #570   | searchlight | same room; sweeps the road when the dog wakes |
| #376   | roadrunner | wandering companion/animal; Parent = 0 until lured out with the bag of crumbs |
| #402   | bag of crumbs | lures/feeds the roadrunner |
| #10    | your hand | bare-hand attack text |
| #35    | your foot | kick attack text |

Objects #391, #73, and #570 are all siblings under parent #174 (`Next` chain: 570 → 73 → 391).

## Blockhouse (#174) Room Exits

| Direction (prop) | Destination | Gate |
|---|---|---|
| NORTH (63) | Object 497 | unconditional |
| NE (62) | Object 544 | unconditional |
| EAST (61) | Object 132 | unconditional |
| SE (60) | Object 132 | unconditional |
| SOUTH (59) | Object 529 | unconditional |
| WEST (57) | Object 529 | unconditional |
| **NW (56)** | **Object 497** (same as N) | unconditional — `0x26EB4`: "You skirt around the [blockhouse]." Always works, dog or no dog. |
| **SW (58)** | **Object 529** (same as S/W) | **PER routine `0x26EC8`: `G99 > 0x1B (27)` only.** Below that, blocked with "Another look at the shepherd encourages you not to go that way." |

So there are *two* "go around the blockhouse" directions: **NW always works** (flavored as skirting around it), while **SW only opens once the story clock passes tick 27** — the same tick where the dog is scripted to leave.

Room properties #33 and #28 both store `0x0187` (391 decimal — the dog's object number) as a generic "guard present" pointer; both are zeroed (`PUT_PROP OBJECT174 PROPERTY33/28 0x00`) in the same routine that removes the dog, right before `REMOVE_OBJ OBJECT391`.

## Dog's Handler (prop #50, routine `0x214B0`)

Called on essentially any verb aimed at the dog.

### 1. Name-calling gag
If the parsed noun matched a synonym of "hellhound"/"alexis"/"wolf", or the word "hell" was used, it jumps straight to `0x17BDC` (a canned rebuke) and returns — bypasses all normal handling.

```
CALL_VS 0x11294 ("hellhound","alexis",WOLF) -> -(SP)
JZ (SP)+ [FALSE] 0x214C9
CALL_2S 0x112FC ("hell") -> -(SP)
JZ (SP)+ [TRUE] 0x214CF
CALL_1S 0x17BDC -> -(SP)
RET 0x02
```

### 2. First-contact flag
`SET_ATTR OBJECT391 ATTRIBUTE24` — marks the dog as "dealt with" once any interaction happens.

### 3. Long description (gated by global **G5F**)
If G5F is unset, prints the full flavor text and returns:

> "You're looking at a hundred and ten pounds of hard, flea-bitten muscle, leashed to the blockhouse [#73] with a chain of the type used to moor ocean liners. Good thing it's sleeping."

### 4. Verb dispatch (global **G8B** = current verb, **G6D** = direct object)

| Verb code(s) | Behavior |
|---------------|----------|
| `0x51` | "The sleeping animal exhibits no interest." (generic inert response, e.g. ASK/TELL) |
| `0x4D`, `0x54` | `INSERT_OBJ G6D → OBJECT174`: "You deposit [item] under the sleeping dog's nose." (feed/give/put) |
| `0x92`, `0xBC` | `INSERT_OBJ G6D → room`: "…falls short of its target by several feet." (throw — always a comic miss) |
| unmatched | falls through to the same long description as step 3 |

### 5. Wake-check tables
`SCAN_TABLE` against global table **G9F** (16 entries), then a second inline set of verb codes (`0xC0/0xAD/0xA7`, `0x66/0x74/0x7F`, `0x7B/0x7E`) — these catch touch/pet/stroke-type verbs.

- If ATTRIBUTE23 already set on the dog (reuses the same "awake/running" bit the Kensington Gardens lemmings group uses) → `0x21794`: "curls its lip and rumbles… But you didn't wake it up… this time." (near-miss, stays asleep)
- If not set → `0x217E8`, the real wake sequence (see below).

### 6. Attack verbs (`0x65`, `0x31`, `0x32`, `0x1A`, `0x64`)
Always harmless, regardless of weapon:

> "Boldly, fearlessly, you march up to the dozing shepherd and draw back [your hand (#10) / your foot (#35), kick / held weapon] to deal the sleeping monster a mighty blow… But the dog snorts a bit in its sleep, and you bravely scurry backwards several dozen yards."

Weak held weapons (checked via `GET_PROP GDD PROPERTY47 < 3`) get an extra snarky aside: "(or as mighty a blow as you can expect from [weapon])". **GDD** holds the attack instrument (bare hand/foot/held item).

### 7. Smell/bathe verbs
- `0x55` → "…slobbers gently in its sleep."
- `0xAB` → "…could use a bath. Any volunteers?"

Both harmless.

### 8. Unconditional wake (`0x95`)
One verb code calls `0x217E8` directly with no sleep check at all — this action wakes the dog no matter what.

### 9. Fallback
`SCAN_TABLE` against global table **GCB** (79 entries): if matched, "A second look at the sleeping brute" + paddr text (global **G63**); otherwise falls through to the default library response.

## Waking the Dog (`0x217E8` → `0x21894`)

```
PRINT "[dog] lifts a heavy eyelid"
... (flavor via 0x217DC / 0x22040)
PRINT "It peers at you for a moment, yawns and drifts back to sleep. ...
       A set of long, white fangs snaps together, an inch shy of your
       left leg. Looks as if sleepytime is over."
CALL_1S 0x21894
```

`0x21894` escalates into the base's guard/searchlight response:

| Routine | Effect |
|---------|--------|
| `0x3B438` | "…a commotion worthy of an American Kennel Club convention." |
| `0x3B464` | "Hold it!" — you raise your hands |
| `0x3B49C` | A guard's silhouette in the searchlight glare: "You… you some kinda spy or somethin'?" |
| `0x3B6E0` | Jeeps converge — capture/chase sequence |

These same routines are also invoked from the **room's own per-turn handler** (`0x26DA4`, object #174 prop #50) and the **searchlight's own handler** (`0x3B290`, object #570 prop #50) — confirming the dog, the searchlight, and the guard patrol are one integrated stealth encounter, not independent events.

## Breaking the Searchlight (Object #570, routine `0x3B290`)

The searchlight has its own independent interaction set, separate from the dog's:

| Verb code(s) | Behavior |
|---|---|
| `0x3E` | "[Searchlight]'s powerful beam slices over your head, towards a point on the northeast [horizon]." (ambient, examine-adjacent) |
| `0x3F`, `0x42` | "The glare makes your eyes hurt." (look at/into it) |
| `0x92` (THROW ... AT), `0xBC` (THROW ... OVER) | see below |
| other | `SCAN_TABLE` against **GCB**; if matched → "[it]'s out of your reach."; otherwise default library response |

### Where you have to be

Object #570's `Parent` is #174 (Outside Blockhouse), and routine `0x3B290` never tests `GAE` (current room) anywhere in it. There's no separate "hidden vantage point" or alternate room this works from — by ordinary object scoping, the searchlight simply isn't referenceable at all unless you're standing in room #174 itself. Same room the dog and blockhouse are in; no special positioning beyond that.

### `AT` vs `OVER` — this is the part I missed the first time

Both throw-type verbs (`0x92`/`0xBC`) reach the same entry gate (global **G5F** must be nonzero, same flag that gates the dog's long description, or you just get "out of your reach"), and both print the same "You pitch [item] {over/at} " flavor line — **but only `0x92` (AT) ever reaches the weight check that can actually break the light**:

```
JE G8B 0x92 0xBC [FALSE] → out of reach     ; must be a throw at all
...
JE G6D <protected-object list> [TRUE] → "…falls short and…" (see below — always a miss)
JE G8B 0xBC [FALSE] 0x3B343                 ; if verb is OVER (0xBC):
  → "…It disappears behind the blockhouse." — clean miss, weight never even checked
                                              ; only verb AT (0x92) falls through to:
GET_PROP G6D PROPERTY48 -> value
JG value 0x02 [FALSE] → "It skitters off the rim and slides harmlessly" (too light)
                       → "The powerful beam of [searchlight] flickers and dies" (breaks it)
```

So `THROW <object> OVER SEARCHLIGHT` can **never** break it, no matter how heavy the object — it just sails behind the blockhouse. You specifically need `THROW <object> AT SEARCHLIGHT`, and that object needs `PROPERTY48 > 2`.

### Objects that always miss, regardless of weight

Before the weight check even runs, a hardcoded list of object numbers is checked (`JE G6D 0x39 0x8E 0x14 [TRUE]`, `JE G6D 0x08 0x0192 0x01B4 [TRUE]`, `JE G6D 0x0178 0x1B [FALSE] → else falls into the same miss text`) — objects #8 (slip of cardboard), #20 (burial shroud), #57, #142, #376 (the roadrunner), #27 (the lemming), #402 (bag of crumbs), #436 all "fall short" unconditionally. This reads as a shared "protected/plot-critical or living object" safety list reused elsewhere in the game, not something scene-specific — but it does mean you can't solve this by throwing your companion animals (or the crumbs meant to feed them) at the light even if they're otherwise heavy enough.

### Candidate objects (checked against PROPERTY48)

Only weight (`PROPERTY48 > 2`) is tested — no other property matters. Checked a few obvious candidates in the disassembly:

| Object | PROPERTY48 | Heavy enough? | Actually reachable at the Blockhouse? |
|---|---|---|---|
| Walkie-talkie (#60) | `5` | Yes | **Yes** — starts in "Underground" (#87), same zone (Parent #88) as the Blockhouse; also the object the "'Damn!' curses..." line specifically calls out |
| Lantern (#357) | `4` | Yes | **Likely** — sits in a different "Underground" chamber (#131), also Parent #88, same connected zone as #87 and Cliff Edge (#43) |
| Axe (#83, "silver axe") | `7` | Yes | **No** — Parent #408, tied to a different chapter's puzzle entirely |
| Umbrella (#549, "parrot's umbrella") | `7` | Yes | **No** — belongs to the old woman NPC (#567) in an unrelated location/reality |
| Steak knife (#393) | `2` | **No** (exactly at the threshold, fails) | n/a |

### What happens to the thrown object

This is asymmetric, and it matters: whether you keep the object depends on whether you succeeded.

```
THROW X OVER searchlight (miss, verb 0xBC)          → CALL 0x110CC → REMOVE_OBJ(X)   ; gone for good
THROW X AT searchlight, too light (≤2)               → CALL 0x110CC → REMOVE_OBJ(X)   ; gone for good
THROW X AT searchlight, heavy enough (>2) — breaks it → no REMOVE_OBJ / no relocation call at all
```

`0x110CC` is the routine that actually deletes the object (`REMOVE_OBJ`, defaulting its argument to `G6D` when called with none). Both failure paths (the clean "OVER" miss, and the "too light" bounce) call it — the object is genuinely destroyed/lost, consistent with the flavor text ("disappears behind the blockhouse," "slides off the rim"). The **success** path — breaking the light with `AT` and a heavy-enough object — never calls it and never repositions the object either. Since nothing changes its parent, it simply stays wherever it was (i.e. still in your inventory). **Fail, and you permanently lose the item. Succeed, and you keep it.**

### The dog decides what happens next

Assuming `AT` + a heavy-enough object gets past both checks, what happens after the light dies depends on whether the dog is still there:

```
→ "The powerful beam of [searchlight] flickers and dies"
→ CALL 0x393C4                              ; (a shared "did anyone notice" check)
→ sometimes: "'Damn!' curses [a voice on] the walkie-talkie."
→ JIN OBJECT391 OBJECT174 [FALSE] 0x3B3F3   ; is the dog still here?
```

- **Dog still present** (before the scripted G99==27 recall) → "As your eyes adjust to the gloom, you hear a deep, menacing growl. You turn and find yourself one inch away from the longest set of choppers you've ever seen." → `CALL 0x21894`, the *same* capture sequence as waking it directly. Breaking the light while the still-sleeping dog is right next to you in the resulting darkness is worse, not better.
- **Dog already gone** (after G99 > 27, post-recall) → falls to `0x1D4B8` instead — a different branch (the same "hinge squeaks" routine used in the recall event), with no dog-mauling risk.

So disabling the searchlight is only safe *after* the dog has left — before that point it's a trap, not a solution.

## The Roadrunner Side-Encounter (Object #376)

Object #376 is a wandering "roadrunner" companion animal (Parent = 0 until it's lured out — vocab: bird, roadrunner), fed/lured with the bag of crumbs (#402). Its own per-turn handler (prop #50, `0x20BFC`) drives a large shared movement/behavior routine at `0x1C5BC` — this routine runs every turn the roadrunner is active (gated on global **G5D** being zero) and handles it wandering between rooms.

When the roadrunner's current room contains the sleeping dog (`JIN OBJECT391 <roadrunner's room>`), a special vignette triggers instead of ordinary wandering text — this is **not player-commanded**, it fires automatically as part of the roadrunner's AI:

1. `0x1CA8C` — the roadrunner "notices the German shepherd," perches on its head, and starts pecking at sand fleas behind its ears. Sets ATTRIBUTE11 on the dog (marks "roadrunner currently harassing it") and ATTRIBUTE3 (first-encounter flag).
2. `0x1CBB0` — next turn, the dog "lifts an eyelid and peeks up at the bird." Its expression "hardens from sleepy distraction to annoyance... and then to outrage!" It snaps at the roadrunner, which "digs in and holds on for dear life" — then **"the dog sees you"** and calls `0x21894`, the *same* searchlight/guard capture sequence as the player directly waking it.
3. Alternatively (`0x1C633`, checked first each turn), the roadrunner can lose interest on its own: "it abandons the dog, trots back to your side" (`0x1CCA8`) — a safe resolution, but one the player doesn't control turn-to-turn.

**This is a coin-flip escalation, not a subduing tool.** Letting the roadrunner wander near the dog can just as easily *cause* the capture sequence as end harmlessly. It has no code path that changes the SW exit's `G99` gate or removes the dog early — the dog's departure is handled entirely by the scripted event below, independent of the roadrunner.

## Scripted Dog Recall ("It's time, Wolf!")

Routine `0x1D390`, run once per relevant clock tick:

```
JE G99 0x1D [FALSE] ...          ; separate flare branch (tick 29)
...
JE G99 0x18 0x1B 0x1C [FALSE] RFALSE   ; ticks 24, 27, 28 — flare/signal sequence
JE G99 0x1B [FALSE] ...                ; specifically tick 27:
  JE GAE 0x01B5 0xAE [FALSE] ...       ;   if player is at room 437 or Blockhouse (174)...
    CALL 0x1D55C / 0x1DAB4              ;   ...print the flare going up
    JE GAE 0xAE [FALSE] ...
      CALL 0x1D4B8   ; "A hinge squeaks... 'It's time, Wolf!' calls a voice" (at Blockhouse)
      -- else --
      "The GIs hurry out of their jeeps and take cover..." (at room 437)
PUT_PROP OBJECT174 PROPERTY33 0x00
PUT_PROP OBJECT174 PROPERTY28 0x00
REMOVE_OBJ OBJECT391                    ; dog leaves the world, unconditionally
```

This fires at a single fixed point in the story clock (**G99 == 0x1B / 27**) regardless of player action — if the player happens to be at the Blockhouse or room 437 at that moment they get an eyewitness description of the dog being called off ("Wolf," presumably the dog's actual name, matches its vocab synonym); otherwise it just happens offscreen. Either way, the dog is gone for the rest of the game from this point on. This is presumably tied to the historical Trinity test's real timeline (dawn shift-change / imminent detonation), not to anything the player did.

## Summary

Object #391 is a chained, sleeping guard dog outside the Blockhouse (#174). The blockhouse (#73) itself is passive scenery — its handler never references the dog. The searchlight (#570), however, is a genuine second half of the same encounter: most direct dog interactions (examining, feeding, throwing things, insults, smelling, attacking) are safe or comedic no-ops, but a subset of touch/pet-type verbs risk waking it (ATTRIBUTE23 check), one verb code (`0x95`) wakes it unconditionally, and a wandering roadrunner companion (#376) can independently trigger the same escalation just by lingering near it. Waking the dog by any of these paths triggers the searchlight sweep and a shared guard capture/chase sequence. The relationship also runs the other way: trying to disable the searchlight by throwing something heavy at it only ends well if the dog has *already* left — otherwise breaking the light plunges you into the dark right next to it, triggering the same capture sequence.

**None of this affects mobility around the building**, though. The NW exit around the blockhouse is always open; the SW exit opens once the world clock (G99) passes tick 27 — the same tick at which the dog is unconditionally scripted to be called away and removed from the game. The dog's departure and the SW route opening are parallel effects of the same clock, not cause-and-effect; the dog↔searchlight relationship is real, but the dog↔movement and dog↔blockhouse relationships are not.
