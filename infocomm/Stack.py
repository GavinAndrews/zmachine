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

    def push_fp(self):
        self.push_word(self.fp-1)

    def new_frame(self):
        self.fp = self.sp
        self.frame_count += 1

    def fixup_frame(self, local_var_count):
        self.stack[self.fp] |= local_var_count << 8

    def dump(self):
        print("-"*20+" STACK "+"-"*20)
        for i, w in enumerate(self.stack):
            if i >= self.sp:
                print(f"{i:4} : {w:04X}")
        print("-"*20+"-------"+"-"*20)