/* SPDX-License-Identifier: MIT */
#pragma once
#include <totem/name_core.h>

struct tn_snapshot {
    unsigned profile;
    enum tn_mode mode;
    char name[TN_NAME_MAX + 1], draft[TN_NAME_MAX + 1];
    bool save_failed;
};
void totem_host_names_snapshot(struct tn_snapshot *out);
void totem_host_names_begin(void);
void totem_host_names_forget(unsigned profile);
