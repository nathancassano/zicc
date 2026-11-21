enum Mode { MODE_NEG = -3, MODE_ZERO = 0, MODE_NEXT, MODE_COUNT = MODE_NEXT + 3, };
typedef enum Mode Mode;
typedef enum { LOW = -32768, LOW_NEXT, HIGH = 32767 } Limits;
enum { ALIAS = MODE_NEXT, MASK = (1 << 3) | 2, CHOICE = 1 ? 7 : 1 / 0,
       LOGIC = 0 && 1 / 0, CHAR_VALUE = 'A', STEP = LOW + 10 };
const Mode choices[MODE_COUNT + 1] = { MODE_NEG, MODE_ZERO, MODE_NEXT, CHOICE, MASK };
Mode global;
struct Packet { char first; Mode mode; char last; };
typedef int Shadow;

Mode identity(Mode x) { return x; }
long widen(Mode x) { return x; }

int main(void)
{
    Mode local = MODE_NEG;
    Mode *pointer = &local;
    Limits limit = LOW;
    struct Packet packet;
    int values[MODE_COUNT + 1];
#ifdef __ZICC__
    if (sizeof(Mode) != 2 || sizeof(enum Mode) != 2 || sizeof(MODE_NEG) != 2) return 1;
    if (sizeof(struct Packet) != 6 || sizeof(values) != 10) return 2;
#endif
    if (LOW != -32768 || LOW_NEXT != -32767 || HIGH != 32767 || STEP != -32758) return 3;
    if (MODE_NEG != -3 || MODE_ZERO != 0 || MODE_NEXT != 1 || MODE_COUNT != 4) return 4;
    if (ALIAS != 1 || MASK != 10 || CHOICE != 7 || LOGIC != 0 || CHAR_VALUE != 65) return 5;
    if (choices[0] != -3 || choices[2] != 1 || choices[3] != 7 || choices[4] != 10) return 6;
    if (widen(local) != -3L || identity(local) != MODE_NEG) return 7;
    *pointer = MODE_NEXT;
    global = *pointer;
    if (global != 1 || limit != LOW || local + 2 != 3) return 8;
    packet.first = 11; packet.mode = MODE_NEG; packet.last = 22;
    if (packet.first != 11 || packet.mode != -3 || packet.last != 22) return 9;
    {
        enum Mode { INNER = -7, INNER_NEXT };
        enum Mode inner = INNER_NEXT;
        typedef enum { LOCAL_FIRST = 3, LOCAL_NEXT } Local;
        Local value = LOCAL_NEXT;
        if (inner != -6 || value != 4) return 10;
    }
    if (MODE_NEXT != 1) return 11;
    { enum { MODE_NEXT = 9 }; if (MODE_NEXT != 9) return 12; }
    if (MODE_NEXT != 1) return 13;
    { int MODE_NEXT = 8; if (MODE_NEXT != 8) return 14; }
    { enum { Shadow = 5 }; if (Shadow != 5) return 15; }
    { Shadow value = 6; if (value != 6) return 16; }
    { typedef enum { LOCAL_ZERO, LOCAL_ONE } Shadow; Shadow value = LOCAL_ONE; if (value != 1) return 17; }
    { Shadow value = 7; if (value != 7) return 18; }
    values[MODE_COUNT] = 42;
    if (values[4] != 42) return 19;
    return 0;
}
