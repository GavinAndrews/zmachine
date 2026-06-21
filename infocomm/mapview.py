#!/usr/bin/env python3
"""
mapview.py  —  Convert a map.txt transition log to an interactive HTML map.

The input file is tab-separated (written by the #map / #see meta-commands):
    Transition:  #42: Palace Gate <TAB> #57: Broad Walk <TAB> n
    Note:        NOTE <TAB> #42: Palace Gate <TAB> sundial here

Usage:
    python mapview.py                    # reads map.txt, writes map.html
    python mapview.py mymap.txt          # reads mymap.txt
    python mapview.py -o out.html        # explicit output file
    python mapview.py mymap.txt -o out.html

The HTML opens in any browser:
    - Scroll to zoom, drag to pan
    - Drag nodes to compass-correct positions
    - "Save positions" downloads map_positions.json
    - "Load positions" restores a saved layout
    - Hover a green node to see its notes
"""

import re
import sys
import json
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# Compass / movement canonicalisation
# ---------------------------------------------------------------------------

COMPASS = {
    'n': 'N',  'north': 'N',
    's': 'S',  'south': 'S',
    'e': 'E',  'east':  'E',
    'w': 'W',  'west':  'W',
    'ne': 'NE', 'northeast': 'NE', 'north-east': 'NE', 'north east': 'NE',
    'nw': 'NW', 'northwest': 'NW', 'north-west': 'NW', 'north west': 'NW',
    'se': 'SE', 'southeast': 'SE', 'south-east': 'SE', 'south east': 'SE',
    'sw': 'SW', 'southwest': 'SW', 'south-west': 'SW', 'south west': 'SW',
    'u': 'U', 'up': 'U', 'climb': 'U', 'ascend': 'U',
    'd': 'D', 'down': 'D', 'descend': 'D',
    'in':    'IN',  'enter':  'IN',  'go in':    'IN',
    'out':   'OUT', 'exit':   'OUT', 'go out':   'OUT', 'leave': 'OUT',
}

def canonical_cmd(raw):
    return COMPASS.get(raw.strip().lower(), raw.strip())


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------

def node_id(loc):
    """'#42: Palace Gate' → 'n42'."""
    m = re.match(r'#(\d+)', loc.strip())
    return f'n{m.group(1)}' if m else 'n' + re.sub(r'[^a-zA-Z0-9]', '_', loc.strip())

def node_label(loc):
    return loc.strip().replace('"', "'")

def edge_label(cmd):
    return cmd.replace('"', "'").replace('|', '\\|')


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_map(path):
    """
    Return (transitions, nodes, notes):
      transitions — sorted list of (from_loc, to_loc, canonical_cmd), no duplicates
      nodes       — {node_id: display_label}
      notes       — {node_id: [unique note strings, ...]}
    """
    raw   = set()
    nodes = {}
    notes = {}

    with open(path, encoding='utf-8') as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                print(f"Warning: line {lineno} skipped (< 3 fields)", file=sys.stderr)
                continue

            if parts[0] == 'NOTE':
                loc  = parts[1].strip()
                text = parts[2].strip()
                nid  = node_id(loc)
                nodes[nid] = node_label(loc)
                bucket = notes.setdefault(nid, [])
                if text not in bucket:
                    bucket.append(text)
            else:
                frm = parts[0].strip()
                to  = parts[1].strip()
                cmd = canonical_cmd('\t'.join(parts[2:]))
                raw.add((frm, to, cmd))
                nodes[node_id(frm)] = node_label(frm)
                nodes[node_id(to)]  = node_label(to)

    return sorted(raw, key=lambda t: (t[0], t[1], t[2])), nodes, notes


# ---------------------------------------------------------------------------
# HTML generation (vis.js Network)
# ---------------------------------------------------------------------------

HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Game Map</title>
<script src="https://unpkg.com/vis-network@9/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #111827; color: #e5e7eb; font: 13px/1.4 sans-serif; }}
  #net {{ position: absolute; inset: 40px 0 0 0; }}
  #bar {{ position: fixed; top: 0; left: 0; right: 0; height: 40px;
          background: #1f2937; border-bottom: 1px solid #374151;
          display: flex; align-items: center; gap: 6px; padding: 0 10px; }}
  #bar span {{ color: #9ca3af; font-size: 11px; margin-left: auto; }}
  button {{ background: #374151; color: #e5e7eb; border: 1px solid #4b5563;
            padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }}
  button:hover {{ background: #4b5563; }}
  button.on {{ background: #065f46; border-color: #059669; }}
  #file-load {{ display: none; }}
</style>
</head>
<body>
<div id="bar">
  <button onclick="fitAll()">Fit</button>
  <button id="phys-btn" class="on" onclick="togglePhysics()">Physics ON</button>
  <button onclick="saveJSON()">Save positions</button>
  <label>
    <button onclick="document.getElementById('file-load').click()">Load positions</button>
    <input id="file-load" type="file" accept=".json" onchange="loadJSON(event)">
  </label>
  <button onclick="clearStorage()" title="Forget saved positions and re-run layout">Clear saved</button>
  <span>Positions auto-saved on drag &nbsp;·&nbsp; Scroll=zoom &nbsp;·&nbsp;
        Right-drag=pan &nbsp;·&nbsp; Hover green node=notes</span>
</div>
<div id="net"></div>

<script>
const STORAGE_KEY = 'map_positions';

// ── load saved positions BEFORE creating anything ────────────────────────
// Injecting coordinates into the raw node data prevents the physics engine
// from ever seeing "unpositioned" nodes, so it cannot override the saved layout.
var savedPos = null;
try {{
  var _raw = localStorage.getItem(STORAGE_KEY);
  if (_raw) savedPos = JSON.parse(_raw);
}} catch(e) {{}}

var NODES_DATA = {nodes};
var EDGES_DATA = {edges};

if (savedPos) {{
  NODES_DATA.forEach(function(n) {{
    var p = savedPos[n.id];
    if (p) {{ n.x = p.x; n.y = p.y; }}
  }});
}}

// Physics starts disabled when we have saved positions so they are never
// overridden by the stabilisation loop.
var physOn = (savedPos === null);

var nodes   = new vis.DataSet(NODES_DATA);
var edges   = new vis.DataSet(EDGES_DATA);
var network = new vis.Network(
  document.getElementById('net'),
  {{ nodes: nodes, edges: edges }},
  {{
    nodes: {{
      shape: 'box', margin: 8,
      color: {{ background:'#1e3a5f', border:'#2563eb',
                highlight:{{ background:'#1d4ed8', border:'#60a5fa' }} }},
      font:  {{ color:'#e5e7eb', size:13, face:'monospace' }},
    }},
    edges: {{
      arrows: 'to',
      color:  {{ color:'#4b5563', highlight:'#9ca3af' }},
      font:   {{ color:'#9ca3af', size:11, align:'middle', background:'#111827' }},
      smooth: {{ type:'curvedCW', roundness: 0.1 }},
    }},
    physics: {{
      enabled: physOn,
      barnesHut: {{ gravitationalConstant:-8000, springLength:160, springConstant:0.04 }},
      stabilization: {{ iterations: 300 }},
    }},
    interaction: {{ dragNodes:true, zoomView:true, dragView:true,
                    multiselect:true, tooltipDelay:150 }},
  }}
);

// Fit view once on first draw (works for both fresh and restored layouts)
network.once('afterDrawing', function() {{ network.fit({{ animation: false }}); }});

// When no saved positions: disable physics after the initial layout settles
if (!savedPos) {{
  network.once('stabilizationIterationsDone', function() {{ setPhysics(false); }});
}}

// ── auto-save ────────────────────────────────────────────────────────────
network.on('dragEnd', function(params) {{
  // Only save when a node was actually moved (not a view pan)
  if (params.nodes && params.nodes.length > 0) {{
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(network.getPositions())); }}
    catch(e) {{}}
  }}
}});

// ── controls ─────────────────────────────────────────────────────────────
function setPhysics(on) {{
  physOn = on;
  network.setOptions({{ physics: {{ enabled: on }} }});
  var btn = document.getElementById('phys-btn');
  btn.textContent = on ? 'Physics ON' : 'Physics OFF';
  btn.classList.toggle('on', on);
}}
function togglePhysics() {{ setPhysics(!physOn); }}
function fitAll()        {{ network.fit({{ animation: true }}); }}

function saveJSON() {{
  var pos  = network.getPositions();
  var blob = new Blob([JSON.stringify(pos, null, 2)], {{type:'application/json'}});
  var a    = document.createElement('a');
  a.href   = URL.createObjectURL(blob);
  a.download = 'map_positions.json';
  a.click();
}}

function loadJSON(evt) {{
  var file = evt.target.files[0];
  if (!file) return;
  file.text().then(function(txt) {{
    var pos = JSON.parse(txt);
    nodes.update(Object.entries(pos).map(function([id, p]) {{ return {{id:id, x:p.x, y:p.y}}; }}));
    setPhysics(false);
    network.fit({{ animation: true }});
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(pos)); }} catch(e) {{}}
  }});
  evt.target.value = '';
}}

function clearStorage() {{
  try {{ localStorage.removeItem(STORAGE_KEY); }} catch(e) {{}}
  savedPos = null;
  setPhysics(true);
  network.stabilize();
}}

// Sync button label with initial state
(function() {{
  var btn = document.getElementById('phys-btn');
  btn.textContent = physOn ? 'Physics ON' : 'Physics OFF';
  btn.classList.toggle('on', physOn);
}})();
</script>
</body>
</html>
"""


def build_html(transitions, nodes, notes):
    vis_nodes = []
    for nid, label in nodes.items():
        node = {'id': nid, 'label': label}
        loc_notes = notes.get(nid, [])
        if loc_notes:
            node['title'] = '\n'.join(f'• {n}' for n in loc_notes)
            node['color'] = {
                'background': '#1c3a2a', 'border': '#16a34a',
                'highlight':  {'background': '#14532d', 'border': '#4ade80'},
            }
        vis_nodes.append(node)

    vis_edges = [
        {'from': node_id(frm), 'to': node_id(to), 'label': edge_label(cmd)}
        for frm, to, cmd in transitions
    ]
    return HTML.format(
        nodes=json.dumps(vis_nodes, ensure_ascii=False),
        edges=json.dumps(vis_edges, ensure_ascii=False),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert a map.txt transition log to an interactive HTML map')
    parser.add_argument('input',  nargs='?', default='map.txt',
                        help='transition log (default: map.txt)')
    parser.add_argument('-o', '--output', metavar='FILE', default='map.html',
                        help='output HTML file (default: map.html)')
    args = parser.parse_args()

    transitions, nodes, notes = parse_map(args.input)

    if not transitions and not notes:
        print('No data found in input file.', file=sys.stderr)
        sys.exit(1)

    note_count = sum(len(v) for v in notes.values())
    print(f'{len(transitions)} transitions, {len(nodes)} locations, '
          f'{note_count} notes.', file=sys.stderr)

    Path(args.output).write_text(build_html(transitions, nodes, notes),
                                 encoding='utf-8')
    print(f'Written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()