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
# HTML output (interactive pan/zoom via svg-pan-zoom)
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Game Map</title>
<style>
  body  {{ margin: 0; background: #1a1a2e; color: #eee; font-family: sans-serif; }}
  #controls {{ position: fixed; top: 8px; left: 8px; z-index: 10;
               display: flex; gap: 6px; }}
  button  {{ background: #16213e; color: #eee; border: 1px solid #0f3460;
             padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 13px; }}
  button:hover {{ background: #0f3460; }}
  #hint   {{ position: fixed; bottom: 8px; left: 8px; font-size: 11px; opacity: .5; }}
  #graph  {{ width: 100vw; height: 100vh; }}
  /* Mermaid node and edge tweaks */
  .node rect, .node circle, .node ellipse, .node polygon
              {{ fill: #16213e !important; stroke: #0f3460 !important; }}
  .edgeLabel  {{ background: #1a1a2e !important; color: #aaa !important; }}
  .edgePath   {{ stroke: #0f3460 !important; }}
  text        {{ fill: #ddd !important; }}
</style>
</head>
<body>
<div id="controls">
  <button onclick="pz.zoomIn()">+</button>
  <button onclick="pz.zoomOut()">−</button>
  <button onclick="pz.resetZoom(); pz.resetPan()">Reset</button>
</div>
<div id="graph" class="mermaid">
{diagram}
</div>
<div id="hint">Scroll to zoom &nbsp;·&nbsp; Drag to pan</div>

<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<script>
mermaid.initialize({{ startOnLoad: false, theme: 'dark',
                      flowchart: {{ rankDir: 'LR', useMaxWidth: false }} }});

mermaid.run({{ nodes: [document.getElementById('graph')] }}).then(() => {{
  const svg = document.querySelector('#graph svg');
  if (svg) {{
    svg.style.width  = '100%';
    svg.style.height = '100%';
    window.pz = svgPanZoom(svg, {{
      zoomEnabled: true, controlIconsEnabled: false,
      fit: true, center: true, minZoom: 0.1, maxZoom: 20,
    }});
  }}
}});
</script>
</body>
</html>
"""


def build_html(transitions, nodes):
    diagram = build_mermaid(transitions, nodes)
    return HTML_TEMPLATE.format(diagram=diagram)


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
