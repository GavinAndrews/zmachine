from enum import IntEnum

import ZStrings
from Instructions import Instructions, OpcodeType
from Stack import Stack
from Utils import Utils


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
    def __init__(self, memory, start, global_variables, object_table, abbreviation_table):
        self.memory = memory
        self.pc = start
        self.globals = global_variables
        self.object_table = object_table
        self.abbreviation_table = abbreviation_table
        self.args = []
        self.stack = Stack()
        self.instructions = Instructions(self, self.stack)

    def next_instruction(self):
        current_pc = self.pc

        if self.pc == 0x5907:
            print("")

        opcode = self.get_byte_and_advance()

        opcode_form = OpcodeForm(opcode >> 6)

        args = []

        match opcode_form:
            case opcode_form.LONG_0 | opcode_form.LONG_1:  # opcode < 0x80
                operand_count = OperandCount.z_2OP
                operand_type1 = OperandType.SMALL_CONSTANT if opcode & 0x40 == 0 else OperandType.VARIABLE
                self.load_operand(operand_type1, args)
                operand_type2 = OperandType.SMALL_CONSTANT if opcode & 0x20 == 0 else OperandType.VARIABLE
                self.load_operand(operand_type2, args)
                op_number = opcode & 0b11111
                self.instructions.execute(OpcodeType.z_2OP, op_number, args, current_pc, opcode)

            case opcode_form.SHORT:
                operand_type1 = OperandType((opcode >> 4) & 0x03)
                op_number = opcode & 0b1111
                if operand_type1 == OperandType.OMITTED:
                    # 0 OP
                    self.instructions.execute(OpcodeType.z_0OP, op_number, args, current_pc, opcode)
                else:
                    # 1 OP
                    self.load_operand(operand_type1, args)
                    self.instructions.execute(OpcodeType.z_1OP, op_number, args, current_pc, opcode)

            case opcode_form.VARIABLE:
                opcode_type = OpcodeType.z_2OP if opcode & 0b00100000 == 0 else OpcodeType.z_VAR
                op_number = opcode & 0b11111

                var_operand_types = self.get_byte_and_advance()
                self.load_operands(var_operand_types, args)
                self.instructions.execute(opcode_type, op_number, args, current_pc, opcode)

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
                    value = self.globals.read_global(variable - 16)

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
            self.globals.write_global(variable - 16, value)

    def branch(self, condition):
        specifier = self.get_byte_and_advance()
        offset_1 = specifier & 0b111111

        if not condition:
            specifier ^= 0x80

        # bit 6 specifies short or long
        if specifier & 0x40 == 0x00:
            # Consider as a signed 16-bit value so if we are -ve, i.e. top bit set
            # make them all set as we expand from 14 bits into 16 bits
            if offset_1 & 0b100000 != 0:
                offset_1 |= 0b11000000
            offset_2 = self.get_byte_and_advance()
            offset = offset_1 << 8 | offset_2
            # Convert to signed
            offset = Utils.from_unsigned_word_to_signed_int(offset)
            pass
        else:
            offset = offset_1

        if specifier & 0x80:
            if offset > 1:
                pc = self.get_pc()
                pc += offset - 2
                self.set_pc(pc)
            else:
                # Special Case 0 False, 1 True
                self.ret(offset)

    def jump(self, delta):
        self.set_pc(self.pc + delta)

    def loadb(self, address):
        return Utils.mread_byte(self.memory, address)

    def loadw(self, address):
        return Utils.mread_word(self.memory, address)

    def storeb(self, address, value):
        Utils.mwrite_byte(self.memory, address, value)

    def storew(self, address, value):
        Utils.mwrite_word(self.memory, address, value)

    def call(self, address, args, call_type):
        # print(f"Call to {address*2:04X}, args: {args}")
        pc = self.get_pc()
        self.stack.push_word(pc >> 9)
        self.stack.push_word(pc & 0x1ff)
        self.stack.push_fp()
        self.stack.push_word(len(args) | (call_type << 12))
        self.stack.mark_frame()

        address *= 2  # V3 Address
        self.set_pc(address)

        local_var_count = self.get_byte_and_advance()
        self.stack.fixup_frame(local_var_count)

        for i in range(0, local_var_count):
            v = self.get_word_and_advance()
            if i < len(args):
                v = args[i]
            self.stack.push_word(v)

    def ret(self, value):
        self.stack.unmark_frame()
        ct = self.stack.pop_word() >> 12
        self.stack.pop_fp()
        pc = self.stack.pop_word()
        pc |= self.stack.pop_word() << 9
        self.set_pc(pc)
        if ct == 0:
            self.store(value)
        else:
            self.stack.push_word(value)

    # https://zspec.jaredreisinger.com/

    def print_embedded(self):
        embedded_string_address = self.get_pc()
        # Advance past string
        while True:
            value = self.get_word_and_advance()
            if value & 0x8000:
                break
        print(ZStrings.toZString(embedded_string_address, self.memory, self.abbreviation_table), end="")

    def adjust_variable(self, variable, delta):
        # Three types... 0 top of stack, <16 locals, else globals
        if variable == 0:
            value = self.stack.pop_word()
        elif variable < 16:
            value = self.stack.read_local(variable)
        else:
            value = self.globals.read_global(variable - 16)

        value = Utils.from_unsigned_word_to_signed_int(value)
        result = value + delta
        value = Utils.from_signed_int_to_unsigned_word(result)

        # Three types... 0 top of stack, <16 locals, else globals
        if variable == 0:
            self.stack.push_word(value)
        elif variable < 16:
            self.stack.write_local(variable, value)
        else:
            self.globals.write_global(variable - 16, value)

        return result

    def pull(self, destination):
        value = self.stack.pop_word()
        if destination == 0:
            self.stack.push_word(value)
        elif destination < 16:
            self.stack.write_local(destination, value)
        else:
            self.globals.write_global(destination - 16, value)

