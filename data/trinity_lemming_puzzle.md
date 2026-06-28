# Trinity — Lemming Puzzle Analysis

Derived from disassembly of TRINITY.DAT (TRINITY.txt).

## Object References

| Object | Description | Notes |
|--------|-------------|-------|
| #27    | lemming (single) | starts out of world (Parent = 0) |
| #13    | birdcage | container for catching the lemming |
| #96    | lemmings (group) | Kensington Gardens group; ATTRIBUTE23 = running |
| #271   | dead lemming | replacement object on lemming death |
| #277   | rattlesnake | kills the lemming on contact |
| #100   | closet door | ATTRIBUTE19 = open |
| #356   | white door | ATTRIBUTE19 = open; in same object cluster as #100, #277 |
| #526   | fissure | at Cliff Edge (#43); lemming's initial hiding place |

## Key Rooms

| Object | Name | Notes |
|--------|------|-------|
| #43    | Cliff Edge | desert; fissure (#526) is here |
| #327   | Cottage | the bomb shelter / ground zero building |
| #352   | Closet | desert room; SOUTH/OUT to #442 if closet door (#100) open |
| #417   | Herb Garden | WEST to Cottage if OBJECT533 open |
| #213   | Bluff | EAST to Cottage if OBJECT19 open |

## The Puzzle Chain

### 1. Lemming appears
The fissure-examine routine places lemming (#27) **into the fissure** at Cliff Edge (#43).  
(Lemming starts with `Parent = 0` — not in the game world until the fissure is examined.)

### 2. Catch the lemming
The player catches the lemming by putting it **into the birdcage (#13)**.  
Routine `0x31A20`: `INSERT_OBJ OBJECT27 G6D` (G6D = birdcage).

### 3. Release in the Herb Garden — the critical step
The player opens the birdcage while standing in the **Herb Garden (#417)**.

Routine `0x1A040` (lemming landing handler), branch at `0x1A0DE`:

```
JE GAE 0x01A1 [FALSE] 0x1A12C     ← are we in Herb Garden?
TEST_ATTR OBJECT356 ATTRIBUTE19 …  ← is the white door open?
```

**If white door (#356) is already open:** lemming scurries straight through it.

**If white door is closed** (the normal case):  
→ `CALL_2S 0x1A23C (0x0215)` — routine `0x1A23C` runs with OBJECT533 as argument:

```
; 0x1A23C — lemming nudges open a door
SET_ATTR L00 ATTRIBUTE19          ← opens OBJECT533 (Cottage west door)
PRINT "nudges open the [door]. Then it scurries…"
```

Then back in `0x1A040` at `0x1A10D`:
```
TEST_ATTR OBJECT19 ATTRIBUTE19 [TRUE] RTRUE   ← east door already open? done.
SET_ATTR OBJECT19 ATTRIBUTE19                 ← open Cottage east door!
PRINT "You hear a faint creak in the [cottage]."
```

**OBJECT19** is the Cottage's east door — the one gating `EAST TO Cottage IF OBJECT-19 IS OPEN` from the Bluff (#213).

So the lemming scurries through the **west** side of the Cottage and the **east** door swings open as a side-effect, giving the player access from the Bluff.

### 4. Endgame — survive the blast
The bomb countdown routine (`0x1C3B4`) decrements G09 each turn.

- **Player in Cottage (#327) when G09 = 0** → instant death ("cremates you instantly").
- **Player at Bluff (#213) or Herb Garden (#417)** → survives the concussion.

```
JE GAE 0x0147 [FALSE] 0x1C406   ← Cottage = death
…
JE GAE 0xD5 0x01A1 [FALSE] RFALSE  ← Bluff(213) or Herb Garden(417) = survival
```

The player's path to the winning position (Bluff) goes through the Cottage east door — the very door the lemming opened.

## Dangerous Outcomes for the Lemming

| Situation | Result |
|-----------|--------|
| Released in Closet (#352) with closet door (#100) **open** | Killed by rattlesnake (#277) — routine `0x19F8C` |
| Escapes while player is at Cliff Edge (#43), rooms 158 or 247 | Flings itself off; dead lemming (#271) appears at Base of Tower (#146) |
| In birdcage at the Cottage (#327) when bomb detonates | Dead lemming (#271) inserted into birdcage — routine `0x1C3B4` |
| Released in Closet with door **closed** | Plops safely to the floor; stays in Closet |

## Summary

The lemming's **required location** is the **Herb Garden (#417)** — it must be released there (birdcage opened while player is in that room). It then nudges open the Cottage west door (OBJECT533), which causes the Cottage east door (OBJECT19) to open, allowing the player to reach the Bluff (#213) for the winning endgame position.
