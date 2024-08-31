class TraceFile:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'r')
        self.lines = self.file.readlines()
        self.index = 0

    def read(self):
        if self.index < len(self.lines):
            line = self.lines[self.index]
            self.index += 1
            return line
        else:
            return None

    def close(self):
        self.file.close()