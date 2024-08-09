import sys
from enum import IntEnum

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

        self.op0_functions = [self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op1_functions = [self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op2_functions = [self.illegal, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.instruction_add, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.var_functions = [self.instruction_call, self.instruction_storew, self.instruction_storeb,
                              self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.all_functions = [self.op0_functions, self.op1_functions, self.op2_functions, self.var_functions]

    def execute(self, op_type, op_number, args, current_pc, opcode):
        try:
            print(f"EXECUTE: {current_pc:04X} {opcode:02X} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")
            self.all_functions[op_type][op_number](args)
        except RuntimeError as  re:
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
            self.store(0)
        else:
            self.do_call(args[0], args[1:], 0)

    def do_call(self, address, args, call_type):
        # print(f"Call to {address*2:04X}, args: {args}")
        pc = self.processor.get_pc()
        self.stack.push_word(pc >> 9)
        self.stack.push_word(pc & 0x1ff)
        self.stack.push_fp()
        self.stack.push_word(len(args) | (call_type << 12))
        self.stack.new_frame()

        address *= 2  # V3 Address
        self.processor.set_pc(address)

        local_var_count = self.processor.get_byte_and_advance()
        self.stack.fixup_frame(local_var_count)

        for i in range(0, local_var_count):
            v = self.processor.get_word_and_advance()
            if i < len(args):
                v = args[i]
            self.stack.push_word(v)



    def store(self, param):
        raise RuntimeError("Unimplemented call")

    def instruction_storew(self, args):
        raise RuntimeError("Unimplemented storew")

    def instruction_storeb(self, args):
        raise RuntimeError("Unimplemented storeb")

    def instruction_add(self, args):
        # Arithmetic is Signed, Args and Stack etc are considered unsigned
        a0 = Utils.from_unsigned_word_to_signed_int(args[0])
        a1 = Utils.from_unsigned_word_to_signed_int(args[1])
        result = a0 + a1
        self.processor.store(Utils.from_signed_int_to_unsigned_word(result))
