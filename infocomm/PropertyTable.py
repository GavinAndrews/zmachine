from typing import Optional

from ZStrings import toZString
from infocomm.PropertyTableEntry import PropertyTableEntry
from array import array


class PropertyTable:
    def __init__(self, memory: array, start_location: int, abbreviations, game_version: int = 3):
        self.memory = memory
        self.start_location = start_location
        self.abbreviations = abbreviations
        self.game_version = game_version

    def _skip_description(self) -> int:
        """Returns the address of the first property entry (after the description string)."""
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        paddr += 2 * dlen + 1
        return paddr

    def description(self) -> str:
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        if dlen > 0:
            return toZString(paddr + 1, self.memory, self.abbreviations, dlen)
        else:
            return ""

    def dump_properties(self) -> None:
        paddr = self._skip_description()

        while True:
            n, l, header_size = PropertyTableEntry.decode_n_and_l(
                self.memory, paddr, self.game_version)
            if n == 0:
                break

            print(f"    {paddr:04X} {self.memory[paddr]:02X} ", end="")
            if header_size == 2:
                print(f"{self.memory[paddr + 1]:02X} ", end="")

            paddr += header_size
            for j in range(0, l):
                print(f"{self.memory[paddr]:02X} ", end="")
                paddr += 1

            space = " " * max(1, 32 - 3 * l)
            print(f"{space}{n:3}/{l}  (PROP#{n})")

    def find_first_property(self) -> Optional[PropertyTableEntry]:
        paddr = self._skip_description()

        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, paddr, self.game_version)

        if n != 0:
            return PropertyTableEntry(paddr, self.memory, self.game_version)
        else:
            return None

    def find_next_property(self, previous: PropertyTableEntry) -> Optional[PropertyTableEntry]:
        paddr = previous.get_address()

        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, paddr, self.game_version)

        # Advance past this property's header and data
        paddr += header_size + l

        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, paddr, self.game_version)

        if n != 0:
            return PropertyTableEntry(paddr, self.memory, self.game_version)
        else:
            return None

    def get_property_table_entry_for_property_number(self, property_number: int) -> Optional[PropertyTableEntry]:
        prop = self.find_first_property()
        while prop is not None:
            if prop.get_property_number() == property_number:
                return prop
            if prop.get_property_number() < property_number:
                return None
            prop = self.find_next_property(prop)
        return None

    def get_property_table_entry_after_property_number(self, property_number: int) -> Optional[PropertyTableEntry]:
        prop = self.find_first_property()
        if property_number == 0:
            return prop

        while prop is not None:
            if prop.get_property_number() == property_number:
                return self.find_next_property(prop)
            if prop.get_property_number() < property_number:
                return None
            prop = self.find_next_property(prop)
        return None

    def get_property_table_entry_address(self, property_number: int) -> Optional[int]:
        prop = self.get_property_table_entry_for_property_number(property_number)
        if prop is None:
            return None
        else:
            return prop.get_address()

    def get_description(self) -> str:
        return self.description()