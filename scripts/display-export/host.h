/* Host-only state/event adapter. Firmware drawing sources are compiled directly. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HOST_ARG_1 _ignore,
#define HOST_ENABLED(x) HOST_ENABLED_(HOST_ARG_##x)
#define HOST_ENABLED_(x) HOST_ENABLED__(x 1, 0)
#define HOST_ENABLED__(_ignored, value, ...) value
#define IS_ENABLED(x) HOST_ENABLED(x)
#define LOG_MODULE_DECLARE(...)
#define LOG_DBG(...)
#define ZMK_SUBSCRIPTION(...)
#define ZMK_SPLIT_BLE_PERIPHERAL_COUNT CONFIG_ZMK_SPLIT_BLE_CENTRAL_PERIPHERALS

typedef struct sys_snode { struct sys_snode *next; } sys_snode_t;
typedef struct { sys_snode_t *head, *tail; } sys_slist_t;
#define SYS_SLIST_STATIC_INIT(...) {NULL, NULL}
static inline void sys_slist_append(sys_slist_t *list, sys_snode_t *node) {
    node->next = NULL;
    if (list->tail) list->tail->next = node;
    else list->head = node;
    list->tail = node;
}
#define SYS_SLIST_FOR_EACH_CONTAINER(list, item, field) \
    for (sys_snode_t *n = (list)->head; \
         n && ((item = (void *)((char *)n - offsetof(__typeof__(*item), field))), 1); \
         n = n->next)

typedef struct { int source, level; } zmk_event_t;
#define ZMK_DISPLAY_WIDGET_LISTENER(name, type, callback, getter) \
    void name##_inject(const zmk_event_t *event) { callback(getter(event)); } \
    void name##_init(void) { name##_inject(NULL); }

enum { ZMK_TRANSPORT_USB, ZMK_TRANSPORT_BLE };
struct zmk_endpoint_instance { int transport; };
struct host_state {
    int transport, profile, connected, bonded, usb, battery, mods, indicators, wpm;
    const char *layer;
};
extern struct host_state state;
static inline struct zmk_endpoint_instance zmk_endpoints_selected(void) {
    return (struct zmk_endpoint_instance){state.transport};
}
static inline int zmk_ble_active_profile_index(void) { return state.profile; }
static inline bool zmk_ble_active_profile_is_connected(void) { return state.connected; }
static inline bool zmk_ble_active_profile_is_open(void) { return !state.bonded; }
static inline bool zmk_usb_is_hid_ready(void) { return state.usb; }
static inline bool zmk_usb_is_powered(void) { return state.usb; }
static inline uint8_t zmk_battery_state_of_charge(void) { return state.battery; }
static inline uint8_t zmk_hid_get_explicit_mods(void) { return state.mods; }
static inline uint8_t zmk_keymap_highest_layer_active(void) { return 0; }
static inline const char *zmk_keymap_layer_name(uint8_t index) { return state.layer; }
struct zmk_battery_state_changed { int state_of_charge; };
struct zmk_peripheral_battery_state_changed { int source, state_of_charge; };
struct zmk_wpm_state_changed { int state; };
struct zmk_hid_indicators_changed { int indicators; };
static inline const struct zmk_battery_state_changed *as_zmk_battery_state_changed(const zmk_event_t *e) {
    return NULL;
}
static inline const struct zmk_peripheral_battery_state_changed *as_zmk_peripheral_battery_state_changed(const zmk_event_t *e) {
    static struct zmk_peripheral_battery_state_changed event;
    if (!e) return NULL;
    event = (struct zmk_peripheral_battery_state_changed){e->source, e->level};
    return &event;
}
static inline struct zmk_wpm_state_changed *as_zmk_wpm_state_changed(const zmk_event_t *e) {
    static struct zmk_wpm_state_changed event;
    event.state = state.wpm;
    return &event;
}
static inline struct zmk_hid_indicators_changed *as_zmk_hid_indicators_changed(const zmk_event_t *e) {
    static struct zmk_hid_indicators_changed event;
    event.indicators = state.indicators;
    return &event;
}
