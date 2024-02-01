# rpasm

Reverse Polish Assembly, an esoteric programming language combining Assembly with Reverse Polish Notation.

Output is in x86_64 Intel assembly.
[NASM](https://www.nasm.us/) is recommended for assembling.

## Types

- `byte`: 8-bit
- `word`: 16-bit
- `dword`: 32-bit
- `qword`: 64-bit

## Tokens

- `<num>`: Pushes `num` onto the stack.
- `$<num>`: Pushes a copy of the value at offset `num`.
- `@<num>`: Pushes the address of the value at offset `num`.
- `?<num>`: Removes `num` values off the stack.
- `:<num>`: Swaps the value at offset 0 with the value at offset `num`.
- `#<type>`: Consumes 1. Pushes the value at the consumed address of type `type`.
- `.<id>`: Defines section `id`.
- `:<id>`: Defines label `id`.
- `$<id>`: Pushes the value of label `id` onto the stack.
- `"..."`: String. Defines the data for a nil-terminated string.
- `;...`: Comment. Everything on the same line after a `;` is ignored.
- `==`: Equality. Consumes 2. Pushes 1 if equal, 0 if not equal.
- `!=`: Non-Equality. Consumes 2. Pushes 1 if not equal, 0 if equal.
- `+`: Addition. Consumes 2. Pushes argument 1 + argument 2.
- `-`: Subtraction. Consumes 2. Pushes argument 1 - argument 2.
- `global(label)`: Makes `label` global.
- `data(type, value...)`: Inserts numeric data.
- `call(label, n_args)`: Inserts a call to function `label`. Consumes `n_args`. Pushes the return value of the function.
- `syscall(n_args)`: Inserts a syscall. Consumes `n_args`. Pushes the return value of the syscall.
- `jmp(label)`: Jumps to `label`.
- `jmpif(label)`: Consumes 1. Jumps to `label` if the consumed value is not 0.
- `args(n_args)`: Pushes `n_args` arguments onto the stack.
- `return()`: Pops into the return register and returns from the function.
