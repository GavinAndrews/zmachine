# Trinity — Tundra: Soviet Control Bunkers (Death Trap)

Derived from disassembly of TRINITY.DAT (TRINITY.txt). A separate location from the New Mexico Blockhouse (see `data/trinity_dog_puzzle.md`) — this is a different chapter/historical setting entirely.

## TL;DR

Object #56 ("Tundra") has a SOUTHWEST exit that is **not** a puzzle to solve — it's a scripted death. The game warns you once, then asks "go that way?" if you try again; answering yes gets you shot in the back by a Soviet sentry. Examining the distant buildings first gives you the same warning content directly and is the correct, safe way to satisfy your curiosity about this exit.

## Object References

| Object | Description | Notes |
|--------|-------------|-------|
| #56    | Tundra | room; exits N/NE/E lead onward normally, SE/S/W/NW are flat "rock walls block your path", SW is the death trap |
| #168   | group of buildings | distant "military [installations]"; visible from Tundra; examining it sets ATTRIBUTE23 |
| #330   | guards | armed guards patrolling the distant bunker complex |
| #348   | (military structure type, printed after OBJECT150/OBJECT168) | used in the "look like military ___" description |

The "hammer-and-sickle insignia" in the death text marks this as the Soviet nuclear test chapter — a parallel vignette to the American Trinity/White Sands New Mexico chapter, with an analogous but much harsher "restricted military area" mechanic.

## The SW Exit (`0x31C50`, prop #58 of object #56)

```
TEST_ATTR OBJECT168 ATTRIBUTE23 [TRUE] → already warned, go to confirmation (below)
  (not yet warned):
    SET_ATTR OBJECT168 ATTRIBUTE23
    CALL 0x111A0 → "Perhaps you should take a moment to examine the [group of buildings] first."
    RFALSE                                    ; movement blocked, no death yet, no prompt yet

  (already warned — either by a prior SW attempt, or by EXAMINE, see below):
    PRINT "...go that way?"
    <read yes/no via 0x14500>
    NO  → CLEAR_ATTR OBJECT168 ATTRIBUTE23; CALL 0x116C8; RFALSE   ; cancels safely, resets warning
    YES → PRINT: "...choked with scientific instruments, tended by men in heavy overcoats.
           One of the guards patrolling the area greets your unexpected arrival by shooting
           you in the back. As your blood seeps into the permafrost, you note with interest
           the hammer-and-sickle insignia on the uniform of your grim assailant."
          CALL 0x28C40   ; death handler
```

Two attempts are required to reach the fatal confirmation on movement alone: the first SW attempt only prints the "perhaps you should examine..." nudge and blocks; the second (or any attempt after ATTRIBUTE23 is already set) actually offers the yes/no choice, and "yes" kills you outright.

## Examining the Buildings Does Double Duty (`0x31BB0`, prop #50 of object #168)

```
JE G8B 0x3E [FALSE] → (some other verb entirely, see below)
  SET_ATTR G6D ATTRIBUTE23     ; G6D == OBJECT168 here — same flag the SW-exit routine checks!
  PRINT "The distant [buildings] look like military [installations]. Armed guards are
         patrolling the area."
  RTRUE
```

So `EXAMINE BUILDINGS` (verb `0x3E`) both (a) tells you plainly that the area is guarded, and (b) sets the same ATTRIBUTE23 flag that the SW-exit routine uses to decide "has the player already been warned." Practically: if you examine the buildings before ever trying to walk SW, your first SW attempt skips the vague nudge and goes straight to the "go that way?" prompt — the game has already given you the real information via EXAMINE instead. This is a deliberate, working "look before you leap" design, not a coincidence — it rewards the sensible action instead of just gating on repetition.

### A second path to the same danger — the guards themselves (`0x31BF4`, `0x31C2C`)

Object #330 ("guards") has its own handler:

```
SCAN_TABLE G8B G9F 0x10 [FALSE] → "Luckily, the guards don't notice. You're still too far away."
                                  ; harmless — not an attention-grabbing verb
[TRUE] (attention-grabbing verb, from the same G9F table the sleeping dog's wake-check uses)
  → CALL 0x31C2C
      JE G8B 0xCA 0x4C [FALSE] → (other handling)
      JE GAE 0x38 [FALSE] → (other handling)   ; GAE == 0x38 (56, Tundra)
      CALL 0x31C50   ; the SAME death-confirmation routine as the SW exit
```

So it's not only walking SW that can trigger this — certain "loud"/attention-drawing actions directed at the distant guards while standing in Tundra can also route into the same confirmation-then-death sequence. The safe response to the guards, at a distance, is anything that isn't in the G9F "attention" verb table (plain EXAMINE is fine, per the "you're still too far away" branch).

## Answer: is this somewhere you need to go?

**No.** This is a hard "don't" — a genuine, scripted death, not a required story beat and not mere atmospheric color either (color wouldn't kill you). The correct play is:

1. `EXAMINE` the buildings (and optionally the guards, using an innocuous verb) to get the actual warning text.
2. Do not confirm "yes" if the game asks "go that way?" — answer no, or better, just don't attempt SW again at all.

Compare with the New Mexico Blockhouse (#174): that SW exit is a legitimate, eventually-passable route gated by the world clock (G99), with no death risk at all. Tundra's SW is the opposite pattern — a warned, deliberate, fatal dead end. The two "SW exits blocked, with narrative-sounding excuses" look superficially similar in play, but the underlying mechanics (and correct player response) are opposite: wait it out at the Blockhouse; never attempt it at Tundra.
