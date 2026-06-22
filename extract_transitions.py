"""
extract_transitions.py

Parses a Trinity disassembly text file (produced by e.g. TXD/infodump)
and extracts room-to-room transitions for the 12 compass directions.

Direction property numbers (52–63):
  52=OUT  53=IN   54=DOWN  55=UP
  56=NW   57=W    58=SW    59=S
  60=SE   61=E    62=NE    63=N

Exit property data comes in three forms:
  DIRECT:      (NORTH TO OBJECT-12)
  CONDITIONAL: (WEST TO OBJECT-297 IF OBJECT-128 IS OPEN)
  PER ROUTINE: (UP PER Routine at 0x24820)
  STRING:      (NORTH "You can only go up...")      <- blocked, ignored

Usage:
  python extract_transitions.py [path/to/TRINITY.txt]
"""

import re
import sys
from pathlib import Path

DIRECTION_PROPS = {
    52: "OUT", 53: "IN", 54: "DOWN", 55: "UP",
    56: "NW",  57: "W",  58: "SW",  59: "S",
    60: "SE",  61: "E",  62: "NE",  63: "N",
}

# Regex patterns for property lines
# e.g.   023AF 7F    00 0C                   63/2  (NORTH TO OBJECT-12)
RE_PROP = re.compile(
    r'^\s+[0-9A-F]{5}\s+'      # address
    r'[0-9A-F ]+\s+'           # hex bytes
    r'(\d+)/(\d+)\s+'          # prop_num/prop_size
    r'\((.+)\)$'               # (content)
)

RE_DIRECT      = re.compile(r'^(\w+) TO OBJECT-(\d+)$')
RE_CONDITIONAL = re.compile(r'^(\w+) TO OBJECT-(\d+) IF OBJECT-(\d+) IS (\w+)$')
RE_PER         = re.compile(r'^(\w+) PER Routine at (0x[0-9A-Fa-f]+)$')

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
                objects[current_obj]["name"] = m.group(1)
                continue

            m = RE_PROP.match(line)
            if not m:
                continue

            prop_num = int(m.group(1))
            content  = m.group(3).strip()

            if prop_num not in DIRECTION_PROPS:
                continue

            direction = DIRECTION_PROPS[prop_num]

            md = RE_DIRECT.match(content)
            if md:
                dest = int(md.group(2))
                objects[current_obj]["exits"].append({
                    "dir": direction, "type": "direct", "dest": dest,
                })
                continue

            mc = RE_CONDITIONAL.match(content)
            if mc:
                dest   = int(mc.group(2))
                gate   = int(mc.group(3))
                state  = mc.group(4)
                objects[current_obj]["exits"].append({
                    "dir": direction, "type": "conditional",
                    "dest": dest, "gate_obj": gate, "gate_state": state,
                })
                continue

            mp = RE_PER.match(content)
            if mp:
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
            if exit["type"] not in ("direct", "conditional"):
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

    tsv_path = txt_path.with_name("trinity_transitions.tsv")
    export_edges(objects, tsv_path)

    map_path = txt_path.with_name("trinity_map.txt")
    export_mapview(objects, map_path)
