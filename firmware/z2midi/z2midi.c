/* z2midi - see z2midi.h */
#include "z2midi.h"


/* Buttons of report 0x01, bytes 3..8. Button i is bit (i % 8) of byte 3 + i / 8 and sends
 *   note = 36 + i          (every bit gets a note, so no control is lost)
 * z2m_button_led[i] = LED lit by the same note: 0 none, 0x01..0x3F index in output report 0x80,
 * 0x40 | n = RGB pad whose R is at index n of report 0x80, 0x80 | n = index n of report 0x81. */
const uint8_t z2m_button_led[Z2M_NUM_BUTTONS] = {
    0x80 | 0x25, 0x80 | 0x26, 0x03, 0x05, 0x04, 0, 0, 0,
    0x11, 0x19, 0x80 | 0x23, 0x80 | 0x24, 0x13, 0x1B, 0x14, 0x1C,
    0x80 | 0x22, 0x0D, 0x0F, 0x10, 0, 0, 0, 0,
    0x09, 0x07, 0x40 | 0x1D, 0x40 | 0x20, 0x40 | 0x23, 0x40 | 0x26, 0x0E, 0,
    0x06, 0x08, 0x0A, 0x40 | 0x29, 0x40 | 0x2C, 0x40 | 0x2F, 0x40 | 0x32, 0x16,
    0x15, 0x17, 0x18, 0, 0, 0, 0, 0x80 | 0x28,
};
#ifndef Z2M_NO_NAMES
const char *const z2m_button_names[Z2M_NUM_BUTTONS] = {
    "TRAKTOR A", "TRAKTOR B", "SNAP (S)", "SETTINGS (gear)",
    "QUANT (Q)", "unknown 3.20", "unknown 3.40", "BROWSE push",
    "LOAD A", "LOAD B", "CUE (headphone) A", "CUE (headphone) B",
    "REL/INTL A", "REL/INTL B", "SYNC A", "SYNC B",
    "MIC", "FX1 ON", "A FX1 assign", "A FX2 assign",
    "unknown 5.10", "unknown 5.20", "LOOP A push", "unknown 5.80",
    "DECK C", "DECK A", "PAD A1", "PAD A2",
    "PAD A3", "PAD A4", "FLUX A", "unknown 6.80",
    "SHIFT", "DECK B", "DECK D", "PAD B1",
    "PAD B2", "PAD B3", "PAD B4", "FLUX B",
    "FX2 ON", "B FX1 assign", "B FX2 assign", "unknown 8.08",
    "unknown 8.10", "LOOP B push", "unknown 8.40", "XFADER REVERSE switch",
};
#endif
const int z2m_num_buttons = Z2M_NUM_BUTTONS;

/* Report 0x02: value i is the u16 LE at byte 1 + 2*i.
 * CCs use the MIDI "undefined" ranges 20-31 and 102-115 so no app treats them specially. */
const z2m_analog_def z2m_analog[Z2M_NUM_ANALOG] = {
    {20 Z2M_NAME("MIC/AUX VOL")}, {21 Z2M_NAME("MIC/AUX TONE")}, {22 Z2M_NAME("HEADPHONE VOL")}, {23 Z2M_NAME("CUE MIX")},
    {24 Z2M_NAME("MAIN VOL")}, {25 Z2M_NAME("BOOTH or XF CURVE (0x0B)")}, {26 Z2M_NAME("FX1 DRY/WET")}, {27 Z2M_NAME("FX1 FX")},
    {28 Z2M_NAME("GAIN A")}, {29 Z2M_NAME("HI A")}, {30 Z2M_NAME("MID A")}, {31 Z2M_NAME("LOW A")},
    {102 Z2M_NAME("FILTER A")}, {103 Z2M_NAME("FX2 DRY/WET")}, {104 Z2M_NAME("FX2 FX")}, {105 Z2M_NAME("GAIN B")},
    {106 Z2M_NAME("HI B")}, {107 Z2M_NAME("MID B")}, {108 Z2M_NAME("LOW B")}, {109 Z2M_NAME("FILTER B")},
    {110 Z2M_NAME("DECK C VOL")}, {111 Z2M_NAME("DECK D VOL")}, {112 Z2M_NAME("FADER A")}, {113 Z2M_NAME("FADER B")},
    {114 Z2M_NAME("CROSSFADER")}, {115 Z2M_NAME("XF CURVE or BOOTH (0x33)")},
};

/* Report 0x01 bytes 1..2: 4-bit absolute counters -> relative CC (1..7 up, 127..121 down). */
const z2m_encoder_def z2m_encoders[Z2M_NUM_ENCODERS] = {
    {1, 0, 16 Z2M_NAME("BROWSE encoder")},
    {1, 4, 17 Z2M_NAME("LOOP A encoder")},
    {2, 0, 18 Z2M_NAME("LOOP B encoder")},
};

static void pkt(z2m_pkt *p, uint8_t status, uint8_t d1, uint8_t d2)
{
    p->b[0] = (uint8_t)(status >> 4);  /* cable 0, CIN = status high nibble for 8x..Ex */
    p->b[1] = status;
    p->b[2] = d1 & 0x7F;
    p->b[3] = d2 & 0x7F;
}

void z2m_init(z2m_state *s)
{
    volatile uint8_t *p = (volatile uint8_t *)s;    /* volatile: keeps xcc from calling memset */
    for (unsigned i = 0; i < sizeof *s; i++) p[i] = 0;
    s->led80[0] = 0x80;
    s->led81[0] = 0x81;
    s->led_dirty = 3;
}

#ifndef Z2M_NO_NAMES   /* lookups for tests/docs only; not needed in the firmware */
int z2m_button_note(int byte, uint8_t mask)
{
    for (int i = 0; i < Z2M_NUM_BUTTONS; i++)
        if (3 + i / 8 == byte && (1u << (i % 8)) == mask) return 36 + i;
    return -1;
}

int z2m_analog_cc(int index)
{
    return (index >= 0 && index < Z2M_NUM_ANALOG) ? z2m_analog[index].cc : -1;
}
#endif

/* Pad layers. Button indices: DECK C 24, DECK A 25, pads A 26-29, DECK B 33, DECK D 34, pads B 35-38.
   The firmware owns the DECK A-D LEDs (they show the layer) and draws the pads from padc:
   layer 1 blue, 2 purple, 3 yellow, 4 white, brightness = velocity the host sent for that layer. */
static void set80(z2m_state *s, int idx, uint8_t v);

static int pad_of_button(int i)          /* 0..3 left, 4..7 right, -1 no pad */
{
    if (i >= 26 && i <= 29) return i - 26;
    if (i >= 35 && i <= 38) return i - 31;
    return -1;
}

/* Cue colours (djay "padColorsActive/Dimmed"): velocity 1-16 = palette colour full, 17-32 = the same
   colour dimmed. Entry = R<<4 | G<<2 | B, 2 bits each (0..3). Any other velocity keeps the old
   behaviour: brightness in the colour of the layer. Order (1-16): red, red-orange, orange, amber,
   yellow, lime, green, spring, cyan, sky, blue, indigo, violet, magenta, pink, white.
   Entries 16-19: layer colours blue, purple, yellow, white at level 2 (brightness v = 2 * (v / 2)). */
static const uint8_t z2m_pal[20] = {
    0x30, 0x34, 0x38, 0x39, 0x3C, 0x2C, 0x0C, 0x0D, 0x0F, 0x0B, 0x03, 0x13, 0x23, 0x33, 0x31, 0x3F,
    0x02, 0x22, 0x28, 0x2A,
};

static void render_pad(z2m_state *s, int p)
{
    int l = s->layer[p >> 2];
    unsigned v = s->padc[l][p];
    int base = ((p >> 2) ? 0x29 : 0x1D) + 3 * (p & 3);
    unsigned c, k;
    if (v - 1 < 32) {                     /* 1..32: palette */
        c = z2m_pal[(v - 1) & 15];
        k = v > 16 ? 8 : 42;              /* 2-bit level * k: 0..126 full, 0..24 dimmed */
    } else {                              /* layer colour: 1 = B, 2 = R+B, 3 = R+G, 4 = R+G+B */
        c = z2m_pal[16 + l];
        k = v >> 1;                       /* level 2 * (v / 2) = v, rounded down to even */
    }
    set80(s, base,     (uint8_t)((c >> 4) * k));
    set80(s, base + 1, (uint8_t)(((c >> 2) & 3) * k));
    set80(s, base + 2, (uint8_t)((c & 3) * k));
}

static void render_side(z2m_state *s, int side)
{
    int l = s->layer[side];
    set80(s, side ? 0x08 : 0x07, (l & 1) ? 127 : 0);    /* DECK A / B */
    set80(s, side ? 0x0A : 0x09, (l & 2) ? 127 : 0);    /* DECK C / D */
    for (int p = 0; p < 4; p++) render_pad(s, 4 * side + p);
}

static int buttons_in(z2m_state *s, const uint8_t *r, z2m_pkt *out, int max)
{
    int n = 0;
    if (!s->have_btn) {
        for (int i = 0; i < Z2M_REPORT01_LEN; i++) s->btn[i] = r[i];
        s->have_btn = 1;
        return 0;
    }
    for (int e = 0; e < Z2M_NUM_ENCODERS && n < max; e++) {
        const z2m_encoder_def *d = &z2m_encoders[e];
        int now = (r[d->byte] >> d->shift) & 0xF;
        int was = (s->btn[d->byte] >> d->shift) & 0xF;
        int delta = (now - was) & 0xF;
        if (delta >= 8) delta -= 16;
        if (delta) pkt(&out[n++], 0xB0 | Z2M_CH_MAIN, d->cc, (uint8_t)(delta > 0 ? delta : 128 + delta));
    }
    for (int i = 0; i < Z2M_NUM_BUTTONS && n < max; i++) {
        int byte = 3 + i / 8; uint8_t mask = (uint8_t)(1u << (i % 8));
        uint8_t now = r[byte] & mask, was = s->btn[byte] & mask;
        if (now == was) continue;
        uint8_t ch = Z2M_CH_MAIN;
        int p = pad_of_button(i);
        if (p >= 0) {                                   /* pads: channel of the layer at press time */
            if (now) s->pad_ch[p] = (uint8_t)Z2M_LAYER_CH(s->layer[p >> 2]);
            ch = s->pad_ch[p];
        } else if (now && (i == 24 || i == 25 || i == 33 || i == 34)) {
            int side = i >= 33;
            s->layer[side] ^= (uint8_t)((i == 25 || i == 33) ? 1 : 2);
            render_side(s, side);
        }
        if (now) pkt(&out[n++], 0x90 | ch, (uint8_t)(36 + i), 127);
        else     pkt(&out[n++], 0x80 | ch, (uint8_t)(36 + i), 0);
    }
    for (int i = 0; i < Z2M_REPORT01_LEN; i++) s->btn[i] = r[i];
    return n;
}

static int analog_in(z2m_state *s, const uint8_t *r, z2m_pkt *out, int max)
{
    int n = 0;
    for (int i = 0; i < Z2M_NUM_ANALOG && n < max; i++) {
        int v = r[1 + 2 * i] | (r[2 + 2 * i] << 8);
        if (v > 4095) v = 4095;
        int cc = v >> 5;                       /* 0..127 */
        int diff = v - s->ana[i];
        if (diff < 0) diff = -diff;
        int extreme = (cc == 0 || cc == 127);
        if (!s->have_ana || (cc != s->ana_cc[i] && (diff >= Z2M_HYST || extreme))) {
            s->ana[i] = (uint16_t)v;
            s->ana_cc[i] = (uint8_t)cc;
            pkt(&out[n++], 0xB0 | Z2M_CH_MAIN, z2m_analog[i].cc, (uint8_t)cc);
        }
    }
    s->have_ana = 1;
    return n;
}

int z2m_panel_in(z2m_state *s, const uint8_t *report, int len, z2m_pkt *out, int max)
{
    if (len < 1) return 0;
    if (report[0] == 0x01 && len >= Z2M_REPORT01_LEN) return buttons_in(s, report, out, max);
    if (report[0] == 0x02 && len >= Z2M_REPORT02_LEN) return analog_in(s, report, out, max);
    return 0;
}

static void set80(z2m_state *s, int idx, uint8_t v)
{
    if (idx < 1 || idx >= Z2M_LED80_LEN) return;
    if (s->led80[idx] != v) { s->led80[idx] = v; s->led_dirty |= 1; }
}

static void set81(z2m_state *s, int idx, uint8_t v)
{
    if (idx < 1 || idx >= Z2M_LED81_LEN) return;
    if (s->led81[idx] != v) { s->led81[idx] = v; s->led_dirty |= 2; }
}

void z2m_midi_in(z2m_state *s, const uint8_t p[4])
{
    uint8_t cin = p[0] & 0x0F, st = p[1], ch = st & 0x0F, d1 = p[2] & 0x7F, d2 = p[3] & 0x7F;
    uint8_t kind = st & 0xF0;
    if (cin < 0x8 || cin > 0xE) return;          /* only channel voice messages */

    if (kind == 0xB0 && ch == Z2M_CH_LED80) { set80(s, d1, d2); return; }
    if (kind == 0xB0 && ch == Z2M_CH_LED81) {
        unsigned m = d1 - 65u;                   /* CC 65-68: level meter A, B, C, D as a bar of d2 LEDs */
        if (m < 4) {                             /* (0..7; djay "monoMeter" with midiMaxValue 7) */
            for (unsigned i = 0; i < 7; i++) set81(s, (int)(2 + 8 * m + i), i < d2 ? 127 : 0);
            return;
        }
        set81(s, d1, d2);
        return;
    }

    if (kind != 0x90 && kind != 0x80) return;
    uint8_t vel = (kind == 0x80) ? 0 : d2;
    if (d1 < 36 || d1 >= 36 + Z2M_NUM_BUTTONS) return;
    int pad = pad_of_button(d1 - 36);
    if (pad >= 0 && (ch == 0 || (ch >= 3 && ch <= 5))) {  /* pad LED of layer 1-4 */
        int l = ch ? ch - 2 : 0;
        s->padc[l][pad] = vel;
        if (s->layer[pad >> 2] == l) render_pad(s, pad);
        return;
    }
    if (ch != Z2M_CH_MAIN) return;
    if (d1 == 60 || d1 == 61 || d1 == 69 || d1 == 70) return;   /* DECK A-D LEDs show the layer */
    uint8_t code = z2m_button_led[d1 - 36];
    if (!code) return;
    if (code & 0x80) { set81(s, code & 0x7F, vel); return; }
    set80(s, code, vel);
}
