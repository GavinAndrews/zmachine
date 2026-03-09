import sys
import time as time_mod
from enum import IntEnum

import ZStrings
from Utils import Utils
import Processor
from infocomm.Quetzal import Quetzal
from infocomm.TraceFile import TraceFile


class OpcodeType(IntEnum):
    z_0OP = 0
    z_1OP = 1
    z_2OP = 2
    z_VAR = 3
    z_EXT = 4   # V5+ extended opcodes (0xBE prefix)


class Instructions:
    def __init__(self, processor: Processor, dictionary, scripting):

        self.processor = processor
        self.quiet = True
        self.check_trace = False
        self.dictionary = dictionary
        self.scripting = scripting
        self.random = 0x1234

        # Output stream 3 support: stack of (table_address, current_length) tuples
        # When non-empty, print output goes to memory instead of the screen
        self.stream3_stack = []

        if self.check_trace:
            self.trace_file = TraceFile("H:\\linux_trace_script2.txt")

        self.op0_functions = [
            self.instruction_rtrue,         # 0
            self.instruction_rfalse,        # 1
            self.instruction_print,         # 2
            self.instruction_print_ret,     # 3
            self.instruction_nop,           # 4  nop
            self.instruction_save,          # 5
            self.instruction_restore,       # 6
            self.instruction_restart,       # 7
            self.instruction_ret_popped,    # 8
            self.instruction_pop,           # 9  pop (V1-4)
            self.instruction_quit,          # 10
            self.instruction_new_line,      # 11
            self.instruction_show_status,   # 12 no-op in V4
            self.instruction_verify,        # 13 stub as true
            self.unimplemented,             # 14
            self.instruction_piracy,        # 15 stub as genuine
        ]

        self.op1_functions = [
            self.instruction_jz,            # 0
            self.instruction_get_sibling,   # 1
            self.instruction_get_child,     # 2
            self.instruction_get_parent,    # 3
            self.instruction_get_prop_len,  # 4
            self.instruction_inc,           # 5
            self.instruction_dec,           # 6
            self.instruction_print_addr,    # 7
            self.instruction_call_1s,       # 8  call_1s (V4+)
            self.instruction_remove_object, # 9
            self.instruction_print_obj,     # 10
            self.instruction_ret,           # 11
            self.instruction_jump,          # 12
            self.instruction_print_paddr,   # 13
            self.instruction_load,          # 14
            self.instruction_not,           # 15 not (V1-4)
        ]

        self.op2_functions = [
            self.illegal,                       # 0
            self.instruction_je,                # 1
            self.instruction_jl,                # 2
            self.instruction_jg,                # 3
            self.instruction_dec_chk,           # 4
            self.instruction_inc_chk,           # 5
            self.instruction_jin,               # 6
            self.instruction_test,              # 7
            self.instruction_or,                # 8
            self.instruction_and,               # 9
            self.instruction_test_attr,         # 10
            self.instruction_set_attr,          # 11
            self.instruction_clear_attr,        # 12
            self.instruction_store,             # 13
            self.instruction_insert_obj,        # 14
            self.instruction_loadw,             # 15
            self.instruction_loadb,             # 16
            self.instruction_get_prop,          # 17
            self.instruction_get_prop_addr,     # 18
            self.instruction_get_next_prop,     # 19
            self.instruction_add,               # 20
            self.instruction_sub,               # 21
            self.instruction_mul,               # 22
            self.instruction_div,               # 23
            self.instruction_mod,               # 24
            self.instruction_call_2s,           # 25 call_2s (V4+)
            self.unimplemented,                 # 26 call_2n (V5+)
            self.unimplemented,                 # 27 set_colour (V5+)
            self.unimplemented,                 # 28 throw (V5+)
            self.unimplemented,                 # 29
            self.unimplemented,                 # 30
            self.unimplemented,                 # 31
        ]

        self.var_functions = [
            self.instruction_call,              # 0  call / call_vs
            self.instruction_storew,            # 1
            self.instruction_storeb,            # 2
            self.instruction_put_prop,          # 3
            self.instruction_read,              # 4  sread/aread
            self.instruction_print_char,        # 5
            self.instruction_print_num,         # 6
            self.instruction_random,            # 7
            self.instruction_push,              # 8
            self.instruction_pull,              # 9
            self.instruction_split_window,      # 10
            self.instruction_set_window,        # 11
            self.instruction_call_vs2,          # 12 call_vs2 (V4+)
            self.instruction_erase_window,      # 13
            self.instruction_erase_line,        # 14
            self.instruction_set_cursor,        # 15
            self.instruction_get_cursor,        # 16
            self.instruction_set_text_style,    # 17
            self.instruction_buffer_mode,       # 18
            self.instruction_output_stream,     # 19
            self.instruction_input_stream,      # 20
            self.instruction_sound_effect,      # 21 sound_effect
            self.instruction_read_char,         # 22 read_char (V4+)
            self.instruction_scan_table,        # 23 scan_table (V4+)
            self.unimplemented,                 # 24 not (V5+)
            self.instruction_call_vn,           # 25 call_vn (V4+)
            self.instruction_call_vn2,          # 26 call_vn2 (V4+)
            self.unimplemented,                 # 27 tokenise (V5+)
            self.unimplemented,                 # 28 encode_text (V5+)
            self.unimplemented,                 # 29 copy_table (V5+)
            self.unimplemented,                 # 30 print_table (V5+)
            self.instruction_check_arg_count,   # 31 check_arg_count (V4+)
        ]

        self.ext_functions = [
            self.unimplemented,                 # 0  save (V5+)
            self.unimplemented,                 # 1  restore (V5+)
            self.instruction_log_shift,         # 2
            self.instruction_art_shift,         # 3
            self.instruction_set_font,          # 4
            self.unimplemented,                 # 5  draw_picture (V6)
            self.unimplemented,                 # 6  picture_data (V6)
            self.unimplemented,                 # 7  erase_picture (V6)
            self.unimplemented,                 # 8  set_margins (V6)
            self.instruction_save_undo,         # 9
            self.instruction_restore_undo,      # 10
            self.unimplemented,                 # 11 print_unicode
            self.unimplemented,                 # 12 check_unicode
        ]

        self.all_functions = [
            self.op0_functions,
            self.op1_functions,
            self.op2_functions,
            self.var_functions,
            self.ext_functions,
        ]

    def execute(self, op_type, op_number, args, current_pc, opcode):
        try:
            implementation = self.all_functions[op_type][op_number]
            if not self.quiet:
                print(
                    f"EXECUTE: {current_pc:04X} {opcode:02X} {implementation.__name__.replace('instruction_', ''):12} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")

            if self.check_trace:
                trace_address = self.trace_file.read().strip()
                current_pc_as_hex = f"{current_pc:04X}"
                if trace_address != current_pc_as_hex:
                    print(f"BAD {trace_address} {current_pc_as_hex}")
                    exit()
                else:
                    print(f"GOOD {trace_address} {current_pc_as_hex}")

            implementation(args)
        except RuntimeError as re:
            print(f"{re} : {current_pc:04X} {opcode:02X} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")
            self.processor.stack.dump()
            sys.exit(101)

    def unimplemented(self, args):
        raise RuntimeError("Unimplemented function")

    def illegal(self, args):
        raise RuntimeError("Illegal function")

    # ---------------------------------------------------------------------- #
    # Output helpers - route through stream 3 if active                       #
    # ---------------------------------------------------------------------- #

    def _print_str(self, s):
        if self.stream3_stack:
            table_addr, length = self.stream3_stack[-1]
            for ch in s:
                Utils.mwrite_byte(self.processor.memory, table_addr + 2 + length, ord(ch))
                length += 1
            Utils.mwrite_word(self.processor.memory, table_addr, length)
            self.stream3_stack[-1] = (table_addr, length)
        else:
            print(s, end="")

    def _print_char(self, ch):
        if self.stream3_stack:
            table_addr, length = self.stream3_stack[-1]
            Utils.mwrite_byte(self.processor.memory, table_addr + 2 + length, ord(ch))
            length += 1
            Utils.mwrite_word(self.processor.memory, table_addr, length)
            self.stream3_stack[-1] = (table_addr, length)
        else:
            print(ch, end="")

    ################################################################################################
    # Call Instructions                                                                            #
    ################################################################################################

    def instruction_call(self, args):
        if args[0] == 0x0000:
            self.processor.store(0)
        else:
            self.processor.call(args[0], args[1:], 0)

    def instruction_call_vs2(self, args):
        if args[0] == 0:
            self.processor.store(0)
        else:
            self.processor.call(args[0], args[1:], 0)

    def instruction_call_2s(self, args):
        if args[0] == 0:
            self.processor.store(0)
        else:
            self.processor.call(args[0], args[1:2], 0)

    def instruction_call_1s(self, args):
        if args[0] == 0:
            self.processor.store(0)
        else:
            self.processor.call(args[0], [], 0)

    def instruction_call_vn(self, args):
        if args[0] != 0:
            self.processor.call(args[0], args[1:], 1)

    def instruction_call_vn2(self, args):
        if args[0] != 0:
            self.processor.call(args[0], args[1:], 1)

    ################################################################################################
    # Memory Instructions                                                                          #
    ################################################################################################

    def instruction_storew(self, args):
        self.processor.storew(args[0] + 2 * args[1], args[2])

    def instruction_store(self, args):
        variable = args[0]
        value = args[1]
        if variable == 0:
            self.processor.stack.push_word(value)
        elif variable < 16:
            self.processor.stack.write_local(variable, value)
        else:
            self.processor.globals.write_global(variable - 16, value)

    def instruction_storeb(self, args):
        Utils.mwrite_byte(self.processor.memory, args[0] + args[1], args[2])

    def instruction_loadb(self, args):
        self.processor.store(self.processor.loadb(args[0] + args[1]))

    def instruction_loadw(self, args):
        self.processor.store(self.processor.loadw(args[0] + 2 * args[1]))

    ################################################################################################
    # Arithmetic Instructions                                                                      #
    ################################################################################################

    def instruction_add(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.store(Utils.from_signed_int_to_unsigned_word(a0 + a1))

    def instruction_sub(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.store(Utils.from_signed_int_to_unsigned_word(a0 - a1))

    def instruction_mul(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.store(Utils.from_signed_int_to_unsigned_word(a0 * a1))

    def instruction_div(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.store(Utils.from_signed_int_to_unsigned_word(int(a0 / a1)))

    def instruction_mod(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = a0 - int(a0 / a1) * a1  # truncate-towards-zero, not floor
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_or(self, args):
        self.processor.store(args[0] | args[1])

    def instruction_and(self, args):
        self.processor.store(args[0] & args[1])

    def instruction_not(self, args):
        self.processor.store((~args[0]) & 0xFFFF)

    ################################################################################################
    # Branch Instructions                                                                          #
    ################################################################################################

    def instruction_je(self, args):
        self.processor.branch(any(args[0] == args[i] for i in range(1, len(args))))

    def instruction_jz(self, args):
        self.processor.branch(args[0] == 0)

    def instruction_jl(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.branch(a0 < a1)

    def instruction_jg(self, args):
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.branch(a0 > a1)

    def instruction_jin(self, args):
        child = args[0]
        parent = args[1]
        if child == 0:
            self.processor.branch(parent == 0)
        else:
            child_entry = self.processor.object_table.get_object_table_entry(child)
            self.processor.branch(child_entry.get_parent_object_number() == parent)

    def instruction_test(self, args):
        self.processor.branch(args[0] & args[1] == args[1])

    def instruction_test_attr(self, args):
        entry = self.processor.object_table.get_object_table_entry(args[0])
        self.processor.branch(entry.test_attr(args[1]))

    def instruction_dec_chk(self, args):
        result = self.processor.adjust_variable(args[0], -1)
        self.processor.branch(result < Utils.from_unsigned_word_to_signed_int(args[1]))

    def instruction_inc_chk(self, args):
        result = self.processor.adjust_variable(args[0], 1)
        self.processor.branch(result > Utils.from_unsigned_word_to_signed_int(args[1]))

    def instruction_verify(self, args):
        self.processor.branch(True)

    def instruction_piracy(self, args):
        self.processor.branch(True)

    ################################################################################################
    # Return Instructions                                                                          #
    ################################################################################################

    def instruction_ret(self, args):
        self.processor.ret(args[0])

    def instruction_rtrue(self, args):
        self.processor.ret(1)

    def instruction_rfalse(self, args):
        self.processor.ret(0)

    def instruction_ret_popped(self, args):
        self.processor.ret(self.processor.stack.pop_word())

    ################################################################################################
    # Jump / Variable Instructions                                                                 #
    ################################################################################################

    def instruction_jump(self, args):
        self.processor.jump(Utils.from_unsigned_word_to_signed_int(args[0]) - 2)

    def instruction_inc(self, args):
        self.processor.adjust_variable(args[0], 1)

    def instruction_dec(self, args):
        self.processor.adjust_variable(args[0], -1)

    def instruction_load(self, args):
        variable = args[0]
        if variable == 0:
            value = self.processor.stack.peek_word()
        elif variable < 16:
            value = self.processor.stack.read_local(variable)
        else:
            value = self.processor.globals.read_global(variable - 16)
        self.processor.store(value)

    def instruction_push(self, args):
        self.processor.stack.push_word(args[0])

    def instruction_pull(self, args):
        self.processor.pull(args[0])

    def instruction_pop(self, args):
        self.processor.stack.pop_word()

    ################################################################################################
    # Object Instructions                                                                          #
    ################################################################################################

    def instruction_set_attr(self, args):
        self.processor.object_table.get_object_table_entry(args[0]).set_attr(args[1])

    def instruction_clear_attr(self, args):
        self.processor.object_table.get_object_table_entry(args[0]).clear_attr(args[1])

    def instruction_insert_obj(self, args):
        self.processor.object_table.insert_object(args[0], args[1])

    def instruction_remove_object(self, args):
        self.processor.object_table.remove_object(args[0])

    def instruction_get_parent(self, args):
        entry = self.processor.object_table.get_object_table_entry(args[0])
        self.processor.store(entry.get_parent_object_number())

    def instruction_get_child(self, args):
        if args[0] == 0:
            first_child = 0
        else:
            entry = self.processor.object_table.get_object_table_entry(args[0])
            first_child = entry.get_child_object_number()
        self.processor.store(first_child)
        self.processor.branch(first_child != 0)

    def instruction_get_sibling(self, args):
        if args[0] == 0:
            next_sibling = 0
        else:
            entry = self.processor.object_table.get_object_table_entry(args[0])
            next_sibling = entry.get_next_sibling_object_number()
        self.processor.store(next_sibling)
        self.processor.branch(next_sibling != 0)

    def instruction_print_obj(self, args):
        entry = self.processor.object_table.get_object_table_entry(args[0])
        self._print_str(entry.get_property_table().get_description())

    def instruction_put_prop(self, args):
        entry = self.processor.object_table.get_object_table_entry(args[0])
        prop = entry.get_property_table().get_property_table_entry_for_property_number(args[1])
        prop.put_value(args[2])

    def instruction_get_prop(self, args):
        if args[0] == 0:
            self.processor.store(0)
        else:
            entry = self.processor.object_table.get_object_table_entry(args[0])
            prop = entry.get_property_table().get_property_table_entry_for_property_number(args[1])
            if prop is None:
                value = self.processor.object_table.get_property_default(args[1])
            else:
                value = prop.get_value()
            self.processor.store(value)

    def instruction_get_prop_addr(self, args):
        if args[0] == 0:
            self.processor.store(0)
        else:
            mask = 0x3F if self.processor.game_version >= 4 else 0x1F
            property_number = args[1] & mask
            entry = self.processor.object_table.get_object_table_entry(args[0])
            prop = entry.get_property_table().get_property_table_entry_for_property_number(property_number)
            if prop is not None:
                self.processor.store(prop.get_data_address())
            else:
                self.processor.store(0)

    def instruction_get_prop_len(self, args):
        addr = args[0]
        if addr == 0:
            self.processor.store(0)
            return
        if self.processor.game_version <= 3:
            size_byte = Utils.mread_byte(self.processor.memory, addr - 1)
            length = (size_byte >> 5) + 1
        else:
            size_byte = Utils.mread_byte(self.processor.memory, addr - 1)
            if size_byte & 0x80:
                length = size_byte & 0x3F
                if length == 0:
                    length = 64
            else:
                length = 2 if (size_byte & 0x40) else 1
        self.processor.store(length)

    def instruction_get_next_prop(self, args):
        if args[0] == 0:
            self.processor.store(0)
        else:
            entry = self.processor.object_table.get_object_table_entry(args[0])
            value = entry.get_property_table().get_property_table_entry_after_property_number(args[1])
            self.processor.store(0 if value is None else value.get_property_number())

    ################################################################################################
    # Print Instructions                                                                           #
    ################################################################################################

    def instruction_print(self, args):
        embedded_string_address = self.processor.get_pc()
        s = ZStrings.toZString(embedded_string_address, self.processor.memory,
                               self.processor.abbreviation_table)
        while True:
            value = self.processor.get_word_and_advance()
            if value & 0x8000:
                break
        self._print_str(s)

    def instruction_print_ret(self, args):
        embedded_string_address = self.processor.get_pc()
        s = ZStrings.toZString(embedded_string_address, self.processor.memory,
                               self.processor.abbreviation_table)
        while True:
            value = self.processor.get_word_and_advance()
            if value & 0x8000:
                break
        self._print_str(s)
        self._print_str("\n")
        self.processor.ret(1)

    def instruction_print_paddr(self, args):
        zstring_address = self.processor.packed_address(args[0])
        self._print_str(ZStrings.toZString(zstring_address, self.processor.memory,
                                           self.processor.abbreviation_table))

    def instruction_print_addr(self, args):
        self._print_str(ZStrings.toZString(args[0], self.processor.memory,
                                           self.processor.abbreviation_table))

    def instruction_print_char(self, args):
        self._print_char(ZStrings.singleZSCIIChar(args[0]))

    def instruction_print_num(self, args):
        self._print_str(str(Utils.from_unsigned_word_to_signed_int(args[0])))

    def instruction_new_line(self, args):
        self._print_str("\n")

    ################################################################################################
    # I/O Instructions                                                                             #
    ################################################################################################

    def Zinstruction_read(self, args):
        """
        sread (V3) / aread (V4+)
        V3: args = [text_buf, parse_buf]
        V4: args = [text_buf, parse_buf, time (opt), routine (opt)]
             text_buf byte 0 = max chars
             text_buf byte 1 = existing chars count (V4, usually 0)
             text starts at byte 2 (V4) or byte 1 (V3)
        """
        text_addr    = args[0]
        parse_addr   = args[1] if len(args) > 1 else None
        time_tenths  = args[2] if len(args) > 2 else 0
        time_routine = args[3] if len(args) > 3 else 0

        if self.processor.game_version >= 4:
            text_start = text_addr + 2
        else:
            text_start = text_addr + 1

        separators = set(self.dictionary.get_seperators())
        if ' ' not in separators:
            separators.add(" ")

        in_string = self._get_input_line(time_tenths, time_routine)
        in_string = in_string.lower()

        for index, c in enumerate(in_string):
            Utils.mwrite_byte(self.processor.memory, text_start + index, ord(c) & 0xFF)
        Utils.mwrite_byte(self.processor.memory, text_start + len(in_string), 0)

        if self.processor.game_version >= 4:
            Utils.mwrite_byte(self.processor.memory, text_addr + 1, len(in_string))

        if parse_addr is not None:
            self._tokenise(in_string, parse_addr, separators)

        if self.processor.game_version >= 4:
            self.processor.store(13)   # terminating character = Enter

    def instruction_read(self, args):
        """
        sread (V3) / aread (V4+)
        V3: args = [text_buf, parse_buf]
        V4: args = [text_buf, parse_buf, time (opt), routine (opt)]
             text_buf byte 0 = max chars
             text_buf byte 1 = existing chars count (V4, usually 0)
             text starts at byte 2 (V4) or byte 1 (V3)
        """
        text_addr = args[0]
        parse_addr = args[1] if len(args) > 1 else None
        time_tenths = args[2] if len(args) > 2 else 0
        time_routine = args[3] if len(args) > 3 else 0

        # Get max characters from text buffer
        max_chars = Utils.mread_byte(self.processor.memory, text_addr)
        if self.processor.game_version >= 4:
            text_start = text_addr + 2
            # Clear existing text length byte
            Utils.mwrite_byte(self.processor.memory, text_addr + 1, 0)
        else:
            text_start = text_addr + 1

        # Get separators from dictionary
        separators = set(self.dictionary.get_seperators())
        if ' ' not in separators:
            separators.add(" ")

        # Get input
        in_string = self._get_input_line(time_tenths, time_routine)
        in_string = in_string.lower()

        # Truncate to max_chars-1 (leave room for null terminator)
        if len(in_string) > max_chars - 1:
            in_string = in_string[:max_chars - 1]

        # Write to text buffer
        for index, c in enumerate(in_string):
            Utils.mwrite_byte(self.processor.memory, text_start + index, ord(c) & 0xFF)
        # Null terminator
        Utils.mwrite_byte(self.processor.memory, text_start + len(in_string), 0)

        # Update input length for V4+
        if self.processor.game_version >= 4:
            Utils.mwrite_byte(self.processor.memory, text_addr + 1, len(in_string))

        # Parse if parse buffer provided
        if parse_addr is not None and parse_addr != 0:
            Utils.mwrite_byte(self.processor.memory, parse_addr + 1, 0)
            if in_string.strip():
                self._tokenise(in_string, parse_addr, separators)

        # Store terminating character (13 for Enter)
        if self.processor.game_version >= 4:
            self.processor.store(13)


    def instruction_read_char(self, args):
        """
        read_char 1 [time routine] -> (result)
        args[0] = 1 (keyboard), args[1] = time_tenths (opt), args[2] = routine (opt)
        """
        time_tenths  = args[1] if len(args) > 1 else 0
        time_routine = args[2] if len(args) > 2 else 0

        script_line = self.scripting.get_line() if self.scripting is not None else None
        if script_line is not None:
            ch = script_line[0] if script_line else '\r'
            zscii = 13 if ch in ('\r', '\n') else ord(ch)
            self.processor.store(zscii)
            return

        # Print a prompt so the user knows to press a key
        if time_tenths == 0 or time_routine == 0:
            # Untimed: plain single character read
            print("[Press any key to continue...]", end=' ', flush=True)
            ch = self._read_single_char_plain()
            print()  # New line after key press
        else:
            ch = self._read_single_char_timed(time_tenths, time_routine)

        zscii = 13 if ch in ('\r', '\n', '') else ord(ch)
        self.processor.store(zscii)

    def ZZZinstruction_read_char(self, args):
        """
        read_char 1 [time routine] -> (result)
        args[0] = 1 (keyboard), args[1] = time_tenths (opt), args[2] = routine (opt)
        """
        time_tenths  = args[1] if len(args) > 1 else 0
        time_routine = args[2] if len(args) > 2 else 0

        script_line = self.scripting.get_line() if self.scripting is not None else None
        if script_line is not None:
            ch = script_line[0] if script_line else '\r'
            zscii = 13 if ch in ('\r', '\n') else ord(ch)
            self.processor.store(zscii)
            return

        if time_tenths == 0 or time_routine == 0:
            # Untimed: plain single character read
            ch = self._read_single_char_plain()
        else:
            ch = self._read_single_char_timed(time_tenths, time_routine)

        zscii = 13 if ch in ('\r', '\n', '') else ord(ch)
        self.processor.store(zscii)

    # ---------------------------------------------------------------------- #
    # Input helpers                                                            #
    # ---------------------------------------------------------------------- #

    def _location_prompt(self):
        """Print [Room Name] before input prompt. Safe - never crashes."""
        try:
            player_number = self.processor.globals.read_global(0)
            player_obj = self.processor.object_table.get_object_table_entry(player_number)
            if player_obj is not None:
                loc = player_obj.get_parent_object_number()
                loc_entry = self.processor.object_table.get_object_table_entry(loc)
                if loc_entry is not None:
                    print(f"[{loc_entry.get_property_table().get_description()}] ",
                          end="", flush=True)
        except Exception:
            pass

    def _get_input_line(self, time_tenths, time_routine):
        """
        Read a full line of input.
        If time_tenths and time_routine are non-zero, call the Z-machine
        routine every time_tenths/10 seconds; abort input if it returns true.
        Cross-platform: works on Windows and Linux/macOS.
        """
        # Script mode - no timing needed
        script_line = self.scripting.get_line() if self.scripting is not None else None
        if script_line is not None:
            return script_line

        self._location_prompt()

        # No timed input - fast path
        if time_tenths == 0 or time_routine == 0:
            return input()

        # Timed input
        interval = time_tenths / 10.0
        last_tick = time_mod.time()
        line = []

        if sys.platform == 'win32':
            import msvcrt

            def _kbhit():
                return msvcrt.kbhit()

            def _getch():
                return msvcrt.getwche()

            while True:
                if _kbhit():
                    ch = _getch()
                    if ch in ('\r', '\n'):
                        print()
                        return ''.join(line)
                    elif ch in ('\x08',):        # backspace
                        if line:
                            line.pop()
                            print('\b \b', end='', flush=True)
                    elif ch == '\x03':           # Ctrl-C
                        raise KeyboardInterrupt
                    elif ch >= ' ':
                        line.append(ch)
                else:
                    now = time_mod.time()
                    if now - last_tick >= interval:
                        last_tick = now
                        if self.processor.call_and_run(time_routine, []):
                            print()
                            return ''.join(line)
                    time_mod.sleep(0.02)

        else:
            # Linux / macOS — use tty raw mode + select
            import tty, termios, select
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            try:
                while True:
                    ready = select.select([sys.stdin], [], [], 0.02)[0]
                    if ready:
                        ch = sys.stdin.read(1)
                        if ch in ('\r', '\n'):
                            print()
                            return ''.join(line)
                        elif ch in ('\x08', '\x7f'):   # backspace or DEL
                            if line:
                                line.pop()
                                print('\b \b', end='', flush=True)
                        elif ch == '\x03':             # Ctrl-C
                            raise KeyboardInterrupt
                        elif ch >= ' ':
                            print(ch, end='', flush=True)
                            line.append(ch)
                    else:
                        now = time_mod.time()
                        if now - last_tick >= interval:
                            last_tick = now
                            if self.processor.call_and_run(time_routine, []):
                                print()
                                return ''.join(line)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _read_single_char_plain(self):
        """Read one character without timing (used by read_char when no timer)."""
        if sys.platform == 'win32':
            import msvcrt
            return msvcrt.getwche()
        else:
            import tty, termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            try:
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch

    def _read_single_char_timed(self, time_tenths, time_routine):
        """Read one character with timed callback support."""
        interval = time_tenths / 10.0
        last_tick = time_mod.time()

        if sys.platform == 'win32':
            import msvcrt
            while True:
                if msvcrt.kbhit():
                    return msvcrt.getwche()
                now = time_mod.time()
                if now - last_tick >= interval:
                    last_tick = now
                    if self.processor.call_and_run(time_routine, []):
                        return '\r'   # abort - return Enter as terminator
                time_mod.sleep(0.02)
        else:
            import tty, termios, select
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
            try:
                while True:
                    ready = select.select([sys.stdin], [], [], 0.02)[0]
                    if ready:
                        return sys.stdin.read(1)
                    now = time_mod.time()
                    if now - last_tick >= interval:
                        last_tick = now
                        if self.processor.call_and_run(time_routine, []):
                            return '\r'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _tokenise(self, in_string, parse_addr, separators):
        """Parse in_string into words and write to the parse buffer according to Z-machine spec."""
        max_tokens = Utils.mread_byte(self.processor.memory, parse_addr)
        Utils.mwrite_byte(self.processor.memory, parse_addr + 1, 0)

        # Tokenise input
        words = []
        current_word = ""
        in_word = False

        for i, c in enumerate(in_string):
            if c in separators:
                if in_word:
                    words.append((current_word, i - len(current_word)))
                    current_word = ""
                    in_word = False
            else:
                current_word += c
                in_word = True

        if in_word:
            words.append((current_word, len(in_string) - len(current_word)))

        words = words[:max_tokens]

        token_count = len(words)
        Utils.mwrite_byte(self.processor.memory, parse_addr + 1, token_count)

        token_data_start = parse_addr + 2
        key_words = self.dictionary.dictionary_entry_key_words

        for i, (word, start_pos) in enumerate(words):
            token_addr = token_data_start + (i * 4)

            encoded_zstring = ZStrings.convertToEncodedWords(word)
            encoded_zstring = [w & 0x7FFF for w in encoded_zstring]

            while len(encoded_zstring) < key_words:
                encoded_zstring.append(0x14A5)
            encoded_zstring = encoded_zstring[:key_words]
            encoded_zstring[-1] |= 0x8000

            dict_addr = self.dictionary.find_phrase(encoded_zstring)
            if dict_addr is None:
                dict_addr = 0

            Utils.mwrite_word(self.processor.memory, token_addr, dict_addr)
            Utils.mwrite_byte(self.processor.memory, token_addr + 2, len(word))
            Utils.mwrite_byte(self.processor.memory, token_addr + 3, start_pos + 1)

    def instruction_random(self, args):
        range_val = Utils.from_unsigned_word_to_signed_int(args[0])
        if range_val < 0:
            self.random = abs(range_val)
            self.processor.store(0)
        elif range_val == 0:
            self.random = int(time_mod.time()) & 0x7FFFFFFF
            self.processor.store(0)
        else:
            self.random = (self.random * 0x343FD + 0x269EC3) & 0x7FFFFFFF
            n = (self.random >> 16) & 0x7FFF
            self.processor.store(n % range_val + 1)

    def instruction_scan_table(self, args):
        x      = args[0]
        table  = args[1]
        length = args[2]
        form   = args[3] if len(args) > 3 else 0x82

        field_len    = form >> 8 if (form >> 8) != 0 else (form & 0x7F)
        if field_len == 0:
            field_len = 2
        word_compare = bool(form & 0x80)

        found_addr = 0
        for i in range(length):
            addr = table + i * field_len
            val = (Utils.mread_word(self.processor.memory, addr)
                   if word_compare
                   else Utils.mread_byte(self.processor.memory, addr))
            if val == x:
                found_addr = addr
                break

        self.processor.store(found_addr)
        self.processor.branch(found_addr != 0)

    def instruction_check_arg_count(self, args):
        arg_number = args[0]
        details    = self.processor.stack.stack[self.processor.stack.fp - 4]
        supplied   = details & 0x00FF
        self.processor.branch(arg_number <= supplied)

    ################################################################################################
    # Save / Restore                                                                               #
    ################################################################################################

    def instruction_save(self, args):
        print(f"Save to file: ", end="")
        in_string = input().strip()
        if not in_string:
            in_string = "save.qzl"
        q = Quetzal(self.processor.filename)
        q.write_quetzal_save(self.processor.memory, self.processor.purbot,
                             self.processor.stack, self.processor.get_pc(), in_string)
        self.processor.save_succeeded()

    def instruction_restore(self, args):
        print(f"Restore from file: ", end="")
        in_string = input().strip()
        if not in_string:
            in_string = "save.qzl"
        q = Quetzal(self.processor.filename)
        q.read_quetzal_save(in_string)
        q.process_file()
        self.processor.restore(q.game_data, q.new_stack, q.restore_pc)

    ################################################################################################
    # Display / Window Instructions                                                                #
    ################################################################################################

    def instruction_split_window(self, args):
        pass

    def instruction_set_window(self, args):
        pass

    def instruction_erase_window(self, args):
        if args[0] == 0:
            print("\n" * 3, end="")

    def instruction_erase_line(self, args):
        pass

    def instruction_set_cursor(self, args):
        pass

    def instruction_get_cursor(self, args):
        array_addr = args[0]
        Utils.mwrite_word(self.processor.memory, array_addr,     1)
        Utils.mwrite_word(self.processor.memory, array_addr + 2, 1)

    def instruction_set_text_style(self, args):
        pass

    def instruction_buffer_mode(self, args):
        pass

    def instruction_show_status(self, args):
        pass

    def instruction_sound_effect(self, args):
        pass  # no-op in a text-only interpreter

    def instruction_nop(self, args):
        pass

    ################################################################################################
    # Output / Input Stream                                                                        #
    ################################################################################################

    def instruction_output_stream(self, args):
        stream = Utils.from_unsigned_word_to_signed_int(args[0])
        if stream == 3:
            table_addr = args[1] if len(args) > 1 else 0
            self.stream3_stack.append((table_addr, 0))
            Utils.mwrite_word(self.processor.memory, table_addr, 0)
        elif stream == -3:
            if self.stream3_stack:
                self.stream3_stack.pop()

    def instruction_input_stream(self, args):
        pass

    ################################################################################################
    # Extended Opcodes                                                                             #
    ################################################################################################

    def instruction_log_shift(self, args):
        number = args[0]
        places = Utils.from_unsigned_word_to_signed_int(args[1])
        if places >= 0:
            result = (number << places) & 0xFFFF
        else:
            result = (number >> (-places)) & 0xFFFF
        self.processor.store(result)

    def instruction_art_shift(self, args):
        number = Utils.from_unsigned_word_to_signed_int(args[0])
        places = Utils.from_unsigned_word_to_signed_int(args[1])
        if places >= 0:
            result = number << places
        else:
            result = number >> (-places)
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_set_font(self, args):
        self.processor.store(1)

    def instruction_save_undo(self, args):
        self.processor.store(0xFFFF)

    def instruction_restore_undo(self, args):
        self.processor.store(0)

    ################################################################################################
    # Misc                                                                                         #
    ################################################################################################

    def instruction_quit(self, args):
        sys.exit(0)

    def instruction_restart(self, args):
        print("\n[RESTART not implemented - exiting]")
        sys.exit(0)

