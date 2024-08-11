from PropertyTable import PropertyTable


class ObjectTableEntry(object):
    def __init__(self, start_location, memory, entry_size, abbreviations, n):
        self.start_location = start_location
        self.memory = memory
        self.entry_size = entry_size
        self.abbreviations = abbreviations
        self.n = n

    def properties_address(self):
        # Last two bytes of Object Table Entry is pointer to properties
        return int.from_bytes(self.memory[self.start_location + self.entry_size - 2
                                          : self.start_location + self.entry_size - 2 + 2],
                              'big')

    def get_property_table_entry(self, property_number):
        ptable = PropertyTable(self.memory, self.properties_address(), self.abbreviations)
        return ptable.find(property_number)

    def test_attr(self, attribute_number):
        attr_address = self.start_location+(attribute_number >> 3)
        attrs = self.memory[attr_address]
        result = attrs & (0b1000000 >> (attribute_number & 0b111))
        return result

    def describe(self):
        ptable = PropertyTable(self.memory, self.properties_address(), self.abbreviations)
        print(f"[{self.n}] {ptable.description()}")