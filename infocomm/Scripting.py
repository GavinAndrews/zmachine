class Scripting:
    def __init__(self, filename):
        with open(filename) as file:
            raw = [line.rstrip() for line in file]

        # If any line starts with '>' this is a transcript — only '>' lines are commands.
        # Otherwise every line is a command (plain command list).
        is_transcript = any(line.startswith('>') for line in raw)

        self.lines = []
        for line in raw:
            if line.startswith('> '):
                content = line[2:]
                if content.strip():            # skip '> ' with no real command
                    self.lines.append(content)
            elif line.startswith('>'):
                content = line[1:]
                if content.strip():            # skip bare '>' (game prompts)
                    self.lines.append(content)
            elif not is_transcript:
                self.lines.append(line)        # plain commands file

        self.current = 0

    def get_line(self):
        # Skip pure comment lines (## ...) but return everything else
        while self.current < len(self.lines):
            line = self.lines[self.current]
            self.current += 1
            if line.startswith('##'):
                continue
            return line
        return None                            # exhausted — fall through to interactive
