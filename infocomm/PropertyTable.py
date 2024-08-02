from infocomm.PropertyEntry import PropertyEntry
class PropertyTable:
    def __init__(self, memory):
        self.memory = memory

    def find(self, address):
        return PropertyEntry(address, self.memory)



