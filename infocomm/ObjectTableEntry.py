from PropertyTable import PropertyTable


class ObjectTableEntry(object):
    def __init__(self, start_location, memory, entry_size, abbreviations, n, object_table):
        self.start_location = start_location
        self.memory = memory
        self.entry_size = entry_size
        self.abbreviations = abbreviations
        self.n = n
        self.object_table = object_table

    def get_parent_object_number(self):
        return int(self.memory[self.start_location + 4])

    def set_parent_object_number(self, value):
        self.memory[self.start_location + 4] = value & 0xFF

    def get_next_sibling_object_number(self):
        return int(self.memory[self.start_location + 5])

    def set_next_sibling_object_number(self, value):
        self.memory[self.start_location + 5] = value & 0xFF

    def get_child_object_number(self):
        return int(self.memory[self.start_location + 6])

    def set_child_object_number(self, value):
        self.memory[self.start_location + 6] = value & 0xFF

    def get_prior_sibling_object_number(self):
        parent_object_number = self.get_parent_object_number()
        if parent_object_number == 0:
            return 0
        parent = self.object_table.get_object_table_entry(parent_object_number)
        prior_sibling_object_number = 0
        sibling_object_number = parent.get_child_object_number()
        while sibling_object_number != self.n:
            prior_sibling_object_number = sibling_object_number
            sibling = self.object_table.get_object_table_entry(sibling_object_number)
            sibling_object_number = sibling.get_next_sibling_object_number()
        return prior_sibling_object_number

    def properties_address(self):
        # Last two bytes of Object Table Entry is pointer to properties
        return int.from_bytes(self.memory[self.start_location + self.entry_size - 2
                                          : self.start_location + self.entry_size - 2 + 2],
                              'big')

    def get_property_table_entry(self, property_number):
        ptable = PropertyTable(self.memory, self.properties_address(), self.abbreviations)
        return ptable.find(property_number)

    def get_property_table_entry_value(self, property_number):
        ptable = PropertyTable(self.memory, self.properties_address(), self.abbreviations)
        property_entry = ptable.find(property_number)
        if property_entry is None:
            return self.object_table.get_property_default(property_number)
        else:
            return property_entry.get_value()

    def test_attr(self, attribute_number):
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        result = attrs & (0b1000000 >> (attribute_number & 0b111))
        return result

    def set_attr(self, attribute_number):
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        attrs = attrs | (0b1000000 >> (attribute_number & 0b111))
        self.memory[attr_address] = attrs

    def clear_attr(self, attribute_number):
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        attrs = attrs & (~(0b1000000 >> (attribute_number & 0b111)) & 0xFF)
        self.memory[attr_address] = attrs

    def get_description(self):
        ptable = PropertyTable(self.memory, self.properties_address(), self.abbreviations)
        return ptable.description()

    def describe(self):
        return f"[{self.n}] {self.get_description()}"

    def unlink(self):
        # If we have no parent... then we are not linked it so nothing to do...
        parent_object_number = self.get_parent_object_number()
        parent = self.object_table.get_object_table_entry(parent_object_number)
        if parent_object_number == 0:
            return
        # We have a few things to do...
        # Unlink ourselves from parent child chain... first find if we have a younger sibling...
        prior_sibbling_object_number = self.get_prior_sibling_object_number()
        next_sibling_object_number = self.get_next_sibling_object_number()

        if prior_sibbling_object_number != 0:
            prior_sibbling = self.object_table.get_object_table_entry(prior_sibbling_object_number)
            prior_sibbling.set_next_sibling_object_number(self.get_next_sibling_object_number())
        else:
            if next_sibling_object_number != 0:
                parent.set_child_object_number(next_sibling_object_number)

        self.set_parent_object_number(0)
        self.set_next_sibling_object_number(0)
