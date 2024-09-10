from array import array

from PropertyTable import PropertyTable
import ObjectTable


class ObjectTableEntry:
    def __init__(self, start_location: int, memory: array, entry_size: int, abbreviations: int, n: int,
                 object_table: ObjectTable) -> None:
        self.start_location = start_location
        self.memory = memory
        self.entry_size = entry_size
        self.abbreviations = abbreviations
        self.n = n
        self.object_table = object_table

    def get_parent_object_number(self):
        return int(self.memory[self.start_location + 4])

    def set_parent_object_number(self, value) -> None:
        self.memory[self.start_location + 4] = value & 0xFF

    def get_next_sibling_object_number(self) -> int:
        return int(self.memory[self.start_location + 5])

    def set_next_sibling_object_number(self, value) -> None:
        self.memory[self.start_location + 5] = value & 0xFF

    def get_child_object_number(self) -> int:
        return int(self.memory[self.start_location + 6])

    def set_child_object_number(self, value) -> None:
        self.memory[self.start_location + 6] = value & 0xFF

    def get_prior_sibling_object_number(self) -> int:
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

    def properties_address(self) -> int:
        # Last two bytes of Object Table Entry is pointer to properties
        return int.from_bytes(self.memory[self.start_location + self.entry_size - 2
                                          : self.start_location + self.entry_size - 2 + 2],
                              'big')

    def get_property_table(self) -> PropertyTable:
        return PropertyTable(self.memory, self.properties_address(), self.abbreviations)

    def test_attr(self, attribute_number: int) -> int:
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        result = attrs & (0b10000000 >> (attribute_number & 0b111))
        return result

    def set_attr(self, attribute_number: int) -> None:
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        attrs = attrs | (0b10000000 >> (attribute_number & 0b111))
        self.memory[attr_address] = attrs

    def clear_attr(self, attribute_number: int) -> None:
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        attrs = attrs & (~(0b10000000 >> (attribute_number & 0b111)) & 0xFF)
        self.memory[attr_address] = attrs

    def describe(self) -> str:
        return f"[{self.n}] {self.get_description()}"

    def unlink(self) -> None:
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
            else:
                parent.set_child_object_number(0)

        self.set_parent_object_number(0)
        self.set_next_sibling_object_number(0)
