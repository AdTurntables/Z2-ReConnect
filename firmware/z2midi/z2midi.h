/*
 * z2midi - HID <-> USB-MIDI translation core for the Traktor Kontrol Z2 custom firmware.
 *
 * Pure C99, no allocation, no OS. Runs inside the XMOS firmware (compiled by xcc as a C
 * file and called from the HID/panel task) and on a PC for unit tests.
 *
 * Input side : the Z2 panel state in the exact layout of the stock HID input reports
 *              0x01 (buttons + 4-bit encoders, 10 bytes incl. report id) and
 *              0x02 (26 x u16 LE, 0..4095, 53 bytes incl. report id).
 * Output side: USB-MIDI 1.0 event packets (4 bytes, cable 0).
 * MIDI in    : USB-MIDI packets from the host -> LED brightness buffers in the exact layout
 *              of the stock HID output reports 0x80 (94 LEDs) and 0x81 (40 LEDs).
 *
 * Field offsets come from the community decode in Mixxx PR #3038 (see
 * tools/ref/mixxx_z2) and the live HID caps of the device (tools/z2_hid_caps.json).
 */
#ifndef Z2MIDI_H
#define Z2MIDI_H

#include <stdint.h>

/* Z2M_NO_NAMES: firmware build without descriptive strings (no absolute pointers in tables) */
#ifdef Z2M_NO_NAMES
#define Z2M_NAME(s)
#define Z2M_NAME_FIELD
#else
#define Z2M_NAME(s) , s
#define Z2M_NAME_FIELD ; const char *name
#endif

#define Z2M_REPORT01_LEN   10   /* id + 9 bytes */
#define Z2M_REPORT02_LEN   53   /* id + 26 * 2 */
#define Z2M_LED80_LEN      95   /* id + 94 */
#define Z2M_LED81_LEN      41   /* id + 40 */

#define Z2M_NUM_ANALOG     26
#define Z2M_NUM_ENCODERS    3   /* browse, loop A, loop B (4th nibble unused) */

/* MIDI channel layout (0-based) */
#define Z2M_CH_MAIN        0    /* buttons (notes), knobs/faders (CC), encoders (CC rel) */
#define Z2M_CH_LED80       1    /* CC n -> raw LED n of output report 0x80 (1..94) */
#define Z2M_CH_LED81       2    /* CC n -> raw LED n of output report 0x81 (1..40) */

/* Analog hysteresis in 12-bit units: a 7-bit step is 32 units. */
#define Z2M_HYST           6

typedef struct {
    uint8_t  btn[Z2M_REPORT01_LEN];      /* last report 0x01 seen */
    uint16_t ana[Z2M_NUM_ANALOG];        /* last 12-bit values that produced a CC */
    uint8_t  ana_cc[Z2M_NUM_ANALOG];     /* last 7-bit value sent */
    uint8_t  have_btn, have_ana;
    uint8_t  led80[Z2M_LED80_LEN];       /* ready-to-send HID output report 0x80 */
    uint8_t  led81[Z2M_LED81_LEN];       /* ready-to-send HID output report 0x81 */
    uint8_t  led_dirty;                  /* bit0: 0x80 changed, bit1: 0x81 changed */
    uint8_t  sysex_state;
    /* pad layers per side (0 = left, 1 = right): bit0 = DECK A/B lit, bit1 = DECK C/D lit.
       layer 0: none, 1: A/B, 2: C/D, 3: both. Pads send on Z2M_LAYER_CH(layer). */
    uint8_t  layer[2];
    uint8_t  pad_ch[8];                  /* channel a held pad's note-on went out on */
    uint8_t  padc[4][8];                 /* pad brightness per layer, set by the host */
} z2m_state;

/* MIDI channel (0-based) of pad layer l: 1, 4, 5, 6 for layers 1-4 (2, 3 are the raw LED channels) */
#define Z2M_LAYER_CH(l)    ((l) ? (l) + 2 : 0)

/* USB-MIDI event packet; word aligned so copies are single word moves (no libc helper) */
typedef struct { uint8_t b[4]; } __attribute__((aligned(4))) z2m_pkt;

void z2m_init(z2m_state *s);

/* Feed one panel report (0x01 or 0x02, byte 0 = report id).
 * Writes up to max packets to out, returns how many were written.
 * The first report of each kind only primes the state for buttons, but sends all analog
 * positions once so the host learns the current fader/knob positions. */
int z2m_panel_in(z2m_state *s, const uint8_t *report, int len, z2m_pkt *out, int max);

/* Feed one USB-MIDI packet from the host (LED feedback). */
void z2m_midi_in(z2m_state *s, const uint8_t pkt[4]);

/* Lookups (for docs/tests): returns -1 when not mapped. */
int z2m_button_note(int byte, uint8_t mask);
int z2m_analog_cc(int index);

typedef struct { uint8_t cc Z2M_NAME_FIELD; } z2m_analog_def;
typedef struct { uint8_t byte, shift, cc Z2M_NAME_FIELD; } z2m_encoder_def;

#define Z2M_NUM_BUTTONS    48
extern const uint8_t         z2m_button_led[Z2M_NUM_BUTTONS];
#ifndef Z2M_NO_NAMES
extern const char *const     z2m_button_names[Z2M_NUM_BUTTONS];
#endif
extern const int             z2m_num_buttons;
extern const z2m_analog_def  z2m_analog[Z2M_NUM_ANALOG];
extern const z2m_encoder_def z2m_encoders[Z2M_NUM_ENCODERS];

#endif
