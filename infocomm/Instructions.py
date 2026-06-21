import sys
import time as time_mod
from enum import IntEnum


class _UndoPerformed(Exception):
    """Raised by the undo meta-command to unwind Python's call stack cleanly."""
    pass

class _RestartRequested(Exception):
    """Raised by the restart opcode to unwind back to the main run loop."""
    pass

import ZStrings
from Utils import Utils
import Processor
from Quetzal import Quetzal
from TraceFile import TraceFile


class OpcodeType(IntEnum):
    z_0OP = 0
    z_1OP = 1
    z_2OP = 2
    z_VAR = 3
    z_EXT = 4   # V5+ extended opcodes (0xBE prefix)


class Instructions:
    def __init__(self, processor: Processor, dictionary, scripting, screen=None):

        self.processor = processor
        self.quiet = True
        self.check_trace = False
        self.trace_count = 0
        self.dictionary = dictionary
        self.scripting = scripting
        self.random = 0x1234
        self.screen = screen

        # Output stream 1 (screen): can be disabled by output_stream -1
        self.stream1_active = True
        # Output stream 3: stack of (table_address, current_length) tuples
        # When non-empty, print output goes to memory instead of the screen
        self.stream3_stack = []
        self._undo_stack = []
        self._undo_max_depth = 10
        self._interp_undo_stack = []   # interpreter-level saves (works for all versions)
        self._skip_next_interp_save = False
        self.undo_random_continue = False  # if True, RNG is NOT reset on undo
        self.trace_callback = None   # callable(pc, name, args) or None
        self.map_file = None          # open file for transition logging, or None
        self._map_prev_loc = None     # location string at start of last turn
        self._map_prev_cmd = None     # command typed last turn
        self._map_notes = {}          # loc -> [note, ...] kept in memory
        self._current_opcode_pc = 0
        self.show_location = False
        self.location_global = None   # None = auto-detect; set via #loc G N
        self._player_obj_num = None   # cached once confirmed (parent has a name)
        self._player_candidates = None  # cached list of all player-named objects

        if self.check_trace:
            self.trace_file = TraceFile("C:\\Users\\Gavin\\Documents\\Projects\\software\\infocom\\linux_trace_trinity_1.txt")

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
            self.instruction_set_colour,        # 27 set_colour (V5+)
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
        self._current_opcode_pc = current_pc
        try:
            implementation = self.all_functions[op_type][op_number]
            if self.trace_callback is not None:
                try:
                    name = implementation.__name__.replace('instruction_', '').upper()
                    self.trace_callback(current_pc, name, args)
                except Exception:
                    pass
            if not self.quiet or self.trace_count > 0:
                import sys as _sys
                _sys.stderr.write(
                    f"EXECUTE: {current_pc:04X} {opcode:02X} {implementation.__name__.replace('instruction_', ''):12} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}\n")
                if self.trace_count > 0:
                    self.trace_count -= 1

            if self.check_trace:
                trace_address = self.trace_file.read().strip().split()[0]
                current_pc_as_hex = f"{current_pc:04X}"
                if trace_address != current_pc_as_hex:
                    print(f"BAD {trace_address} {current_pc_as_hex}")
                    exit()
                else:
                    #print(f"GOOD {trace_address} {current_pc_as_hex}")
                    pass

            implementation(args)
        except RuntimeError as re:
            import sys as _sys
            _sys.stderr.write(f"{re} : {current_pc:04X} {opcode:02X} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}\n")
            self.processor.stack.dump()
            sys.exit(101)

    def unimplemented(self, args):
        raise RuntimeError("Unimplemented function")

    def illegal(self, args):
        raise RuntimeError("Illegal function")

    # ---------------------------------------------------------------------- #
    # Output helpers - route through stream 3 if active, else Screen          #
    # ---------------------------------------------------------------------- #

    def _print_str(self, s):
        if self.stream3_stack:
            table_addr, length = self.stream3_stack[-1]
            for ch in s:
                Utils.mwrite_byte(self.processor.memory, table_addr + 2 + length, ord(ch))
                length += 1
            Utils.mwrite_word(self.processor.memory, table_addr, length)
            self.stream3_stack[-1] = (table_addr, length)
        elif self.stream1_active:
            self.screen.print_str(s)

    def _print_char(self, ch):
        if self.stream3_stack:
            table_addr, length = self.stream3_stack[-1]
            Utils.mwrite_byte(self.processor.memory, table_addr + 2 + length, ord(ch))
            length += 1
            Utils.mwrite_word(self.processor.memory, table_addr, length)
            self.stream3_stack[-1] = (table_addr, length)
        elif self.stream1_active:
            self.screen.print_char(ch)

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
            self.processor.call(args[0], args[1:], 2)  # 2 = void: discard return value

    def instruction_call_vn2(self, args):
        if args[0] != 0:
            self.processor.call(args[0], args[1:], 2)  # 2 = void: discard return value

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

    def _save_interp_undo(self):
        """Save interpreter-level undo snapshot before each read instruction."""
        if self._skip_next_interp_save:
            self._skip_next_interp_save = False
            return
        import array as _array
        stack = self.processor.stack
        self._interp_undo_stack.append({
            'pc':          self._current_opcode_pc,
            'memory':      _array.array('B', self.processor.memory),
            'stack_data':  _array.array('L', stack.stack),
            'random':      self.random,
            'sp':          stack.sp,
            'fp':          stack.fp,
            'frame_count': stack.frame_count,
        })
        if len(self._interp_undo_stack) > self._undo_max_depth:
            self._interp_undo_stack.pop(0)

    def instruction_read(self, args):
        """sread (V3) / aread (V4+)"""
        self._save_interp_undo()

        # Map: check whether the previous command caused a location transition.
        if self.map_file and self._map_prev_cmd is not None:
            new_loc = self._map_location()
            if new_loc and self._map_prev_loc and new_loc != self._map_prev_loc:
                try:
                    self.map_file.write(
                        f'{self._map_prev_loc}\t{new_loc}\t{self._map_prev_cmd}\n')
                    self.map_file.flush()
                except Exception:
                    pass
        if self.map_file:
            self._map_prev_loc = self._map_location()

        text_addr    = args[0]
        parse_addr   = args[1] if len(args) > 1 else None
        time_tenths  = args[2] if len(args) > 2 else 0
        time_routine = args[3] if len(args) > 3 else 0

        max_chars = Utils.mread_byte(self.processor.memory, text_addr)
        if self.processor.game_version >= 4:
            text_start = text_addr + 2
            Utils.mwrite_byte(self.processor.memory, text_addr + 1, 0)
        else:
            text_start = text_addr + 1

        separators = set(self.dictionary.get_seperators())
        if ' ' not in separators:
            separators.add(" ")

        while True:
            in_string = self._get_input_line(max_chars, time_tenths, time_routine)
            in_string = in_string.lower()
            if self._handle_meta_command(in_string):
                continue   # meta-command handled; ask for another line
            break

        if self.map_file:
            self._map_prev_cmd = in_string  # stored; transition checked next turn

        if len(in_string) > max_chars - 1:
            in_string = in_string[:max_chars - 1]

        for index, c in enumerate(in_string):
            Utils.mwrite_byte(self.processor.memory, text_start + index, ord(c) & 0xFF)
        Utils.mwrite_byte(self.processor.memory, text_start + len(in_string), 0)

        if self.processor.game_version >= 4:
            Utils.mwrite_byte(self.processor.memory, text_addr + 1, len(in_string))

        if parse_addr is not None and parse_addr != 0:
            Utils.mwrite_byte(self.processor.memory, parse_addr + 1, 0)
            if in_string.strip():
                self._tokenise(in_string, parse_addr, separators)

        if self.processor.game_version >= 5:
            self.processor.store(13)   # V5+ aread stores terminating character; V4 sread does not

        self.trace_count = 0


    def instruction_read_char(self, args):
        """read_char 1 [time routine] -> (result)"""
        time_tenths  = args[1] if len(args) > 1 else 0
        time_routine = args[2] if len(args) > 2 else 0

        ch = self._read_single_char(time_tenths, time_routine)
        zscii = 13 if ch in ('\r', '\n', '') else ord(ch)
        self.processor.store(zscii)

    # ---------------------------------------------------------------------- #
    # Input helpers                                                            #
    # ---------------------------------------------------------------------- #

    def _handle_meta_command(self, line):
        """Handle interpreter-level commands (work regardless of game vocabulary).
        Returns True if the line was a meta-command (caller should loop for new input)."""
        cmd = line.strip().split()
        if not cmd:
            return False
        verb = cmd[0]
        if verb == 'undo' and len(cmd) == 1:
            # _save_interp_undo() fires at the START of instruction_read, so the
            # most-recent snapshot is the *current* state (saved moments ago before
            # the user typed anything).  We must discard it and restore the one
            # before it, which represents the state at the previous turn.
            if len(self._interp_undo_stack) < 2:
                self.screen.print_str("[Nothing to undo.]\n")
                return True
            self._interp_undo_stack.pop()        # discard current-state snapshot
            s = self._interp_undo_stack.pop()    # restore previous-state snapshot
            mem = self.processor.memory
            for i, b in enumerate(s['memory']):
                mem[i] = b
            stack = self.processor.stack
            for i, w in enumerate(s['stack_data']):
                stack.stack[i] = w
            stack.sp          = s['sp']
            stack.fp          = s['fp']
            stack.frame_count = s['frame_count']
            self.processor.set_pc(s['pc'])
            if not self.undo_random_continue:
                self.random = s['random']
            # Clear only the status bar (upper window) — it still shows the
            # location we just undid.  The lower window is untouched.
            # The game redraws the status bar correctly on the next turn.
            self.screen.erase_window(1)
            # Print feedback so the user can see the undo happened and knows
            # the game is ready for a new command.  The game's own '>' prompt
            # was before the read opcode we restored to, so it won't re-appear.
            self.screen.print_str('\n[Undone.]\n\n> ')
            # Do NOT set _skip_next_interp_save: after restoring, instruction_read
            # will re-save the restored state as a new snapshot, which is correct.
            raise _UndoPerformed()
        if verb in ('script', 'transcript'):
            if self.screen.stream2_active:
                self.screen.print_str("[Transcript is already active.]\n")
            else:
                self.screen.print_str("Transcript file name (blank = transcript.txt): ")
                self.screen.refresh()
                name = self.screen.read_line(128).strip()
                self.screen.open_transcript(name if name else None)
                self.screen.print_str("[Transcript started.]\n")
            return True
        if verb in ('unscript', 'notranscript', 'noscript'):
            if not self.screen.stream2_active:
                self.screen.print_str("[No transcript is active.]\n")
            else:
                self.screen.close_transcript()
                self.screen.print_str("[Transcript ended.]\n")
            return True
        if verb == '#loc':
            if len(cmd) == 3 and cmd[1].upper() == 'G':
                try:
                    self.location_global = int(cmd[2])
                    self.show_location = True
                    self.screen.print_str(f"[Location display on, using global {self.location_global}]\n")
                except ValueError:
                    self.screen.print_str("[Usage: #loc  or  #loc G <number>]\n")
            else:
                self.show_location = not self.show_location
                self.location_global = None  # reset to auto-detect
                state = "on" if self.show_location else "off"
                self.screen.print_str(f"[Location display {state}]\n")
            return True
        if verb == '#globals':
            count = int(cmd[1]) if len(cmd) > 1 else 20
            self._dump_globals(count)
            return True
        if verb == '#help':
            self.screen.print_str(
                "[Interpreter commands:\n"
                "  undo                   Undo last move (interpreter-level, works in all versions)\n"
                "  script / transcript    Start transcript (prompts for filename)\n"
                "  unscript / noscript    Stop transcript\n"
                "  #loc                   Toggle location display before each prompt\n"
                "  #loc G <n>             Pin location to global variable n\n"
                "  #commands <file>        Read commands from file (plain list or transcript)\n"
                "  #map <file>            Log location transitions to file (from / to / command)\n"
                "  #map off               Stop map logging\n"
                "  #see <note>            Add a note to the current location (shown in map)\n"
                "  #see                   Show notes for the current location\n"
                "  #remap                 Regenerate map.html from map.txt\n"
                "  #remap <file>          Regenerate from a specific map file\n"
                "  #seed <n>              Seed RNG (any positive integer; 0 = time-based)\n"
                "  #obj <n>               Dump runtime state of object n\n"
                "  #globals [count]       Show first <count> globals (default 20)\n"
                "  #help                  Show this list\n"
                "]\n"
            )
            return True
        if verb == '#commands':
            if len(cmd) < 2:
                self.screen.print_str("[Usage: #commands <filename>]\n")
            else:
                filename = ' '.join(cmd[1:])
                try:
                    from Scripting import Scripting
                    self.scripting = Scripting(filename)
                    self.screen.print_str(f"[Reading commands from {filename}]\n")
                except FileNotFoundError:
                    self.screen.print_str(f"[File not found: {filename}]\n")
                except Exception as e:
                    self.screen.print_str(f"[Error loading {filename}: {e}]\n")
            return True
        if verb == '#map':
            if len(cmd) >= 2 and cmd[1].lower() == 'off':
                if self.map_file:
                    self.map_file.close()
                    self.map_file = None
                    self._map_prev_loc = None
                    self._map_prev_cmd = None
                    self.screen.print_str("[Map logging stopped]\n")
                else:
                    self.screen.print_str("[Map logging was not active]\n")
            else:
                filename = ' '.join(cmd[1:]) if len(cmd) >= 2 else 'map.txt'
                try:
                    if self.map_file:
                        self.map_file.close()
                    # Reload any notes already in the file into memory
                    self._map_notes = {}
                    try:
                        with open(filename, encoding='utf-8') as rf:
                            for line in rf:
                                parts = line.rstrip('\n').split('\t')
                                if len(parts) == 3 and parts[0] == 'NOTE':
                                    self._map_notes.setdefault(parts[1], []).append(parts[2])
                    except FileNotFoundError:
                        pass
                    self.map_file = open(filename, 'a', encoding='utf-8')
                    self._map_prev_loc = self._map_location()
                    self._map_prev_cmd = None
                    self.screen.print_str(f"[Map logging to {filename}]\n")
                except Exception as e:
                    self.screen.print_str(f"[Error opening map file: {e}]\n")
            return True
        if verb == '#see':
            loc = self._map_location()
            if not loc:
                self.screen.print_str("[Cannot determine current location]\n")
                return True
            if len(cmd) < 2:
                # Show notes for current location in-game
                notes = self._map_notes.get(loc, [])
                if notes:
                    self.screen.print_str(f"[Notes for {loc}:]\n")
                    for n in notes:
                        self.screen.print_str(f"  - {n}\n")
                else:
                    self.screen.print_str(f"[No notes for {loc}]\n")
            else:
                note = ' '.join(cmd[1:])
                self._map_notes.setdefault(loc, []).append(note)
                if self.map_file:
                    self.map_file.write(f'NOTE\t{loc}\t{note}\n')
                    self.map_file.flush()
                    self.screen.print_str(f"[Note added for {loc}]\n")
                else:
                    self.screen.print_str(
                        f"[Note saved in memory. Start #map to also persist to file.]\n")
            return True
        if verb == '#remap':
            if self.map_file:
                map_path = self.map_file.name
            elif len(cmd) >= 2:
                map_path = ' '.join(cmd[1:])
            else:
                map_path = 'map.txt'
            import os
            html_path = os.path.splitext(map_path)[0] + '.html'
            try:
                import mapview
                transitions, nodes, notes = mapview.parse_map(map_path)
                html = mapview.build_html(transitions, nodes, notes)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                n_notes = sum(len(v) for v in notes.values())
                self.screen.print_str(
                    f"[Map written to {html_path}: "
                    f"{len(transitions)} transitions, {len(nodes)} locations, "
                    f"{n_notes} notes]\n")
            except FileNotFoundError:
                self.screen.print_str(f"[Map file not found: {map_path}]\n")
            except Exception as e:
                self.screen.print_str(f"[Error regenerating map: {e}]\n")
            return True
        if verb == '#seed':
            if len(cmd) > 1:
                try:
                    seed = int(cmd[1])
                    if seed == 0:
                        self.random = int(time_mod.time()) & 0x7FFFFFFF
                        self.screen.print_str(f"[RNG seeded from clock]\n")
                    else:
                        self.random = seed & 0x7FFFFFFF
                        self.screen.print_str(f"[RNG seeded with {seed}]\n")
                except ValueError:
                    self.screen.print_str("[Usage: #seed <number>]\n")
            else:
                self.screen.print_str("[Usage: #seed <number>]\n")
            return True
        if verb == '#obj':
            if len(cmd) > 1:
                try:
                    self._dump_object(int(cmd[1]))
                except ValueError:
                    self.screen.print_str("[Usage: #obj <number>]\n")
            else:
                self.screen.print_str("[Usage: #obj <number>]\n")
            return True
        return False

    def _map_location(self):
        """Return '#N: Room Name' for the current room (object ID included to
        disambiguate maze rooms that share a description)."""
        try:
            obj_count = self.processor.object_table.object_count
            if self.processor.game_version <= 3 or self.location_global is not None:
                g   = self.location_global if self.location_global is not None else 0
                num = self.processor.globals.read_global(g)
            else:
                num = 0
                player_num = self._find_player_object(obj_count)
                if player_num:
                    player = self.processor.object_table.get_object_table_entry(player_num)
                    num = player.get_parent_object_number() if player else 0
            if not num:
                return None
            obj  = self.processor.object_table.get_object_table_entry(num)
            name = obj.get_property_table().get_description().strip() if obj else ''
            return f'#{num}: {name}' if name else f'#{num}'
        except Exception:
            return None

    def _current_location_str(self):
        """Return 'Obj#N: Room Name' for the player's current room, or None on error.

        V1-V3: global 0 IS the room (Z-Machine spec section 8.2).
        V4+: scan globals 0-30 for the first value that refers to a valid,
             named object (description length >= 4).  The user can override
             with '#loc G N' once they know which global holds the room.
        """
        try:
            obj_count = self.processor.object_table.object_count
            if self.processor.game_version <= 3 or self.location_global is not None:
                g = self.location_global if self.location_global is not None else 0
                val = self.processor.globals.read_global(g)
                return self._obj_location_str(val, obj_count)

            # V4+: find the player object (named "yourself", "you", etc.) and
            # return its parent as the current room.  Cache the player object
            # number so we only scan once per session.
            player_num = self._find_player_object(obj_count)
            if player_num:
                player = self.processor.object_table.get_object_table_entry(player_num)
                room_num = player.get_parent_object_number() if player else 0
                if room_num:
                    room = self.processor.object_table.get_object_table_entry(room_num)
                    if room:
                        name = room.get_property_table().get_description().strip()
                        if name:
                            return f"Obj#{room_num}: {name}"
            return None
        except Exception:
            return None

    # Common short names Infocom games give the player object.
    _PLAYER_NAMES = frozenset({
        'yourself', 'you', 'self', 'me', 'adventurer', 'hero', 'cretin',
        'player', 'i',
    })

    def _find_player_object(self, obj_count):
        """Return the player object number whose parent is a named room.

        Scans the object table once to collect all player-named candidates,
        then each call picks whichever one currently has a named parent.
        Only caches permanently once a confirmed live player is found.
        """
        if self._player_obj_num is not None:
            return self._player_obj_num

        # Build candidate list once
        if self._player_candidates is None:
            self._player_candidates = []
            for n in range(1, obj_count + 1):
                try:
                    obj = self.processor.object_table.get_object_table_entry(n)
                    if obj is None:
                        continue
                    desc = obj.get_property_table().get_description().strip().lower()
                    if desc in self._PLAYER_NAMES:
                        self._player_candidates.append(n)
                except Exception:
                    continue

        # Pick the candidate whose parent currently has a description
        for n in self._player_candidates:
            try:
                obj = self.processor.object_table.get_object_table_entry(n)
                parent_num = obj.get_parent_object_number() if obj else 0
                if parent_num:
                    p = self.processor.object_table.get_object_table_entry(parent_num)
                    if p and p.get_property_table().get_description().strip():
                        self._player_obj_num = n   # confirmed — cache it
                        return n
            except Exception:
                continue

        # Not yet confirmed — return first candidate without caching
        return self._player_candidates[0] if self._player_candidates else None

    def _obj_location_str(self, obj_num, obj_count):
        """Return 'Obj#N: name' if obj_num is a valid named object, else None."""
        if not (1 <= obj_num <= obj_count):
            return None
        obj = self.processor.object_table.get_object_table_entry(obj_num)
        if obj is None:
            return None
        name = obj.get_property_table().get_description().strip()
        if len(name) >= 4:
            return f"Obj#{obj_num}: {name}"
        return None

    def _dump_object(self, obj_num):
        """Dump runtime state of a single object."""
        obj_count = self.processor.object_table.object_count
        if not (1 <= obj_num <= obj_count):
            self.screen.print_str(f"[Object {obj_num} out of range (1-{obj_count})]\n")
            return
        obj = self.processor.object_table.get_object_table_entry(obj_num)
        if obj is None:
            self.screen.print_str(f"[Object {obj_num} not found]\n")
            return
        try:
            desc    = obj.get_property_table().get_description().strip()
            parent  = obj.get_parent_object_number()
            sibling = obj.get_next_sibling_object_number()
            child   = obj.get_child_object_number()
        except Exception as e:
            self.screen.print_str(f"[Error reading object {obj_num}: {e}]\n")
            return

        def name(n):
            if n == 0:
                return "none"
            try:
                o = self.processor.object_table.get_object_table_entry(n)
                d = o.get_property_table().get_description().strip() if o else ""
                return f"#{n} \"{d}\"" if d else f"#{n}"
            except Exception:
                return f"#{n}"

        self.screen.print_str(f"[Obj#{obj_num}: \"{desc}\"]\n")
        self.screen.print_str(f"  Parent:  {name(parent)}\n")
        self.screen.print_str(f"  Sibling: {name(sibling)}\n")

        # Walk child chain
        children = []
        c = child
        seen = set()
        while c and c not in seen:
            seen.add(c)
            children.append(name(c))
            try:
                co = self.processor.object_table.get_object_table_entry(c)
                c = co.get_next_sibling_object_number() if co else 0
            except Exception:
                break
        if children:
            self.screen.print_str(f"  Children ({len(children)}):\n")
            for ch in children:
                self.screen.print_str(f"    {ch}\n")
        else:
            self.screen.print_str(f"  Children: none\n")
        self.screen.refresh()

    def _dump_globals(self, count):
        """Print first N globals; flag those pointing to named objects."""
        obj_count = self.processor.object_table.object_count
        self.screen.print_str(f"[Globals 0-{count - 1}:]\n")
        for g in range(count):
            try:
                val = self.processor.globals.read_global(g)
                note = ""
                if 1 <= val <= obj_count:
                    obj = self.processor.object_table.get_object_table_entry(val)
                    if obj:
                        desc = obj.get_property_table().get_description().strip()
                        if desc:
                            parent_num = obj.get_parent_object_number()
                            parent_named = False
                            if parent_num:
                                p = self.processor.object_table.get_object_table_entry(parent_num)
                                if p and p.get_property_table().get_description().strip():
                                    parent_named = True
                            tag = "room?" if not parent_named else "item?"
                            note = f'  [{tag}] "{desc}"'
                self.screen.print_str(f"  G{g:02d} = {val:5d} (0x{val:04X}){note}\n")
            except Exception:
                self.screen.print_str(f"  G{g:02d} = ?\n")
        self.screen.refresh()

    def _get_input_line(self, max_chars, time_tenths, time_routine):
        script_line = self.scripting.get_line() if self.scripting is not None else None
        if script_line is not None:
            return script_line

        if self.show_location:
            loc = self._current_location_str()
            if loc:
                self.screen.print_location_prompt(f'[{loc}]')

        cb = (lambda: self.processor.call_and_run(time_routine, [])) if (time_tenths and time_routine) else None
        return self.screen.read_line(max_chars, time_tenths, cb)

    def _read_single_char(self, time_tenths, time_routine):
        script_line = self.scripting.get_line() if self.scripting is not None else None
        if script_line is not None:
            ch = script_line[0] if script_line else '\r'
            return ch

        cb = (lambda: self.processor.call_and_run(time_routine, [])) if (time_tenths and time_routine) else None
        return self.screen.read_char(time_tenths, cb)

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
        # Position in parse buffer counts from start of text_buf:
        # V1-3: text starts at byte 1, so offset = 1
        # V4+:  text starts at byte 2 (byte 1 is the length count), so offset = 2
        text_offset = 2 if self.processor.game_version >= 4 else 1

        for i, (word, start_pos) in enumerate(words):
            token_addr = token_data_start + (i * 4)

            encoded_zstring = ZStrings.convertToEncodedWords(word, key_words)

            dict_addr = self.dictionary.find_phrase(encoded_zstring)
            if dict_addr is None:
                dict_addr = 0

            Utils.mwrite_word(self.processor.memory, token_addr, dict_addr)
            Utils.mwrite_byte(self.processor.memory, token_addr + 2, len(word))
            Utils.mwrite_byte(self.processor.memory, token_addr + 3, start_pos + text_offset)

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
        self.screen.print_str("Save to file: ")
        self.screen.refresh()
        in_string = self.screen.read_line(128).strip()
        if not in_string:
            in_string = "save.qzl"
        q = Quetzal(self.processor.filename)
        q.write_quetzal_save(self.processor.memory, self.processor.purbot,
                             self.processor.stack, self.processor.get_pc(), in_string)
        self.processor.save_succeeded()

    def instruction_restore(self, args):
        self.screen.print_str("Restore from file: ")
        self.screen.refresh()
        in_string = self.screen.read_line(128).strip()
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
        self.screen.split_window(args[0])

    def instruction_set_window(self, args):
        self.screen.set_window(args[0])

    def instruction_erase_window(self, args):
        win = Utils.from_unsigned_word_to_signed_int(args[0])
        self.screen.erase_window(win)

    def instruction_erase_line(self, args):
        self.screen.erase_line()

    def instruction_set_cursor(self, args):
        row = args[0]
        col = args[1] if len(args) > 1 else 1
        self.screen.set_cursor(row, col)

    def instruction_get_cursor(self, args):
        row, col = self.screen.get_cursor()
        array_addr = args[0]
        Utils.mwrite_word(self.processor.memory, array_addr,     row)
        Utils.mwrite_word(self.processor.memory, array_addr + 2, col)

    def instruction_set_text_style(self, args):
        self.screen.set_text_style(args[0])

    def instruction_set_colour(self, args):
        fg = args[0] if len(args) > 0 else 1
        bg = args[1] if len(args) > 1 else 1
        self.screen.set_colour(fg, bg)

    def instruction_buffer_mode(self, args):
        pass  # buffering is handled transparently by Screen

    def instruction_show_status(self, args):
        pass  # V4+ game manages its own upper window; V1-3 status is not needed here

    def instruction_sound_effect(self, args):
        pass  # no-op: sound data requires a Blorb resource file

    def instruction_nop(self, args):
        pass

    ################################################################################################
    # Output / Input Stream                                                                        #
    ################################################################################################

    def instruction_output_stream(self, args):
        stream = Utils.from_unsigned_word_to_signed_int(args[0])
        if stream == 1:
            self.stream1_active = True
        elif stream == -1:
            self.stream1_active = False
        elif stream == 2:
            pass  # transcript enable: handled by meta-command #transcript
        elif stream == -2:
            self.screen.close_transcript()
        elif stream == 3:
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
        import array as _array
        stack = self.processor.stack
        self._undo_stack.append({
            'pc':          self.processor.pc,
            'memory':      _array.array('B', self.processor.memory),
            'stack_data':  _array.array('L', stack.stack),
            'sp':          stack.sp,
            'fp':          stack.fp,
            'frame_count': stack.frame_count,
        })
        if len(self._undo_stack) > self._undo_max_depth:
            self._undo_stack.pop(0)   # discard oldest
        self.processor.store(1)

    def instruction_restore_undo(self, args):
        if not self._undo_stack:
            self.processor.store(0)
            return
        s = self._undo_stack.pop()
        mem = self.processor.memory
        for i, b in enumerate(s['memory']):
            mem[i] = b
        stack = self.processor.stack
        for i, w in enumerate(s['stack_data']):
            stack.stack[i] = w
        stack.sp          = s['sp']
        stack.fp          = s['fp']
        stack.frame_count = s['frame_count']
        self.processor.set_pc(s['pc'])
        self.processor.store(2)

    ################################################################################################
    # Misc                                                                                         #
    ################################################################################################

    def instruction_quit(self, args):
        sys.exit(0)

    def instruction_restart(self, args):
        raise _RestartRequested()


