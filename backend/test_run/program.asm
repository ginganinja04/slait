section .data
    msg db "Hello from NASM!", 0xa
    len equ $ - msg

section .text
    global _start
_start:
    mov rax, 1          ; syscall: write
    mov rdi, 1          ; stdout
    mov rsi, msg
    mov rdx, len
    syscall

    mov rax, 60         ; syscall: exit
    xor rdi, rdi
    syscall
