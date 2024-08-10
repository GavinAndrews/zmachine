from PropertyTable import PropertyTable


class ObjectTableEntry(object):
    def __init__(self, start_location, memory, entry_size, abbreviations):
        self.start_location = start_location
        self.memory = memory
        self.entry_size = entry_size
        self.abbreviations = abbreviations

    def properties_address(self):
        # Last two bytes of Object Table Entry is pointer to properties
        return int.from_bytes(self.memory[self.start_location + self.entry_size - 2
                                          : self.start_location + self.entry_size - 2 + 2],
                              'big')

    def get_property_table_entry(self, property_number):
        ptable = PropertyTable(self.memory, self.properties_address(), self.abbreviations)
        return ptable.find(property_number)
