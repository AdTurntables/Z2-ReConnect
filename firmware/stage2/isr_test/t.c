#include <stdio.h>
void isr_test(unsigned *kstack_top);
int main(void) {
    static unsigned ks[8];
    ks[6] = 0xCAFE1234;
    isr_test(&ks[5]);
    printf(ks[2] == 0xCAFE1234 ? "ISR TEST: ok, sp[6] = %08x\n" : "ISR TEST: FAILED %08x\n", ks[2]);
    return ks[2] != 0xCAFE1234;
}
