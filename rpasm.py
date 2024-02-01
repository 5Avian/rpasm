#!/usr/bin/env python

from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Generator, Iterator, TextIO

PREFIXES = [
    "$",
    "@",
    "?",
    ":",
    "#",
    ".",
]
TYPES = {
    "byte": "b",
    "word": "w",
    "dword": "d",
    "qword": "q",
}
RDI_BY_SIZE = {
    "byte": "dil",
    "word": "di",
    "dword": "edi",
    "qword": "rdi",
}
CONDITIONAL_OPERATORS = {
    "==": "e",
    "!=": "ne",
}
SIMPLE_BINARY_OPERATORS = {
    "+": "add",
    "-": "sub",
}
FUNCTIONS = [
    "global",
    "data",
    "call",
    "syscall",
    "jmp",
    "jmpif",
    "return",
]
CALL_ARG_REGS = [
    "rdi",
    "rsi",
    "rdx",
    "rcx",
    "r8",
    "r9",
]
SYSCALL_ARG_REGS = [
    "rax",
    "rdi",
    "rsi",
    "rdx",
    "r10",
    "r8",
    "r9",
]

def asm_str(val: str) -> str:
    if not val.endswith("\0"):
        val += "\0"
    asm_str = "db "
    for c in val:
        if asm_str != "db ":
            asm_str += ", "
        asm_str += str(ord(c))
    return asm_str

class Token:
    pass

@dataclass
class FunctionToken(Token):
    name: str
    args: list[str | int]

@dataclass
class ValueToken(Token):
    prefix: str | None
    value: str | int

@dataclass
class StringToken(Token):
    value: str

class Scanner:
    _stream: TextIO
    _c: str

    def __init__(self, stream: TextIO):
        self._stream = stream
    
    def _next(self) -> str:
        self._c = self._stream.read(1)
        return self._c
    
    def scan(self) -> Generator[Token, None, None]:
        self._next()
        while self._c:
            if self._c.isspace():
                self._next()
            elif self._c == ";": # comment
                while self._c and self._c != "\n":
                    self._next()
                if self._c:
                    self._next()
            elif self._c == '"': # string
                tk = StringToken("")
                self._next()
                while self._c and self._c != '"':
                    tk.value += self._c
                    self._next()
                if not self._c:
                    raise Exception("unclosed string")
                self._next()
                yield tk
            else: # value/function
                prefix = None
                value = ""
                if self._c in PREFIXES:
                    prefix = self._c
                    self._next()
                while self._c and not self._c.isspace() and self._c != "(":
                    value += self._c
                    self._next()
                if self._c != "(": # value
                    yield ValueToken(prefix, int(value) if value.isdigit() else value)
                    continue
                elif prefix is not None:
                    raise Exception("functions cannot be prefixed")
                # function
                args = []
                i = 0
                self._next()
                while True: # args
                    while self._c.isspace():
                        self._next()
                    if self._c == ")":
                        break
                    args.append("")
                    while self._c and self._c != "," and self._c != ")":
                        args[i] += self._c
                        self._next()
                    if self._c == ",":
                        self._next()
                    if args[i].isdigit():
                        args[i] = int(args[i])
                    i += 1
                if not self._c:
                    raise Exception("unclosed function")
                self._next()
                yield FunctionToken(value, args)
                
class Compiler:
    _stream: Iterator[Token]

    def __init__(self, stream: Iterator[Token]):
        self._stream = stream
    
    def compile(self) -> Generator[str, None, None]:
        for tk in self._stream:
            if isinstance(tk, StringToken):
                yield asm_str(tk.value)
            elif isinstance(tk, FunctionToken):
                if tk.name == "global" and len(tk.args) == 1 and isinstance(tk.args[0], str):
                    yield "global %s" % (tk.args[0])
                elif tk.name == "data" and len(tk.args) >= 2 and tk.args[0] in TYPES and all(isinstance(arg, int) for arg in tk.args[1:]):
                    yield "d%s %s" % (
                        TYPES[tk.args[0]],
                        ", ".join(str(arg) for arg in tk.args[1:])
                    )
                elif tk.name == "call" and len(tk.args) == 2 and isinstance(tk.args[0], str) and isinstance(tk.args[1], int):
                    for i in reversed(range(tk.args[1])):
                        yield "pop %s" % (CALL_ARG_REGS[i])
                    yield "call %s" % (tk.args[0])
                    yield "push rax"
                elif tk.name == "syscall" and len(tk.args) == 1 and isinstance(tk.args[0], int):
                    for i in reversed(range(tk.args[0])):
                        yield "pop %s" % (SYSCALL_ARG_REGS[i])
                    yield "syscall"
                    yield "push rax"
                elif tk.name == "jmp" and len(tk.args) == 1 and isinstance(tk.args[0], str):
                    yield "jmp %s" % (tk.args[0])
                elif tk.name == "jmpif" and len(tk.args) == 1 and isinstance(tk.args[0], str):
                    yield "pop rax"
                    yield "test rax, rax"
                    yield "jnz %s" % (tk.args[0])
                elif tk.name == "return" and len(tk.args) == 0:
                    yield "pop rax"
                    yield "ret"
                elif tk.name == "args" and len(tk.args) == 1 and isinstance(tk.args[0], int):
                    for i in range(tk.args[0]):
                        yield "push %s" % (CALL_ARG_REGS[i])
                else:
                    raise Exception("invalid function")
            elif isinstance(tk, ValueToken) and isinstance(tk.value, str):
                if tk.prefix == "#" and tk.value in TYPES:
                    yield "pop rax"
                    yield "xor rdi, rdi"
                    yield "mov %s, %s [rax]" % (RDI_BY_SIZE[tk.value], tk.value)
                    yield "push rdi"
                elif tk.prefix == ".":
                    yield "section %s" % (tk.value)
                elif tk.prefix == ":":
                    yield "%s:" % (tk.value)
                elif tk.prefix == "$":
                    yield "mov rax, %s" % (tk.value)
                    yield "push rax"
                elif tk.prefix is None and tk.value in CONDITIONAL_OPERATORS:
                    yield "pop rax"
                    yield "pop rdi"
                    yield "xor rsi, rsi"
                    yield "cmp rax, rdi"
                    yield "set%s sil" % (CONDITIONAL_OPERATORS[tk.value])
                    yield "push rsi"
                elif tk.prefix is None and tk.value in SIMPLE_BINARY_OPERATORS:
                    yield "pop rax"
                    yield "pop rdi"
                    yield "%s rax, rdi" % (SIMPLE_BINARY_OPERATORS[tk.value])
                    yield "push rax"
                else:
                    raise Exception("invalid string value")
            elif isinstance(tk, ValueToken) and isinstance(tk.value, int):
                if tk.prefix is None:
                    yield "push %i" % (tk.value)
                elif tk.prefix == "$":
                    yield "mov rax, [rsp + %i]" % (tk.value * 8)
                    yield "push rax"
                elif tk.prefix == "@":
                    yield "mov rax, rsp"
                    yield "add rax, %i" % (tk.value * 8)
                    yield "push rax"
                elif tk.prefix == "?":
                    yield "add rsp, %i" % (tk.value * 8)
                elif tk.prefix == ":":
                    yield "mov rax, [rsp]"
                    yield "mov rdi, [rsp + %i]" % (tk.value * 8)
                    yield "mov [rsp], rdi"
                    yield "mov [rsp + %i], rax" % (tk.value * 8)
                else:
                    raise Exception("invalid integer value")
            else:
                raise Exception("invalid token")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("output", type=str)
    args = parser.parse_args()

    with open(args.input, "r") as input, open(args.output, "w") as output:
        for line in Compiler(Scanner(input).scan()).compile():
            output.write(line + "\n")
