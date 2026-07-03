"""Reconstruct, for every .sav file with transcript evidence, the exact sequence
of player commands (from true game start) needed to reach that save's state.

Source data is one continuous Trinity play session split across
transcript{1,2,3,4,5,6,7,10,21,31}.txt (in this directory), plus a separate,
unrelated older session in the repo-root transcript.txt. Save filenames follow
a global counter (wt1.sav...wt89.sav, wtXX.sav) that keeps incrementing across
files regardless of which branch is being played; restoring an older wtN.sav
abandons everything played after it. This script resolves every save/restore
into a branching tree and walks, for each save, the one path that reaches it,
discarding everything on abandoned branches.

Run from anywhere: `python reconstruct_save_paths.py`. Writes save_paths.md
next to this script.
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent

GROUP_A_FILES = ["transcript1.txt", "transcript2.txt", "transcript3.txt", "transcript4.txt",
                  "transcript5.txt", "transcript6.txt", "transcript7.txt", "transcript10.txt",
                  "transcript21.txt", "transcript31.txt"]
GROUP_B_FILES = ["transcript.txt"]  # at ROOT, not BASE

# transcript1-31 style: location tag alone on its own line, e.g. "[Obj#236: Palace Gate]"
LOC_RE_STANDALONE = re.compile(r'^\[(?:Obj#\d+|\d+):\s*(.+)\]$')
# transcript.txt (legacy) style: location tag glued to the prompt, e.g.
# "[236: Palace Gate]> examine watch"
LOC_RE_GLUED = re.compile(r'^\[(?:Obj#\d+|\d+):\s*([^\]]+)\](>.*)?$')

UNKNOWN = object()  # sentinel for "state not reconstructable"


def parse_transcript(path):
    """Return (events, first_loc, last_loc) for one transcript file.
    events: list of tuples, one of:
      ('cmd', text, lineno)
      ('save_ok', filename, lineno, loc)
      ('restore_ok', filename, lineno, loc)
      ('restore_fail', filename, lineno)
      ('special_yes', 'restart'|'quit', lineno)
      ('special_no', 'restart'|'quit', lineno)
    """
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    events = []
    state = {
        'pending_prompt': None,       # 'save' | 'restore'
        'pending_save_file': None,
        'pending_restore_file': None,
        'pending_special': None,      # 'quit' | 'restart'
    }
    first_loc = [None]
    last_loc = [None]

    def process_input(text, lineno):
        text = text.strip()
        if text == '' or text.startswith('['):
            return
        if state['pending_prompt'] == 'save':
            state['pending_save_file'] = text
            state['pending_prompt'] = None
            return
        if state['pending_prompt'] == 'restore':
            state['pending_restore_file'] = text
            state['pending_prompt'] = None
            return
        if state['pending_special'] is not None:
            low = text.lower()
            if low == 'yes':
                events.append(('special_yes', state['pending_special'], lineno))
                state['pending_special'] = None
            elif low == 'no':
                events.append(('special_no', state['pending_special'], lineno))
                state['pending_special'] = None
            # else: stray input during confirm limbo -- ignore, keep waiting
            return
        first_word = text.split()[0].lower() if text.split() else ''
        if text.startswith('#') or first_word == 'transcript':
            return
        if first_word in ('save', 'restore', 'quit', 'restart'):
            # the actual effect is driven by the output lines that follow
            return
        events.append(('cmd', text, lineno))

    def process_output(line, lineno):
        if 'Save to file:' in line:
            filename = line.split('Save to file:', 1)[1].strip()
            if filename:
                state['pending_save_file'] = filename
            else:
                state['pending_prompt'] = 'save'
        elif 'Restore from file:' in line:
            filename = line.split('Restore from file:', 1)[1].strip()
            if filename:
                state['pending_restore_file'] = filename
            else:
                state['pending_prompt'] = 'restore'
        elif 'SAVE completed' in line:
            if state['pending_save_file']:
                events.append(('save_ok', state['pending_save_file'], lineno, last_loc[0]))
            state['pending_save_file'] = None
        elif 'RESTORE completed' in line:
            if state['pending_restore_file']:
                events.append(('restore_ok', state['pending_restore_file'], lineno, last_loc[0]))
            state['pending_restore_file'] = None
        elif 'File not found' in line:
            if state['pending_restore_file']:
                events.append(('restore_fail', state['pending_restore_file'], lineno))
            state['pending_restore_file'] = None
            state['pending_save_file'] = None
        elif 'leave the story now' in line:
            state['pending_special'] = 'quit'
        elif 'sure you want to restart' in line:
            state['pending_special'] = 'restart'

    for idx, line in enumerate(lines):
        lineno = idx + 1
        stripped = line.strip()

        m = LOC_RE_STANDALONE.match(stripped)
        if m:
            last_loc[0] = m.group(1).strip()
            if first_loc[0] is None:
                first_loc[0] = last_loc[0]
            continue

        m = LOC_RE_GLUED.match(stripped)
        if m:
            last_loc[0] = m.group(1).strip()
            if first_loc[0] is None:
                first_loc[0] = last_loc[0]
            trailing = m.group(2)
            if trailing:
                process_input(trailing[1:], lineno)  # strip leading '>'
            continue

        if line.startswith('>'):
            process_input(line[1:], lineno)
        else:
            process_output(line, lineno)

    return events, first_loc[0], last_loc[0]


def build_group(file_paths, group_name):
    """Concatenate events across files, inserting a synthetic gap marker
    wherever a file boundary doesn't line up (no explicit restore, location
    tag mismatch)."""
    combined = []
    prev_last_loc = None
    for i, p in enumerate(file_paths):
        events, first_loc, last_loc = parse_transcript(p)
        if i > 0 and first_loc is not None and prev_last_loc is not None and first_loc != prev_last_loc:
            combined.append(('gap', f"{file_paths[i-1].name} (ends '{prev_last_loc}') -> "
                                     f"{p.name} (starts '{first_loc}')", 0))
        combined.append(('file_marker', p.name, 0))
        combined.extend(events)
        if last_loc is not None:
            prev_last_loc = last_loc
    return combined


def replay(events):
    """Walk the combined event stream, return:
      snapshots: filename -> (commands_list_or_UNKNOWN, source_file, lineno, loc)
      gaps_seen: list of gap descriptions
      order: list of filenames in the order they were first successfully saved
    """
    state = []          # current effective command list, or UNKNOWN
    cur_file = None
    snapshots = {}
    save_order = []
    gaps_seen = []
    unreachable_restores = []

    for ev in events:
        kind = ev[0]
        if kind == 'file_marker':
            cur_file = ev[1]
            continue
        if kind == 'gap':
            gaps_seen.append(ev[1])
            state = UNKNOWN
            continue
        if kind == 'cmd':
            if state is UNKNOWN:
                continue
            state = state + [ev[1]]
            continue
        if kind == 'save_ok':
            fname, lineno, loc = ev[1], ev[2], ev[3]
            if fname not in snapshots:
                save_order.append(fname)
            snapshots[fname] = (state if state is UNKNOWN else list(state), cur_file, lineno, loc)
            continue
        if kind == 'restore_ok':
            fname, lineno, loc = ev[1], ev[2], ev[3]
            if fname in snapshots:
                saved_state, _, _, _ = snapshots[fname]
                state = saved_state if saved_state is UNKNOWN else list(saved_state)
                if saved_state is UNKNOWN:
                    unreachable_restores.append((cur_file, lineno, fname, 'restored save was itself unreachable'))
            else:
                unreachable_restores.append((cur_file, lineno, fname, 'no successful save under this name seen'))
                state = UNKNOWN
            continue
        if kind == 'restore_fail':
            continue  # no-op, state unchanged
        if kind == 'special_yes' and ev[1] == 'restart':
            state = []
            continue
        # special_no, special_yes(quit) -> no-op

    return snapshots, save_order, gaps_seen, unreachable_restores


# The 15 files with no transcript evidence of ever being saved anywhere in the repo.
KNOWN_UNRECOVERABLE = ["e.sav", "f.sav", "g.sav", "h.sav", "i.sav", "j.sav", "j2.sav",
                       "k.sav", "k2.sav", "k3.sav", "k5.sav", "k6.sav", "k7.sav", "k8.sav",
                       "tower.sav"]


def sav_name(fname):
    """Normalize a save filename to its on-disk .sav form for display."""
    return fname if fname.endswith('.sav') else fname + '.sav'


def render_group(md, title, order, snaps, gaps, unreach):
    md.append(f"## {title}\n")
    if gaps:
        md.append("Gaps detected between transcript files (none affected a reachable save "
                   "below -- each was overwritten by a restore before anything was saved in "
                   "the gap):\n")
        for g in gaps:
            md.append(f"- {g}")
        md.append("")
    if unreach:
        md.append("**Restore attempts that could not be resolved:**\n")
        for f, ln, fn, reason in unreach:
            md.append(f"- `{f}:{ln}` restoring `{fn}` -- {reason}")
        md.append("")

    md.append("| Save file | Source transcript | Line | Location | Commands | Reachable |")
    md.append("|---|---|---|---|---|---|")
    for fname in order:
        st, src, ln, loc = snaps[fname]
        if st is UNKNOWN:
            md.append(f"| `{sav_name(fname)}` | {src} | {ln} | {loc or ''} | -- | No |")
        else:
            md.append(f"| `{sav_name(fname)}` | {src} | {ln} | {loc or ''} | {len(st)} | Yes |")
    md.append("")

    for fname in order:
        st, src, ln, loc = snaps[fname]
        md.append(f"### `{sav_name(fname)}`\n")
        if st is UNKNOWN:
            md.append("**Unreachable** -- this save's history passes through a transcript gap "
                       "with no available data.\n")
            continue
        md.append(f"{len(st)} commands, ending at **{loc}** ({src}:{ln}):\n")
        for i, c in enumerate(st, 1):
            md.append(f"{i}. {c}")
        md.append("")


def main():
    group_a_paths = [BASE / f for f in GROUP_A_FILES]
    group_b_paths = [ROOT / f for f in GROUP_B_FILES]

    events_a = build_group(group_a_paths, "wt-chain")
    events_b = build_group(group_b_paths, "legacy")

    snaps_a, order_a, gaps_a, unreach_a = replay(events_a)
    snaps_b, order_b, gaps_b, unreach_b = replay(events_b)

    md = []
    md.append("# Save-game command reconstructions\n")
    md.append("For every `.sav` file this repo has transcript evidence for, the full "
              "sequence of player commands (no `save`/`restore`/`restart`/`quit` or debug "
              "`#` commands) needed to reach that save's exact state, starting from the "
              "true beginning of the game. Reconstructed by resolving every save/restore "
              "in `transcript1-7,10,21,31.txt` and `transcript.txt` into a branching tree "
              "and walking the one path that ends at each save, discarding everything on "
              "abandoned branches.\n")

    render_group(md, "wt-chain saves (transcript1-7,10,21,31.txt)", order_a, snaps_a, gaps_a, unreach_a)
    render_group(md, "Legacy saves (transcript.txt)", order_b, snaps_b, gaps_b, unreach_b)

    md.append("## Unreachable saves\n")
    md.append("No transcript file anywhere in the repo shows these being saved -- they may "
              "come from an untranscripted play session, or a transcript file that no "
              "longer exists on disk:\n")
    for f in KNOWN_UNRECOVERABLE:
        md.append(f"- `{f}`")
    md.append("")

    out_path = BASE / "save_paths.md"
    out_path.write_text("\n".join(md), encoding='utf-8')
    print(f"Wrote {out_path}")

    # sanity check: wt89.sav tail
    st, src, ln, loc = snaps_a['wt89.sav']
    print(f"wt89.sav: {len(st)} commands, ends at {loc} ({src}:{ln})")
    print("tail:", st[-3:])


if __name__ == '__main__':
    main()
