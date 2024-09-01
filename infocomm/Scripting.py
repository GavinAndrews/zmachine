class Scripting:
    def __init__(self):
        filename = "../script"
        with open(filename) as file:
            self.lines = [line.rstrip() for line in file]
        self.current = 0

    def get_line(self):
        if self.current<len(self.lines):
            line = self.lines[self.current]
            self.current += 1
            return line
        else:
            return None

