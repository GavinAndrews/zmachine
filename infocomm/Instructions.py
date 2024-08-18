import sys
from enum import IntEnum

import ZStrings
from Utils import Utils


class OpcodeType(IntEnum):
    z_0OP = 0
    z_1OP = 1
    z_2OP = 2
    z_VAR = 3


class Instructions:
    def __init__(self, processor, stack):

        self.processor = processor
        self.stack = stack
        self.quiet = False

        self.op0_functions = [self.instruction_rtrue, self.instruction_rfalse, self.instruction_print,
                              self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.instruction_ret_popped, self.unimplemented, self.unimplemented,
                              self.instruction_new_line,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op1_functions = [self.instruction_jz, self.instruction_get_sibling, self.instruction_get_child,
                              self.instruction_get_parent,
                              self.unimplemented, self.instruction_inc, self.instruction_dec, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.instruction_print_obj, self.instruction_ret,
                              self.instruction_jump, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op2_functions = [self.illegal, self.instruction_je, self.instruction_jl, self.instruction_jg,
                              self.instruction_dec_chk, self.instruction_inc_chk, self.instruction_jin,
                              self.unimplemented,
                              self.instruction_or, self.instruction_and, self.instruction_test_attr,
                              self.instruction_set_attr,
                              self.instruction_clear_attr, self.instruction_store, self.instruction_insert_obj,
                              self.instruction_loadw,
                              self.instruction_loadb, self.instruction_get_prop, self.unimplemented, self.unimplemented,
                              self.instruction_add, self.instruction_sub, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.var_functions = [self.instruction_call, self.instruction_storew, self.instruction_storeb,
                              self.instruction_put_prop,
                              self.instruction_read, self.instruction_print_char, self.instruction_print_num,
                              self.unimplemented,
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
                    f"EXECUTE: {current_pc:04X} {opcode:02X} {implementation.__name__.replace("instruction_", ""):12} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")
            implementation(args)
        except RuntimeError as re:
            print(f"{re} : {current_pc:04X} {opcode:02X} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")
            self.stack.dump()
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
            self.stack.push_word(value)
        elif variable < 16:
            self.stack.write_local(variable, value)
        else:
            self.processor.globals.write_global(variable - 16, value)

    def instruction_storeb(self, args):
        raise RuntimeError("Unimplemented storeb")

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
        property_table_entry = self.processor.object_table.get_property_table_entry(object_number, property_number)
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

    def instruction_other(self, args):
        raise RuntimeError("Unimplemented " + __name__)

    def instruction_print(self, args):
        self.processor.print_embedded()

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
        self.processor.object_table.insert_object(moving_object, destination_object)

    def instruction_push(self, args):
        self.stack.push_word(args[0])

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
        print(object_table_entry.get_description(), end="")

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
            value = object_table_entry.get_property_table_entry_value(property_number)
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
        value = self.stack.pop_word()
        self.processor.ret(value)

    def instruction_read(self, args):
        text_addr = args[0]
        parse_addr = args[1]

        in_string = "open      mailbox"

        max_chars = Utils.mread_byte(self.processor.memory, text_addr)
        print(max_chars, end="")

        seperators = self.processor.dictionary.get_seperators()
        in_string = in_string.lower()

        words = []
        start = None
        current = ""
        for index, c in enumerate(in_string):
            if c != ' ':
                if start is None:
                    start = index
                current += c
            else:
                if len(current) > 0:
                    words.append((start, current))
                start = None
                current = ""
        if len(current) > 0:
            words.append((start, current))

        print(words)
        pass
