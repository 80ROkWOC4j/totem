/* SPDX-License-Identifier: MIT
 * Exercise the actual firmware backend with deterministic BT/settings adapters.
 * Core input tests are separate; these cover persistence and async lifetimes.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define ZMK_BLE_PROFILE_COUNT 5
#define K_FOREVER 0
#define K_NO_WAIT 0
#define K_MSEC(ms) (ms)
#define K_MUTEX_DEFINE(name) int name
#define K_WORK_DELAYABLE_DEFINE(name, cb) struct k_work_delayable name
#define SETTINGS_STATIC_HANDLER_DEFINE(...)
#define BT_CONN_CB_DEFINE(name) struct conn_callbacks name
#define BT_SECURITY_L2 2
#define BT_ATT_ERR_UNLIKELY 14
#define BT_GATT_ITER_STOP 0
#define BT_UUID_GAP_DEVICE_NAME ((void *)0x2a00)
#define BT_CONN_STATE_CONNECTED 1
typedef struct { uint8_t type, val[6]; } bt_addr_le_t;
static const bt_addr_le_t any;
#define BT_ADDR_LE_ANY (&any)
struct k_work { int unused; };
struct k_work_delayable { int unused; };
struct bt_conn { int refs, security, state; bt_addr_le_t peer; };
struct bt_conn_info { int state; };
struct conn_callbacks { void (*disconnected)(struct bt_conn *, uint8_t); };
struct bt_gatt_read_params {
    uint8_t (*func)(struct bt_conn *, uint8_t, struct bt_gatt_read_params *, const void *, uint16_t);
    size_t handle_count;
    struct { const void *uuid; uint16_t start_handle, end_handle; } by_uuid;
};
struct zmk_position_state_changed { unsigned position; bool state; };
typedef struct { bool is_position; struct zmk_position_state_changed data; } zmk_event_t;
struct zmk_listener { int (*callback)(const zmk_event_t *); };
typedef int (*settings_read_cb)(void *, void *, size_t);
static unsigned active;
static int64_t now;
static bt_addr_le_t peers[5];
static struct bt_conn host = {.refs = 1, .security = 2};
static struct bt_gatt_read_params *pending;
static struct bt_conn *pending_conn;
static int read_calls, save_calls, fail_save;
static uint8_t disk[5][128];
static size_t disk_size[5];
static void k_mutex_lock(int *mutex, int wait) { (void)mutex; (void)wait; }
static void k_mutex_unlock(int *mutex) { (void)mutex; }
static int64_t k_uptime_get(void) { return now; }
static int k_work_reschedule(struct k_work_delayable *work, int delay) { return 0; }
static int bt_addr_le_cmp(const bt_addr_le_t *a, const bt_addr_le_t *b) { return memcmp(a, b, sizeof(*a)); }
static struct bt_conn *bt_conn_ref(struct bt_conn *c) { c->refs++; return c; }
static void bt_conn_unref(struct bt_conn *c) { assert(c->refs > 1); c->refs--; }
static int bt_conn_get_security(struct bt_conn *c) { return c->security; }
static const bt_addr_le_t *bt_conn_get_dst(struct bt_conn *c) { return &c->peer; }
static int bt_conn_get_info(struct bt_conn *c, struct bt_conn_info *info) { info->state = c->state; return 0; }
static bt_addr_le_t *zmk_ble_profile_address(unsigned i) { return &peers[i]; }
static unsigned zmk_ble_active_profile_index(void) { return active; }
static bool zmk_ble_active_profile_is_open(void) { return !bt_addr_le_cmp(&peers[active], &any); }
static bool zmk_ble_active_profile_is_connected(void) { return host.state == 1; }
static struct bt_conn *zmk_ble_active_profile_conn(void) { return bt_conn_ref(&host); }
static const struct zmk_position_state_changed *as_zmk_position_state_changed(const zmk_event_t *e) {
    return e->is_position ? &e->data : NULL;
}
static int activity(const zmk_event_t *event) { return 0; }
const struct zmk_listener zmk_listener_activity = {.callback = activity};
static int settings_save_one(const char *key, const void *data, size_t len) {
    if (fail_save) return -5;
    unsigned i; assert(sscanf(key, "tnames/%u", &i) == 1 && i < 5);
    assert(len <= sizeof(disk[i])); memcpy(disk[i], data, len); disk_size[i] = len;
    save_calls++; return 0;
}
static int settings_delete(const char *key) {
    if (fail_save) return -5;
    unsigned i; assert(sscanf(key, "tnames/%u", &i) == 1 && i < 5);
    disk_size[i] = 0; save_calls++; return 0;
}
static int bt_gatt_read(struct bt_conn *c, struct bt_gatt_read_params *params) {
    assert(!pending); pending = params; pending_conn = c; read_calls++; return 0;
}
static void respond(uint8_t err, const char *name) {
    struct bt_gatt_read_params *params = pending;
    struct bt_conn *c = pending_conn;
    assert(params); pending = NULL; pending_conn = NULL;
    assert(params->func(c, err, params, name, name ? strlen(name) : 0) == BT_GATT_ITER_STOP);
}
static void bt_gatt_cancel(struct bt_conn *c, void *params) {
    if (pending == params) respond(BT_ATT_ERR_UNLIKELY, NULL);
}

#include "../firmware/host-names/src/host_names.c"

static int read_disk(void *arg, void *buf, size_t len) {
    unsigned i = *(unsigned *)arg;
    memcpy(buf, disk[i], len); return len;
}
static void key(unsigned p, bool down) {
    zmk_event_t e = {.is_position = true, .data = {p, down}};
    assert(totem_host_names_capture(&e)); totem_host_names_after_dispatch();
}

int main(void) {
    active = 1; peers[1].val[0] = 42; host.peer = peers[1]; host.state = 1;
    loaded(); tick(NULL);
    assert(read_calls == 1 && pending && host.refs == 3);
    respond(0, "Galaxy Z Flip6"); assert(host.refs == 2);
    tick(NULL); assert(read_calls == 1 && disk_size[1] == sizeof(struct name_record));
    struct tn_snapshot s; totem_host_names_snapshot(&s);
    assert(!strcmp(s.name, "Galaxy Z Flip6"));
    int writes = save_calls;
    for (int i = 0; i < 10; i++) tick(NULL);
    assert(save_calls == writes && read_calls == 1); /* No polling wear / GATT spam. */

    totem_host_names_begin(); tn_after_dispatch(&editor);
    strcpy(editor.draft, "Flip6");
    key(37, true); fail_save = 1; tick(NULL);
    assert(editor.mode == TN_EDIT && save_failed);
    assert(!strcmp(records[1].alias, "")); key(37, false);
    fail_save = 0; key(37, true); tick(NULL); key(37, false);
    assert(editor.mode == TN_IDLE && !strcmp(records[1].alias, "Flip6"));
    memset(&records[1], 0, sizeof(records[1]));
    assert(load("1", disk_size[1], read_disk, &active) == 0);
    totem_host_names_snapshot(&s); assert(!strcmp(s.name, "Flip6"));

    totem_host_names_begin(); tn_after_dispatch(&editor);
    editor.draft[0] = 0; key(37, true); tick(NULL); key(37, false);
    totem_host_names_snapshot(&s); assert(!strcmp(s.name, "Galaxy Z Flip6"));

    host.state = 0; disconnected(&host, 0); assert(host.refs == 1);
    host.state = 1; tick(NULL); assert(pending && read_calls == 2);
    /* Clear + re-pair to the SAME address while the old reply is in flight. */
    totem_host_names_forget(1); peers[1] = any; reconcile();
    peers[1] = host.peer; reconcile();
    respond(0, "Obsolete name"); assert(!*records[1].automatic && !*records[1].alias);
    host.state = 0; disconnected(&host, 0); tick(NULL);
    totem_host_names_snapshot(&s); assert(!strcmp(s.name, "BT 2"));
    host.state = 1; tick(NULL); assert(pending);
    now += 10001; tick(NULL); assert(!pending && host.refs == 2);
    tick(NULL); assert(read_calls == 3); /* Timeout does not continuously retry. */
    host.state = 0; disconnected(&host, 0); assert(host.refs == 1);

    /* Editing one profile cannot write a different profile after a switch. */
    totem_host_names_begin(); tn_after_dispatch(&editor); strcpy(editor.draft, "Wrong");
    key(37, true); active = 2; tick(NULL); key(37, false);
    assert(editor.mode == TN_IDLE && !*records[1].alias && !*records[2].alias);
    totem_host_names_begin(); assert(editor.mode == TN_IDLE); /* Empty slot. */

    /* Nested non-position events must not activate editing before keyup completes. */
    active = 1;
    zmk_event_t old_key = {.is_position = true, .data = {34, true}};
    assert(!totem_host_names_capture(&old_key)); totem_host_names_after_dispatch();
    totem_host_names_begin(); old_key.data.state = false;
    assert(!totem_host_names_capture(&old_key));
    zmk_event_t nested = {0};
    assert(!totem_host_names_capture(&nested)); totem_host_names_after_dispatch();
    assert(editor.mode == TN_ARMING && dispatch_depth == 1);
    totem_host_names_after_dispatch(); assert(editor.mode == TN_EDIT && dispatch_depth == 0);
    now += 60001; tick(NULL); assert(editor.mode == TN_IDLE);

    /* An explicit clear removes the on-disk record as well. */
    totem_host_names_forget(1); peers[1] = any; tick(NULL);
    assert(disk_size[1] == 0);
    puts("host-name persistence, clearing, GATT lifetime and timeout tests passed");
    return 0;
}
