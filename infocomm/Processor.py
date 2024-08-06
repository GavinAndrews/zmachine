from collections import deque
from enum import IntEnum

from Instructions import Instructions, OpcodeType


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
    def __init__(self, memory, start):
        self.memory = memory
        self.pc = start
        self.frames = deque()
        self.args = []
        self.instructions = Instructions()

    def next_instruction(self):
        opcode = self.get_byte_and_advance()
        opcode_form = OpcodeForm(opcode >> 6)

        self.args = []

        print(f"OPCODE: {opcode:02X} {opcode_form:02b}")
        match opcode_form:
            case opcode_form.LONG_0, opcode_form.LONG_1:  # opcode < 0x80
                operand_count = OperandCount.z_2OP
                operand_type1 = OperandType.SMALL_CONSTANT if opcode & 0x40 == 0 else OperandType.VARIABLE
                self.load_operand(operand_type1)
                operand_type2 = OperandType.SMALL_CONSTANT if opcode & 0x20 == 0 else OperandType.VARIABLE
                self.load_operand(operand_type2)
                op_number = opcode & 0x1F
                self.instructions.execute(OpcodeType.VAR, op_number)

            case opcode_form.SHORT:
                operand_type1 = OperandType((opcode >> 4) & 0x03)
                op_number = opcode & 0x0F
                if operand_type1 == OperandType.OMITTED:
                    # 0 OP
                    self.instructions.execute(OpcodeType.OP0, op_number)
                else:
                    # 1 OP
                    self.load_operand(operand_type1)
                    self.instructions.execute(OpcodeType.OP1, op_number)

            case opcode_form.VARIABLE:
                operand_count = OperandCount.z_2OP if opcode & 0b00100000 == 0 else OperandCount.z_VAR
                print(f"Form: {opcode_form.name}, OperandCount: {operand_count.name}")
                opcode_number = opcode & 0xb11111

                var_operand_types = self.get_byte_and_advance()
                self.load_operands(var_operand_types)

            case _:
                pass

        print(f"OPCODE NUMBER: {opcode_number:02X}")

    def load_operand(self, operand_type):
        match operand_type:
            case OperandType.SMALL_CONSTANT:
                value = int(self.get_byte_and_advance())
            case OperandType.VARIABLE:
                # Three types... 0 top of stack, <16 locals, else globals
                raise RuntimeError("Unimplemented")
                pass
        self.args.append(value)

    def load_operands(self, var_operand_types):
        pass

    def get_byte_and_advance(self):
        v = self.memory[self.pc]
        self.pc += 1
        return v

    # https://zspec.jaredreisinger.com/
