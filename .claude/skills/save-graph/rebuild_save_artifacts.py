#!/usr/bin/env python3
"""Rebuild save_paths.md and saves.html for a game from its gameplay/<game>/
transcripts and .sav files.

Generalizes the old infocomm/reconstruct_save_paths.py + build_saves_graph.py
(which hardcoded an explicit transcript file list and a fixed "goal" save
name, and broke once transcripts moved out of infocomm/ into gameplay/<game>/).
This version auto-discovers every transcript*.txt in gameplay/<game>/ and
auto-orders them by how each file's opening ties to the others:
  - opens with `restore <name>` -> depends on whichever transcript(s)
    produced a successful save of <name>
  - opens with the interpreter's fresh-start banner (copyright text / RNG
    seed message) and no restore -> a genuine fresh game start
  - neither of the above -> the game process just kept running while
    transcript logging was toggled off/on (no restore, no restart), so the
    file is a raw continuation of whichever other transcript's *ending*
    location matches this file's *opening* location
Files are grouped into independent play-session trees by this combined
dependency graph and each group is replayed as one continuous stream (so an
unrelated fresh-start session's command list never leaks into another
session's state, but a raw mid-session split carries state across the file
boundary exactly like the original recording did).

Location is read from `[Obj#NNN: ...]` tags when present; transcripts
recorded with `#loc` off have no tags at all, so location instead falls back
to the bare room-name line that some turns echo immediately above the next
prompt (this fallback is enabled per-file, only when the file has zero tags
anywhere -- matching the fact that `#loc` is toggled once per session, not
per turn).

saves.html is regenerated from the CURRENT saves.html (not from map.html) --
only the data blocks (NODES_DATA/EDGES_DATA/PATHS), the "Route to" dropdown
options, and the unreachable-saves badge are replaced by regex. Every other
concept already in the file (physics-off-after-settle, drag-to-reposition
autosave, JPEG/PDF export, the goal-save highlight, the destination filter
that limits which nodes are shown) survives untouched because it's not
touched.

Usage (run from anywhere):
    python rebuild_save_artifacts.py [--game trinity] [--goal SAVENAME]
                                      [--paths-only] [--html-only]
"""
import argparse
import json
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
REPO_ROOT = SKILL_DIR.parents[2]

LOC_RE_STANDALONE = re.compile(r'^\[(?:Obj#\d+|\d+):\s*(.+)\]$')
LOC_RE_GLUED = re.compile(r'^\[(?:Obj#\d+|\d+):\s*([^\]]+)\](>.*)?$')
BRACKET_PROMPT_RE = re.compile(r'^\[.*?\]\s*>(.*)$')
# Bare room-name footer line, used only for transcripts with no [Obj#...] tags
# at all (i.e. #loc was off for that whole session): short, capitalized,
# no sentence punctuation -- unlike ordinary game-text lines.
FOOTER_RE = re.compile(r"^\s*[A-Z][A-Za-z0-9' ]{0,38}$")

UNKNOWN = object()  # sentinel for "state not reconstructable"


# ---------------------------------------------------------------------------
# Per-file parsing
# ---------------------------------------------------------------------------

FRESH_START_RE = re.compile(r'Copyright \(C\)1986 Infocom|RNG seeded')


def parse_transcript(path):
    """Return (events, first_loc, last_loc, has_fresh_start_banner).
    events is a list of:
      ('cmd', text, lineno)
      ('save_ok', filename, lineno, loc)
      ('restore_ok', filename, lineno, loc)
      ('restore_fail', filename, lineno)
      ('special_yes', 'restart'|'quit', lineno)
      ('special_no', 'restart'|'quit', lineno)
    """
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    uses_tags = any(LOC_RE_STANDALONE.match(l.strip()) or LOC_RE_GLUED.match(l.strip())
                     for l in lines)
    has_fresh_start = any(FRESH_START_RE.search(l) for l in lines[:20])

    events = []
    state = {
        'pending_prompt': None,       # 'save' | 'restore'
        'pending_save_file': None,
        'pending_restore_file': None,
        'pending_special': None,      # 'quit' | 'restart'
    }
    first_loc = [None]
    last_loc = [None]

    def set_loc(value):
        last_loc[0] = value
        if first_loc[0] is None:
            first_loc[0] = value

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
            set_loc(m.group(1).strip())
            continue

        m = LOC_RE_GLUED.match(stripped)
        if m:
            set_loc(m.group(1).strip())
            trailing = m.group(2)
            if trailing:
                process_input(trailing[1:], lineno)
            continue

        m = BRACKET_PROMPT_RE.match(stripped)
        if m and m.group(1).strip():
            # e.g. "[Type RESTART, RESTORE or QUIT.] >restore" -- a system
            # prompt and the player's command glued onto one line, seen only
            # in tag-less transcripts.
            process_input(m.group(1), lineno)
            continue

        if line.startswith('>'):
            if not uses_tags:
                cmd_text = line[1:].strip()
                if cmd_text and idx > 0:
                    prev = lines[idx - 1].rstrip('\n')
                    if prev.strip() and FOOTER_RE.match(prev) and not prev.lstrip().startswith('>'):
                        set_loc(prev.strip())
            process_input(line[1:], lineno)
        else:
            process_output(line, lineno)

    return events, first_loc[0], last_loc[0], has_fresh_start


# ---------------------------------------------------------------------------
# Auto-discovery: classify files, find producers, group, order
# ---------------------------------------------------------------------------

def classify_open(events):
    """Return ('restore', target, immediate) for the file's first restore of
    a save it did NOT itself produce earlier in its own stream -- a restore
    of a name the file already saved is just ordinary mid-session
    save-scumming (die, reload your own recent save) and carries no
    cross-file signal. immediate=True if that external restore is the very
    first meaningful event; False if some throwaway commands ran first under
    whatever-state-was-inherited before the file corrects itself. Otherwise
    ('open', None, None) -- the caller decides genesis vs. raw-continuation
    using the fresh-start banner and location, since that needs file-level
    info this function doesn't have."""
    seen_self_saves = set()
    had_cmd_or_failed_restore = False
    for ev in events:
        kind = ev[0]
        if kind == 'save_ok':
            seen_self_saves.add(ev[1])
        elif kind == 'restore_ok':
            target = ev[1]
            if target not in seen_self_saves:
                return ('restore', target, not had_cmd_or_failed_restore)
        elif kind in ('cmd', 'restore_fail'):
            had_cmd_or_failed_restore = True
    return ('open', None, None)


def collect_producers(events_by_path):
    producers = {}
    for p, events in events_by_path.items():
        for ev in events:
            if ev[0] == 'save_ok':
                producers.setdefault(ev[1], set()).add(p)
    return producers


def natural_key(path):
    nums = tuple(int(x) for x in re.findall(r'\d+', path.stem))
    return (nums, path.stem)


def topo_order(members, deps):
    member_set = set(members)
    local_deps = {f: (deps.get(f, set()) & member_set) for f in members}
    dependents = {f: set() for f in members}
    for f, ds in local_deps.items():
        for d in ds:
            dependents[d].add(f)
    indegree = {f: len(local_deps[f]) for f in members}
    ready = [f for f in members if indegree[f] == 0]
    order = []
    remaining = set(members)
    while ready:
        ready.sort(key=natural_key)
        f = ready.pop(0)
        order.append(f)
        remaining.discard(f)
        for dep in dependents[f]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                ready.append(dep)
    if remaining:  # dependency cycle -- shouldn't happen, but don't drop data
        order.extend(sorted(remaining, key=natural_key))
    return order


def build_groups(paths):
    """Return (groups, events_by_path, needs_reset). groups: list of
    (label, ordered_paths). needs_reset: set of paths whose leading commands
    (before their own first restore) ran under an undetermined state and
    must be discarded rather than tacked onto whatever the group's prior
    file left behind."""
    parsed = {p: parse_transcript(p) for p in paths}
    events_by_path = {p: parsed[p][0] for p in paths}
    file_info = {p: {'first_loc': parsed[p][1], 'last_loc': parsed[p][2], 'fresh_start': parsed[p][3]}
                 for p in paths}

    producers = collect_producers(events_by_path)
    loc_producers = {}
    for p in paths:
        ll = file_info[p]['last_loc']
        if ll:
            loc_producers.setdefault(ll, set()).add(p)

    classification = {}
    needs_reset = set()
    for p in paths:
        kind, target, immediate = classify_open(events_by_path[p])
        if kind == 'restore':
            classification[p] = ('restore', target)
            if not immediate:
                needs_reset.add(p)
        elif file_info[p]['fresh_start']:
            classification[p] = ('genesis', None)
        else:
            classification[p] = ('location', file_info[p]['first_loc'])

    deps = {}
    for p in paths:
        kind, target = classification[p]
        if kind == 'restore':
            deps[p] = producers.get(target, set()) - {p}
        elif kind == 'location':
            candidates = loc_producers.get(target, set()) - {p}
            preceding = {c for c in candidates if natural_key(c) < natural_key(p)}
            candidates = preceding or candidates
            deps[p] = {max(candidates, key=natural_key)} if candidates else set()
        else:
            deps[p] = set()

    parent = {p: p for p in paths}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for p in paths:
        for d in deps[p]:
            union(p, d)

    comp_members = {}
    for p in paths:
        comp_members.setdefault(find(p), []).append(p)

    groups = []
    for members in comp_members.values():
        order = topo_order(members, deps)
        genesis_members = [m for m in members if classification[m][0] == 'genesis']
        if genesis_members:
            label_root = sorted(genesis_members, key=natural_key)[0]
            label = f"Session starting at {label_root.name}"
        else:
            first = sorted(members, key=natural_key)[0]
            kind, target = classification[first]
            if kind == 'restore':
                label = (f"Unresolved branch in {first.name} "
                          f"(restores '{target}', never saved anywhere in these transcripts)")
            else:
                label = f"Unresolved branch in {first.name} (no matching predecessor location found)"
        groups.append((label, order))

    groups.sort(key=lambda g: natural_key(g[1][0]))
    return groups, events_by_path, needs_reset


# ---------------------------------------------------------------------------
# Replay: turn an ordered event stream into per-save command lists
# ---------------------------------------------------------------------------

def replay(events):
    state = []
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
            # this file's leading commands ran under an undetermined state
            # (no restore yet, and no reliable predecessor) -- discard
            # whatever the prior file in this stream left behind.
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
            continue
        if kind == 'special_yes' and ev[1] == 'restart':
            state = []
            continue
        # special_no, special_yes(quit) -> no-op

    return snapshots, save_order, unreachable_restores


def concat_group(paths, events_by_path, needs_reset):
    combined = []
    for p in paths:
        combined.append(('file_marker', p.name, 0))
        if p in needs_reset:
            combined.append(('reset', None, 0))
        combined.extend(events_by_path[p])
    return combined


def sav_name(fname):
    return fname if fname.endswith('.sav') else fname + '.sav'


# ---------------------------------------------------------------------------
# save_paths.md
# ---------------------------------------------------------------------------

def render_group_md(md, title, order, snaps, unreach):
    md.append(f"## {title}\n")
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
            md.append("**Unreachable** -- this save's history passes through an unresolved restore "
                       "with no available data.\n")
            continue
        md.append(f"{len(st)} commands, ending at **{loc}** ({src}:{ln}):\n")
        for i, c in enumerate(st, 1):
            md.append(f"{i}. {c}")
        md.append("")


def write_save_paths_md(game_dir, groups, events_by_path, out_path):
    md = []
    md.append("# Save-game command reconstructions\n")
    md.append("For every `.sav` file these transcripts have evidence for, the full sequence of "
               "player commands (no `save`/`restore`/`restart`/`quit` or debug `#` commands) needed "
               "to reach that save's exact state, starting from the true beginning of its session. "
               "Regenerated by `rebuild_save_artifacts.py`, which auto-discovers every "
               "`transcript*.txt` in this directory and auto-orders them by restore-dependency: a "
               "transcript that opens with `restore <name>` is chained after whichever transcript(s) "
               "produced `<name>`; independent play sessions (no shared save history) become separate "
               "groups below.\n")

    unrecoverable = compute_unrecoverable(game_dir, events_by_path)

    for title, order, snaps, unreach in groups:
        render_group_md(md, title, order, snaps, unreach)

    md.append("## Unreachable saves\n")
    md.append("`.sav` files on disk in this directory with no transcript evidence of ever being "
               "saved -- they may come from an untranscripted play session, or a transcript file "
               "that no longer exists:\n")
    for f in unrecoverable:
        md.append(f"- `{sav_name(f)}`")
    md.append("")

    out_path.write_text("\n".join(md), encoding='utf-8')
    print(f"Wrote {out_path}")
    return unrecoverable


def compute_unrecoverable(game_dir, events_by_path):
    """`.sav` files on disk with no transcript evidence of ever being saved."""
    on_disk = {p.name for p in game_dir.glob("*.sav")}
    all_saved = set()
    for events in events_by_path.values():
        for ev in events:
            if ev[0] == 'save_ok':
                all_saved.add(sav_name(ev[1]))
    return sorted(on_disk - all_saved)


# ---------------------------------------------------------------------------
# saves.html
# ---------------------------------------------------------------------------

def build_prefix_edges(items):
    edges = []
    for name, cmds in items:
        if name == 'START':
            continue
        best_parent = 'START'
        best_len = 0
        for other_name, other_cmds in items:
            if other_name == name:
                continue
            L = len(other_cmds)
            if L > best_len and L <= len(cmds) and cmds[:L] == other_cmds:
                best_len = L
                best_parent = other_name
        edges.append((best_parent, name, list(cmds[best_len:])))
    return edges


def node_id(name):
    return 'sv_' + re.sub(r'[^A-Za-z0-9]', '_', name)


def write_saves_html(items, meta, goal_name, unrecoverable, saves_html_path):
    if not saves_html_path.exists():
        print(f"No existing {saves_html_path} to use as a template -- skipping HTML generation. "
              f"(Concepts like the physics-settle scaffold and JPEG/PDF export live only in that "
              f"file; create it once by hand or point --html at a template before rerunning.)")
        return

    SAVE_COLOR = {"background": "#1e3a5f", "border": "#2563eb",
                  "highlight": {"background": "#1d4ed8", "border": "#60a5fa"}}
    START_COLOR = {"background": "#1c3a2a", "border": "#16a34a",
                   "highlight": {"background": "#14532d", "border": "#4ade80"}}
    GOAL_COLOR = {"background": "#7c2d12", "border": "#f59e0b",
                  "highlight": {"background": "#9a3412", "border": "#fbbf24"}}
    CMD_COLOR = {"background": "#27272a", "border": "#52525b",
                 "highlight": {"background": "#3f3f46", "border": "#a1a1aa"}}

    nodes = []
    for name, cmds in items:
        if name == 'START':
            nodes.append({"id": "start", "label": "START", "shape": "box", "color": START_COLOR})
            continue
        loc, src, ln = meta[name]
        label = f"{sav_name(name)}\n{loc}" if loc else sav_name(name)
        title = f"{sav_name(name)} -- {loc}\n{src}:{ln}\n{len(cmds)} total commands"
        node = {"id": node_id(name), "label": label, "title": title, "shape": "box", "color": SAVE_COLOR}
        if name == goal_name:
            node["color"] = GOAL_COLOR
        nodes.append(node)

    edges = build_prefix_edges(items)
    vis_edges = []
    for parent, child, cmds in edges:
        from_id = "start" if parent == "START" else node_id(parent)
        to_id = node_id(child)
        cmd_node_id = "cmd_" + to_id
        cmd_label = "\n".join(cmds) if cmds else "(no commands)"
        nodes.append({"id": cmd_node_id, "label": cmd_label, "shape": "box", "color": CMD_COLOR,
                      "font": {"align": "left", "face": "monospace", "size": 11},
                      "margin": 10, "title": f"{len(cmds)} commands"})
        vis_edges.append({"from": from_id, "to": cmd_node_id, "arrows": "to"})
        vis_edges.append({"from": cmd_node_id, "to": to_id, "arrows": "to"})

    parent_of = {child: parent for parent, child, _ in edges}

    def chain(name):
        rev = []
        cur = name
        while cur != 'START':
            rev.append(cur)
            cur = parent_of[cur]
        rev.reverse()
        return rev

    paths = {}
    dest_options = []
    for name, _ in items:
        if name == 'START' or name not in meta:
            continue
        path_ids = ["start"]
        for n in chain(name):
            path_ids.append("cmd_" + node_id(n))
            path_ids.append(node_id(n))
        dest_label = sav_name(name)
        paths[dest_label] = path_ids
        dest_options.append(dest_label)

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(vis_edges, ensure_ascii=False)
    paths_json = json.dumps(paths, ensure_ascii=False)

    template = saves_html_path.read_text(encoding='utf-8')

    template = re.sub(r"var NODES_DATA = \[.*?\];",
                       lambda m: "var NODES_DATA = " + nodes_json + ";",
                       template, count=1, flags=re.S)
    template = re.sub(r"var EDGES_DATA = \[.*?\];",
                       lambda m: "var EDGES_DATA = " + edges_json + ";",
                       template, count=1, flags=re.S)
    template = re.sub(r"var PATHS = \{.*?\};",
                       lambda m: "var PATHS = " + paths_json + ";",
                       template, count=1, flags=re.S)

    dest_option_html = "".join(f'<option value="{d}">{d}</option>' for d in sorted(dest_options))
    template = re.sub(
        r'(<option value="ALL">ALL</option>).*?(</select>)',
        lambda m: m.group(1) + dest_option_html + m.group(2),
        template, count=1, flags=re.S)

    unreachable_note = ("Not shown (no transcript evidence anywhere in these transcripts): " +
                         ", ".join(sav_name(f) for f in unrecoverable)) if unrecoverable else "None"
    template = re.sub(
        r'<span style="margin-left:auto; color:#9ca3af; font-size:11px;" title="[^"]*">\d+ saves unreachable \(hover\)</span>',
        lambda m: (f'<span style="margin-left:auto; color:#9ca3af; font-size:11px;" title="{unreachable_note}">'
                    f'{len(unrecoverable)} saves unreachable (hover)</span>'),
        template, count=1)

    saves_html_path.write_text(template, encoding='utf-8')
    print(f"Wrote {saves_html_path}")
    print(f"nodes={len(nodes)} edges={len(vis_edges)} goal={sav_name(goal_name) if goal_name else '(none)'}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default="trinity", help="game subdirectory under gameplay/ (default: trinity)")
    ap.add_argument("--goal", default=None, help="save name to highlight as the goal (default: longest reconstructed command chain)")
    ap.add_argument("--paths-only", action="store_true", help="only write save_paths.md")
    ap.add_argument("--html-only", action="store_true", help="only write saves.html")
    args = ap.parse_args()

    game_dir = REPO_ROOT / "gameplay" / args.game
    paths = sorted(game_dir.glob("transcript*.txt"), key=natural_key)
    if not paths:
        raise SystemExit(f"No transcript*.txt found in {game_dir}")

    groups, events_by_path, needs_reset = build_groups(paths)

    rendered_groups = []       # (title, order, snaps, unreach) for md
    items = [('START', tuple())]
    meta = {}

    for title, order in groups:
        combined = concat_group(order, events_by_path, needs_reset)
        snaps, save_order, unreach = replay(combined)
        rendered_groups.append((title, save_order, snaps, unreach))
        for fname in save_order:
            st, src, ln, loc = snaps[fname]
            if st is not UNKNOWN:
                items.append((fname, tuple(st)))
                meta[fname] = (loc, src, ln)

    goal_name = args.goal
    if goal_name and goal_name not in meta:
        print(f"Warning: --goal {goal_name!r} is not a reachable save; falling back to auto-selection")
        goal_name = None
    if not goal_name and items[1:]:
        # pick by longest reconstructed command chain (furthest progress)
        goal_name = max(items[1:], key=lambda it: len(it[1]))[0]

    if not args.html_only:
        unrecoverable = write_save_paths_md(game_dir, rendered_groups, events_by_path,
                                             game_dir / "save_paths.md")
    else:
        unrecoverable = compute_unrecoverable(game_dir, events_by_path)

    if not args.paths_only:
        write_saves_html(items, meta, goal_name, unrecoverable, game_dir / "saves.html")

    if goal_name:
        st = meta[goal_name]
        cmds = next(cmds for n, cmds in items if n == goal_name)
        print(f"Goal save: {sav_name(goal_name)} -- {len(cmds)} commands, ends at {st[0]} ({st[1]}:{st[2]})")
        print("tail:", list(cmds[-3:]))


if __name__ == '__main__':
    main()
