from typing import Optional

from ZStrings import toZString
from infocomm.PropertyTableEntry import PropertyTableEntry
from array import array


class PropertyTable:
    def __init__(self, memory: array, start_location: int, abbreviations: int):
        self.memory = memory
        self.start_location = start_location
        self.abbreviations = abbreviations

    def description(self) -> str:
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        if dlen > 0:
            s = toZString(paddr + 1, self.memory, self.abbreviations, dlen)
            return s
        else:
            return ""

    def dump_properties(self) -> None:

        # Skip Description
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        paddr += 2 * dlen + 1

        while True:
            prop = self.memory[paddr]
            if prop == 0:
                break

            print(f"    {paddr:04X} {prop:02X} ", end="")

            l = (prop >> 5) + 1
            n = prop & 0x1F

            paddr += 1
            for j in range(0, l):
                print(f"{self.memory[paddr]:02X} ", end="")
                paddr += 1
            space = " " * (32 - 3 * l)
            print(f"{space}{n:3}/{l}  (PROP#{n})")

    def find_first_property(self) -> Optional[PropertyTableEntry]:

        # Skip Description
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        paddr += 2 * dlen + 1

        prop = self.memory[paddr]

        n, l = PropertyTableEntry.decode_n_and_l(prop)

        if n != 0:
            return PropertyTableEntry(paddr, self.memory)
        else:
            return None

    def find_next_property(self, previous:PropertyTableEntry)-> Optional[PropertyTableEntry]:

        paddr = previous.get_address()

        # Advance to next one
        n, l = PropertyTableEntry.decode_n_and_l(self.memory[paddr])
        paddr += 1
        paddr += l

        prop = self.memory[paddr]

        n, l = PropertyTableEntry.decode_n_and_l(prop)
        if n != 0:
            return PropertyTableEntry(paddr, self.memory)
        else:
            return None

    def get_property_table_entry_for_property_number(self, property_number: int) -> Optional[PropertyTableEntry]:

        property = self.find_first_property()
        while property is not None:
            if property.get_property_number() == property_number:
                return property
            if property.get_property_number() < property_number:
                return None
            property = self.find_next_property(property)

        return None

    def get_property_table_entry_after_property_number(self, property_number: int) -> Optional[PropertyTableEntry]:
        property = self.find_first_property()
        if property_number == 0:
            return property

        while property is not None:
            if property.get_property_number() == property_number:
                return self.find_next_property(property)
            if property.get_property_number() < property_number:
                return None
            property = self.find_next_property(property)

        return None

    def get_property_table_entry_address(self, property_number) -> Optional[int]:
        property_entry = self.get_property_table_entry_for_property_number(property_number)
        if property_entry is None:
            return None
        else:
            return property_entry.get_address()

    def get_description(self) -> str:
        return self.description()
