class PropertyEntry:
    def __init__(self, address, memory):
        self.address = address
        self.memory = memory

    def describe(self):
        description_length = int(self.memory[self.address])
        print(description_length)
        pass


