from array import array

from Header import Header
from Stack import Stack


class Quetzal:
    def __init__(self, game_file):

        self.game_file = game_file

        self.save_data = None
        self.game_data = None

        self.ifhd_data = None
        self.cmem_data = None
        self.umem_data = None
        self.stks_data = None

        self.restore_pc = None   # Set by process_ifhd(), consumed by processor.restore()

        with open(game_file, mode='rb') as file:
            file_bytes = file.read()
            self.game_data = array('B', file_bytes)

    def read_quetzal_save(self, file_path: str) -> None:
        with open(file_path, 'rb') as file:
            self.save_data = bytearray(file.read())

    # ---------------------------------------------------------------------- #
    # Load path                                                                #
    # ---------------------------------------------------------------------- #

    def process_ifhd(self):
        release_number = int.from_bytes(self.ifhd_data[0:2], byteorder='big', signed=False)
        serial_number  = self.ifhd_data[2:8]
        checksum       = int.from_bytes(self.ifhd_data[8:10], byteorder='big', signed=False)

        # PC is 3 bytes at offset 10 (IFhd chunk is 13 bytes, padded to 14)
        pc = int.from_bytes(self.ifhd_data[10:13], byteorder='big', signed=False)

        # BUG FIX 1: store the restore PC so Processor.restore() can use it
        self.restore_pc = pc

        header = Header(self.game_data)

        matching_serial   = header.SERIAL   == serial_number
        matching_release  = header.ZORKID   == release_number
        matching_checksum = header.PCHKSUM  == checksum

        good = matching_serial and matching_release and matching_checksum
        if not good:
            raise RuntimeError(
                f"Save file does not match game file "
                f"(serial={'OK' if matching_serial else 'BAD'}, "
                f"release={'OK' if matching_release else 'BAD'}, "
                f"checksum={'OK' if matching_checksum else 'BAD'})")

    def process_cmem(self):
        """Decode run-length-encoded XOR delta and apply to game_data."""

        sequence = bytearray()
        data = self.cmem_data        # already exact chunk_length bytes (no pad byte)
        while len(data) > 0:
            byte = data[0]
            if byte == 0:
                # BUG FIX: run of zeroes: count = data[1] + 1
                occurrences = data[1] + 1
                data = data[2:]
            else:
                occurrences = 1
                data = data[1:]
            sequence.extend([byte] * occurrences)

        # XOR the sequence with the original game data to recover saved memory
        for i in range(len(sequence)):
            self.game_data[i] ^= sequence[i]

    def process_stks(self):
        """Reconstruct the call stack from the Stks chunk."""

        self.new_stack = Stack()

        # For versions other than V6, the first Quetzal frame is a dummy frame
        # that holds only the bottom-of-stack eval words (not a real call frame).
        dummy_frame = True

        data = self.stks_data
        while len(data) > 0:
            # Each frame header is 8 bytes
            frame_pc        = int.from_bytes(data[0:3], byteorder='big', signed=False)
            flags           = data[3]
            result_variable = data[4]
            arg_supplied    = data[5]
            eval_word_count = int.from_bytes(data[6:8], byteorder='big', signed=False)
            data = data[8:]

            local_word_count = flags & 0x0F
            is_procedure     = bool(flags & 0x10)

            # Read local variable values
            locals_data = []
            for _ in range(local_word_count):
                word = int.from_bytes(data[0:2], byteorder='big', signed=False)
                locals_data.append(word)
                data = data[2:]

            # Read eval stack words for this frame
            eval_data = []
            for _ in range(eval_word_count):
                word = int.from_bytes(data[0:2], byteorder='big', signed=False)
                eval_data.append(word)
                data = data[2:]

            if dummy_frame:
                # The dummy frame's eval words sit at the very bottom of the stack
                for word in eval_data:
                    self.new_stack.push_word(word)
            else:
                # BUG FIX 2: adjusted_pc goes back one byte so that ret() can
                # call store() which re-reads the result variable byte from memory.
                # Quetzal stores the return PC PAST the result variable byte,
                # so we subtract 1 to point back at it.
                adjusted_pc = frame_pc - 1

                self.new_stack.push_word(adjusted_pc >> 9)
                self.new_stack.push_word(adjusted_pc & 0x1FF)
                self.new_stack.push_fp()

                call_type = 1 if is_procedure else 0
                # Reconstruct arg_count from supplied-args bitfield
                arg_count = bin(arg_supplied).count('1')
                self.new_stack.push_word(arg_count | (call_type << 12))
                self.new_stack.mark_frame()
                self.new_stack.fixup_frame(local_word_count)

                # Push locals (first local = local 1, pushed last so read_local(1) works)
                for word in locals_data:
                    self.new_stack.push_word(word)

                # BUG FIX 3: push eval stack for non-dummy frames too
                for word in eval_data:
                    self.new_stack.push_word(word)

            dummy_frame = False

    def process_file(self):
        # BUG FIX 4: print() returns None — don't assign its result
        print(self.save_data[0:4].decode('utf-8'))

        form_length = int.from_bytes(self.save_data[4:8], byteorder='big', signed=False)
        self.form_data = self.save_data[8:8 + form_length]

        print(self.form_data[0:4].decode('utf-8'))
        self.inner_data = self.form_data[4:]

        remaining_data = self.inner_data
        while len(remaining_data) > 0:
            chunk_type   = remaining_data[0:4].decode('utf-8')
            chunk_length = int.from_bytes(remaining_data[4:8], byteorder='big', signed=False)
            # BUG FIX 5: slice exactly chunk_length bytes so no pad byte leaks into chunk data.
            # Use padded_chunk_length only to advance the outer pointer.
            padded_chunk_length = (chunk_length + 1) & ~1
            chunk_data = remaining_data[8:8 + chunk_length]

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

    # ---------------------------------------------------------------------- #
    # Save path                                                                #
    # ---------------------------------------------------------------------- #

    def write_quetzal_save(self, memory, purbot, stack, pc, fname):

        self.ifhd_data = self.build_ifhd(pc)
        self.cmem_data = self.build_cmem(memory, purbot)
        self.umem_data = None
        self.stks_data = self.build_stks(memory, stack)

        chunks = []
        if self.ifhd_data is not None:
            chunks.append((b'IFhd', self.ifhd_data))
        if self.cmem_data is not None:
            chunks.append((b'CMem', self.cmem_data))
        if self.umem_data is not None:
            chunks.append((b'UMem', self.umem_data))
        if self.stks_data is not None:
            chunks.append((b'Stks', self.stks_data))

        # Calculate FORM body size: 4 bytes for 'IFZS' + each chunk's header + data (+ pad)
        form_size = 4
        for _, data in chunks:
            form_size += 8 + len(data)
            if len(data) % 2 == 1:
                form_size += 1

        self.save_data = bytearray()
        self.save_data.extend(b'FORM')
        self.save_data.extend(form_size.to_bytes(4, 'big'))
        self.save_data.extend(b'IFZS')

        for tag, data in chunks:
            self.save_data.extend(tag)
            self.save_data.extend(len(data).to_bytes(4, 'big'))
            self.save_data.extend(data)
            if len(data) % 2 == 1:
                self.save_data.append(0)

        with open(fname, 'wb') as file:
            file.write(self.save_data)

    def build_ifhd(self, pc):
        """Build the IFhd identification chunk (13 bytes)."""
        header = Header(self.game_data)
        ifhd = bytearray()
        ifhd.extend(header.ZORKID.to_bytes(2, 'big'))
        ifhd.extend(header.SERIAL)
        ifhd.extend(header.PCHKSUM.to_bytes(2, 'big'))
        ifhd.extend(pc.to_bytes(3, 'big'))
        return ifhd

    def build_cmem(self, memory, purbot):
        """Build run-length-encoded XOR delta of dynamic memory."""
        cmem = bytearray()
        zero_run = 0

        for i in range(purbot):
            delta = memory[i] ^ self.game_data[i]
            if delta == 0:
                zero_run += 1
            else:
                # Flush any pending zero run
                while zero_run >= 256:
                    cmem.append(0)
                    cmem.append(255)
                    zero_run -= 256
                if zero_run > 0:
                    cmem.append(0)
                    cmem.append(zero_run - 1)
                    zero_run = 0
                cmem.append(delta)

        # Trailing zero runs are omitted (spec allows this)
        return cmem

    def build_stks(self, memory, stack):
        """Serialise the call stack to Quetzal Stks format."""

        # Walk the stack to find frame boundaries.
        # frames[i] is the index of the word BEFORE frame i's header.
        frames = [stack.sp]
        i = stack.fp + 4
        while i < stack.stack_size + 4:
            frames.append(i)
            next_fp = stack.stack[i - 3]   # saved FP word
            i = next_fp + 4 + 1

        stks = bytearray()

        # ------------------------------------------------------------------ #
        # Dummy frame: bottom-of-stack eval words only (6 zero header bytes) #
        # ------------------------------------------------------------------ #
        stks.extend(b'\x00' * 6)   # pc(3) + flags(1) + result_var(1) + arg_supply(1)

        nstk = stack.stack_size - frames[-1]
        stks.extend(nstk.to_bytes(2, 'big'))

        for idx in range(stack.stack_size - 1, stack.stack_size - nstk - 1, -1):
            stks.extend(stack.stack[idx].to_bytes(2, 'big'))

        # ------------------------------------------------------------------ #
        # Real call frames, innermost first                                   #
        # ------------------------------------------------------------------ #
        for frame_index in range(len(frames) - 1, 0, -1):
            current_frame = frames[frame_index]

            # Reconstruct what was pushed at call time
            raw_pc     = stack.stack[current_frame - 1] << 9 | stack.stack[current_frame - 2]
            details    = stack.stack[current_frame - 4]
            call_type  = (details & 0xF000) >> 12
            var_count  = (details & 0x0F00) >> 8
            arg_count  = details & 0x00FF

            # Eval stack = words between this frame and the previous one,
            # minus the 4-word call overhead and the local variables
            local_stack_count = (frames[frame_index] - frames[frame_index - 1]
                                 - var_count - 4)

            is_procedure = (call_type != 0)

            if is_procedure:
                # BUG FIX: procedures have no result variable
                variable_for_result = 0
                quetzal_pc = raw_pc   # raw_pc already points past the call
            else:
                # raw_pc points at the result variable byte; read it and advance
                variable_for_result = memory[raw_pc]
                quetzal_pc = raw_pc + 1  # Quetzal stores PC past the result byte

            # arg_present bitfield: bit n set if arg n+1 was supplied
            arg_present_bitfield = (1 << arg_count) - 1 if arg_count > 0 else 0

            flags = var_count | (0x10 if is_procedure else 0x00)

            stks.extend(quetzal_pc.to_bytes(3, 'big'))
            stks.append(flags)
            stks.append(variable_for_result)
            stks.append(arg_present_bitfield)
            stks.extend(local_stack_count.to_bytes(2, 'big'))

            # Locals then eval stack (both stored innermost-first)
            for vi in range(var_count + local_stack_count):
                stks.extend(stack.stack[current_frame - 5 - vi].to_bytes(2, 'big'))

        return stks


if __name__ == '__main__':
    q = Quetzal('../data/ZORK1.DAT')
    file_path = '../saves/z1.s1'
    q.read_quetzal_save(file_path)
    q.process_file()