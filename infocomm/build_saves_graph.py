"""Build saves.html: an interactive vis-network graph of every reachable .sav
file, derived from reconstruct_save_paths.py's branch resolution.

Nodes are START, one box per reachable save, and one box per command sequence
sitting on the edge between a save and its parent (found by matching each
save's longest common command-list prefix against every other save -- this
naturally folds overwritten saves and abandoned branches into whichever edge
actually has them as ancestry, no special-casing needed). Clones the toolbar/
physics/localStorage-persistence scaffold from map.html and adds a "Route to"
destination filter driven by a precomputed start->save path for every save.

Run from anywhere: `python build_saves_graph.py`. Writes saves.html next to
this script, using map.html (same directory) as its template.
"""
import json
import re
from pathlib import Path

from reconstruct_save_paths import (BASE, ROOT, GROUP_A_FILES, GROUP_B_FILES, UNKNOWN,
                                     build_group, replay, sav_name, KNOWN_UNRECOVERABLE)

MAP_HTML = BASE / "map.html"
OUT_HTML = BASE / "saves.html"


def build_prefix_edges(items):
    """items: list of (name, commands_tuple). Returns list of (parent, child, incremental)
    by finding, for each item, the other item whose command list is its longest exact
    prefix (with the implicit 'START' -> () always available)."""
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


def main():
    group_a_paths = [BASE / f for f in GROUP_A_FILES]
    group_b_paths = [ROOT / f for f in GROUP_B_FILES]

    events_a = build_group(group_a_paths, "wt-chain")
    events_b = build_group(group_b_paths, "legacy")

    snaps_a, order_a, _, _ = replay(events_a)
    snaps_b, order_b, _, _ = replay(events_b)

    items = [('START', tuple())]
    meta = {}  # name -> (loc, src, ln)
    for fname in order_a:
        st, src, ln, loc = snaps_a[fname]
        if st is UNKNOWN:
            continue
        items.append((fname, tuple(st)))
        meta[fname] = (loc, src, ln)
    for fname in order_b:
        st, src, ln, loc = snaps_b[fname]
        if st is UNKNOWN:
            continue
        items.append((fname, tuple(st)))
        meta[fname] = (loc, src, ln)

    edges = build_prefix_edges(items)

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
            nodes.append({"id": "start", "label": "START", "shape": "box",
                          "color": START_COLOR})
            continue
        loc, src, ln = meta[name]
        label = f"{sav_name(name)}\n{loc}" if loc else sav_name(name)
        title = f"{sav_name(name)} -- {loc}\n{src}:{ln}\n{len(cmds)} total commands"
        node = {"id": node_id(name), "label": label, "title": title, "shape": "box",
                "color": SAVE_COLOR}
        if name in ('wt89.sav', 'wt89'):
            node["color"] = GOAL_COLOR
        nodes.append(node)

    vis_edges = []
    for parent, child, cmds in edges:
        from_id = "start" if parent == "START" else node_id(parent)
        to_id = node_id(child)
        cmd_node_id = "cmd_" + to_id
        cmd_label = "\n".join(cmds) if cmds else "(no commands)"
        nodes.append({"id": cmd_node_id, "label": cmd_label, "shape": "box",
                      "color": CMD_COLOR,
                      "font": {"align": "left", "face": "monospace", "size": 11},
                      "margin": 10, "title": f"{len(cmds)} commands"})
        vis_edges.append({"from": from_id, "to": cmd_node_id, "arrows": "to"})
        vis_edges.append({"from": cmd_node_id, "to": to_id, "arrows": "to"})

    # ── destination filter: for every reachable save, the ordered list of node
    # ids (start, cmd-boxes, save-boxes) on the route from START to it ──────
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
    all_names = order_a + order_b
    for name in all_names:
        if name not in meta:
            continue  # unreachable, skip
        path_ids = ["start"]
        for n in chain(name):
            path_ids.append("cmd_" + node_id(n))
            path_ids.append(node_id(n))
        dest_label = sav_name(name)
        paths[dest_label] = path_ids
        dest_options.append(dest_label)

    unreachable_note = ("Not shown (no transcript evidence anywhere in the repo): " +
                         ", ".join(KNOWN_UNRECOVERABLE))

    template = MAP_HTML.read_text(encoding='utf-8')

    template = template.replace("<title>Game Map</title>", "<title>Save Graph</title>")
    template = template.replace("var STORAGE_KEY = 'map_positions';",
                                 "var STORAGE_KEY = 'saves_positions';")

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(vis_edges, ensure_ascii=False)
    paths_json = json.dumps(paths, ensure_ascii=False)

    # NOTE: re.sub's replacement-string argument interprets backslash escapes
    # (e.g. json.dumps' \\n for embedded newlines), which would corrupt the
    # JSON. Always pass a lambda so the replacement is inserted verbatim.
    template = re.sub(r"var NODES_DATA = \[.*?\];",
                       lambda m: "var NODES_DATA = " + nodes_json + ";",
                       template, count=1, flags=re.S)
    template = re.sub(r"var EDGES_DATA = \[.*?\];",
                       lambda m: "var EDGES_DATA = " + edges_json + ";",
                       template, count=1, flags=re.S)
    template = re.sub(r"(var EDGES_DATA = .*?;\n)",
                       lambda m: m.group(1) + "var PATHS = " + paths_json + ";\n",
                       template, count=1, flags=re.S)

    dest_option_html = "".join(f'<option value="{d}">{d}</option>' for d in dest_options)
    template = template.replace(
        '  <button onclick="clearStorage()" title="Forget saved positions and re-run layout">Clear saved</button>\n',
        '  <button onclick="clearStorage()" title="Forget saved positions and re-run layout">Clear saved</button>\n'
        '  <label style="display:flex;align-items:center;gap:4px;font-size:12px;">\n'
        '    Route to:\n'
        '    <select id="dest-filter" onchange="filterToDestination(this.value)"\n'
        '            style="background:#374151;color:#e5e7eb;border:1px solid #4b5563;border-radius:4px;padding:2px 4px;font-size:12px;cursor:pointer;">\n'
        '      <option value="ALL">ALL</option>\n'
        f'      {dest_option_html}\n'
        '    </select>\n'
        '  </label>\n'
    )
    # Same barnesHut one-shot settle as map.html, but our nodes are much
    # bigger (multi-line command boxes) so give it more room/time.
    # _physicsSettled/dragStart: the instant the user grabs ANY node, physics
    # is forced off unconditionally (not gated behind a one-shot-run guard) --
    # otherwise re-arming physics via Auto-layout/Clear-saved would silently
    # defeat a guarded version of this and the dragged node would snap back.
    # A timeout is also a fallback in case stabilization never completes.
    template = template.replace(
        "if (loadedCount > 0) {\n"
        "  setStatus('Loaded ' + loadedCount + ' saved positions');\n"
        "  network.once('afterDrawing', function() { network.fit({ animation: false }); });\n"
        "} else {\n"
        "  setStatus('No saved positions — drag nodes to arrange, then they auto-save');\n"
        "  // Spread nodes with a one-shot layout so they are not all at origin\n"
        "  network.setOptions({ physics: {\n"
        "    enabled: true,\n"
        "    barnesHut: { gravitationalConstant:-8000, springLength:160, springConstant:0.04 },\n"
        "    stabilization: { iterations: 300 }\n"
        "  } });\n"
        "  network.once('stabilizationIterationsDone', function() {\n"
        "    network.setOptions({ physics: { enabled: false } });\n"
        "    network.fit({ animation: false });\n"
        "    saveToStorage();\n"
        "    setStatus('Auto-laid out. Drag nodes to correct positions — they auto-save.');\n"
        "  });\n"
        "}",
        "var _physicsSettled = (loadedCount > 0);\n"
        "function _stopPhysics() {\n"
        "  if (_physicsSettled) return;\n"
        "  _physicsSettled = true;\n"
        "  network.setOptions({ physics: { enabled: false } });\n"
        "  network.fit({ animation: false });\n"
        "  saveToStorage();\n"
        "  setStatus('Drag nodes to arrange — they auto-save.');\n"
        "}\n"
        "if (loadedCount > 0) {\n"
        "  setStatus('Loaded ' + loadedCount + ' saved positions');\n"
        "  network.once('afterDrawing', function() { network.fit({ animation: false }); });\n"
        "} else {\n"
        "  setStatus('No saved positions — arranging, or drag any node to place it now');\n"
        "  network.setOptions({ physics: {\n"
        "    enabled: true,\n"
        "    barnesHut: { gravitationalConstant:-12000, springLength:220, springConstant:0.03, avoidOverlap:0.5 },\n"
        "    stabilization: { iterations: 500 }\n"
        "  } });\n"
        "  network.once('stabilizationIterationsDone', _stopPhysics);\n"
        "  setTimeout(_stopPhysics, 6000);\n"
        "}\n"
        "network.on('dragStart', function(params) {\n"
        "  if (params.nodes.length === 0) return;\n"
        "  _physicsSettled = true;\n"
        "  network.setOptions({ physics: { enabled: false } });\n"
        "});"
    )
    template = template.replace(
        "}\n</script>\n</body>",
        "}\n\n"
        "function filterToDestination(dest) {\n"
        "  var keep = dest === 'ALL' ? null : new Set(PATHS[dest] || []);\n"
        "  nodes.update(nodes.get().map(function(n) {\n"
        "    return { id: n.id, hidden: keep ? !keep.has(n.id) : false };\n"
        "  }));\n"
        "  edges.update(edges.get().map(function(e) {\n"
        "    var show = keep ? (keep.has(e.from) && keep.has(e.to)) : true;\n"
        "    return { id: e.id, hidden: !show };\n"
        "  }));\n"
        "  network.fit({ animation: true });\n"
        "}\n"
        "</script>\n</body>"
    )

    # Drop the per-node "Notes" toggle -- it doesn't apply to this graph
    # (no notes field on these nodes) -- and add an unreachable-saves badge.
    template = template.replace(
        '  <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:12px;">\n'
        '    <input type="checkbox" id="show-notes" onchange="toggleNotes(this.checked); saveToStorage();">\n'
        '    Notes\n'
        '  </label>\n', '')
    template = template.replace(
        "<span id=\"status\" style=\"margin-left:auto; color:#6ee7b7;\">—</span>",
        f"<span style=\"margin-left:auto; color:#9ca3af; font-size:11px;\" title=\"{unreachable_note}\">"
        f"{len(KNOWN_UNRECOVERABLE)} saves unreachable (hover)</span>"
        "<span id=\"status\" style=\"color:#6ee7b7; margin-left:12px;\">—</span>"
    )

    OUT_HTML.write_text(template, encoding='utf-8')
    print(f"Wrote {OUT_HTML}")
    print(f"nodes={len(nodes)} edges={len(vis_edges)}")


if __name__ == '__main__':
    main()
