/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zmk/ble.h>
#include <zmk/events/position_state_changed.h>
#include <totem/name_hooks.h>

/* Separate from ZMK's bond layout: upgrading does not invalidate pairings. */
struct name_record {
    uint8_t version;
    bt_addr_le_t peer;
    char automatic[TN_NAME_MAX + 1], alias[TN_NAME_MAX + 1];
};
static struct name_record records[ZMK_BLE_PROFILE_COUNT];
static unsigned generation[ZMK_BLE_PROFILE_COUNT];
static bool dirty[ZMK_BLE_PROFILE_COUNT], ready;
static struct tn_editor editor;
static unsigned edit_profile, edit_generation;
static int64_t edit_activity;
static bool save_failed;
static unsigned dispatch_depth;
static struct bt_conn *attempted[ZMK_BLE_PROFILE_COUNT];
static struct {
    struct bt_gatt_read_params params;
    struct bt_conn *conn;
    unsigned profile, generation;
    int64_t started;
} query;
K_MUTEX_DEFINE(names_mutex);
static void tick(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(names_work, tick);

static int store(unsigned i, const struct name_record *record) {
    char key[20];
    snprintf(key, sizeof(key), "tnames/%u", i);
    return bt_addr_le_cmp(&record->peer, BT_ADDR_LE_ANY) == 0
               ? settings_delete(key) : settings_save_one(key, record, sizeof(*record));
}

static bool valid_name(const char *name) {
    for (unsigned i = 0; i <= TN_NAME_MAX; i++) {
        if (!name[i]) return true;
        if ((unsigned char)name[i] < 32 || (unsigned char)name[i] > 126) return false;
    }
    return false;
}

static int load(const char *key, size_t len, settings_read_cb read_cb, void *arg) {
    char *end;
    unsigned long i = strtoul(key, &end, 10);
    if (end == key || *end || i >= ZMK_BLE_PROFILE_COUNT) return -ENOENT;
    if (len != sizeof(struct name_record)) return -EINVAL;
    struct name_record r;
    int count = read_cb(arg, &r, sizeof(r));
    if (count != sizeof(r) || r.version != 1 || !valid_name(r.alias) || !valid_name(r.automatic))
        return -EINVAL;
    k_mutex_lock(&names_mutex, K_FOREVER);
    records[i] = r;
    k_mutex_unlock(&names_mutex);
    return 0;
}

static int loaded(void) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    ready = true;
    k_mutex_unlock(&names_mutex);
    k_work_reschedule(&names_work, K_MSEC(250));
    return 0;
}
SETTINGS_STATIC_HANDLER_DEFINE(totem_names, "tnames", NULL, load, loaded, NULL);

/* Called on every explicit bond-address change, including BT_CLR followed by
 * re-pairing the same host. Address comparison alone cannot detect that case. */
void totem_host_names_forget(unsigned i) {
    if (i >= ZMK_BLE_PROFILE_COUNT) return;
    k_mutex_lock(&names_mutex, K_FOREVER);
    memset(&records[i], 0, sizeof(records[i]));
    records[i].version = 1;
    generation[i]++;
    dirty[i] = true;
    if (editor.mode != TN_IDLE && edit_profile == i) tn_finish(&editor);
    k_mutex_unlock(&names_mutex);
}

/* Must hold names_mutex. Also validates persisted records on first boot. */
static void reconcile(void) {
    for (unsigned i = 0; i < ZMK_BLE_PROFILE_COUNT; i++) {
        /* Close the disconnect/read-start race without pinning a dead slot. */
        if (attempted[i]) {
            struct bt_conn_info info;
            if (bt_conn_get_info(attempted[i], &info) || info.state != BT_CONN_STATE_CONNECTED) {
                bt_conn_unref(attempted[i]);
                attempted[i] = NULL;
            }
        }
        const bt_addr_le_t *peer = zmk_ble_profile_address(i);
        if (bt_addr_le_cmp(peer, &records[i].peer)) {
            memset(&records[i], 0, sizeof(records[i]));
            records[i].version = 1;
            records[i].peer = *peer;
            generation[i]++;
            dirty[i] = true;
        }
    }
    if (editor.mode != TN_IDLE &&
        (edit_profile != zmk_ble_active_profile_index() ||
         edit_generation != generation[edit_profile])) tn_finish(&editor);
}

void totem_host_names_begin(void) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    if (ready && editor.mode == TN_IDLE && !zmk_ble_active_profile_is_open()) {
        reconcile();
        edit_profile = zmk_ble_active_profile_index();
        edit_generation = generation[edit_profile];
        tn_begin(&editor, records[edit_profile].alias);
        edit_activity = k_uptime_get();
        save_failed = false;
    }
    k_mutex_unlock(&names_mutex);
}

bool totem_host_names_capture(const zmk_event_t *event) {
    const struct zmk_position_state_changed *position = as_zmk_position_state_changed(event);
    enum tn_action action;
    k_mutex_lock(&names_mutex, K_FOREVER);
    dispatch_depth++;
    if (!position) {
        k_mutex_unlock(&names_mutex);
        return false;
    }
    if (ready) reconcile();
    bool consumed = tn_position(&editor, position->position, position->state, &action);
    if (editor.mode != TN_IDLE) edit_activity = k_uptime_get();
    if (action == TN_SAVE) k_work_reschedule(&names_work, K_NO_WAIT);
    k_mutex_unlock(&names_mutex);
    if (consumed) {
        /* Keep the display awake without feeding editor input to the keymap. */
        extern const struct zmk_listener zmk_listener_activity;
        zmk_listener_activity.callback(event);
    }
    return consumed;
}

void totem_host_names_after_dispatch(void) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    /* Key release listeners can raise nested events before releasing HID mods. */
    if (--dispatch_depth == 0) tn_after_dispatch(&editor);
    k_mutex_unlock(&names_mutex);
}

void totem_host_names_snapshot(struct tn_snapshot *out) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    unsigned i = zmk_ble_active_profile_index();
    *out = (struct tn_snapshot){.profile = i, .mode = editor.mode, .save_failed = save_failed};
    tn_display_name(out->name, records[i].alias, records[i].automatic, i);
    memcpy(out->draft, editor.draft, sizeof(out->draft));
    k_mutex_unlock(&names_mutex);
}

static uint8_t name_read(struct bt_conn *conn, uint8_t err, struct bt_gatt_read_params *params,
                         const void *data, uint16_t length) {
    char name[TN_NAME_MAX + 1] = {0};
    if (!err && data) tn_sanitize(name, data, length);
    k_mutex_lock(&names_mutex, K_FOREVER);
    unsigned i = query.profile;
    if (*name && query.generation == generation[i] &&
        !bt_addr_le_cmp(zmk_ble_profile_address(i), &records[i].peer) &&
        strcmp(name, records[i].automatic)) {
        memcpy(records[i].automatic, name, sizeof(name));
        dirty[i] = true;
    }
    struct bt_conn *held = query.conn;
    query.conn = NULL;
    k_mutex_unlock(&names_mutex);
    if (held) bt_conn_unref(held);
    /* One value only. The parameters are static and stay alive across callbacks. */
    return BT_GATT_ITER_STOP;
}

static void disconnected(struct bt_conn *conn, uint8_t reason) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    for (unsigned i = 0; i < ZMK_BLE_PROFILE_COUNT; i++) {
        if (attempted[i] == conn) {
            attempted[i] = NULL;
            bt_conn_unref(conn);
        }
    }
    k_mutex_unlock(&names_mutex);
}
BT_CONN_CB_DEFINE(totem_names_connection) = {.disconnected = disconnected};

static void try_query(void) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    struct bt_conn *pending = query.conn ? bt_conn_ref(query.conn) : NULL;
    bool expired = pending && k_uptime_get() - query.started > 10000;
    k_mutex_unlock(&names_mutex);
    if (pending) {
        /* This pinned Zephyr invokes the read callback when cancelling. */
        if (expired) bt_gatt_cancel(pending, &query.params);
        bt_conn_unref(pending);
        return;
    }
    if (!zmk_ble_active_profile_is_connected() || zmk_ble_active_profile_is_open()) return;
    struct bt_conn *conn = zmk_ble_active_profile_conn();
    if (!conn) return;
    if (bt_conn_get_security(conn) < BT_SECURITY_L2) {
        bt_conn_unref(conn);
        return;
    }
    k_mutex_lock(&names_mutex, K_FOREVER);
    unsigned i = zmk_ble_active_profile_index();
    if (attempted[i] == conn ||
        bt_addr_le_cmp(bt_conn_get_dst(conn), zmk_ble_profile_address(i))) {
        k_mutex_unlock(&names_mutex);
        bt_conn_unref(conn);
        return;
    }
    if (attempted[i]) bt_conn_unref(attempted[i]);
    attempted[i] = bt_conn_ref(conn);
    query.conn = conn; /* Own the reference until callback, including errors. */
    query.profile = i;
    query.generation = generation[i];
    query.started = k_uptime_get();
    query.params = (struct bt_gatt_read_params){
        .func = name_read, .handle_count = 0,
        .by_uuid = {.uuid = BT_UUID_GAP_DEVICE_NAME, .start_handle = 1, .end_handle = 0xffff},
    };
    k_mutex_unlock(&names_mutex);
    int err = bt_gatt_read(conn, &query.params);
    if (err) name_read(conn, BT_ATT_ERR_UNLIKELY, &query.params, NULL, 0);
}

static void tick(struct k_work *work) {
    k_mutex_lock(&names_mutex, K_FOREVER);
    if (!ready) {
        k_mutex_unlock(&names_mutex);
        return;
    }
    reconcile();
    if (editor.mode != TN_IDLE && k_uptime_get() - edit_activity > 60000) tn_finish(&editor);
    if (editor.mode == TN_SAVING) {
        unsigned i = edit_profile, gen = generation[i];
        struct name_record candidate = records[i];
        tn_sanitize(candidate.alias, editor.draft, strlen(editor.draft));
        k_mutex_unlock(&names_mutex);
        int err = store(i, &candidate);
        k_mutex_lock(&names_mutex, K_FOREVER);
        reconcile();
        if (editor.mode == TN_SAVING && generation[i] == gen) {
            if (err) {
                save_failed = true;
                editor.mode = TN_EDIT;
            } else {
                memcpy(records[i].alias, candidate.alias, sizeof(candidate.alias));
                tn_finish(&editor);
            }
        }
    }
    for (unsigned i = 0; i < ZMK_BLE_PROFILE_COUNT; i++) {
        if (!dirty[i]) continue;
        struct name_record copy = records[i];
        unsigned gen = generation[i];
        k_mutex_unlock(&names_mutex);
        int err = store(i, &copy);
        k_mutex_lock(&names_mutex, K_FOREVER);
        if (!err && generation[i] == gen && !memcmp(&copy, &records[i], sizeof(copy))) dirty[i] = false;
    }
    k_mutex_unlock(&names_mutex);
    try_query();
    k_work_reschedule(&names_work, K_MSEC(250));
}
