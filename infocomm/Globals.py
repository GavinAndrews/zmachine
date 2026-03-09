from infocomm.Utils import Utils


class Globals:
    def __init__(self, memory: bytes, game_version: int, start_location: int = None) -> None:
        self.memory = memory
        self.game_version = game_version
        if start_location is not None:
            self.start_location = start_location
        else:
            # Read globals address from header bytes 0x0C-0x0D (same for all versions)
            self.start_location = int.from_bytes(memory[0x0C:0x0E], 'big')

    def read_global(self, global_number: int) -> int:
        location = self.start_location + global_number * 2
        w = Utils.mread_word(self.memory, location)
        return w

    def write_global(self, global_number: int, value: int) -> None:
        location = self.start_location + global_number * 2
        self.memory[location] = value >> 8
        self.memory[location + 1] = value & 0xFF

    def dump(self) -> None:
        print(f"[DEBUG] Global variables start at 0x{self.start_location:04X}")
        for i in range(0, 16):  # Just show first 16 globals
            w = self.read_global(i)
            print(f"  Global[{i}] = {w} (0x{w:04X})")