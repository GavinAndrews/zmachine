"""
analyze_routines.py

Second-pass analysis of Trinity direction routines.

For every "PER Routine" exit in trinity_transitions.tsv, finds the routine
body in TRINITY.txt and performs a linear-scan analysis to extract:
  - what room object numbers the routine can return (destinations)
  - what branch conditions (TEST_ATTR, JZ, JE, JIN …) guard those returns

Classifications:
  BLOCKER     — always returns false / prints a message and fails
  MOVER       — returns exactly one room (unconditional navigation)
  CONDITIONAL — returns different rooms depending on game state
  COMPLEX     — delegates to sub-routines or returns via stack/globals

Usage:
  python analyze_routines.py [data/TRINITY.txt] [data/trinity_transitions.tsv]
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


# ── 1. Parse TRINITY.txt ──────────────────────────────────────────────────────

def parse_trinity_txt(path):
    """
    Returns:
        obj_names : {int: str}          object id → short name
        routines  : {int: [str, ...]}   routine addr → raw body lines
    """
    obj_names = {}
    routines = {}
    current_obj = None
    current_routine = None

    RE_OBJ     = re.compile(r'^Object: (\d+)$')
    RE_DESC    = re.compile(r'^\s+Description = "(.+)"$')
    RE_ROUTINE = re.compile(r'^Routine: (0x[0-9A-Fa-f]+)')
    # Instruction start: flush-left 5-hex-digit address
    RE_INSTR   = re.compile(r'^[0-9A-Fa-f]{5} ')
    # Continuation: 6 leading spaces then a hex digit
    RE_CONT    = re.compile(r'^      [0-9A-Fa-f]')

    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip()

            m = RE_OBJ.match(line)
            if m:
                current_obj = int(m.group(1))
                continue

            m = RE_DESC.match(line)
            if m and current_obj is not None:
                # Strip Inform/ZIL abbreviation markers: {word} → word
                name = re.sub(r'\{([^}]*)\}', r'\1', m.group(1))
                obj_names[current_obj] = name
                current_obj = None
                continue

            m = RE_ROUTINE.match(line)
            if m:
                current_routine = int(m.group(1), 16)
                routines[current_routine] = []
                continue

            if current_routine is not None:
                if RE_INSTR.match(line) or RE_CONT.match(line):
                    routines[current_routine].append(line)

    return obj_names, routines


# ── 2. Load unresolved entries from TSV ───────────────────────────────────────

def load_tsv_routines(tsv_path):
    """
    Returns list of (from_id, from_name, direction, routine_addr_int)
    for every row whose 'condition' column starts with 'routine 0x…'.
    """
    entries = []
    with open(tsv_path, encoding='utf-8') as f:
        next(f)                        # skip header
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 6:
                continue
            from_id, from_name, direction, to_id, to_name, condition = parts[:6]
            if condition.startswith('routine 0x'):
                addr_str = condition.split()[1]
                try:
                    entries.append((int(from_id), from_name, direction,
                                    int(addr_str, 16)))
                except ValueError:
                    pass
    return entries


# ── 3. Analyse a single routine ───────────────────────────────────────────────

def _obj_label(obj_names, ref):
    """Turn 'OBJECT26' → '#26 (left door)' using the object table."""
    m = re.match(r'OBJECT(\d+)', ref)
    if m:
        n = int(m.group(1))
        name = obj_names.get(n, '')
        return f'#{n} ({name})' if name else f'#{n}'
    return ref


def analyze_routine(addr, lines, obj_names):
    """
    Linear-scan analysis of a routine's body lines.

    Returns a dict:
        classification : str
        returns        : set of int  (all observed return values)
        destinations   : set of int  (return values > 1, likely room IDs)
        conditions     : [str]       (human-readable branch descriptions)
        locals         : {str: set of int}
        calls          : [str]       (called routine hex strings)
    """
    returns     = set()
    conditions  = []
    locals_vals = defaultdict(set)   # 'L00' -> {460, 442, …}
    calls       = []
    push_lits   = []                 # stack of literal values from PUSH 0xNNN

    for line in lines:

        # ── TEST_ATTR obj attr [SENSE] target ─────────────────────────────
        m = re.search(
            r'TEST_ATTR\s+(\S+)\s+(ATTRIBUTE\d+)\s+\[(TRUE|FALSE)\]\s+(\S+)',
            line)
        if m:
            obj_ref, attr, sense, target = m.groups()
            label = _obj_label(obj_names, obj_ref)
            not_pfx = 'NOT ' if sense == 'FALSE' else ''
            conditions.append(
                f'if {not_pfx}{label} has {attr}  →jump {target}')

        # ── JZ var [SENSE] target ─────────────────────────────────────────
        m = re.search(r'\bJZ\s+(\S+)\s+\[(TRUE|FALSE)\]\s+(\S+)', line)
        if m:
            var, sense, target = m.groups()
            zero_w = 'nonzero' if sense == 'FALSE' else 'zero'
            conditions.append(f'if {var} is {zero_w}  →jump {target}')

        # ── JE v1 v2 [SENSE] target ───────────────────────────────────────
        m = re.search(
            r'\bJE\s+(\S+)\s+(\S+)\s+\[(TRUE|FALSE)\]\s+(\S+)', line)
        if m:
            v1, v2, sense, target = m.groups()
            eq_w = 'not equal' if sense == 'FALSE' else 'equal'
            conditions.append(f'if {v1} {eq_w} {v2}  →jump {target}')

        # ── JL / JG / JLE / JGE ──────────────────────────────────────────
        m = re.search(
            r'\b(JL|JG|JLE|JGE)\s+(\S+)\s+(\S+)\s+\[(TRUE|FALSE)\]\s+(\S+)',
            line)
        if m:
            op, v1, v2, sense, target = m.groups()
            not_pfx = 'NOT ' if sense == 'FALSE' else ''
            conditions.append(f'if {not_pfx}{op}({v1}, {v2})  →jump {target}')

        # ── JIN obj1 obj2 [SENSE] target ──────────────────────────────────
        m = re.search(
            r'\bJIN\s+(\S+)\s+(\S+)\s+\[(TRUE|FALSE)\]\s+(\S+)', line)
        if m:
            o1, o2, sense, target = m.groups()
            in_w = 'not inside' if sense == 'FALSE' else 'inside'
            l1 = _obj_label(obj_names, o1)
            l2 = _obj_label(obj_names, o2)
            conditions.append(f'if {l1} is {in_w} {l2}  →jump {target}')

        # ── PUSH immediate (stack literal — may feed STORE L00 (SP)+) ─────
        m = re.search(r'\bPUSH\s+(0x[0-9A-Fa-f]+|\d+)\b', line)
        if m:
            val = m.group(1)
            push_lits.append(
                int(val, 16) if val.startswith('0x') else int(val))

        # ── STORE local, immediate value ──────────────────────────────────
        m = re.search(r'\bSTORE\s+(L\d+)\s+(0x[0-9A-Fa-f]+|\d+)\b', line)
        if m:
            local, val = m.groups()
            val_int = int(val, 16) if val.startswith('0x') else int(val)
            locals_vals[local].add(val_int)

        # ── STORE local, (SP)+ — pop stack top into local ─────────────────
        m = re.search(r'\bSTORE\s+(L\d+)\s+\(SP\)\+', line)
        if m:
            local = m.group(1)
            for lit in push_lits:
                locals_vals[local].add(lit)
            push_lits.clear()

        # ── RET (unified: hex, decimal, local, global) ────────────────────
        m = re.search(r'\bRET\s+(\S+)', line)
        if m:
            operand = m.group(1)
            if re.match(r'^0x[0-9A-Fa-f]+$', operand):
                returns.add(int(operand, 16))
            elif re.match(r'^-?\d+$', operand):
                returns.add(int(operand))
            elif re.match(r'^L\d+$', operand):
                stored = locals_vals.get(operand, set())
                if stored:
                    returns.update(stored)
                else:
                    returns.add(-1)          # local not yet tracked
            elif re.match(r'^G[0-9A-Fa-f]{2}$', operand, re.I):
                returns.add(-1)              # global — hard to trace statically

        # ── RTRUE / RFALSE ────────────────────────────────────────────────
        if re.search(r'\bRTRUE\b', line):
            returns.add(1)
        if re.search(r'\bRFALSE\b', line):
            returns.add(0)

        # ── RET_POPPED (returns whatever's on the stack) ──────────────────
        if re.search(r'\bRET_POPPED\b', line):
            returns.add(-2)

        # ── CALL_* → record callee ────────────────────────────────────────
        m = re.search(r'\bCALL_\w+\s+(0x[0-9A-Fa-f]+)', line)
        if m:
            calls.append(m.group(1))

    # Room destinations: values > 1 (not false/true)
    destinations = {v for v in returns if v > 1}

    # Classify
    has_unknown = (-1 in returns) or (-2 in returns)

    if not returns:
        cls = 'COMPLEX'
    elif returns <= {0}:
        cls = 'BLOCKER'
    elif returns <= {0, 1} and not has_unknown:
        cls = 'BLOCKER'
    elif destinations and conditions:
        cls = 'CONDITIONAL'
    elif destinations and len(destinations) == 1:
        cls = 'MOVER'
    elif destinations:
        # Multiple destinations but no conditions found — probably complex
        # branching we can't track linearly
        cls = 'CONDITIONAL'
    elif has_unknown:
        cls = 'COMPLEX'
    else:
        cls = 'BLOCKER'

    return {
        'classification': cls,
        'returns':        returns,
        'destinations':   destinations,
        'conditions':     conditions,
        'locals':         dict(locals_vals),
        'calls':          calls,
    }


# ── 4. Main ───────────────────────────────────────────────────────────────────

def _dest_label(obj_names, obj_id):
    name = obj_names.get(obj_id, '?')
    return f'#{obj_id} ({name})'


def main():
    txt_path = (Path(sys.argv[1]) if len(sys.argv) > 1
                else Path('data/TRINITY.txt'))
    tsv_path = (Path(sys.argv[2]) if len(sys.argv) > 2
                else Path('data/trinity_transitions.tsv'))
    out_txt = txt_path.with_name('trinity_routine_analysis.txt')
    out_tsv = txt_path.with_name('trinity_conditional_transitions.tsv')

    print(f'Parsing {txt_path} …')
    obj_names, routines = parse_trinity_txt(txt_path)
    print(f'  {len(obj_names):,} objects, {len(routines):,} routines found')

    print(f'Loading {tsv_path} …')
    unresolved = load_tsv_routines(tsv_path)
    print(f'  {len(unresolved)} unresolved routine exits')

    by_routine = defaultdict(list)
    for from_id, from_name, direction, addr in unresolved:
        by_routine[addr].append((from_id, from_name, direction))
    print(f'  {len(by_routine)} unique routine addresses')

    # Analyse
    results = {}
    missing = []
    for addr in sorted(by_routine.keys()):
        body = routines.get(addr)
        if not body:
            missing.append(addr)
            results[addr] = {
                'classification': 'COMPLEX',
                'returns': set(), 'destinations': set(),
                'conditions': [], 'locals': {}, 'calls': [],
            }
        else:
            results[addr] = analyze_routine(addr, body, obj_names)

    counts = defaultdict(int)
    for r in results.values():
        counts[r['classification']] += 1

    # ── Text report ───────────────────────────────────────────────────────────
    out_lines = []

    def W(*args):
        out_lines.append(' '.join(str(a) for a in args))

    W('Trinity Direction Routine Analysis')
    W('=' * 70)
    W(f'Analysed {len(results)} unique routines '
      f'({len(unresolved)} total unresolved exits)')
    if missing:
        W(f'  {len(missing)} routine bodies not found in disassembly '
          f'(marked COMPLEX)')
    W()
    W('Classifications:')
    for cls in ('CONDITIONAL', 'MOVER', 'BLOCKER', 'COMPLEX'):
        W(f'  {cls:12s} {counts[cls]}')
    W()

    for cls_filter in ('CONDITIONAL', 'MOVER', 'COMPLEX', 'BLOCKER'):
        section = []
        for addr in sorted(by_routine.keys()):
            r = results[addr]
            if r['classification'] != cls_filter:
                continue

            callers  = by_routine[addr]
            dests    = r['destinations']
            dest_str = ', '.join(_dest_label(obj_names, d)
                                 for d in sorted(dests))

            section.append('')
            section.append(f'Routine 0x{addr:05X}  [{cls_filter}]')

            if addr in missing:
                section.append('  !! Body not found in disassembly')

            section.append('  Used by:')
            for from_id, from_name, direction in sorted(callers,
                                                         key=lambda x: x[0]):
                section.append(f'    #{from_id} {from_name} / {direction}')

            if dests:
                section.append(f'  Destinations: {dest_str}')

            if r['conditions']:
                section.append('  Conditions:')
                for c in r['conditions']:
                    section.append(f'    {c}')

            if r['locals']:
                for lname, vals in sorted(r['locals'].items()):
                    named = ', '.join(
                        f'{v} ({obj_names.get(v, "?")})' for v in sorted(vals))
                    section.append(f'  {lname} set to: {named}')

            if r['calls']:
                section.append(f'  Calls: {", ".join(r["calls"])}')

            flags = []
            if -1 in r['returns']:
                flags.append('returns-via-global/untracked-local')
            if -2 in r['returns']:
                flags.append('returns-stack-result')
            if flags:
                section.append(f'  Flags: {", ".join(flags)}')

        if section:
            W()
            W('=' * 70)
            W(cls_filter + ' ROUTINES')
            W('=' * 70)
            out_lines.extend(section)

    report = '\n'.join(out_lines)
    out_txt.write_text(report, encoding='utf-8')
    print(f'\nReport  -> {out_txt}')

    # ── Enhanced conditional TSV ──────────────────────────────────────────────
    # Emit a new TSV with resolved destinations for MOVER and CONDITIONAL routines
    new_rows = []
    for from_id, from_name, direction, addr in unresolved:
        r = results[addr]
        cls = r['classification']
        if cls not in ('CONDITIONAL', 'MOVER'):
            continue
        for dest in sorted(r['destinations']):
            dest_name = obj_names.get(dest, '')
            cond_parts = [f'via routine 0x{addr:05X}']
            if r['conditions']:
                # Abbreviated: first two conditions
                cond_parts.append('; '.join(r['conditions'][:2]))
            new_rows.append((from_id, from_name, direction,
                             dest, dest_name, ' | '.join(cond_parts)))

    with open(out_tsv, 'w', encoding='utf-8') as f:
        f.write('from_id\tfrom_name\tdirection\tto_id\tto_name\tcondition\n')
        for row in new_rows:
            f.write('\t'.join(str(x) for x in row) + '\n')
    print(f'Cond TSV -> {out_tsv}  ({len(new_rows)} rows)')

    print()
    print('Summary:')
    print(f'  CONDITIONAL  {counts["CONDITIONAL"]:3d}  routines with state-dependent destinations')
    print(f'  MOVER        {counts["MOVER"]:3d}  routines with single unconditional destination')
    print(f'  BLOCKER      {counts["BLOCKER"]:3d}  routines that always block movement')
    print(f'  COMPLEX      {counts["COMPLEX"]:3d}  routines needing deeper / recursive analysis')


if __name__ == '__main__':
    main()
