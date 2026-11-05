/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TN_NAME_MAX 24
enum tn_mode { TN_IDLE, TN_ARMING, TN_EDIT, TN_SAVING, TN_DRAIN };
enum tn_action { TN_NONE, TN_SAVE, TN_CANCEL };
struct tn_editor {
    uint64_t held, passthrough;
    enum tn_mode mode;
    char draft[TN_NAME_MAX + 1];
};

void tn_sanitize(char out[TN_NAME_MAX + 1], const void *data, size_t len);
void tn_display_name(char out[TN_NAME_MAX + 1], const char *alias,
                     const char *automatic, unsigned profile);
void tn_begin(struct tn_editor *e, const char *alias);
/* Returns true only for events that must not reach the normal keymap. */
bool tn_position(struct tn_editor *e, unsigned position, bool pressed, enum tn_action *action);
/* Called after normal key releases have been dispatched, never before. */
void tn_after_dispatch(struct tn_editor *e);
void tn_finish(struct tn_editor *e);
