import array
import itertools
import rich


class Stack:
    def __init__(self):
        self.stack_size = 1024
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

        # Build Frame indices: These are indices to the word BEFORE the frame
        frames = list()
        frames.append(self.sp)
        i = self.fp + 4
        while i < self.stack_size + 4:
            frames.append(i)
            next_fp = self.stack[i - 3]  # Look back 3 words to FP
            i = next_fp + 4 + 1  # Advance over Arg Count and Flags, FP and PC LO, PC HI WORDS and then 1 more

        print("-"*20+" STACK "+"-"*20)
        for i, w in enumerate(self.stack):
            if i >= self.sp:
                print(f"{i:04X} : {w:04X}", end="")
                if self.sp == i:
                    rich.print("[bold red] <<<<<<<<<< SP[/bold red]", end="")
                if self.fp == i:
                    print(" <<<<<<<<<< FP", end="")
                if i in frames :
                    rich.print("[bold blue]  <<<<<<<<<< FRAME[/bold blue]", end="")
                print()
        print("-"*20+"-------"+"-"*20)