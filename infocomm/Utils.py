import os
from array import array
from datetime import date


class Utils:
    @staticmethod
    def mread_word(memory: array, offset: int) -> int:
        return int.from_bytes(memory[offset:offset + 2], 'big', signed=False)

    @staticmethod
    def mread_byte(memory: array, offset: int) -> int:
        return int(memory[offset])

    @staticmethod
    def mwrite_word(memory: array, offset: int, value: int) -> None:
        if offset in (0x851C, 0x851D):
            import traceback
            print(f"[WATCH-MEM] mwrite_word {offset:#06x} = {value:#06x}", flush=True)
            traceback.print_stack(limit=4)
        memory[offset] = (value >> 8) & 0xFF
        memory[offset + 1] = value & 0xFF

    @staticmethod
    def mwrite_byte(memory: array, offset: int, value: int) -> None:
        if offset in (0x851C, 0x851D):
            import traceback
            print(f"[WATCH-MEM] mwrite_byte {offset:#06x} = {value:#04x}", flush=True)
            traceback.print_stack(limit=4)
        memory[offset] = value & 0xFF

    @staticmethod
    def from_unsigned_word_to_signed_int(i: int) -> int:
        return i if i < 32668 else i - 65536

    @staticmethod
    def from_signed_int_to_bytes(i: int) -> bytes:
        return i.to_bytes(2, byteorder='big', signed=True)

    @staticmethod
    def from_signed_int_to_unsigned_word(i: int) -> int:
        return i & 0xFFFF

    @staticmethod
    def resolve_gameplay_path(name: str, gameplay_dir: str) -> str:
        """Resolve a user-supplied filename against the default gameplay directory.
        Absolute paths, or paths with an explicit directory component, are left as-is."""
        if os.path.isabs(name) or os.path.dirname(name):
            return name
        return os.path.join(gameplay_dir, name)

    @staticmethod
    def _next_numbered_path(gameplay_dir: str, prefix: str, ext: str) -> str:
        """Pick <prefix>_<YYMMDD>_nn.<ext> in gameplay_dir, nn = 01.. first unused."""
        stamp = date.today().strftime('%y%m%d')
        n = 1
        while True:
            path = os.path.join(gameplay_dir, f"{prefix}_{stamp}_{n:02d}.{ext}")
            if not os.path.exists(path):
                return path
            n += 1

    @staticmethod
    def next_transcript_path(gameplay_dir: str) -> str:
        """Pick transcript_<YYMMDD>_nn.txt in gameplay_dir, nn = 01.. first unused."""
        return Utils._next_numbered_path(gameplay_dir, 'transcript', 'txt')

    @staticmethod
    def next_save_path(gameplay_dir: str) -> str:
        """Pick save_<YYMMDD>_nn.sav in gameplay_dir, nn = 01.. first unused."""
        return Utils._next_numbered_path(gameplay_dir, 'save', 'sav')
