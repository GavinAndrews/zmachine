from ZStrings import toZString
from infocomm.PropertyTableEntry import PropertyTableEntry


class PropertyTable:
    def __init__(self, memory, start_location, abbreviations):
        self.memory = memory
        self.start_location = start_location
        self.abbreviations = abbreviations

    def description(self):
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        if dlen > 0:
            s = toZString(paddr + 1, self.memory, self.abbreviations, dlen)
            return s
        else:
            return ""

    def dump_properties(self):

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

    def find(self, property_number, search_next=False):

        # Skip Description
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        paddr += 2 * dlen + 1

        found = False
        at_end_of_list = False

        while True:
            prop = self.memory[paddr]

            n, l = PropertyTableEntry.decode_n_and_l(prop)

            if n == property_number or (search_next and property_number == 0):
                found = True
                at_end_of_list = n == 0
                break

            if n < property_number:  # End of list or a property with a lower number
                break

            # Advance to next one
            paddr += 1
            paddr += l

        if search_next and property_number != 0 and found:
            paddr += 1
            paddr += l
            prop = self.memory[paddr]
            if prop == 0:
                return None

        return PropertyTableEntry(paddr, self.memory) if found else None
