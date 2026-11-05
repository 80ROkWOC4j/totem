/* SPDX-License-Identifier: MIT */
#pragma once
#include <zmk/event_manager.h>
#include <totem/host_names.h>
bool totem_host_names_capture(const zmk_event_t *event);
void totem_host_names_after_dispatch(void);
