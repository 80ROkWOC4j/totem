/* SPDX-License-Identifier: MIT */
#include <totem/name_core.h>
#include <stdio.h>
#include <string.h>

void tn_sanitize(char out[TN_NAME_MAX + 1], const void *data, size_t len) {
    const unsigned char *s = data;
    size_t n = 0;
    bool readable = false;
    for (size_t i = 0; i < len && s[i] && n < TN_NAME_MAX; i++) {
        if (s[i] >= 32 && s[i] <= 126) {
            out[n++] = s[i];
            readable |= s[i] != ' ';
        } else if (s[i] >= 0xc0) {
            out[n++] = '?'; /* One placeholder per non-ASCII UTF-8 character. */
        }
    }
    while (n && out[n - 1] == ' ') n--;
    out[readable ? n : 0] = 0;
}

void tn_display_name(char out[TN_NAME_MAX + 1], const char *alias,
                     const char *automatic, unsigned profile) {
    if (*alias || *automatic) {
        snprintf(out, TN_NAME_MAX + 1, "%s", *alias ? alias : automatic);
    } else {
        snprintf(out, TN_NAME_MAX + 1, "BT %u", profile + 1);
    }
}

void tn_begin(struct tn_editor *e, const char *alias) {
    if (e->mode != TN_IDLE) return;
    snprintf(e->draft, sizeof(e->draft), "%s", alias);
    e->passthrough = e->held;
    e->mode = TN_ARMING;
}

void tn_finish(struct tn_editor *e) {
    /* Existing keys from before entry still need their ordinary releases. */
    e->mode = e->held ? TN_DRAIN : TN_IDLE;
}

void tn_after_dispatch(struct tn_editor *e) {
    if (!e->held && e->mode == TN_ARMING) e->mode = TN_EDIT;
    if (!e->held && e->mode == TN_DRAIN) e->mode = TN_IDLE;
}

bool tn_position(struct tn_editor *e, unsigned p, bool pressed, enum tn_action *action) {
    *action = TN_NONE;
    if (p >= 38) return false;
    uint64_t bit = UINT64_C(1) << p;
    bool was_pressed = (e->held & bit) != 0;
    if (pressed) e->held |= bit;
    else e->held &= ~bit;
    if (e->mode == TN_IDLE) return false;
    if (!pressed && (e->passthrough & bit)) {
        e->passthrough &= ~bit;
        return false;
    }
    if (e->mode != TN_EDIT || !pressed || was_pressed) return true;
    if (p == 32) {
        *action = TN_CANCEL;
        tn_finish(e);
    } else if (p == 37) {
        *action = TN_SAVE;
        e->mode = TN_SAVING;
    } else if (p == 33) {
        size_t n = strlen(e->draft);
        if (n) e->draft[n - 1] = 0;
    } else {
        static const char keys[] = "qwertyuiopasdfghjkl;-zxcvbnm,./'";
        char c = p < 32 ? keys[p] : (p == 35 ? ' ' : 0);
        if ((e->held & (UINT64_C(1) << 34)) && p < 10) c = "1234567890"[p];
        if (e->held & (UINT64_C(1) << 36)) {
            if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
            else if (c == '-') c = '_';
        }
        size_t n = strlen(e->draft);
        if (c && n < TN_NAME_MAX) {
            e->draft[n] = c;
            e->draft[n + 1] = 0;
        }
    }
    return true;
}
