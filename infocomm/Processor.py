from enum import IntEnum

from Instructions import Instructions, OpcodeType
from Stack import Stack


class OpcodeForm(IntEnum):
    VARIABLE = 0b11
    SHORT = 0b10
    LONG_0 = 0b00
    LONG_1 = 0b01


class OperandCount(IntEnum):
    z_VAR = 0
    z_2OP = 1
    z_1OP = 2
    z_0OP = 3


class OperandType(IntEnum):
    LARGE = 0b00
    SMALL_CONSTANT = 0b01
    VARIABLE = 0b10
    OMITTED = 0b11


class Processor:
    def __init__(self, memory, start, globals):
        self.memory = memory
        self.pc = start
        self.globals = globals
        self.args = []
        self.stack = Stack()
        self.instructions = Instructions(self, self.stack)

    def next_instruction(self):
        opcode = self.get_byte_and_advance()
        opcode_form = OpcodeForm(opcode >> 6)

        args = []

        print(f"OPCODE: {opcode:02X} {opcode_form:02b}")
        match opcode_form:
            case opcode_form.LONG_0 | opcode_form.LONG_1:  # opcode < 0x80
                operand_count = OperandCount.z_2OP
                operand_type1 = OperandType.SMALL_CONSTANT if opcode & 0x40 == 0 else OperandType.VARIABLE
                self.load_operand(operand_type1, args)
                operand_type2 = OperandType.SMALL_CONSTANT if opcode & 0x20 == 0 else OperandType.VARIABLE
                self.load_operand(operand_type2, args)
                op_number = opcode & 0b11111
                self.instructions.execute(OpcodeType.z_2OP, op_number, args)

            case opcode_form.SHORT:
                operand_type1 = OperandType((opcode >> 4) & 0x03)
                op_number = opcode & 0b1111
                if operand_type1 == OperandType.OMITTED:
                    # 0 OP
                    self.instructions.execute(OpcodeType.z_0OP, op_number, args)
                else:
                    # 1 OP
                    self.load_operand(operand_type1, args)
                    self.instructions.execute(OpcodeType.z_1OP, op_number, args)

            case opcode_form.VARIABLE:
                operand_count = OperandCount.z_2OP if opcode & 0b00100000 == 0 else OperandCount.z_VAR
                print(f"Form: {opcode_form.name}, OperandCount: {operand_count.name}")
                op_number = opcode & 0b11111

                var_operand_types = self.get_byte_and_advance()
                self.load_operands(var_operand_types, args)
                self.instructions.execute(OpcodeType.z_VAR, op_number, args)

    def load_operand(self, operand_type, args):
        match operand_type:
            case OperandType.LARGE:
                value = self.get_word_and_advance()
            case OperandType.SMALL_CONSTANT:
                value = int(self.get_byte_and_advance())
            case OperandType.VARIABLE:
                variable = int(self.get_byte_and_advance())
                # Three types... 0 top of stack, <16 locals, else globals
                if variable == 0:
                    value = self.stack.pop_word()
                elif variable < 16:
                    value = self.stack.read_local(variable)
                else:
                    value = self.globals.read_global(variable-16)

        args.append(value)

    def load_operands(self, var_operand_types, args):
        for i in range(6, -1, -2):
            operand_type = var_operand_types >> i & 0b11
            if operand_type == OperandType.OMITTED:
                break
            self.load_operand(operand_type, args)

    def get_byte_and_advance(self):
        v = self.memory[self.pc]
        self.pc += 1
        return v

    def get_word_and_advance(self):
        v = int.from_bytes(self.memory[self.pc:self.pc + 2], 'big')
        self.pc += 2
        return v

    def get_pc(self):
        return self.pc

    def set_pc(self, new_address):
        self.pc = new_address

    def store(self, value):
        variable = int(self.get_byte_and_advance())
        # Three types... 0 top of stack, <16 locals, else globals
        if variable == 0:
            self.stack.push_word(value)
        elif variable < 16:
            self.stack.write_local(variable, value)
        else:
            self.globals.write_global(variable-16, value)

    # https://zspec.jaredreisinger.com/
