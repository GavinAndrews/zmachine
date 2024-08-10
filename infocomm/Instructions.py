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

        self.op1_functions = [self.instruction_jz, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.instruction_ret,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op2_functions = [self.illegal, self.instruction_je, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.instruction_add, self.instruction_sub, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                              self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.var_functions = [self.instruction_call, self.instruction_storew, self.instruction_storeb,
                              self.instruction_put_prop,
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
            implementation = self.all_functions[op_type][op_number]
            print(f"EXECUTE: {current_pc:04X} {opcode:02X} {implementation.__name__[12:]:12} {op_type.name:5} {op_number:3} {[f'{x:04X}' for x in args]}")
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
            self.store(0)
        else:
            self.processor.call(args[0], args[1:], 0)

    def store(self, param):
        raise RuntimeError("Unimplemented call")

    # storew
    # args[0] address of table, [1] index in table, [2] value
    def instruction_storew(self, args):
        self.processor.storew(args[0] + 2 * args[1], args[2])

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
            if args[0] == args[i - 1]:
                match = True
                break
        self.processor.branch(match)

    def instruction_jz(self, args):
        self.processor.branch(args[0] == 0)

    def instruction_ret(self, args):
        self.processor.ret(args[0])

    def instruction_put_prop(self, args):
        raise RuntimeError("Unimplemented put_prop")
