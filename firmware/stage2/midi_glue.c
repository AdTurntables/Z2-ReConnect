/*
 * midi_glue - bridge between NI's HID thread (Z2 firmware 42, core 1) and z2midi.
 *
 * Built with xcc as a small standalone program, then relocated into the dormant CDC-ECM packet
 * pool of core 1 (0x19f8c..0x1af6c). The assembly hooks (hooks.S) switch cp/dp to this blob's
 * own values while calling in, with interrupts disabled, so nothing here may keep absolute
 * pointers to its own data (z2midi is built with Z2M_NO_NAMES for that reason).
 */
#include "../z2midi/z2midi.h"

#define RING 32                       /* USB-MIDI packets, power of two */
#define CHUNK_PKTS 15                 /* 60 bytes per USB transfer (< 64, never needs a ZLP) */

/* LED ownership (HID feature report 0xF1, byte 1): which LED groups the host drives.
   01 deck A, 02 deck B, 04 master VU, 08 mic, 10 7-segment, 20 USB symbol, 80 browse.
   Default leaves the master/mic VU meters to the hardware. Byte 2 (audio routing flags) stays 0,
   the value the Z2 reports without NI software (read from the device 2026-11-20). */
#define OWN_DEFAULT 0xB3
#define CH_CONFIG   15                /* MIDI channel 16: CC 126 = mask bits 0-6, CC 127 >= 64 = bit 7 */

static z2m_state st;
static z2m_pkt ring[RING];
static unsigned head, tail;           /* head: write, tail: read */
static uint8_t f1[4];                 /* 0xF1, mask, routing (0), pad */
static unsigned owned;
static unsigned tmr, t_f1;            /* own timer (0 = none free), time of the last 0xF1 */
#define F1_REFRESH 100000000u         /* 1 s at the 100 MHz reference clock */

__attribute__((used)) void mg_init(void)
{
    z2m_init(&st);
    st.led_dirty = 0;                 /* nothing is sent until the host sends LED MIDI */
    head = tail = 0;
    f1[0] = 0xF1; f1[1] = OWN_DEFAULT; f1[2] = 0; f1[3] = 0;
    owned = 0;
    asm volatile("getr %0, 1" : "=r"(tmr));   /* timer, condition none: "in" returns the time */
}

/* LED reports that must go out (same bits as mg_midi). Also covers LEDs the panel side changed
   itself (pad layers): z2_hook_token calls this after every finished MIDI IN transfer, so a layer
   switch is drawn as soon as its DECK note has reached the host.
   LED ownership (0xF1) is claimed with the first LED change and claimed again with the next LED
   change once a second has passed since the last 0xF1: after the USB cable was pulled and plugged
   in again (mixer still powered, this code is not re-initialised) the Z2 has taken the LEDs back.
   Whenever 0xF1 goes out, both LED reports follow so the panel shows the complete state. */
__attribute__((used)) int mg_pending(void)
{
    int r = st.led_dirty & 3;
    st.led_dirty = 0;
    if (r) {
        unsigned now = 0;
        if (tmr) asm volatile("in %0, res[%1]" : "=r"(now) : "r"(tmr));
        if (!owned || !tmr || now - t_f1 > F1_REFRESH) { owned = 1; t_f1 = now; r = 7; }
    }
    return r;
}

/* USB-MIDI packets from the host. Returns bit0: report 0x80 changed, bit1: 0x81 changed,
   bit2: feature 0xF1 must be (re)sent. */
__attribute__((used)) int mg_midi(const uint8_t *buf, int len)
{
    int f1_dirty = 0;
    for (int i = 0; i + 3 < len; i += 4) {
        const uint8_t *p = &buf[i];
        uint8_t cin = p[0] & 0x0F;
        if (cin == 0xB && (p[1] & 0xF0) == 0xB0 && (p[1] & 0x0F) == CH_CONFIG && (p[2] == 126 || p[2] == 127)) {
            if (p[2] == 126) f1[1] = (uint8_t)((f1[1] & 0x80) | (p[3] & 0x7F));
            else             f1[1] = (uint8_t)((f1[1] & 0x7F) | (p[3] >= 64 ? 0x80 : 0));
            owned = 1; f1_dirty = 1;
            continue;
        }
        z2m_midi_in(&st, p);
    }
    return mg_pending() | (f1_dirty ? 4 : 0);
}

/* runtime address of a report buffer: 0 = LED report 0x80, 1 = 0x81, 2 = feature 0xF1 */
__attribute__((used)) uint8_t *mg_buf(int which)
{
    return which == 0 ? st.led80 : which == 1 ? st.led81 : f1;
}

__attribute__((used)) void mg_report(const uint8_t *report, int len)
{
    z2m_pkt tmp[32];
    int n = z2m_panel_in(&st, report, len, tmp, 32);
    for (int i = 0; i < n; i++) {
        if (((head + 1) & (RING - 1)) == (tail & (RING - 1)) && head - tail >= RING - 1) continue;
        ring[head & (RING - 1)] = tmp[i];
        head++;
    }
}

/* Copy up to CHUNK_PKTS packets into out (word aligned, 60 bytes); returns bytes. */
__attribute__((used)) int mg_next(uint8_t *out)
{
    int n = 0;
    while (tail != head && n < CHUNK_PKTS) {
        z2m_pkt *p = &ring[tail & (RING - 1)];
        out[4 * n + 0] = p->b[0]; out[4 * n + 1] = p->b[1];
        out[4 * n + 2] = p->b[2]; out[4 * n + 3] = p->b[3];
        tail++; n++;
    }
    return 4 * n;
}

int main(void)
{
    /* never run on the device; references the hooks (pc-relative) so the linker keeps them,
       the hooks in turn reference mg_init / mg_report / mg_next / mg_midi / mg_buf */
    asm volatile("ldap r11, z2_hook_init\n ldap r11, z2_hook_report\n ldap r11, z2_hook_token" ::: "r11");
    return 0;
}
