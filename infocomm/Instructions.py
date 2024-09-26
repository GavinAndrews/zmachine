import sys
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


class Instructions:
    def __init__(self, processor: Processor, dictionary, scripting):

        self.processor = processor
        self.quiet = True
        self.check_trace = False
        self.dictionary = dictionary
        self.scripting = scripting
        self.random = 0x1234

        if self.check_trace:
            self.trace_file = TraceFile("H:\\linux_trace.txt")

        self.op0_functions = [self.instruction_rtrue, self.instruction_rfalse, self.instruction_print,
                              self.instruction_print_ret,
                              self.unimplemented, self.instruction_save, self.instruction_restore, self.unimplemented,
                              self.instruction_ret_popped, self.unimplemented, self.instruction_quit,
                              self.instruction_new_line,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op1_functions = [self.instruction_jz, self.instruction_get_sibling, self.instruction_get_child,
                              self.instruction_get_parent,
                              self.instruction_get_prop_len, self.instruction_inc, self.instruction_dec,
                              self.unimplemented,
                              self.unimplemented, self.instruction_remove_object, self.instruction_print_obj, self.instruction_ret,
                              self.instruction_jump, self.instruction_print_paddr, self.instruction_load,
                              self.unimplemented]

        self.op2_functions = [self.illegal, self.instruction_je, self.instruction_jl, self.instruction_jg,
                              self.instruction_dec_chk, self.instruction_inc_chk, self.instruction_jin,
                              self.instruction_test,
                              self.instruction_or, self.instruction_and, self.instruction_test_attr,
                              self.instruction_set_attr,
                              self.instruction_clear_attr, self.instruction_store, self.instruction_insert_obj,
                              self.instruction_loadw,
                              self.instruction_loadb, self.instruction_get_prop, self.instruction_get_prop_addr,
                              self.instruction_get_next_prop,
                              self.instruction_add, self.instruction_sub, self.instruction_mul, self.instruction_div,
                              self.instruction_mod, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.var_functions = [self.instruction_call, self.instruction_storew, self.instruction_storeb,
                              self.instruction_put_prop,
                              self.instruction_read, self.instruction_print_char, self.instruction_print_num,
                              self.instruction_random,
                              self.instruction_push, self.instruction_pull, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.all_functions = [self.op0_functions, self.op1_functions, self.op2_functions, self.var_functions]

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

            implementation(args)
        except RuntimeError as re:
            print(f"{re} : {current_pc:04X} {opcode:02X} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")
            self.processor.stack.dump()
            sys.exit(101)

    def unimplemented(self, args):
        raise RuntimeError("Unimplemented function")

    def illegal(self, args):
        raise RuntimeError("Illegal function")

    ################################################################################################
    # VAR Instructions # VAR Instructions # VAR Instructions # VAR Instructions # VAR Instructions #
    ################################################################################################
    def instruction_call(self, args):
        if args[0] == 0x0000:
            # When the address 0 is called as a routine, nothing happens and the return value is false.
            self.processor.store(0)
        else:
            self.processor.call(args[0], args[1:], 0)

    # storew
    # args[0] address of table, [1] index in table, [2] value
    def instruction_storew(self, args):
        self.processor.storew(args[0] + 2 * args[1], args[2])

    def instruction_store(self, args):
        variable = args[0]
        value = args[1]
        # Three types... 0 top of stack, <16 locals, else globals
        if variable == 0:
            self.processor.stack.push_word(value)
        elif variable < 16:
            self.processor.stack.write_local(variable, value)
        else:
            self.processor.globals.write_global(variable - 16, value)

    def instruction_storeb(self, args):
        table_address = args[0]
        offset = args[1]
        value = args[2]
        Utils.mwrite_byte(self.processor.memory, table_address + offset, value)

    def instruction_add(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = a0 + a1
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_sub(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = a0 - a1
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_mul(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = a0 * a1
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_div(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = int(a0 / a1)
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_mod(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = a0 % a1
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))

    def instruction_je(self, args):
        # Jump if a is equal to any of the subsequent operands. (Thus @je a never jumps and @je a b jumps if a = b.)
        match = False
        for i in range(1, len(args)):
            if args[0] == args[i]:
                match = True
                break
        self.processor.branch(match)

    def instruction_jz(self, args):
        self.processor.branch(args[0] == 0)

    def instruction_jl(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.branch(a0 < a1)

    def instruction_jg(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.branch(a0 > a1)

    def instruction_ret(self, args):
        self.processor.ret(args[0])

    def instruction_put_prop(self, args):
        object_number = args[0]
        property_number = args[1]
        property_value = args[2]
        property_table_entry = self.processor.object_table.get_object_table_entry(object_number).get_property_table().get_property_table_entry_for_property_number(property_number)
        property_table_entry.put_value(property_value)

    # test_attr object attribute?(label)
    def instruction_test_attr(self, args):
        object_number = args[0]
        attribute_number = args[1]
        object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
        result = object_table_entry.test_attr(attribute_number)
        self.processor.branch(result)

    def instruction_set_attr(self, args):
        object_number = args[0]
        attribute_number = args[1]
        object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
        object_table_entry.set_attr(attribute_number)

    def instruction_clear_attr(self, args):
        object_number = args[0]
        attribute_number = args[1]
        object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
        object_table_entry.clear_attr(attribute_number)

    def instruction_new_line(self, args):
        print("")

    def instruction_loadb(self, args):
        value = self.processor.loadb(args[0] + args[1])
        self.processor.store(value)

    def instruction_loadw(self, args):
        value = self.processor.loadw(args[0] + 2 * args[1])
        self.processor.store(value)

    def instruction_or(self, args):
        self.processor.store(args[0] | args[1])

    def instruction_and(self, args):
        self.processor.store(args[0] & args[1])

    def instruction_print_num(self, args):
        value = Utils.from_unsigned_word_to_signed_int(args[0])
        print(value, end="")

    def instruction_print_char(self, args):
        print(ZStrings.singleZSCIIChar(args[0]), end="")

    def instruction_dec(self, args):
        self.processor.adjust_variable(args[0], -1)

    def instruction_dec_chk(self, args):
        result = self.processor.adjust_variable(args[0], -1)
        compare = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.branch(result < compare)

    def instruction_inc(self, args):
        self.processor.adjust_variable(args[0], 1)

    def instruction_inc_chk(self, args):
        result = self.processor.adjust_variable(args[0], 1)
        compare = Utils.from_unsigned_word_to_signed_int(args[1])
        self.processor.branch(result > compare)

    def instruction_jump(self, args):
        delta = Utils.from_unsigned_word_to_signed_int(args[0]) - 2
        self.processor.jump(delta)

    def instruction_rtrue(self, args):
        self.processor.ret(1)

    def instruction_rfalse(self, args):
        self.processor.ret(0)

    # z_insert_obj, make an object the first child of another object.
    #
    # args[0] : object to be moved
    # args[1] : destination object
    def instruction_insert_obj(self, args):
        moving_object = args[0]
        destination_object = args[1]
        # print(f"Move Object [{moving_object}]"
        #       f"{self.processor.object_table.get_object_table_entry(moving_object).get_property_table().get_description()} "
        #       f"to [{destination_object}]"
        #       f"{self.processor.object_table.get_object_table_entry(destination_object).get_property_table().get_description()}")
        self.processor.object_table.insert_object(moving_object, destination_object)

    def instruction_push(self, args):
        self.processor.stack.push_word(args[0])

    def instruction_pull(self, args):
        self.processor.pull(args[0])

    # jin obj1 obj2?(label)
    # Jump if object a is a direct child of b, i.e., if parent of a is b.
    def instruction_jin(self, args):
        child = args[0]
        parent = args[1]

        if child == 0:
            self.processor.branch(parent == 0)
        else:
            child_table_entry = self.processor.object_table.get_object_table_entry(child)
            self.processor.branch(child_table_entry.get_parent_object_number() == parent)

    # print_obj object
    # Print short name of object (the Z-encoded string in the object header, not a property).
    # If the object number is invalid, the interpreter should halt with a suitable error message.
    def instruction_print_obj(self, args):
        object_number = args[0]
        object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
        print(object_table_entry.get_property_table().get_description(), end="")

    # get_parent object → (result)
    # Get parent object (note that this has no “branch if exists” clause).
    def instruction_get_parent(self, args):
        object_number = args[0]
        object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
        parent = object_table_entry.get_parent_object_number()
        self.processor.store(parent)

    # get_child object → (result)?(label)
    # Get first object contained in given object, branching if this exists, i.e. is not nothing (i.e., is not 0).
    def instruction_get_child(self, args):
        object_number = args[0]
        if object_number == 0:
            first_child = 0
        else:
            object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
            first_child = object_table_entry.get_child_object_number()
        self.processor.store(first_child)
        self.processor.branch(first_child != 0)

    def instruction_v9(self, args):
        raise RuntimeError("Unimplemented " + __name__)

    # get_prop object property → (result)
    # Read property from object (resulting in the default value if it had no such declared property).
    # If the property has length 1, the value is only that byte.
    # If it has length 2, the first two bytes of the property are taken as a word value.
    # It is illegal for the opcode to be used if the property has length greater than 2, and the result is unspecified.
    def instruction_get_prop(self, args):
        object_number = args[0]
        if object_number == 0:
            self.processor.store(0)
        else:
            property_number = args[1]
            object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
            property = object_table_entry.get_property_table().get_property_table_entry_for_property_number(property_number)
            if property is None:
                value = self.processor.object_table.get_property_default(property_number)
            else:
                value = property.get_value()
            self.processor.store(value)

    # get_sibling object → (result)?(label)
    # Get next object in tree, branching if this exists, i.e. is not 0.
    def instruction_get_sibling(self, args):
        object_number = args[0]
        if object_number == 0:
            next_sibling = 0
        else:
            object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
            next_sibling = object_table_entry.get_next_sibling_object_number()
        self.processor.store(next_sibling)
        self.processor.branch(next_sibling != 0)

    # ret_popped
    # Pops top of stack and returns that. (This is equivalent to ret sp, but is one byte cheaper.)
    def instruction_ret_popped(self, args):
        value = self.processor.stack.pop_word()
        self.processor.ret(value)

    def instruction_read(self, args):
        text_addr = args[0]
        parse_addr = args[1]

        max_chars = Utils.mread_byte(self.processor.memory, text_addr)
        text_addr += 1

        # print(f"max_chars={max_chars}")

        separators = set(self.dictionary.get_seperators())
        space_in_separators = ' ' in separators
        if not space_in_separators:
            separators.add(" ")

        script_line = self.scripting.get_line() if self.scripting is not None else None
        if script_line is not None:
            in_string = script_line
        else:
            # Dump Location
            print(f"[{self.processor.object_table.get_object_table_entry(4).get_parent_object_number()}] ", end="")
            in_string = input()  # "open mailbox"
        in_string = in_string.lower()

        for index, c in enumerate(in_string):
            Utils.mwrite_byte(self.processor.memory, text_addr + index, ord(c) & 0xFF)

        # Null terminator
        Utils.mwrite_byte(self.processor.memory, text_addr + len(in_string), 0)

        words = []
        start = 0
        current_word = ""
        for i, c in enumerate(in_string):
            if c in separators:
                if len(current_word) > 0:
                    words.append((start, current_word))
                    current_word = ""
                if c != ' ' or space_in_separators:
                    words.append((i, c))
                start = i + 1
            else:
                current_word = current_word + c

        # Last Word
        if len(current_word) > 0:
            words.append((start, current_word))

        max_tokens = Utils.mread_byte(self.processor.memory, parse_addr)
        parse_addr += 1

        # print(f"max_tokens={max_tokens}")

        # Token Count
        Utils.mwrite_byte(self.processor.memory, parse_addr, len(words))
        parse_addr += 1

        # TODO Max Tokens Exceeded?

        # Now Tokenize words...
        for start, word in words:

            encoded_zstring = ZStrings.convertToEncodedWords(word)

            result = self.dictionary.find_phrase(encoded_zstring)

            if result is not None:
                dictionary_table_entry = self.dictionary.find(result)
                dict_addr = dictionary_table_entry.get_start_address()
                Utils.mwrite_word(self.processor.memory, parse_addr, dict_addr)
            else:
                Utils.mwrite_word(self.processor.memory, parse_addr, 0)

            parse_addr += 2

            Utils.mwrite_byte(self.processor.memory, parse_addr, len(word))
            parse_addr += 1

            Utils.mwrite_byte(self.processor.memory, parse_addr, start + 1)
            parse_addr += 1

    def instruction_test(self, args):
        bitmap = args[0]
        flags = args[1]
        self.processor.branch(bitmap & flags == flags)

    def instruction_get_prop_addr(self, args):
        object_number = args[0]
        if object_number == 0:
            self.processor.store(0)
        else:
            mask = 0x1f
            property_number = args[1] & mask
            object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
            addr = object_table_entry.get_property_table().get_property_table_entry_address(property_number)
            # +1 to skip size byte in property table entry
            if addr is not None:
                self.processor.store(addr + 1)
            else:
                self.processor.store(0)

    def instruction_other(self, args):
        raise RuntimeError("Unimplemented " + __name__)

    #
    # get_prop_len property-address → (result)
    #
    # Get length of property data (in bytes) for the given object’s property. It is illegal to try to find the property
    # length of a property which does not exist for the given object, and an interpreter should halt with an error
    # message (if it can efficiently check this condition).
    #

    def instruction_get_prop_len(self, args):
        addr = args[0]
        # @get_prop_len 0 must return 0. This is required by some Infocom games and files generated by old versions of Inform.
        if addr == 0:
            self.processor.store(0)
        else:
            # Move back from data to length byte
            addr -= 1

            # V1-3 only, TODO Add later version support
            property_length = (Utils.mread_byte(self.processor.memory, addr) >> 5) + 1

            self.processor.store(property_length)

    def instruction_print(self, args):
        self.processor.print_embedded()

    # print_ret
    # 0OP:179 3 print_ret <literal-string>
    # Print the quoted (literal) Z-encoded string, then print a new-line and then return true (i.e., 1).
    def instruction_print_ret(self, args):
        self.processor.print_embedded()
        print("")  # New Line
        self.processor.ret(1)

    def instruction_print_paddr(self, args):
        self.processor.print_paddr(args[0])

    def instruction_quit(self, args):
        sys.exit(0)

    def instruction_load(self, args):
        variable = args[0]
        if variable == 0:
            value = self.processor.stack.peek_word()
        elif variable < 16:
            value = self.processor.stack.read_local(variable)
        else:
            value = self.processor.globals.read_global(variable - 16)
        self.processor.store(value)

    def instruction_random(self, args):
        range = args[0]
        self.random = (self.random * 0x343FD + 0x269EC3) & 0x7FFFFFFF
        n = (self.random >> 16) & 0x7FFF
        result = n % range + 1
        self.processor.store(result)

    # get_next_prop
    # 2OP:19 13
    # get_next_prop object property → (result)
    #
    # Gives the number of the next property provided by the quoted object. This may be zero, indicating the end of
    # the property list; if called with zero, it gives the first property number present. It is illegal to try to find
    # the next property of a property which does not exist, and an interpreter should halt with an error message
    # (if it can efficiently check this condition).
    def instruction_get_next_prop(self, args):
        object_number = args[0]
        if object_number == 0:
            self.processor.store(0)
        else:
            property_number = args[1]
            object_table_entry = self.processor.object_table.get_object_table_entry(object_number)
            value = object_table_entry.get_property_table().get_property_table_entry_after_property_number(property_number)
            if value is None:
                self.processor.store(0)
            else:
                self.processor.store(value.get_property_number())

    def instruction_remove_object(self, args):
        moving_object = args[0]
        # print(f"Remove Object [{moving_object}]"
        #       f"{self.processor.object_table.get_object_table_entry(moving_object).get_property_table().get_description()} ")
        self.processor.object_table.remove_object(moving_object)


    def instruction_restore(self, args):
        print(f"Restore from file:  ", end="")
        in_string = input()  # "z1.s1"
        q = Quetzal(self.processor.filename)
        q.read_quetzal_save(in_string)
        q.process_file()

        self.processor.restore(q.game_data, q.new_stack)

    def instruction_save(self, args):
        print(f"Restore from file:  ", end="")
        in_string = "z1.s0" # input()  # "z1.s1"
        q = Quetzal(self.processor.filename)
        q.write_quetzal_save(self.processor.memory, self.processor.stack, self.processor.get_pc(), in_string)
        raise RuntimeError("Unimplemented " + __name__)




