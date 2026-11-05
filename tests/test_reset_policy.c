#include <assert.h>
#include "../bootloader/src/reset_policy.h"

int main(void) {
    assert(!totem_reset_enters_ota(0, 0, true, false)); /* power on */
    assert(totem_reset_enters_ota(1, 0, true, false)); /* physical reset */
    assert(!totem_reset_enters_ota(1, true, true, false));
    assert(!totem_reset_enters_ota(4, true, true, false));
    assert(!totem_reset_enters_ota(4, 0, true, false)); /* software reset */
    assert(!totem_reset_enters_ota(5, 0, true, false)); /* combined reset */
    assert(!totem_reset_enters_ota(2, 0, true, false)); /* watchdog */
    assert(!totem_reset_enters_ota(8, 0, true, false)); /* lockup */
    assert(!totem_reset_enters_ota(0x10000, 0, true, false)); /* wake */
    assert(!totem_reset_enters_ota(1, 0, true, true)); /* double reset/USB */
    assert(!totem_reset_enters_ota(1, 0, false, false)); /* upstream recovery */
    assert(!totem_reset_enters_ota(1, true, false, true));

    /* Hardware model: pin reset clears GPREGRET2, but the uninitialized RAM
     * record survives. This transition was missed by the old tests. Real
     * hardware verification of RAM retention is still required separately.
     */
    volatile totem_reset_state_t ram = {0, 0};
    uint8_t gpregret2 = 0xD6; /* obsolete totem1 storage */
    totem_reset_mark_dfu(&ram);
    gpregret2 = 0; /* physical pin reset */
    bool was_in_dfu = totem_reset_consume_dfu(&ram);
    assert(gpregret2 == 0 && was_in_dfu);
    assert(!totem_reset_enters_ota(1, was_in_dfu, true, false));
    assert(!totem_reset_consume_dfu(&ram)); /* consumed only once */
    assert(totem_reset_enters_ota(1, false, true, false)); /* next normal reset */

    /* Explicit USB requests win. Stale RAM never makes power-on select OTA. */
    totem_reset_mark_dfu(&ram);
    assert(!totem_reset_enters_ota(1, totem_reset_consume_dfu(&ram), true, true));
    totem_reset_mark_dfu(&ram);
    assert(!totem_reset_enters_ota(0, totem_reset_consume_dfu(&ram), true, false));

    /* Interrupted writes/corrupt RAM cannot impersonate a previous DFU wait. */
    ram.magic = TOTEM_DFU_RETURN_MARKER;
    ram.inverse = 0;
    assert(!totem_reset_consume_dfu(&ram));
    totem_reset_mark_dfu(&ram);
    ram.magic ^= 1;
    assert(!totem_reset_consume_dfu(&ram));
    totem_reset_mark_dfu(&ram);
    totem_reset_clear(&ram); /* successful upload / timeout / app handoff */
    assert(!totem_reset_consume_dfu(&ram));

    /* Invalid apps remain in upstream recovery, never forced to boot. */
    totem_reset_mark_dfu(&ram);
    assert(!totem_reset_enters_ota(1, totem_reset_consume_dfu(&ram), false, false));
    return 0;
}
