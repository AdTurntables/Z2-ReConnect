/* xsim check of the stage-3b ISR patch: inside an interrupt handler entered with "kentsp 5",
   sp[6] is the word above the kernel stack top (NI: dp[0x2d2] = token chanend), also while
   the interrupted thread runs with a foreign dp. */
    .text
    .globl isr_test
    .align 2
isr_test:
    entsp 6
    stw r4, sp[1]
    stw r5, sp[2]
    add r11, r0, 0
    ldaw r1, sp[0]
    stw r1, r11[0]
    set sp, r11
    krestsp 0
    getr r4, 2
    getr r5, 2
    setd res[r4], r5
    setd res[r5], r4
    setc res[r4], 0xa
    ldap r11, isr
    setv res[r4], r11
    eeu res[r4]
    ldaw r11, dp[0]
    stw r11, sp[3]
    ldc r11, 0
    set dp, r11
    setsr 2
    ldc r0, 0
    out res[r5], r0
    add r0, r0, 0
    add r0, r0, 0
    add r0, r0, 0
    add r0, r0, 0
    clrsr 2
    ldw r11, sp[3]
    set dp, r11
    ldw r4, sp[1]
    ldw r5, sp[2]
    retsp 6
    .align 2
isr:
    kentsp 5
    in r1, res[r4]
    ldw r0, sp[6]
    add r0, r0, 0
    stw r0, sp[2]
    krestsp 5
    kret
