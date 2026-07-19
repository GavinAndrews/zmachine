#!/usr/bin/env python3
"""Reconstruct every point-scoring event on the true (restore-pruned) path to
a save, and print/write an ordered breakdown of how the score was earned.

Reuses the transcript-ordering and restore-branch-pruning engine from the
save-graph skill (rebuild_save_artifacts.py) instead of re-implementing it:
that script already knows how to auto-discover transcript*.txt files, chain
them by restore-dependency, and -- critically -- correctly discard any
command run down an abandoned branch that a later `restore` backs out of.
This script adds a parallel "trace" (file + line number per surviving
command) alongside that replay, then scans the *actual transcript text*
between consecutive on-path commands for

    [Your score just went up by N point(s). The total is now M out of 100.]

lines, attributing each one to the command that produced it. Because the
scan window for a command is bounded by the *next on-path command* (not by
end-of-file), score events inside an abandoned branch -- which sits between
two commands that both survive on the true path, since the branch was
restored away -- are never visited at all.

Usage (run from anywhere):
    python score_path.py [--game trinity] [--save SAVENAME] [--out PATH]

  --game NAME   gameplay/<name>/ directory to read (default: trinity)
  --save NAME   analyze the path to this specific .sav file instead of the
                auto-picked one (default: the reachable save with the
                longest command chain -- same "goal" heuristic save-graph
                uses, which in practice is also the highest-scoring one)
  --out PATH    where to write the markdown table (default:
                gameplay/<game>/score_path.md)

Limitation: this only finds score events for games that emit the V4+-style
"your score just went up" announcement (Trinity does; Border Zone-era games
generally do). Status-line-only games (Zork I/II/III, V1-3) never print this
message per pickup, so this script will correctly report zero events for
them -- reconstructing their score history would require diffing periodic
"[Your score is N...]" checkpoints instead, which is not implemented here.
"""
import argparse
import bisect
import importlib.util
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[2]

# --- load the save-graph skill's module by file path (its directory name has
# a hyphen, so it can't be a normal package import) ------------------------
_sg_path = REPO_ROOT / ".claude" / "skills" / "save-graph" / "rebuild_save_artifacts.py"
_spec = importlib.util.spec_from_file_location("rebuild_save_artifacts", _sg_path)
_sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sg)

SCORE_UP_RE = re.compile(
    r'Your score just went up by (\d+) points?\. The total is now (\d+) out of \d+')


# ---------------------------------------------------------------------------
# Replay that also records a (file, lineno) trace per surviving command, so a
# later restore prunes the trace exactly the same way it prunes the command
# list itself. Mirrors rebuild_save_artifacts.replay() branch-for-branch;
# see that function for the meaning of each event kind.
# ---------------------------------------------------------------------------

def replay_with_trace(events):
    trace = []  # ('cmd', file, lineno, text) | ('restore', file, lineno, fname)
    cur_file = None
    snapshots = {}
    save_order = []
    unreachable_restores = []

    for ev in events:
        kind = ev[0]
        if kind == 'file_marker':
            cur_file = ev[1]
            continue
        if kind == 'reset':
            trace = _sg.UNKNOWN
            continue
        if kind == 'cmd':
            if trace is _sg.UNKNOWN:
                continue
            trace = trace + [('cmd', cur_file, ev[2], ev[1])]
            continue
        if kind == 'save_ok':
            fname, lineno, loc = ev[1], ev[2], ev[3]
            if fname not in snapshots:
                save_order.append(fname)
            snapshots[fname] = (trace if trace is _sg.UNKNOWN else list(trace), cur_file, lineno, loc)
            continue
        if kind == 'restore_ok':
            fname, lineno, loc = ev[1], ev[2], ev[3]
            if fname in snapshots:
                saved_trace, _, _, _ = snapshots[fname]
                trace = saved_trace if saved_trace is _sg.UNKNOWN else list(saved_trace)
                if saved_trace is _sg.UNKNOWN:
                    unreachable_restores.append((cur_file, lineno, fname, 'restored save was itself unreachable'))
                else:
                    trace = trace + [('restore', cur_file, lineno, fname)]
            else:
                unreachable_restores.append((cur_file, lineno, fname, 'no successful save under this name seen'))
                trace = _sg.UNKNOWN
            continue
        if kind == 'restore_fail':
            continue
        if kind == 'special_yes' and ev[1] == 'restart':
            trace = []
            continue

    return snapshots, save_order, unreachable_restores


def build_all_snapshots(game_dir):
    paths = sorted(game_dir.glob("transcript*.txt"), key=_sg.natural_key)
    if not paths:
        raise SystemExit(f"No transcript*.txt found in {game_dir}")
    groups, events_by_path, needs_reset = _sg.build_groups(paths)

    all_snapshots = {}
    for _title, order in groups:
        combined = _sg.concat_group(order, events_by_path, needs_reset)
        snaps, _save_order, _unreach = replay_with_trace(combined)
        all_snapshots.update(snaps)

    # Raw (unpruned) command line numbers per file -- used only to bound each
    # on-path command's output-scan window at "the next thing the player
    # typed in the raw transcript", regardless of whether that next command
    # itself ends up on-path. This matters when an abandoned branch sits
    # between two on-path commands (both survive; the branch doesn't): the
    # window must stop at the branch's first command, not skip past the
    # whole abandoned stretch to the next *surviving* command, or score
    # lines from the abandoned stretch get misattributed.
    raw_cmd_lines = {}
    for p, events in events_by_path.items():
        raw_cmd_lines[p.name] = sorted(ev[2] for ev in events if ev[0] == 'cmd')

    return all_snapshots, raw_cmd_lines


def find_save_key(snapshots, name):
    for k in snapshots:
        if _sg.sav_name(k) == _sg.sav_name(name):
            return k
    return None


# ---------------------------------------------------------------------------
# Location lookup (best-effort, same heuristics as the other skills)
# ---------------------------------------------------------------------------

def nearest_location(lines, lineno_1indexed, uses_tags):
    for i in range(lineno_1indexed - 1, -1, -1):
        line = lines[i].strip()
        if uses_tags:
            m = _sg.LOC_RE_STANDALONE.match(line) or _sg.LOC_RE_GLUED.match(line)
            if m:
                return m.group(1).strip()
        elif line and _sg.FOOTER_RE.match(line) and not line.startswith('>'):
            return line
    return None


# ---------------------------------------------------------------------------
# Score extraction over a trace
# ---------------------------------------------------------------------------

def extract_score_events(trace, game_dir, raw_cmd_lines):
    lines_cache = {}
    tags_cache = {}

    def get_lines(fname):
        if fname not in lines_cache:
            text = (game_dir / fname).read_text(encoding='utf-8', errors='replace')
            lines = text.splitlines()
            lines_cache[fname] = lines
            tags_cache[fname] = any(
                _sg.LOC_RE_STANDALONE.match(l.strip()) or _sg.LOC_RE_GLUED.match(l.strip())
                for l in lines)
        return lines_cache[fname]

    events = []
    for entry in trace:
        if entry[0] != 'cmd':
            continue
        _, fname, lineno, text = entry
        lines = get_lines(fname)

        # window end = the next command actually typed in this raw file
        # after `lineno`, whether or not it turns out to be on-path.
        pos = bisect.bisect_right(raw_cmd_lines[fname], lineno)
        end_idx = raw_cmd_lines[fname][pos] - 1 if pos < len(raw_cmd_lines[fname]) else len(lines)

        for j in range(lineno, min(end_idx, len(lines))):
            m = SCORE_UP_RE.search(lines[j])
            if m:
                delta, total = int(m.group(1)), int(m.group(2))
                loc = nearest_location(lines, j + 1, tags_cache[fname])
                events.append({
                    'file': fname, 'line': j + 1, 'delta': delta, 'total': total,
                    'command': text, 'location': loc,
                })
    return events


def verify_running_total(events):
    """Returns (final_total, list of mismatch notes). A mismatch means the
    trace likely still includes an off-path event -- the game's own printed
    totals are authoritative, so if prev + delta != this event's total,
    something upstream is wrong."""
    running = 0
    mismatches = []
    for idx, ev in enumerate(events, 1):
        if running + ev['delta'] != ev['total']:
            mismatches.append(
                f"event #{idx} ({ev['file']}:{ev['line']}): running total {running} "
                f"+ {ev['delta']} != reported total {ev['total']}")
        running = ev['total']
    return running, mismatches


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def render_markdown(target_display_name, target_loc, target_src, events, final_total, mismatches):
    lines = []
    lines.append(f"# Score path to `{target_display_name}`\n")
    lines.append(f"Ends at **{target_loc}** ({target_src}). "
                  f"{len(events)} scoring events, final score {final_total}.\n")
    if mismatches:
        lines.append("**Warning -- running-total mismatches found (path may include an "
                      "off-path branch):**\n")
        for m in mismatches:
            lines.append(f"- {m}")
        lines.append("")

    lines.append("| # | Transcript:Line | +Points | Total | Command | Location |")
    lines.append("|---|---|---|---|---|---|")
    for idx, ev in enumerate(events, 1):
        loc = ev['location'] or ''
        lines.append(f"| {idx} | {ev['file']}:{ev['line']} | {ev['delta']} | {ev['total']} | "
                      f"`{ev['command']}` | {loc} |")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default="trinity", help="game subdirectory under gameplay/ (default: trinity)")
    ap.add_argument("--save", default=None,
                     help="analyze the path to this .sav file (default: reachable save with the "
                          "longest command chain, i.e. furthest progress)")
    ap.add_argument("--out", default=None, help="output markdown path (default: gameplay/<game>/score_path.md)")
    args = ap.parse_args()

    game_dir = REPO_ROOT / "gameplay" / args.game
    snapshots, raw_cmd_lines = build_all_snapshots(game_dir)
    reachable = {k: v for k, v in snapshots.items() if v[0] is not _sg.UNKNOWN}
    if not reachable:
        raise SystemExit("No reachable saves found")

    if args.save:
        key = find_save_key(reachable, args.save)
        if key is None:
            raise SystemExit(f"{args.save!r} is not a reachable save. "
                              f"Reachable saves: {', '.join(sorted(_sg.sav_name(k) for k in reachable))}")
    else:
        key = max(reachable, key=lambda k: len(reachable[k][0]))

    trace, src_file, src_line, loc = reachable[key]
    events = extract_score_events(trace, game_dir, raw_cmd_lines)
    final_total, mismatches = verify_running_total(events)

    n_cmds = sum(1 for e in trace if e[0] == 'cmd')
    print(f"Target save: {_sg.sav_name(key)} -- {n_cmds} commands, ends at {loc} ({src_file}:{src_line})")
    print(f"{len(events)} scoring events found, final score {final_total}")
    if mismatches:
        print("WARNING: running-total mismatches:")
        for m in mismatches:
            print(f"  {m}")
    for idx, ev in enumerate(events, 1):
        print(f"  {idx:2d}. {ev['file']}:{ev['line']:<6} +{ev['delta']:<2} -> {ev['total']:<3} "
              f"{ev['command']!r} ({ev['location'] or '?'})")

    out_path = Path(args.out) if args.out else game_dir / "score_path.md"
    out_path.write_text(
        render_markdown(_sg.sav_name(key), loc, f"{src_file}:{src_line}", events, final_total, mismatches),
        encoding='utf-8')
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()
