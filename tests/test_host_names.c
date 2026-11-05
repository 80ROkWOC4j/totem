/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <totem/name_core.h>

static bool event(struct tn_editor *e, unsigned p, bool pressed, enum tn_action expected) {
    enum tn_action action;
    bool capture = tn_position(e, p, pressed, &action);
    assert(action == expected);
    tn_after_dispatch(e);
    return capture;
}
static void tap(struct tn_editor *e, unsigned p) {
    assert(event(e, p, true, TN_NONE));
    assert(event(e, p, false, TN_NONE));
}

int main(void) {
    char name[TN_NAME_MAX + 1];
    tn_display_name(name, "", "", 4); assert(!strcmp(name, "BT 5"));
    tn_display_name(name, "", "Galaxy", 4); assert(!strcmp(name, "Galaxy"));
    tn_display_name(name, "Work", "Galaxy", 4); assert(!strcmp(name, "Work"));
    const char remote[] = "\x01My \xed\x95\x9c\xea\xb8\x80 PC  ";
    tn_sanitize(name, remote, sizeof(remote)); assert(!strcmp(name, "My ?? PC"));
    tn_sanitize(name, "\xed\x95\x9c", 3); assert(!*name);
    tn_sanitize(name, "   ", 3); assert(!*name);
    tn_sanitize(name, "abcdefghijklmnopqrstuvwxyz", 26); assert(strlen(name) == TN_NAME_MAX);

    struct tn_editor e = {0};
    assert(!event(&e, 33, true, TN_NONE)); /* Enter from held layer keys. */
    assert(!event(&e, 34, true, TN_NONE));
    tn_begin(&e, "");
    assert(e.mode == TN_ARMING);
    assert(event(&e, 0, true, TN_NONE)); /* Early typing cannot leak. */
    assert(!event(&e, 33, false, TN_NONE)); /* Existing key releases MUST pass. */
    assert(!event(&e, 34, false, TN_NONE));
    assert(e.mode == TN_ARMING);
    assert(event(&e, 0, false, TN_NONE));
    assert(e.mode == TN_EDIT && !*e.draft);
    assert(event(&e, 36, true, TN_NONE));
    tap(&e, 13); /* F */
    assert(event(&e, 36, false, TN_NONE));
    tap(&e, 18); tap(&e, 7); tap(&e, 9); /* lip */
    assert(event(&e, 34, true, TN_NONE)); tap(&e, 5); /* 6 */
    assert(event(&e, 34, false, TN_NONE));
    assert(!strcmp(e.draft, "Flip6"));
    assert(event(&e, 37, true, TN_SAVE));
    assert(e.mode == TN_SAVING);
    tap(&e, 0); assert(!strcmp(e.draft, "Flip6"));
    tn_finish(&e); assert(e.mode == TN_DRAIN);
    assert(event(&e, 37, false, TN_NONE)); assert(e.mode == TN_IDLE);
    assert(!event(&e, 0, true, TN_NONE)); assert(!event(&e, 0, false, TN_NONE));

    tn_begin(&e, "Flip6"); tn_after_dispatch(&e);
    tap(&e, 33); assert(!strcmp(e.draft, "Flip"));
    for (int i = 0; i < 30; i++) tap(&e, 0);
    assert(strlen(e.draft) == TN_NAME_MAX);
    assert(event(&e, 32, true, TN_CANCEL));
    assert(event(&e, 0, true, TN_NONE));
    assert(event(&e, 32, false, TN_NONE)); assert(e.mode == TN_DRAIN);
    assert(event(&e, 0, false, TN_NONE)); assert(e.mode == TN_IDLE);

    /* Cancel/profile switch while arming must not strand the original layer. */
    assert(!event(&e, 34, true, TN_NONE));
    tn_begin(&e, ""); tn_finish(&e);
    assert(!event(&e, 34, false, TN_NONE)); assert(e.mode == TN_IDLE);

    /* Enter only after the final old release has gone through the keymap. */
    assert(!event(&e, 36, true, TN_NONE)); tn_begin(&e, "");
    enum tn_action action;
    assert(!tn_position(&e, 36, false, &action)); assert(e.mode == TN_ARMING);
    tn_after_dispatch(&e); assert(e.mode == TN_EDIT);
    tn_finish(&e); assert(e.mode == TN_IDLE);
    puts("host-name precedence, sanitization and modal input tests passed");
    return 0;
}
