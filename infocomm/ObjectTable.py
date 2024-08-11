from infocomm.ObjectTableEntry import ObjectTableEntry


class ObjectTable:
    object_entry_size = 9

    def __init__(self, start_location, memory, abbreviations):
        self.object_start_location = start_location + 31 * 2
        self.memory = memory
        self.abbreviations = abbreviations

        self.object_count = self.determine_extent()
        print(f"{self.object_count}")

    # Object Table ends when we reach an address that has been referred to as a property table
    # so loop through them all and find the lowest property address and quit before we reach it!
    def determine_extent(self):

        start = self.object_start_location
        done = False
        lowest_prop_address = None
        n = 0

        while not done:
            prop_address = int.from_bytes(self.memory[start + ObjectTable.object_entry_size - 2:
                                                      start + ObjectTable.object_entry_size - 2 + 2],
                                          'big')
            if lowest_prop_address is None or prop_address < lowest_prop_address:
                lowest_prop_address = prop_address
            start += self.object_entry_size
            if start >= lowest_prop_address:
                done = True
            n += 1

        return n

    def get_object_table_entry(self, n):
        if n == 0:
            return None
        else:
            return ObjectTableEntry(self.object_start_location + (n - 1) * self.object_entry_size, self.memory,
                                    self.object_entry_size, self.abbreviations, n, self)

    def get_property_table_entry(self, object_number, property_number):
        object_table_entry = self.get_object_table_entry(object_number)
        return object_table_entry.get_property_table_entry(property_number)

    def insert_object(self, moving_object, destination_object):
        moving_object_table_entry = self.get_object_table_entry(moving_object)
        destination_object_table_entry = self.get_object_table_entry(destination_object)
        print("-"*10+" Moving Object "+"-"*10)
        self.show_object_tree(moving_object_table_entry)
        print("-"*10+" Destination Object "+"-"*10)
        self.show_object_tree(destination_object_table_entry)
        # unlink moving_object
        # insert into destination at head
        pass

    def show_object_tree(self, destination_object_table_entry):
        print(f"{destination_object_table_entry.describe()}", end=" : ")
        parent_object_number = destination_object_table_entry.get_parent_object_number()
        print(f"parent_object_number={parent_object_number}", end=", ")
        print(f"child={destination_object_table_entry.get_child_object_number()}", end=", ")
        print(f"next={destination_object_table_entry.get_next_sibling_object_number()}")
        if parent_object_number != 0:
            print("Younger Sibling Chain: ", end="")
            object_number = self.get_object_table_entry(parent_object_number).get_child_object_number()
            while object_number != 0 and object_number != destination_object_table_entry.n:
                ote = self.get_object_table_entry(object_number)
                print(ote.describe(), end=" | ")
                object_number = ote.get_next_sibling_object_number()
            print()
        print("Elder Sibling Chain: ", end="")
        object_number = destination_object_table_entry.get_next_sibling_object_number()
        while object_number != 0:
            ote = self.get_object_table_entry(object_number)
            print(ote.describe(), end=" | ")
            object_number = ote.get_next_sibling_object_number()
        print()
        younger_entry = self.get_object_table_entry(destination_object_table_entry.get_prior_sibling_object_number())
        elder_entry = self.get_object_table_entry(destination_object_table_entry.get_next_sibling_object_number())
        print(f"Younger: {younger_entry.describe() if younger_entry is not None else 'NONE'}")
        print(f"Elder: {elder_entry.describe() if elder_entry is not None else 'NONE'}")

