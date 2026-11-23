/* Host unit tests for z2midi. Build: cc -std=c99 -Wall -Wextra -O2 z2midi.c test_z2midi.c */
#include <stdio.h>
#include <string.h>
#include "z2midi.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

static void set_ana(uint8_t *r, int i, int v) { r[1 + 2 * i] = v & 0xFF; r[2 + 2 * i] = (uint8_t)(v >> 8); }

int main(void)
{
    static z2m_state s; z2m_pkt o[64]; int n;
    uint8_t r1[Z2M_REPORT01_LEN] = {0x01}, r2[Z2M_REPORT02_LEN] = {0x02};
    z2m_init(&s);

    /* first button report only primes */
    CHECK(z2m_panel_in(&s, r1, sizeof r1, o, 64) == 0);

    /* press SYNC A (byte 4, 0x40) -> note on 50 */
    r1[4] = 0x40; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(n == 1 && o[0].b[0] == 0x09 && o[0].b[1] == 0x90 && o[0].b[2] == 50 && o[0].b[3] == 127);
    r1[4] = 0x00; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(n == 1 && o[0].b[0] == 0x08 && o[0].b[1] == 0x80 && o[0].b[2] == 50);

    /* browse encoder +1, LOOP A wraps 0 -> 15 (= -1) */
    r1[1] = 0xF1; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(n == 2 && o[0].b[2] == 16 && o[0].b[3] == 1 && o[1].b[2] == 17 && o[1].b[3] == 127);

    /* all 48 button bits have unique notes */
    for (int a = 0; a < z2m_num_buttons; a++) CHECK(z2m_button_note(3 + a / 8, (uint8_t)(1u << (a % 8))) == 36 + a);
    CHECK(z2m_num_buttons == 48);
    CHECK(z2m_button_note(4, 0x40) == 50);    /* SYNC A */

    /* analog: first report sends all 26 */
    n = z2m_panel_in(&s, r2, sizeof r2, o, 64);
    CHECK(n == 26 && o[0].b[1] == 0xB0 && o[0].b[2] == 20 && o[0].b[3] == 0);
    /* small jitter below hysteresis -> nothing */
    set_ana(r2, 24, 33); n = z2m_panel_in(&s, r2, sizeof r2, o, 64);
    CHECK(n == 1); /* 33>>5 = 1, diff 33 >= hyst */
    set_ana(r2, 24, 64); n = z2m_panel_in(&s, r2, sizeof r2, o, 64);
    CHECK(n == 1 && o[0].b[3] == 2);
    set_ana(r2, 24, 63); n = z2m_panel_in(&s, r2, sizeof r2, o, 64);
    CHECK(n == 0);                       /* 1-unit jitter across a step boundary is ignored */
    set_ana(r2, 24, 0); n = z2m_panel_in(&s, r2, sizeof r2, o, 64);
    CHECK(n == 1 && o[0].b[3] == 0);     /* extremes always get through */
    /* full scale reaches 127 */
    set_ana(r2, 22, 4095); n = z2m_panel_in(&s, r2, sizeof r2, o, 64);
    CHECK(n == 1 && o[0].b[2] == 112 && o[0].b[3] == 127);

    /* LED feedback: note 50 (SYNC A) -> led80[0x14] */
    uint8_t m1[4] = {0x09, 0x90, 50, 100}; s.led_dirty = 0; z2m_midi_in(&s, m1);
    CHECK(s.led80[0x14] == 100 && (s.led_dirty & 1));
    /* pad A1 note 62 on ch1 -> layer 1 cache, drawn blue */
    uint8_t m2[4] = {0x09, 0x90, 62, 77}; z2m_midi_in(&s, m2);
    CHECK(s.led80[0x1D] == 0 && s.led80[0x1E] == 0 && s.led80[0x1F] == 76);   /* 77 -> 2 * (77 / 2) */

    /* ---- pad layers ---- */
    uint8_t m7[4] = {0x09, 0x93, 63, 100};              /* layer 2 (ch4), pad A2 */
    z2m_midi_in(&s, m7);
    CHECK(s.padc[1][1] == 100 && s.led80[0x20] == 0 && s.led80[0x22] == 0);   /* not visible on layer 1 */
    uint8_t m8[4] = {0x09, 0x94, 74, 90};               /* layer 3 (ch5), pad B4 */
    z2m_midi_in(&s, m8); CHECK(s.padc[2][7] == 90 && s.led80[0x32] == 0);
    uint8_t m9[4] = {0x09, 0x90, 61, 127};              /* host LED for DECK A is ignored */
    z2m_midi_in(&s, m9); CHECK(s.led80[0x07] == 0);
    /* press DECK A (button 25: byte 6, 0x02) -> layer 2 on the left, LED A on, pads redrawn purple */
    memset(r1 + 1, 0, 9);
    n = z2m_panel_in(&s, r1, sizeof r1, o, 64);         /* back to idle (encoders and SYNC up) */
    r1[6] = 0x02; s.led_dirty = 0; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(n == 1 && o[0].b[1] == 0x90 && o[0].b[2] == 61);
    CHECK(s.layer[0] == 1 && s.led80[0x07] == 127 && s.led80[0x09] == 0 && (s.led_dirty & 1));
    CHECK(s.led80[0x1F] == 0 && s.led80[0x20] == 100 && s.led80[0x21] == 0 && s.led80[0x22] == 100);
    r1[6] = 0; z2m_panel_in(&s, r1, sizeof r1, o, 64);
    /* pad A2 down on layer 2 -> note 63 on ch4; switch layer while held; note off still on ch4 */
    r1[6] = 0x08; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(n == 1 && o[0].b[0] == 0x09 && o[0].b[1] == 0x93 && o[0].b[2] == 63);
    r1[6] = 0x08 | 0x01; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);   /* + DECK C -> layer 4 */
    CHECK(s.layer[0] == 3 && s.led80[0x09] == 127 && s.led80[0x07] == 127);
    r1[6] = 0; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(n == 2 && o[0].b[1] == 0x80 && o[0].b[2] == 60 && o[1].b[1] == 0x83 && o[1].b[2] == 63);
    /* right side untouched: DECK D (button 34: byte 7, 0x04) -> layer 3, pad B4 yellow 90 */
    r1[7] = 0x04; z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(s.layer[1] == 2 && s.led80[0x0A] == 127 && s.led80[0x08] == 0);
    CHECK(s.led80[0x32] == 90 && s.led80[0x33] == 90 && s.led80[0x34] == 0);
    r1[7] = 0; z2m_panel_in(&s, r1, sizeof r1, o, 64);
    r1[7] = 0x40; n = z2m_panel_in(&s, r1, sizeof r1, o, 64);          /* pad B4 (button 38) -> ch5 */
    CHECK(n == 1 && o[0].b[1] == 0x94 && o[0].b[2] == 74);
    r1[7] = 0; z2m_panel_in(&s, r1, sizeof r1, o, 64);
    /* back to layer 1 on the left: A then C again */
    r1[6] = 0x02; z2m_panel_in(&s, r1, sizeof r1, o, 64); r1[6] = 0; z2m_panel_in(&s, r1, sizeof r1, o, 64);
    r1[6] = 0x01; z2m_panel_in(&s, r1, sizeof r1, o, 64); r1[6] = 0; z2m_panel_in(&s, r1, sizeof r1, o, 64);
    CHECK(s.layer[0] == 0 && s.led80[0x07] == 0 && s.led80[0x09] == 0 && s.led80[0x1F] == 76);
    /* cue colours: velocity 1-16 palette full, 17-32 dimmed, on any layer */
    uint8_t c1[4] = {0x09, 0x90, 62, 1};                /* pad A1, red */
    z2m_midi_in(&s, c1); CHECK(s.led80[0x1D] == 126 && s.led80[0x1E] == 0 && s.led80[0x1F] == 0);
    uint8_t c2[4] = {0x09, 0x90, 62, 3};                /* orange: R 3, G 2 */
    z2m_midi_in(&s, c2); CHECK(s.led80[0x1D] == 126 && s.led80[0x1E] == 84 && s.led80[0x1F] == 0);
    uint8_t c3[4] = {0x09, 0x90, 62, 16 + 9};           /* cyan dimmed: G 3, B 3 at level 8 */
    z2m_midi_in(&s, c3); CHECK(s.led80[0x1D] == 0 && s.led80[0x1E] == 24 && s.led80[0x1F] == 24);
    uint8_t c4[4] = {0x09, 0x90, 62, 16};               /* white */
    z2m_midi_in(&s, c4); CHECK(s.led80[0x1D] == 126 && s.led80[0x1E] == 126 && s.led80[0x1F] == 126);
    uint8_t c5[4] = {0x09, 0x90, 62, 33};               /* 33 is no palette value: blue layer colour */
    z2m_midi_in(&s, c5); CHECK(s.led80[0x1D] == 0 && s.led80[0x1E] == 0 && s.led80[0x1F] == 32);
    uint8_t c6[4] = {0x08, 0x80, 62, 0};                /* note off: dark */
    z2m_midi_in(&s, c6); CHECK(s.led80[0x1D] == 0 && s.led80[0x1E] == 0 && s.led80[0x1F] == 0);
    /* raw CC on ch2 -> led80, ch3 -> led81 (VU) */
    uint8_t m3[4] = {0x0B, 0xB1, 0x35, 127}, m4[4] = {0x0B, 0xB2, 0x05, 64};
    z2m_midi_in(&s, m3); z2m_midi_in(&s, m4);
    CHECK(s.led80[0x35] == 127 && s.led81[0x05] == 64 && (s.led_dirty & 2));
    /* level meters: ch3 CC 65 (A) / 66 (B) = number of lit LEDs 0..7 */
    uint8_t v1[4] = {0x0B, 0xB2, 65, 3}, v2[4] = {0x0B, 0xB2, 66, 9}, v3[4] = {0x0B, 0xB2, 65, 0};
    z2m_midi_in(&s, v1);
    CHECK(s.led81[0x02] == 127 && s.led81[0x04] == 127 && s.led81[0x05] == 0 && s.led81[0x08] == 0);
    z2m_midi_in(&s, v2); CHECK(s.led81[0x0A] == 127 && s.led81[0x10] == 127 && s.led81[0x09] == 0);
    z2m_midi_in(&s, v3); CHECK(s.led81[0x02] == 0 && s.led81[0x04] == 0);
    /* note off clears; CUE A lives in report 0x81 */
    uint8_t m5[4] = {0x09, 0x90, 46, 127}, m6[4] = {0x08, 0x80, 46, 0};
    z2m_midi_in(&s, m5); CHECK(s.led81[0x23] == 127);
    z2m_midi_in(&s, m6); CHECK(s.led81[0x23] == 0);
    CHECK(s.led80[0] == 0x80 && s.led81[0] == 0x81);

    printf(fails ? "%d FAILED\n" : "all z2midi tests passed\n", fails);
    return fails != 0;
}
