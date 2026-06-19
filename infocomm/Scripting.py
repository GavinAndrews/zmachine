class Scripting:
    def __init__(self, filename):
        with open(filename) as file:
            raw = [line.rstrip() for line in file]

        self.lines = []
        for line in raw:
            if line.startswith('> '):
                self.lines.append(line[2:])   # transcript format: strip '> '
            elif line == '>':
                self.lines.append('')          # empty command
            else:
                self.lines.append(line)        # plain command or #meta-command

        self.current = 0

    def get_line(self):
        # Skip blank lines and pure comment lines (## ...) but return #commands
        while self.current < len(self.lines):
            line = self.lines[self.current]
            self.current += 1
            if line.startswith('##'):          # file-level comment, skip
                continue
            return line
        return None                            # exhausted — fall through to interactive
