#!/usr/bin/env python3
"""
map2mermaid.py  —  Convert a map.txt transition log to a Mermaid directed graph.

The input file is tab-separated (written by the #map meta-command):
    #42: Palace Gate    #57: Broad Walk    n

Usage:
    python map2mermaid.py                        # reads map.txt, prints to stdout
    python map2mermaid.py mymap.txt              # reads mymap.txt
    python map2mermaid.py -o map.md              # writes to map.md
    python map2mermaid.py mymap.txt -o out.md
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
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert a map.txt transition log to a Mermaid directed graph')
    parser.add_argument('input', nargs='?', default='map.txt',
                        help='transition log file (default: map.txt)')
    parser.add_argument('-o', '--output', metavar='FILE', default=None,
                        help='write Mermaid markdown to FILE instead of stdout')
    args = parser.parse_args()

    transitions, nodes = parse_map(args.input)

    if not transitions:
        print('No transitions found in input file.', file=sys.stderr)
        sys.exit(1)

    print(f'{len(transitions)} unique transitions, {len(nodes)} locations.',
          file=sys.stderr)

    mermaid = build_mermaid(transitions, nodes)
    output  = f'```mermaid\n{mermaid}\n```\n'

    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f'Written to {args.output}', file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
