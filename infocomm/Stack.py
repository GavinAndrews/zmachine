import array
import itertools


class Stack:
    def __init__(self):
        self.stack = array.array("L", itertools.repeat(0, 1024))
        self.sp = 1024
        self.fp = 1024
        self.frame_count = 0

    def push_word(self, value):
        self.sp -= 1
        self.stack[self.sp] = value

    def pop_word(self):
        value = self.stack[self.sp]
        self.sp += 1
        return value

    def peek_word(self):
        value = self.stack[self.sp]
        return value

    def push_fp(self):
        self.push_word(self.fp-1)

    def pop_fp(self):
        self.fp = self.pop_word()+1

    def mark_frame(self):
        self.fp = self.sp
        self.frame_count += 1

    def unmark_frame(self):
        self.sp = self.fp
        self.frame_count -= 1

    def fixup_frame(self, local_var_count):
        self.stack[self.fp] |= local_var_count << 8

    # local_number 1..15, since fp points to stack element before locals... fp+1 is first local
    def read_local(self, local_number):
        value = self.stack[self.fp-local_number]
        return value

    def write_local(self, local_number, value):
        self.stack[self.fp-local_number] = value

    def dump(self):
        print("-"*20+" STACK "+"-"*20)
        for i, w in enumerate(self.stack):
            if i >= self.sp:
                print(f"{i:4} : {w:04X}", end="")
                if self.sp == i:
                    print(" <<<<<<<<<< SP", end="")
                if self.fp == i:
                    print(" <<<<<<<<<< FP", end="")
                print()
        print("-"*20+"-------"+"-"*20)