class ObjectTable:
    def __init__(self, start_location, memory):
        self.object_start_location = start_location + 31 * 2
        self.memory = memory

        self.object_count = self.determine_extent()
        print(f"{self.object_count}")

    # Object Table ends when we reach an address that has been referred to as a property table
    # so loop through them all and find the lowest property address and quit before we reach it!
    def determine_extent(self):
        object_entry_size = 9

        start = self.object_start_location
        done = False
        lowest_prop_address = None
        n = 0

        while not done:
            prop_address = int.from_bytes(self.memory[start+object_entry_size-2:start+object_entry_size-2+2], 'big')
            if lowest_prop_address is None or prop_address < lowest_prop_address:
                lowest_prop_address = prop_address
            start += object_entry_size
            if start >= lowest_prop_address:
                done = True
            n += 1

        return n






