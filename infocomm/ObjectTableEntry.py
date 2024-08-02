from infocomm.AbbreviationTable import toZString


class ObjectTableEntry(object):
    def __init__(self, start_location, memory, entry_size, abbreviations):
        self.start_location = start_location
        self.memory = memory
        self.entry_size = entry_size
        self.abbreviations = abbreviations

    def property_address(self):
        return int.from_bytes(self.memory[self.start_location + self.entry_size - 2
                                          : self.start_location + self.entry_size - 2 + 2],
                              'big')


    def description(self):
        paddr = self.property_address()
        dlen = int.from_bytes(self.memory[paddr:paddr+1], 'big')
        if dlen>0:
            s = toZString(paddr+1, self.memory, self.abbreviations, dlen)
            return s
        else:
            return ""

    def dump_properties(self):
        paddr = self.property_address()
        dlen = int.from_bytes(self.memory[paddr:paddr+1], 'big')
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
            space = " " * (32 - 3*l)
            print(f"{space }{n:3}/{l}  (PROP#{n})")
