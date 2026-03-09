from Utils import Utils
from array import array


class PropertyTableEntry:
    def __init__(self, address: int, memory: array, game_version: int = 3) -> None:
        self.address: int = address
        self.memory: array = memory
        self.game_version: int = game_version

    @classmethod
    def decode_n_and_l(cls, memory: array, address: int, game_version: int = 3) -> tuple[int, int, int]:
        """
        Returns (property_number, data_length, header_size_in_bytes).
        header_size is 1 in V3, and either 1 or 2 in V4+.
        """
        prop = memory[address]

        if game_version <= 3:
            if prop == 0:
                return 0, 0, 1
            n = prop & 0x1F
            l = (prop >> 5) + 1
            return n, l, 1

        else:  # V4+
            if prop == 0:
                return 0, 0, 1
            n = prop & 0x3F

            if prop & 0x80:
                # Two-byte header: size is in the second byte (low 6 bits)
                size_byte = memory[address + 1]
                l = size_byte & 0x3F
                if l == 0:
                    l = 64  # 0 means 64 per spec
                return n, l, 2
            else:
                # One-byte header: bit 6 indicates size
                l = 2 if (prop & 0x40) else 1
                return n, l, 1

    def get_property_number(self) -> int:
        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, self.address, self.game_version)
        return n

    def get_length(self) -> int:
        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, self.address, self.game_version)
        return l

    def get_header_size(self) -> int:
        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, self.address, self.game_version)
        return header_size

    def get_data_address(self) -> int:
        """Address of the actual property data (after the header byte(s))."""
        return self.address + self.get_header_size()

    def put_value(self, value: int) -> None:
        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, self.address, self.game_version)
        value_address = self.address + header_size
        if l == 1:
            Utils.mwrite_byte(self.memory, value_address, value)
        elif l == 2:
            Utils.mwrite_word(self.memory, value_address, value)
        else:
            raise RuntimeError(
                f"put_value called on property with length {l} > 2 at {self.address:04X}")

    def get_value(self) -> int:
        n, l, header_size = PropertyTableEntry.decode_n_and_l(
            self.memory, self.address, self.game_version)
        value_address = self.address + header_size
        if l == 1:
            return Utils.mread_byte(self.memory, value_address)
        elif l == 2:
            return Utils.mread_word(self.memory, value_address)
        else:
            raise RuntimeError(
                f"get_value called on property with length {l} > 2 at {self.address:04X}")

    def get_address(self) -> int:
        return self.address