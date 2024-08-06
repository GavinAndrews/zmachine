from enum import IntEnum


class OpcodeType(IntEnum):
    OP0 = 0
    OP1 = 1
    VAR = 2


class Instructions:
    def __init__(self):
        self.op0_functions = [self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.op1_functions = [self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.var_functions = [self.illegal, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented,
                          self.unimplemented, self.unimplemented, self.unimplemented, self.unimplemented]

        self.all_functions = [self.op0_functions, self.op1_functions, self.var_functions]

    def execute(self, op_type, op_number):
        self.all_functions[op_type][op_number]()

    def unimplemented(self):
        raise RuntimeError("Unimplemented function")

    def illegal(self):
        raise RuntimeError("Illegal function")
