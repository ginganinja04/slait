section .text
    global _start

_start:
    ; Case 1: CMP equal -> ZF=1, CF=0, SF=0, OF=0, PF=1
    mov rax, 1
    cmp rax, 1
    nop                 ; breakpoint: after CMP-equal

    ; Case 2: Force carry flag explicitly -> CF=1
    stc
    nop                 ; breakpoint: after STC

    ; Case 3: Signed overflow on 8-bit add (0x7f + 1 = 0x80)
    ; Expected: OF=1, SF=1, ZF=0, CF=0
    mov al, 0x7f
    add al, 1
    nop                 ; breakpoint: after signed overflow add

    ; Case 4: Borrow on subtract (0 - 1)
    ; Expected: CF=1, SF=1, ZF=0, OF=0
    xor eax, eax
    sub eax, 1
    nop                 ; breakpoint: after subtract borrow

    ; Case 5: Direction flag
    cld                 ; DF=0
    std                 ; DF=1
    nop                 ; breakpoint: after STD

    ; Exit
    mov rax, 60
    xor rdi, rdi
    syscall
