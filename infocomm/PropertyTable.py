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

    def find(self, property_number):

        # Skip Description
        paddr = self.start_location
        dlen = int.from_bytes(self.memory[paddr:paddr + 1], 'big')
        paddr += 2 * dlen + 1

        found = False
        while True:
            prop = self.memory[paddr]

            # End of List
            if prop == 0:
                break

            n, l = PropertyTableEntry.decode_n_and_l(prop)

            if n == property_number:
                found = True
                break

            # Advance to next one
            paddr += 1
            paddr += l

        return PropertyTableEntry(paddr, self.memory) if found else None
