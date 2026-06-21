#!/usr/bin/env python3
"""
map2mermaid.py  —  Convert a map.txt transition log to a Mermaid directed graph.

The input file is tab-separated (written by the #map meta-command):
    #42: Palace Gate    #57: Broad Walk    n

Usage:
    python map2mermaid.py                        # reads map.txt, prints to stdout
    python map2mermaid.py mymap.txt              # reads mymap.txt
    python map2mermaid.py -o map.md              # writes Mermaid markdown
    python map2mermaid.py -o map.html            # writes interactive HTML (pan/zoom)
    python map2mermaid.py mymap.txt -o out.html
"""

import re
import sys
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# Compass / movement canonicalisation
# ---------------------------------------------------------------------------

COMPASS = {
    # Cardinal
    'n': 'N',  'north': 'N',
    's': 'S',  'south': 'S',
    'e': 'E',  'east':  'E',
    'w': 'W',  'west':  'W',
    # Diagonal
    'ne': 'NE', 'northeast': 'NE', 'north-east': 'NE', 'north east': 'NE',
    'nw': 'NW', 'northwest': 'NW', 'north-west': 'NW', 'north west': 'NW',
    'se': 'SE', 'southeast': 'SE', 'south-east': 'SE', 'south east': 'SE',
    'sw': 'SW', 'southwest': 'SW', 'south-west': 'SW', 'south west': 'SW',
    # Vertical
    'u': 'U', 'up': 'U', 'climb': 'U', 'ascend': 'U',
    'd': 'D', 'down': 'D', 'descend': 'D',
    # In / out
    'in':    'IN',  'enter':  'IN',  'go in':    'IN',
    'out':   'OUT', 'exit':   'OUT', 'go out':   'OUT', 'leave': 'OUT',
}

def canonical_cmd(raw):
    """Return the canonical edge label: abbreviated compass or raw command."""
    key = raw.strip().lower()
    return COMPASS.get(key, raw.strip())


# ---------------------------------------------------------------------------
# Mermaid helpers
# ---------------------------------------------------------------------------

def node_id(loc):
    """'#42: Palace Gate' → 'n42'  (safe Mermaid identifier)."""
    m = re.match(r'#(\d+)', loc.strip())
    if m:
        return f'n{m.group(1)}'
    return 'n' + re.sub(r'[^a-zA-Z0-9]', '_', loc.strip())


def node_label(loc):
    """Escape double-quotes for use inside a Mermaid quoted string."""
    return loc.strip().replace('"', "'")


def mermaid_edge_label(label):
    """Escape characters that would break a Mermaid edge label."""
    return label.replace('"', "'").replace('|', '\\|')


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_map(path):
    """
    Return (transitions, nodes) where:
      transitions — sorted list of (from_loc, to_loc, canonical_cmd) with no duplicates
      nodes       — dict of {node_id: display_label}
    """
    raw = set()
    nodes = {}

    with open(path, encoding='utf-8') as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                print(f"Warning: line {lineno} has fewer than 3 fields, skipped",
                      file=sys.stderr)
                continue
            frm = parts[0].strip()
            to  = parts[1].strip()
            cmd = canonical_cmd('\t'.join(parts[2:]))
            raw.add((frm, to, cmd))
            nodes[node_id(frm)] = node_label(frm)
            nodes[node_id(to)]  = node_label(to)

    transitions = sorted(raw, key=lambda t: (t[0], t[1], t[2]))
    return transitions, nodes


# ---------------------------------------------------------------------------
# Mermaid generation
# ---------------------------------------------------------------------------

def build_mermaid(transitions, nodes):
    lines = [
        '%%{init: {"flowchart": {"rankDir": "LR"}} }%%',
        'graph LR',
        '',
        '    %% Nodes',
    ]

    for nid in sorted(nodes):
        label = nodes[nid]
        lines.append(f'    {nid}["{label}"]')

    lines.append('')
    lines.append('    %% Transitions')

    # Group edges so identical (from, to) pairs with multiple commands are readable
    for frm, to, cmd in transitions:
        fid   = node_id(frm)
        tid   = node_id(to)
        elabel = mermaid_edge_label(cmd)
        lines.append(f'    {fid} -->|"{elabel}"| {tid}')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Interactive HTML output using vis.js Network
# ---------------------------------------------------------------------------
# Nodes can be dragged to compass-correct positions.
# Positions are saved to / loaded from a companion JSON file so the layout
# survives between browser sessions without relying on localStorage.
# ---------------------------------------------------------------------------

VIS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Game Map</title>
<script src="https://unpkg.com/vis-network@9/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body  {{ background: #111827; color: #e5e7eb; font: 13px/1.4 sans-serif; }}
  #net  {{ position: absolute; inset: 40px 0 0 0; }}
  #bar  {{ position: fixed; top: 0; left: 0; right: 0; height: 40px;
           background: #1f2937; border-bottom: 1px solid #374151;
           display: flex; align-items: center; gap: 6px; padding: 0 10px; }}
  #bar span  {{ color: #9ca3af; font-size: 11px; margin-left: auto; }}
  button {{ background: #374151; color: #e5e7eb; border: 1px solid #4b5563;
            padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }}
  button:hover  {{ background: #4b5563; }}
  button.active {{ background: #065f46; border-color: #059669; }}
  #file-load {{ display: none; }}
</style>
</head>
<body>
<div id="bar">
  <button onclick="fitAll()">Fit</button>
  <button id="phys-btn" class="active" onclick="togglePhysics()">Physics ON</button>
  <button onclick="saveJSON()">Save positions</button>
  <label><button onclick="document.getElementById('file-load').click()">Load positions</button>
    <input id="file-load" type="file" accept=".json" onchange="loadJSON(event)"></label>
  <span>Drag nodes to map compass directions &nbsp;·&nbsp; Scroll = zoom &nbsp;·&nbsp; Right-drag = pan</span>
</div>
<div id="net"></div>

<script>
const NODES_DATA = {nodes};
const EDGES_DATA = {edges};

var nodes    = new vis.DataSet(NODES_DATA);
var edges    = new vis.DataSet(EDGES_DATA);
var network  = new vis.Network(
  document.getElementById('net'),
  {{ nodes, edges }},
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
      enabled: true,
      barnesHut: {{ gravitationalConstant:-8000, springLength:160, springConstant:0.04 }},
      stabilization: {{ iterations: 300 }},
    }},
    interaction: {{ dragNodes:true, zoomView:true, dragView:true,
                    multiselect:true, tooltipDelay:200 }},
  }}
);

network.once('stabilizationIterationsDone', () => {{
  network.setOptions({{ physics: {{ enabled: false }} }});
  document.getElementById('phys-btn').textContent = 'Physics OFF';
  document.getElementById('phys-btn').classList.remove('active');
}});

var physOn = true;
function togglePhysics() {{
  physOn = !physOn;
  network.setOptions({{ physics: {{ enabled: physOn }} }});
  const btn = document.getElementById('phys-btn');
  btn.textContent = physOn ? 'Physics ON' : 'Physics OFF';
  btn.classList.toggle('active', physOn);
}}

function fitAll() {{ network.fit({{ animation: true }}); }}

function saveJSON() {{
  const pos = network.getPositions();
  const blob = new Blob([JSON.stringify(pos, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'map_positions.json';
  a.click();
}}

function loadJSON(evt) {{
  const file = evt.target.files[0];
  if (!file) return;
  file.text().then(txt => {{
    const pos = JSON.parse(txt);
    const updates = Object.entries(pos).map(([id, {{x, y}}]) => ({{id, x, y}}));
    nodes.update(updates);
    network.setOptions({{ physics: {{ enabled: false }} }});
    physOn = false;
    const btn = document.getElementById('phys-btn');
    btn.textContent = 'Physics OFF';
    btn.classList.remove('active');
    network.fit({{ animation: true }});
  }});
  evt.target.value = '';
}}
</script>
</body>
</html>
"""


def build_html(transitions, nodes):
    import json

    vis_nodes = [
        {'id': nid, 'label': label}
        for nid, label in nodes.items()
    ]
    vis_edges = [
        {'from': node_id(frm), 'to': node_id(to),
         'label': mermaid_edge_label(cmd)}
        for frm, to, cmd in transitions
    ]
    return VIS_HTML.format(
        nodes=json.dumps(vis_nodes, ensure_ascii=False),
        edges=json.dumps(vis_edges, ensure_ascii=False),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert a map.txt transition log to a Mermaid directed graph')
    parser.add_argument('input', nargs='?', default='map.txt',
                        help='transition log file (default: map.txt)')
    parser.add_argument('-o', '--output', metavar='FILE', default=None,
                        help='output file: .md for Mermaid markdown, '
                             '.html for interactive browser view (default: stdout)')
    args = parser.parse_args()

    transitions, nodes = parse_map(args.input)

    if not transitions:
        print('No transitions found in input file.', file=sys.stderr)
        sys.exit(1)

    print(f'{len(transitions)} unique transitions, {len(nodes)} locations.',
          file=sys.stderr)

    out_path = Path(args.output) if args.output else None

    if out_path and out_path.suffix.lower() == '.html':
        out_path.write_text(build_html(transitions, nodes), encoding='utf-8')
        print(f'Written to {out_path}', file=sys.stderr)
    else:
        mermaid = build_mermaid(transitions, nodes)
        content = f'```mermaid\n{mermaid}\n```\n'
        if out_path:
            out_path.write_text(content, encoding='utf-8')
            print(f'Written to {out_path}', file=sys.stderr)
        else:
            print(content)


if __name__ == '__main__':
    main()
