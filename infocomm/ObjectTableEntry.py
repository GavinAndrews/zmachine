from array import array

from PropertyTable import PropertyTable
from Utils import Utils

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ObjectTable import ObjectTable


class ObjectTableEntry:
    def __init__(self, start_location: int, memory: array, entry_size: int,
                 abbreviations, n: int, object_table: 'ObjectTable',
                 game_version: int = 3) -> None:
        self.start_location = start_location
        self.memory = memory
        self.entry_size = entry_size
        self.abbreviations = abbreviations
        self.n = n
        self.object_table = object_table
        self.game_version = game_version

        if game_version <= 3:
            self._parent_offset = 4
            self._sibling_offset = 5
            self._child_offset = 6
            self._prop_offset = 7
            self._word_links = False
        else:
            self._parent_offset = 6
            self._sibling_offset = 8
            self._child_offset = 10
            self._prop_offset = 12
            self._word_links = True

    def get_parent_object_number(self) -> int:
        if self._word_links:
            return Utils.mread_word(self.memory, self.start_location + self._parent_offset)
        return int(self.memory[self.start_location + self._parent_offset])

    def set_parent_object_number(self, value: int) -> None:
        if self._word_links:
            Utils.mwrite_word(self.memory, self.start_location + self._parent_offset, value)
        else:
            self.memory[self.start_location + self._parent_offset] = value & 0xFF

    def get_next_sibling_object_number(self) -> int:
        if self._word_links:
            return Utils.mread_word(self.memory, self.start_location + self._sibling_offset)
        return int(self.memory[self.start_location + self._sibling_offset])

    def set_next_sibling_object_number(self, value: int) -> None:
        if self._word_links:
            Utils.mwrite_word(self.memory, self.start_location + self._sibling_offset, value)
        else:
            self.memory[self.start_location + self._sibling_offset] = value & 0xFF

    def get_child_object_number(self) -> int:
        if self._word_links:
            return Utils.mread_word(self.memory, self.start_location + self._child_offset)
        return int(self.memory[self.start_location + self._child_offset])

    def set_child_object_number(self, value: int) -> None:
        if self._word_links:
            Utils.mwrite_word(self.memory, self.start_location + self._child_offset, value)
        else:
            self.memory[self.start_location + self._child_offset] = value & 0xFF

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
        return Utils.mread_word(self.memory, self.start_location + self._prop_offset)

    def get_property_table(self) -> PropertyTable:
        return PropertyTable(self.memory, self.properties_address(),
                             self.abbreviations, self.game_version)

    def test_attr(self, attribute_number: int) -> int:
        attr_address = self.start_location + (attribute_number >> 3)
        attrs = self.memory[attr_address]
        return attrs & (0b10000000 >> (attribute_number & 0b111))

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
        return f"[{self.n}] {self.get_property_table().description()}"

    def unlink(self) -> None:
        parent_object_number = self.get_parent_object_number()
        if parent_object_number == 0:
            return

        parent = self.object_table.get_object_table_entry(parent_object_number)
        prior_sibling_object_number = self.get_prior_sibling_object_number()
        next_sibling_object_number = self.get_next_sibling_object_number()

        if prior_sibling_object_number != 0:
            prior_sibling = self.object_table.get_object_table_entry(prior_sibling_object_number)
            prior_sibling.set_next_sibling_object_number(self.get_next_sibling_object_number())
        else:
            if next_sibling_object_number != 0:
                parent.set_child_object_number(next_sibling_object_number)
            else:
                parent.set_child_object_number(0)

        self.set_parent_object_number(0)
        self.set_next_sibling_object_number(0)