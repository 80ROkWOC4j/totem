/* SPDX-License-Identifier: MIT */
#define DT_DRV_COMPAT totem_host_name_editor
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <totem/host_names.h>

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)
#ifdef CONFIG_TOTEM_HOST_NAMES
static int64_t pressed_at;
#endif
static int press(struct zmk_behavior_binding *binding, struct zmk_behavior_binding_event event) {
#ifdef CONFIG_TOTEM_HOST_NAMES
    pressed_at = event.timestamp;
#endif
    return ZMK_BEHAVIOR_OPAQUE;
}
static int release(struct zmk_behavior_binding *binding, struct zmk_behavior_binding_event event) {
#ifdef CONFIG_TOTEM_HOST_NAMES
    if (event.timestamp - pressed_at >= 800) totem_host_names_begin();
#endif
    return ZMK_BEHAVIOR_OPAQUE;
}
static const struct behavior_driver_api api = {
    .binding_pressed = press, .binding_released = release,
    .locality = BEHAVIOR_LOCALITY_CENTRAL,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .get_parameter_metadata = zmk_behavior_get_empty_param_metadata,
#endif
};
BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL,
                       CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &api);
#endif
