"""
extract_transitions.py

Parses an Infocom disassembly text file (produced by e.g. TXD/infodump)
and extracts room-to-room transitions for the compass directions.

Each game assigns its own property numbers to its exit directions (Trinity
uses 52-63, Zork1 uses 19-31, etc.), so instead of a hardcoded property-number
table this matches on the direction *word* the disassembler printed and
canonicalises it via DIRECTION_WORDS. Games also spell directions
differently (Trinity: "NORTHWEST"/"SOUTHWEST", Zork1: "NORTHW"/"SOUTHW"),
which DIRECTION_WORDS also absorbs.

Exit property data comes in these forms:
  DIRECT:            (NORTH TO OBJECT-12)
  CONDITIONAL:        (WEST TO OBJECT-297 IF OBJECT-128 IS OPEN)
  CONDITIONAL GLOBAL: (WEST TO OBJECT-28 IF GLOBAL-143)
  (either conditional form may carry a trailing "ELSE "<blocked message>"",
  which is ignored)
  PER ROUTINE:        (UP PER Routine at 0x24820)
  STRING:             (NORTH "You can only go up...")   <- blocked, ignored

Usage:
  python extract_transitions.py [path/to/TRINITY.txt]
  python extract_transitions.py data/ZORK1.txt
"""

import re
import sys
from pathlib import Path

DIRECTION_WORDS = {
    'NORTH': 'N', 'N': 'N',
    'SOUTH': 'S', 'S': 'S',
    'EAST':  'E', 'E': 'E',
    'WEST':  'W', 'W': 'W',
    'NORTHEAST': 'NE', 'NE': 'NE',
    'NORTHWEST': 'NW', 'NORTHW': 'NW', 'NW': 'NW',
    'SOUTHEAST': 'SE', 'SE': 'SE',
    'SOUTHWEST': 'SW', 'SOUTHW': 'SW', 'SW': 'SW',
    'UP': 'UP', 'U': 'UP',
    'DOWN': 'DOWN', 'D': 'DOWN',
    'IN': 'IN', 'ENTER': 'IN',
    'OUT': 'OUT', 'EXIT': 'OUT',
    'LAND': 'LAND',   # Zork1's river/boat pseudo-direction
}

# Regex patterns for property lines
# e.g.   023AF 7F    00 0C                   63/2  (NORTH TO OBJECT-12)
RE_PROP = re.compile(
    r'^\s+[0-9A-F]{5}\s+'      # address
    r'[0-9A-F ]+\s+'           # hex bytes
    r'\d+/\d+\s+'              # prop_num/prop_size
    r'\((.+)\)$'               # (content)
)

RE_DIRECT       = re.compile(r'^(\w+) TO OBJECT-(\d+)$')
RE_COND_OBJECT  = re.compile(r'^(\w+) TO OBJECT-(\d+) IF OBJECT-(\d+) IS (\w+)(?: ELSE ".*")?$')
RE_COND_GLOBAL  = re.compile(r'^(\w+) TO OBJECT-(\d+) IF GLOBAL-(\d+)(?: ELSE ".*")?$')
RE_PER          = re.compile(r'^(\w+) PER Routine at (0x[0-9A-Fa-f]+)$')

RE_OBJECT_START = re.compile(r'^Object: (\d+)$')
RE_DESCRIPTION  = re.compile(r'^\s+Description = "(.+)"$')


def parse(path: Path):
    objects = {}   # obj_num -> {name, exits: []}
    current_obj = None
    current_name = None

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip()

            m = RE_OBJECT_START.match(line)
            if m:
                current_obj = int(m.group(1))
                current_name = None
                objects[current_obj] = {"name": None, "exits": []}
                continue

            if current_obj is None:
                continue

            m = RE_DESCRIPTION.match(line)
            if m:
                # Strip disassembly abbreviation markers: {and } -> and
                name = re.sub(r'\{([^}]*)\}', r'\1', m.group(1))
                objects[current_obj]["name"] = name
                continue

            m = RE_PROP.match(line)
            if not m:
                continue

            content = m.group(1).strip()

            md = RE_DIRECT.match(content)
            if md:
                direction = DIRECTION_WORDS.get(md.group(1).upper())
                if direction is None:
                    continue
                dest = int(md.group(2))
                objects[current_obj]["exits"].append({
                    "dir": direction, "type": "direct", "dest": dest,
                })
                continue

            mc = RE_COND_OBJECT.match(content)
            if mc:
                direction = DIRECTION_WORDS.get(mc.group(1).upper())
                if direction is None:
                    continue
                dest   = int(mc.group(2))
                gate   = int(mc.group(3))
                state  = mc.group(4)
                objects[current_obj]["exits"].append({
                    "dir": direction, "type": "conditional",
                    "dest": dest, "gate_obj": gate, "gate_state": state,
                })
                continue

            mg = RE_COND_GLOBAL.match(content)
            if mg:
                direction = DIRECTION_WORDS.get(mg.group(1).upper())
                if direction is None:
                    continue
                dest   = int(mg.group(2))
                gate   = int(mg.group(3))
                objects[current_obj]["exits"].append({
                    "dir": direction, "type": "conditional_global",
                    "dest": dest, "gate_global": gate,
                })
                continue

            mp = RE_PER.match(content)
            if mp:
                direction = DIRECTION_WORDS.get(mp.group(1).upper())
                if direction is None:
                    continue
                addr = mp.group(2)
                objects[current_obj]["exits"].append({
                    "dir": direction, "type": "routine", "routine": addr,
                })
                continue

            # Otherwise it's a blocked-direction string — skip

    return objects


def name_of(objects, obj_num):
    obj = objects.get(obj_num)
    if obj and obj["name"]:
        return f'#{obj_num} "{obj["name"]}"'
    return f'#{obj_num}'


def print_transitions(objects):
    rooms_with_exits = {
        n: o for n, o in objects.items()
        if o["exits"]
    }

    print(f"Found {len(rooms_with_exits)} objects with direction exits\n")
    print("=" * 70)

    for obj_num in sorted(rooms_with_exits):
        obj = rooms_with_exits[obj_num]
        label = name_of(objects, obj_num)
        print(f"\nObject {label}")

        for exit in obj["exits"]:
            dir_str = exit["dir"].ljust(5)
            if exit["type"] == "direct":
                dest_label = name_of(objects, exit["dest"])
                print(f"  {dir_str} -> {dest_label}")
            elif exit["type"] == "conditional":
                dest_label = name_of(objects, exit["dest"])
                gate_label = name_of(objects, exit["gate_obj"])
                print(f"  {dir_str} -> {dest_label}  [if {gate_label} is {exit['gate_state']}]")
            elif exit["type"] == "conditional_global":
                dest_label = name_of(objects, exit["dest"])
                print(f"  {dir_str} -> {dest_label}  [if GLOBAL-{exit['gate_global']}]")
            elif exit["type"] == "routine":
                print(f"  {dir_str} -> (routine {exit['routine']})")


def export_mapview(objects, out_path: Path):
    """Write a map.txt compatible file for mapview.py.

    Format (tab-separated):
        #<from_id>: <from_name> TAB #<to_id>: <to_name> TAB <direction>

    Only direct and conditional exits are included (routine exits have no
    known destination without running the interpreter).
    """
    lines = []
    for obj_num, obj in sorted(objects.items()):
        from_name = obj.get("name") or f"Object {obj_num}"
        from_loc  = f"#{obj_num}: {from_name}"
        for exit in obj["exits"]:
            if exit["type"] not in ("direct", "conditional", "conditional_global"):
                continue
            dest     = exit["dest"]
            dest_obj = objects.get(dest, {})
            dest_name = dest_obj.get("name") or f"Object {dest}"
            to_loc    = f"#{dest}: {dest_name}"
            lines.append(f"{from_loc}\t{to_loc}\t{exit['dir']}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"mapview file written to: {out_path}  ({len(lines)} transitions)")


def export_edges(objects, out_path: Path):
    """Write a simple TSV: from_id, from_name, dir, to_id, to_name, condition"""
    rows = []
    for obj_num, obj in sorted(objects.items()):
        for exit in obj["exits"]:
            if exit["type"] == "direct":
                dest = exit["dest"]
                cond = ""
            elif exit["type"] == "conditional":
                dest = exit["dest"]
                gate = objects.get(exit["gate_obj"], {})
                gate_name = gate.get("name") or str(exit["gate_obj"])
                cond = f"if #{exit['gate_obj']} ({gate_name}) is {exit['gate_state']}"
            elif exit["type"] == "conditional_global":
                dest = exit["dest"]
                cond = f"if GLOBAL-{exit['gate_global']}"
            else:
                dest = ""
                cond = f"routine {exit['routine']}"

            dest_name = ""
            if dest:
                d = objects.get(dest, {})
                dest_name = d.get("name") or ""

            rows.append((
                obj_num,
                obj.get("name") or "",
                exit["dir"],
                dest,
                dest_name,
                cond,
            ))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("from_id\tfrom_name\tdirection\tto_id\tto_name\tcondition\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")

    print(f"\nEdge list written to: {out_path}")


if __name__ == "__main__":
    txt_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/TRINITY.txt")
    objects = parse(txt_path)
    print_transitions(objects)

    game_name = txt_path.stem.lower()   # "TRINITY" -> "trinity", "ZORK1" -> "zork1"

    tsv_path = txt_path.with_name(f"{game_name}_transitions.tsv")
    export_edges(objects, tsv_path)

    map_path = txt_path.with_name(f"{game_name}_map.txt")
    export_mapview(objects, map_path)
