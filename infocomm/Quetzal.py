from array import array

from infocomm.Header import Header
from infocomm.Stack import Stack


class Quetzal:
    def __init__(self, game_file):

        self.game_file = game_file

        self.save_data = None
        self.game_data = None

        self.ifhd_data = None
        self.cmem_data = None
        self.umem_data = None
        self.stks_data = None

        with open(game_file, mode='rb') as file:  # b is important -> binary
            file_bytes = file.read()
            self.game_data = array('B', file_bytes)

    def read_quetzal_save(self, file_path: str) -> bytearray:
        with open(file_path, 'rb') as file:
            self.save_data = bytearray(file.read())

    def process_ifhd(self):

        release_number = int.from_bytes(self.ifhd_data[0:2], byteorder='big', signed=False)
        print(f"Release Number: {release_number:04X}")

        serial_number = self.ifhd_data[2:8]
        print(f"Serial: {serial_number.decode('utf-8')}")

        checksum = int.from_bytes(self.ifhd_data[8:10], byteorder='big', signed=False)
        print(f"Checksum: {checksum:04X}")

        # Ignore pad byte at end (only parse 3 bytes)
        pc = int.from_bytes(self.ifhd_data[10:14-1], byteorder='big', signed=False)
        print(f"PC: {pc:04X}")

        header = Header(self.game_data)

        matching_serial = header.SERIAL == serial_number
        matching_release = header.ZORKID == release_number
        matching_checksum = header.PCHKSUM == checksum

        good = matching_serial and matching_release and matching_checksum
        print(good)

    def process_cmem(self):

        # Generate Sequence of Bytes
        sequence = bytearray()
        data = self.cmem_data
        while len(data) > 0:
            occurrences = 1
            byte = data[0]
            if byte == 0:
                occurrences = int.from_bytes(data[1:2], byteorder='big', signed=False)+1
                data = data[2:]
            else:
                data = data[1:]

            for i in range(0, occurrences):
                sequence.append(byte)

        print(f"{len(sequence):04X}")

        # XOR the sequence with the game data
        for i in range(0, len(sequence)):
            self.game_data[i] ^= sequence[i]

    def process_stks(self):

        self.new_stack = Stack()

        # If not V6 the first frame is a dummy frame i.e. only eval stack
        dummy_frame = True

        data = self.stks_data
        while len(data) > 0:
            pc = int.from_bytes(data[0:3], byteorder='big', signed=False)
            print(f"PC: {pc:06X} = {pc>>9:04X} {pc&0x1FF:04X}")

            flags = int.from_bytes(data[3:4], byteorder='big', signed=False)
            call_type = (flags >>4) & 0x01
            print(f"flags: {flags:02X}")

            result_variable_number = int.from_bytes(data[4:5], byteorder='big', signed=False)
            print(f"result_variable_number: {result_variable_number:02X}")

            arg_count = int.from_bytes(data[5:6], byteorder='big', signed=False)
            print(f"arg_count: {arg_count:02X}")

            eval_word_count = int.from_bytes(data[6:8], byteorder='big', signed=False)
            print(f"eval_word_count: {eval_word_count:02X}")

            data = data[8:]

            local_word_count = flags & 0x0F

            if not dummy_frame:
                adjusted_pc = pc - 1
                self.new_stack.push_word(adjusted_pc >> 9)
                self.new_stack.push_word(adjusted_pc & 0x1ff)
                self.new_stack.push_fp()
                self.new_stack.push_word(arg_count | (call_type << 12))
                self.new_stack.mark_frame()
                self.new_stack.fixup_frame(local_word_count)

            for i in range(0, local_word_count):
                word = int.from_bytes(data[0:2], byteorder='big', signed=False)
                print(f"local value: {word:04X}")

                if not dummy_frame:
                    self.new_stack.push_word(word)

                data = data[2:]

            for i in range(0, eval_word_count):
                word = int.from_bytes(data[0:2], byteorder='big', signed=False)
                print(f"Eval value: {word:04X}")

                if dummy_frame:
                    self.new_stack.push_word(word)

                data = data[2:]

            dummy_frame = False

        self.new_stack.dump()


    def process_file(self):
        header = print(self.save_data[0:4].decode('utf-8'))
        print(header)
        form_length = int.from_bytes(self.save_data[4:8], byteorder='big', signed=False)
        print(f"Form Length: {form_length:04X}")
        self.form_data = self.save_data[8:8 + form_length]

        inner_header = print(self.form_data[0:4].decode('utf-8'))
        self.inner_data = self.form_data[4:]

        remaining_data = self.inner_data
        while len(remaining_data) > 0:
            chunk_type = remaining_data[0:4].decode('utf-8')
            print(f"Found Chunk: {chunk_type}")
            chunk_length = int.from_bytes(remaining_data[4:8], byteorder='big', signed=False)
            print(f"Chunk Length: {chunk_length:04X}")
            padded_chunk_length = (chunk_length + 1) & ~1
            chunk_data = remaining_data[8:8 + padded_chunk_length]

            if chunk_type == 'IFhd':
                self.ifhd_data = chunk_data
            elif chunk_type == 'CMem':
                self.cmem_data = chunk_data
            elif chunk_type == 'UMem':
                self.umem_data = chunk_data
            elif chunk_type == 'Stks':
                self.stks_data = chunk_data


            remaining_data = remaining_data[8 + padded_chunk_length:]

        self.process_ifhd()
        self.process_cmem()
        self.process_stks()

    def write_quetzal_save(self, memory, stack, pc, fname):
        # with open(fname, 'wb') as file:
        #     file.write(self.save_data)

        ifhd = self.build_ifhd(pc)
        print(ifhd)

        pass


    def build_ifhd(self, pc):
        ifhd = bytearray()
        header = Header(self.game_data)
        serial = header.SERIAL
        release = header.ZORKID
        checksum = header.PCHKSUM

        ifhd.extend(bytearray(release.to_bytes(2, 'big')))
        ifhd.extend(serial)
        ifhd.extend(bytearray(checksum.to_bytes(2, 'big')))
        ifhd.extend(bytearray(pc.to_bytes(3, 'big')))
        ifhd.append(0)

        for b in ifhd:
            print(f"{b:02X}", end=' ')
        pass


if __name__ == '__main__':
    q = Quetzal('../data/ZORK1.DAT')
    print("Hello, World!")
    file_path = '../saves/z1.s1'
    q.read_quetzal_save(file_path)
    q.process_file()
