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
    return cmd.replace('"', "'")


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
  @media print {{
    body, html {{ background: white; }}
    #bar {{ display: none; }}
    #net  {{ position: static; width: 100vw; height: 100vh; }}
    canvas {{ max-width: 100%; max-height: 100%; }}
  }}
</style>
</head>
<body>
<div id="bar">
  <button onclick="fitAll()">Fit</button>
  <button onclick="autoLayout()">Auto layout</button>
  <button onclick="saveJSON()">Save positions</button>
  <label>
    <button onclick="document.getElementById('file-load').click()">Load positions</button>
    <input id="file-load" type="file" accept=".json" onchange="loadJSON(event)">
  </label>
  <button onclick="clearStorage()" title="Forget saved positions and re-run layout">Clear saved</button>
  <label style="display:flex;align-items:center;gap:4px;font-size:12px;">
    Labels:
    <select id="label-style" onchange="applyLabelStyle(this.value); saveToStorage();"
            style="background:#374151;color:#e5e7eb;border:1px solid #4b5563;border-radius:4px;padding:2px 4px;font-size:12px;cursor:pointer;">
      <option value="labels">Show</option>
      <option value="none">Hide</option>
    </select>
  </label>
  <label style="display:flex;align-items:center;gap:4px;cursor:pointer;font-size:12px;">
    <input type="checkbox" id="show-notes" onchange="toggleNotes(this.checked); saveToStorage();">
    Notes
  </label>
  <button onclick="saveJPEG()" title="Download the current view as a JPEG image">Save JPEG</button>
  <button onclick="printPDF()" title="Open image in new tab — use browser Print to save as PDF">Print / PDF</button>
  <span id="status" style="margin-left:auto; color:#6ee7b7;">—</span>
</div>
<div id="net"></div>

<script>
var STORAGE_KEY = 'map_positions_{namespace}';

function setStatus(msg) {{
  var el = document.getElementById('status');
  if (el) el.textContent = msg;
}}

// ── restore saved positions BEFORE creating the DataSet ──────────────────
// Coordinates are injected directly into NODES_DATA so vis.js never sees
// unpositioned nodes — nothing can override the restored layout.
var NODES_DATA = {nodes};
var EDGES_DATA = {edges};

var savedPos = null;
try {{
  var _raw = localStorage.getItem(STORAGE_KEY);
  if (_raw) savedPos = JSON.parse(_raw);
}} catch(e) {{ setStatus('localStorage unavailable: ' + e); }}

var loadedCount  = 0;
var savedShowNotes = false;
if (savedPos) {{
  savedShowNotes = !!savedPos._showNotes;
  NODES_DATA = NODES_DATA.map(function(n) {{
    var p = savedPos[n.id];
    if (p) {{ loadedCount++; return Object.assign({{}}, n, {{x: p.x, y: p.y}}); }}
    return n;
  }});
}}

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
      font:   {{ color:'#e5e7eb', size:12, align:'middle',
                 background:'#111827', strokeWidth:2, strokeColor:'#111827' }},
      smooth: {{ type:'curvedCW', roundness: 0.2 }},
    }},
    physics: {{ enabled: false }},
    interaction: {{ dragNodes:true, zoomView:true, dragView:true,
                    multiselect:true, tooltipDelay:150 }},
  }}
);

// ── restore label style and notes checkbox after network is ready ─────────
var savedLabelStyle = (savedPos && savedPos._labelStyle) || 'labels';
var _lsel = document.getElementById('label-style');
if (_lsel) {{ _lsel.value = savedLabelStyle; }}
if (savedLabelStyle !== 'labels') {{ applyLabelStyle(savedLabelStyle); }}

if (savedShowNotes) {{
  var cb = document.getElementById('show-notes');
  if (cb) {{ cb.checked = true; toggleNotes(true); }}
}}

var _physicsSettled = (loadedCount > 0);
function _stopPhysics() {{
  if (_physicsSettled) return;
  _physicsSettled = true;
  network.setOptions({{ physics: {{ enabled: false }} }});
  network.fit({{ animation: false }});
  saveToStorage();
  setStatus('Auto-laid out. Drag nodes to correct positions — they auto-save.');
}}

if (loadedCount > 0) {{
  setStatus('Loaded ' + loadedCount + ' saved positions');
  network.once('afterDrawing', function() {{ network.fit({{ animation: false }}); }});
}} else {{
  setStatus('No saved positions — drag nodes to arrange, then they auto-save');
  // Spread nodes with a one-shot layout so they are not all at origin
  network.setOptions({{ physics: {{
    enabled: true,
    barnesHut: {{ gravitationalConstant:-8000, springLength:160, springConstant:0.04 }},
    stabilization: {{ iterations: 300 }}
  }} }});
  network.once('stabilizationIterationsDone', _stopPhysics);
  setTimeout(_stopPhysics, 6000);   // safety net if stabilization never fires
}}

// Dragging a node must kill physics immediately and unconditionally — even
// mid-stabilization — otherwise the still-running simulation fights the drag
// and the node springs back on release.
network.on('dragStart', function(params) {{
  if (params.nodes.length === 0) return;
  _physicsSettled = true;
  network.setOptions({{ physics: {{ enabled: false }} }});
}});

// ── auto-save on every drag (no filter — always save) ────────────────────
network.on('dragEnd', function() {{
  saveToStorage();
}});

function saveToStorage() {{
  try {{
    var data = network.getPositions();
    var _cb = document.getElementById('show-notes');
    data._showNotes = !!(_cb && _cb.checked);
    var _ls = document.getElementById('label-style');
    data._labelStyle = _ls ? _ls.value : 'labels';
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setStatus('Saved (' + Object.keys(network.getPositions()).length + ' nodes)');
  }} catch(e) {{
    setStatus('Save failed: ' + e);
  }}
}}

// ── controls ─────────────────────────────────────────────────────────────
function fitAll() {{ network.fit({{ animation: true }}); }}

function autoLayout() {{
  setStatus('Running layout…');
  network.setOptions({{ physics: {{ enabled: true,
    barnesHut: {{ gravitationalConstant:-8000, springLength:160, springConstant:0.04 }},
    stabilization: {{ iterations: 300 }} }} }});
  network.once('stabilizationIterationsDone', function() {{
    network.setOptions({{ physics: {{ enabled: false }} }});
    network.fit({{ animation: true }});
    saveToStorage();
  }});
}}

function saveJSON() {{
  var pos  = network.getPositions();
  var blob = new Blob([JSON.stringify(pos, null, 2)], {{type:'application/json'}});
  var a    = document.createElement('a');
  a.href   = URL.createObjectURL(blob);
  a.download = 'map_positions_{namespace}.json';
  a.click();
}}

function loadJSON(evt) {{
  var file = evt.target.files[0];
  if (!file) return;
  file.text().then(function(txt) {{
    var pos = JSON.parse(txt);
    nodes.update(Object.entries(pos).map(function([id, p]) {{
      return {{id:id, x:p.x, y:p.y}};
    }}));
    network.fit({{ animation: true }});
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(pos)); }} catch(e) {{}}
    setStatus('Loaded ' + Object.keys(pos).length + ' positions from file');
  }});
  evt.target.value = '';
}}

function applyLabelStyle(style) {{
  var show = (style !== 'none');
  edges.get().forEach(function(e) {{
    edges.update({{ id: e.id, font: {{ color: show ? '#e5e7eb' : 'rgba(0,0,0,0)' }} }});
  }});
}}

function toggleNotes(show) {{
  var updates = nodes.get().map(function(n) {{
    if (!n.notes) return null;
    return {{ id: n.id, label: show ? n.label.split('\\n')[0] + '\\n' + n.notes : n.label.split('\\n')[0] }};
  }}).filter(Boolean);
  nodes.update(updates);
}}

function clearStorage() {{
  try {{ localStorage.removeItem(STORAGE_KEY); }} catch(e) {{}}
  setStatus('Cleared. Running new layout…');
  autoLayout();
}}

function captureFullMap(callback) {{
  // Temporarily expand the container to hold the entire graph at 1:1 scale,
  // fit all nodes into it, capture, then restore everything.
  var PADDING = 60;
  var netDiv  = document.getElementById('net');

  // Compute bounding box from node positions (getBoundingBox() not in vis API)
  var positions = network.getPositions();
  var ids = Object.keys(positions);
  if (ids.length === 0) {{ setStatus('No nodes to export.'); return; }}
  var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  ids.forEach(function(id) {{
    var p = positions[id];
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
  }});
  var graphW = (maxX - minX) + PADDING * 2;
  var graphH = (maxY - minY) + PADDING * 2;

  // Minimum sensible size
  graphW = Math.max(graphW, 800);
  graphH = Math.max(graphH, 600);

  // Save current container style and view state
  var oldStyle   = netDiv.getAttribute('style') || '';
  var oldPos     = network.getViewPosition();
  var oldScale   = network.getScale();

  // Expand container
  netDiv.style.position = 'absolute';
  netDiv.style.width    = graphW + 'px';
  netDiv.style.height   = graphH + 'px';
  netDiv.style.inset    = 'auto';

  // Give vis.js one frame to resize its canvas, then fit + capture
  requestAnimationFrame(function() {{
    network.redraw();
    network.fit({{ animation: false }});

    requestAnimationFrame(function() {{
      var src = network.canvas.frame.canvas;
      var out = document.createElement('canvas');
      out.width  = src.width;
      out.height = src.height;
      var ctx = out.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, out.width, out.height);
      ctx.drawImage(src, 0, 0);

      // Restore container and view
      netDiv.setAttribute('style', oldStyle);
      requestAnimationFrame(function() {{
        network.redraw();
        network.moveTo({{ position: oldPos, scale: oldScale, animation: false }});
        callback(out);
      }});
    }});
  }});
}}

function saveJPEG() {{
  setStatus('Rendering full map…');
  captureFullMap(function(canvas) {{
    var a = document.createElement('a');
    a.href     = canvas.toDataURL('image/jpeg', 0.95);
    a.download = 'map.jpg';
    a.click();
    setStatus('JPEG saved.');
  }});
}}

function printPDF() {{
  setStatus('Rendering full map…');
  captureFullMap(function(canvas) {{
    var dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    // Inject a print-only image into this page to avoid file:// cross-origin
    // restrictions that block window.open() + document.write().
    var img = document.createElement('img');
    img.id  = 'print-export';
    img.src = dataUrl;
    document.body.appendChild(img);

    var style = document.createElement('style');
    style.id  = 'print-export-style';
    style.textContent = (
      '@media print {{' +
      '  @page {{ size: landscape; margin: 0.5cm; }}' +
      '  body > *:not(#print-export) {{ display: none !important; }}' +
      '  #print-export {{ display: block !important; width: 100%; height: auto; }}' +
      '}}'
    );
    document.head.appendChild(style);

    window.print();

    document.body.removeChild(img);
    document.head.removeChild(style);
    setStatus('Print dialog opened.');
  }});
}}
</script>
</body>
</html>
"""


def build_html(transitions, nodes, notes, namespace='map'):
    namespace = re.sub(r'[^a-zA-Z0-9_-]', '_', namespace).lower() or 'map'
    vis_nodes = []
    for nid, label in nodes.items():
        node = {'id': nid, 'label': label}
        loc_notes = notes.get(nid, [])
        if loc_notes:
            node['title'] = '\n'.join(f'• {n}' for n in loc_notes)
            node['notes'] = '\n'.join(loc_notes)   # stored for JS toggle
            node['color'] = {
                'background': '#1c3a2a', 'border': '#16a34a',
                'highlight':  {'background': '#14532d', 'border': '#4ade80'},
            }
        vis_nodes.append(node)

    # Merge only true parallel edges (same from/to pair) into one label.
    # Bidirectional pairs (A→B + B→A) are kept as separate directed edges so
    # each label sits near the correct arrowhead; vis.js dynamic smoothing
    # curves them to opposite sides so they never overlap.
    edge_map = {}
    for frm, to, cmd in transitions:
        key = (node_id(frm), node_id(to))
        edge_map.setdefault(key, []).append(edge_label(cmd))

    DIR_ORDER = ['IN', 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'OUT', 'U', 'D']
    def sort_dirs(labels):
        return sorted(labels, key=lambda d: DIR_ORDER.index(d) if d in DIR_ORDER else len(DIR_ORDER))

    vis_edges = [
        {'from': src, 'to': dst, 'label': ','.join(sort_dirs(labels))}
        for (src, dst), labels in edge_map.items()
    ]
    return HTML.format(
        nodes=json.dumps(vis_nodes, ensure_ascii=False),
        edges=json.dumps(vis_edges, ensure_ascii=False),
        namespace=namespace,
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

    namespace = Path(args.output).resolve().parent.name
    Path(args.output).write_text(build_html(transitions, nodes, notes, namespace=namespace),
                                 encoding='utf-8')
    print(f'Written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()