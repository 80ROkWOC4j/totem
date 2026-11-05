/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <string.h>
#include <totem/host_names.h>
#include <totem/name_widget.h>

static lv_obj_t *name, *overlay, *title, *draft, *help, *footer;
static struct tn_snapshot previous;
static bool rendered;
static lv_anim_t name_scroll;

static lv_obj_t *label(lv_obj_t *parent, int x, int y, int width) {
    lv_obj_t *obj = lv_label_create(parent);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_width(obj, width);
    lv_obj_set_style_text_letter_space(obj, 0, 0);
    lv_label_set_long_mode(obj, LV_LABEL_LONG_SCROLL_CIRCULAR);
    return obj;
}

static void refresh(lv_timer_t *timer) {
    struct tn_snapshot s;
    totem_host_names_snapshot(&s);
    if (!rendered || strcmp(previous.name, s.name)) lv_label_set_text(name, s.name);
    bool editing = s.mode != TN_IDLE && s.mode != TN_DRAIN;
    if (editing) lv_obj_clear_flag(overlay, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(overlay, LV_OBJ_FLAG_HIDDEN);
    if (!rendered || s.profile != previous.profile) {
        char text[20];
        snprintf(text, sizeof(text), "BT %u NAME", s.profile + 1);
        lv_label_set_text(title, text);
    }
    if (!rendered || strcmp(s.draft, previous.draft)) {
        /* Keep the caret and most recent characters visible while typing. */
        char text[18];
        size_t n = strlen(s.draft);
        snprintf(text, sizeof(text), "%s_", s.draft + (n > 14 ? n - 14 : 0));
        lv_label_set_text(draft, text);
    }
    if (!rendered || s.mode != previous.mode || s.save_failed != previous.save_failed) {
        lv_label_set_text(help, s.mode == TN_ARMING ? "Release keys" :
                               s.mode == TN_SAVING ? "Saving..." : "ESC < # _ ^ OK");
        lv_label_set_text(footer, s.save_failed ? "Save failed" : "Empty = auto");
    }
    previous = s;
    rendered = true;
}

void totem_host_names_widget_init(lv_obj_t *screen) {
    name = label(screen, 1, 23, 76);
    lv_anim_init(&name_scroll);
    lv_anim_set_delay(&name_scroll, 1000);
    lv_anim_set_repeat_delay(&name_scroll, 1000);
    lv_obj_set_style_anim(name, &name_scroll, 0);
    lv_obj_set_style_anim_speed(name, 24, 0);
    overlay = lv_obj_create(screen);
    lv_obj_remove_style_all(overlay);
    lv_obj_set_pos(overlay, 0, 0);
    lv_obj_set_size(overlay, 129, 64);
    lv_obj_set_style_bg_color(overlay, lv_color_white(), 0);
    lv_obj_set_style_bg_opa(overlay, LV_OPA_COVER, 0);
    lv_obj_set_style_text_color(overlay, lv_color_black(), 0);
    lv_obj_clear_flag(overlay, LV_OBJ_FLAG_SCROLLABLE);
    title = label(overlay, 1, 2, 126);
    draft = label(overlay, 1, 19, 126);
    help = label(overlay, 1, 39, 126);
    footer = label(overlay, 1, 53, 126);
    refresh(NULL);
    lv_timer_create(refresh, 100, NULL);
}
