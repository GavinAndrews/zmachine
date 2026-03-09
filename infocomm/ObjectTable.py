from array import array

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ObjectTableEntry import ObjectTableEntry

from Utils import Utils


class ObjectTable:
    def __init__(self, start_location, memory, abbreviations, game_version):
        self.game_version = game_version
        if game_version <= 3:
            self.object_entry_size = 9
            self.property_defaults_count = 31
        else:
            self.object_entry_size = 14
            self.property_defaults_count = 63

        self.property_defaults_start_location = start_location
        self.object_start_location = start_location + self.property_defaults_count * 2

        self.memory = memory
        self.abbreviations = abbreviations

        self.object_count = self.determine_extent()

    def determine_extent(self):
        start = self.object_start_location
        done = False
        lowest_prop_address = None
        n = 0

        while not done:
            prop_address = Utils.mread_word(
                self.memory,
                start + self.object_entry_size - 2
            )

            if lowest_prop_address is None or prop_address < lowest_prop_address:
                lowest_prop_address = prop_address

            start += self.object_entry_size
            n += 1

            if start >= lowest_prop_address:
                done = True

        return n


    def ZZZdetermine_extent(self):
        start = self.object_start_location
        done = False
        lowest_prop_address = None
        n = 0

        while not done:
            prop_address = int.from_bytes(
                self.memory[start + self.object_entry_size - 2:
                            start + self.object_entry_size - 2 + 2],
                'big')
            if lowest_prop_address is None or prop_address < lowest_prop_address:
                lowest_prop_address = prop_address
            start += self.object_entry_size
            if start >= lowest_prop_address:
                done = True
            n += 1

        return n

    def get_object_table_entry(self, n) -> 'ObjectTableEntry':
        if n == 0:
            return None
        else:
            from ObjectTableEntry import ObjectTableEntry
            return ObjectTableEntry(
                self.object_start_location + (n - 1) * self.object_entry_size,
                self.memory,
                self.object_entry_size,
                self.abbreviations,
                n,
                self,
                self.game_version)

    def get_property_table_entry(self, object_number, property_number):
        object_table_entry = self.get_object_table_entry(object_number)
        return object_table_entry.get_property_table_entry_for_property_number(property_number)

    def insert_object(self, moving_object, destination_object):
        moving_object_table_entry = self.get_object_table_entry(moving_object)
        destination_object_table_entry = self.get_object_table_entry(destination_object)

        moving_object_table_entry.unlink()

        previous_child = destination_object_table_entry.get_child_object_number()
        destination_object_table_entry.set_child_object_number(moving_object_table_entry.n)
        moving_object_table_entry.set_parent_object_number(destination_object_table_entry.n)
        moving_object_table_entry.set_next_sibling_object_number(previous_child)

    def remove_object(self, moving_object):
        moving_object_table_entry = self.get_object_table_entry(moving_object)
        moving_object_table_entry.unlink()

    def show_object_tree(self, destination_object_table_entry):
        print(f"{destination_object_table_entry.get_property_table().description()}", end=" : ")
        parent_object_number = destination_object_table_entry.get_parent_object_number()
        print(f"parent_object_number={parent_object_number}", end=", ")
        print(f"child={destination_object_table_entry.get_child_object_number()}", end=", ")
        print(f"next={destination_object_table_entry.get_next_sibling_object_number()}")
        if parent_object_number != 0:
            print("Younger Sibling Chain: ", end="")
            object_number = self.get_object_table_entry(parent_object_number).get_child_object_number()
            while object_number != 0 and object_number != destination_object_table_entry.n:
                ote = self.get_object_table_entry(object_number)
                print(ote.get_property_table().description(), end=" | ")
                object_number = ote.get_next_sibling_object_number()
            print()
        print("Older Sibling Chain: ", end="")
        object_number = destination_object_table_entry.get_next_sibling_object_number()
        while object_number != 0:
            ote = self.get_object_table_entry(object_number)
            print(ote.get_property_table().description(), end=" | ")
            object_number = ote.get_next_sibling_object_number()
        print()
        younger_entry = self.get_object_table_entry(
            destination_object_table_entry.get_prior_sibling_object_number())
        older_entry = self.get_object_table_entry(
            destination_object_table_entry.get_next_sibling_object_number())
        print(
            f"Near Sibs: Younger: "
            f"{younger_entry.get_property_table().description() if younger_entry is not None else 'NONE'}",
            end=", ")
        print(
            f"Older: {older_entry.get_property_table().description() if older_entry is not None else 'NONE'}")

    def get_property_default(self, property_number):
        return Utils.mread_word(
            self.memory,
            self.property_defaults_start_location + 2 * (property_number - 1))