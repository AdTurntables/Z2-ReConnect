/* xsim test of midi_glue + z2midi compiled for XS1 (same flags as the firmware blob).
   xcc -Os -target=XK-1A -DZ2M_NO_NAMES -DSIM sim_test.c ../z2midi/z2midi.c -o sim.xe && xsim sim.xe */
#include <stdio.h>
#define main glue_main
#include "midi_glue.c"
#undef main

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

int main(void)
{
    static uint8_t r1[10] = {0x01}, r2[53] = {0x02};
    static uint8_t out[64] __attribute__((aligned(4)));
    int n;
    mg_init();
    mg_report(r1, 10);                       /* primes buttons */
    CHECK(mg_next(out) == 0);
    mg_report(r2, 53);                       /* first analog report: 26 CCs */
    n = mg_next(out); CHECK(n == 60);        /* 15 packets per chunk */
    CHECK(out[0] == 0x0B && out[1] == 0xB0 && out[2] == 20 && out[3] == 0);
    n = mg_next(out); CHECK(n == 44);        /* remaining 11 */
    CHECK(mg_next(out) == 0);
    r1[4] = 0x40; mg_report(r1, 10);         /* SYNC A down */
    n = mg_next(out); CHECK(n == 4 && out[0] == 0x09 && out[1] == 0x90 && out[2] == 50 && out[3] == 127);
    r2[1 + 2 * 24] = 0xff; r2[2 + 2 * 24] = 0x0f; mg_report(r2, 53);   /* crossfader full */
    n = mg_next(out); CHECK(n == 4 && out[1] == 0xB0 && out[2] == 114 && out[3] == 127);
    for (int i = 0; i < 100; i++) { r1[4] ^= 0x40; mg_report(r1, 10); }   /* overflow: no crash */
    int total = 0; while ((n = mg_next(out)) > 0) total += n;
    CHECK(total > 0 && total <= 4 * 63);
    /* LED path: SYNC A note on -> report 0x80 idx 0x14, first LED message also requests 0xF1 */
    static uint8_t m[16] __attribute__((aligned(4))) = {0x09, 0x90, 50, 100,   0x0B, 0xB2, 0x05, 64,
                                                        0x0B, 0xBF, 126, 0x13, 0x0B, 0xBF, 127, 0};
    int mask = mg_midi(m, 8);
    CHECK(mask == 7);                                   /* 0x80 + 0x81 dirty + F1 */
    CHECK(mg_buf(0)[0] == 0x80 && mg_buf(0)[0x14] == 100);
    CHECK(mg_buf(1)[0] == 0x81 && mg_buf(1)[5] == 64);
    CHECK(mg_buf(2)[0] == 0xF1 && mg_buf(2)[1] == 0xB3 && mg_buf(2)[2] == 0);
    CHECK(mg_midi(m, 8) == 0);                          /* same values again: nothing to send */
    mask = mg_midi(m + 8, 8);                           /* ch16 CC126=0x13, CC127=0 -> mask 0x13 */
    CHECK(mask == 4 && mg_buf(2)[1] == 0x13);
    /* pad layers: DECK A press is drawn by the firmware, mg_pending hands it to the hook */
    CHECK(mg_pending() == 0);
    for (int i = 1; i < 10; i++) r1[i] = 0;
    mg_report(r1, 10); while (mg_next(out) > 0) {}
    r1[6] = 0x02; mg_report(r1, 10);
    n = mg_next(out); CHECK(n == 4 && out[1] == 0x90 && out[2] == 61);
    CHECK(mg_pending() == 1 && mg_buf(0)[0x07] == 127);
    CHECK(mg_pending() == 0);
    r1[6] = 0x06; mg_report(r1, 10);                    /* pad A1 on layer 2 -> channel 4 */
    n = mg_next(out); CHECK(n == 4 && out[1] == 0x93 && out[2] == 62);
    /* USB re-plug: more than 1 s after the last 0xF1 the next LED change claims the LEDs again
       and sends both LED reports; right after that only the changed report goes out */
    CHECK(tmr != 0);
    t_f1 -= F1_REFRESH + 1;
    r1[6] = 0; mg_report(r1, 10); r1[6] = 0x02; mg_report(r1, 10); while (mg_next(out) > 0) {}
    CHECK(mg_pending() == 7 && mg_buf(2)[0] == 0xF1);
    r1[6] = 0; mg_report(r1, 10); r1[6] = 0x02; mg_report(r1, 10); while (mg_next(out) > 0) {}
    CHECK(mg_pending() == 1);
    printf(fails ? "XS1 SIM: %d FAILED\n" : "XS1 SIM: all tests passed (total %d bytes after overflow)\n", fails ? fails : total);
    return fails;
}
