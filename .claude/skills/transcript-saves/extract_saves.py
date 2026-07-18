#!/usr/bin/env python3
"""Extract save (and optionally restore) events from an Infocomm interpreter
transcript, along with the location and the 5 preceding player commands.

Usage:
    python extract_saves.py <transcript_file> [--restores] [--json]

Prints a markdown table (or JSON with --json) to stdout. This does the
mechanical line-scanning so the caller doesn't have to page through a
multi-thousand-line transcript by hand; edge cases (teleport-only saves,
notes, table title) still need human review before writing the final file.
"""
import argparse
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

LOCATION_RE = re.compile(r"^\[Obj#\d+:\s*(.+?)\]\s*$")
# Some transcripts prefix the prompt with a bracketed system message, e.g.
# "[Type RESTART, RESTORE or QUIT.] >restore" or "[Please type YES or NO.] >no".
PROMPT_RE = re.compile(r"^(?:\[.*?\]\s*)?>\s*(.*?)\s*$")
# Fallback location footer: transcripts without `[Obj#...]` tags instead echo
# the bare room name on its own line immediately before the next prompt
# (e.g. "Bottom of Stairs" / "                The River"). Room names are
# short, start with a capital letter, and carry no sentence punctuation —
# unlike ordinary game-text lines, which is how this is told apart from prose.
FOOTER_RE = re.compile(r"^\s*[A-Z][A-Za-z0-9' ]{0,38}$")


def parse_transcript(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    events = []  # dict: kind, filename, ok, location, prev_commands
    history = []  # list of dicts: text, kind ('save'/'restore'/None), filename
    current_location = None

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip("\n")

        loc_match = LOCATION_RE.match(line)
        if loc_match:
            current_location = loc_match.group(1).strip()
            i += 1
            continue

        prompt_match = PROMPT_RE.match(line)
        if prompt_match and prompt_match.group(1).strip():
            command = prompt_match.group(1).strip()
            lc = command.lower()

            # No [Obj#...] tag directly above this prompt (or none in this
            # transcript at all) — fall back to the footer-line heuristic.
            if i > 0:
                prev_line = lines[i - 1].rstrip("\n")
                if prev_line.strip() and FOOTER_RE.match(prev_line) and not PROMPT_RE.match(prev_line):
                    current_location = prev_line.strip()

            if lc == "save" or lc == "restore":
                kind = lc
                # Look ahead for "Save/Restore to/from file:" then the
                # filename prompt line, then the completion marker.
                filename = None
                ok = False
                j = i + 1
                # skip the "Save to file:"/"Restore from file:" line
                if j < n and re.search(r"(Save to file|Restore from file):", lines[j]):
                    j += 1
                    fn_match = PROMPT_RE.match(lines[j].rstrip("\n")) if j < n else None
                    if fn_match:
                        filename = fn_match.group(1).strip()
                        j += 1
                    # scan a few lines ahead for the completion/failure marker
                    for k in range(j, min(j + 5, n)):
                        if kind == "save" and "[SAVE completed.]" in lines[k]:
                            ok = True
                            break
                        if kind == "restore" and "[RESTORE completed.]" in lines[k]:
                            ok = True
                            break
                        if "File not found" in lines[k] or "failed" in lines[k].lower():
                            break

                if ok:
                    prev_commands = [
                        h["annotated"] for h in history[-5:]
                    ]
                    events.append({
                        "kind": kind,
                        "filename": filename,
                        "location": current_location,
                        "prev_commands": prev_commands,
                    })
                    short_name = re.sub(r"\.sav$", "", filename, flags=re.IGNORECASE) if filename else filename
                    annotated = f"{kind} (→{short_name})"
                else:
                    annotated = command

                history.append({"text": command, "kind": kind, "filename": filename, "annotated": annotated})
                # skip past the lines consumed by the lookahead (filename
                # prompt, completion/failure marker) so they aren't
                # re-parsed as ordinary player commands.
                i = j
                continue
            else:
                history.append({"text": command, "kind": None, "filename": None, "annotated": command})

        i += 1

    return events


def to_markdown(events, include_restores):
    seen_save_files = set()
    rows = []
    idx = 0
    for ev in events:
        if ev["kind"] == "restore" and not include_restores:
            continue
        idx += 1
        filename = ev["filename"] or "?"
        label = filename
        if ev["kind"] == "save":
            if filename in seen_save_files:
                label = f"{filename} (overwrite)"
            else:
                seen_save_files.add(filename)
        if ev["kind"] == "restore":
            label = f"{filename} (restore)"
        prev = ", ".join(ev["prev_commands"]) if ev["prev_commands"] else "(start of transcript)"
        rows.append((idx, label, ev["location"] or "?", prev))

    lines = ["| # | Save File | Location | Previous 5 Commands |", "|---|-----------|----------|----------------------|"]
    for idx, label, loc, prev in rows:
        lines.append(f"| {idx} | {label} | {loc} | {prev} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", help="path to transcript file")
    parser.add_argument("--restores", action="store_true", help="include restore events in the table")
    parser.add_argument("--json", action="store_true", help="print raw JSON instead of a markdown table")
    args = parser.parse_args()

    events = parse_transcript(args.transcript)
    if not args.restores:
        events_for_output = [e for e in events if e["kind"] == "save"]
    else:
        events_for_output = events

    if args.json:
        json.dump(events_for_output, sys.stdout, indent=2)
        print()
    else:
        print(to_markdown(events, args.restores))


if __name__ == "__main__":
    main()
