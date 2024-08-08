from enum import IntEnum


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

    def execute(self, op_type, op_number, args):
        self.all_functions[op_type][op_number](args)

    def unimplemented(self, args):
        self.stack.dump()
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
        print(f"Call to {address*2:04X}, args: {args}")
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

        self.stack.dump()


    def store(self, param):
        raise RuntimeError("Unimplemented call")

    def instruction_storew(self, args):
        raise RuntimeError("Unimplemented storew")

    def instruction_storeb(self, args):
        raise RuntimeError("Unimplemented storeb")

    def instruction_add(self, args):
        self.processor.store(args[0]+args[1])
