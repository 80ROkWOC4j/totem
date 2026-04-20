# totem

Minimal ZMK user-config repository for the Totem keyboard family.

This repo keeps both firmware variants under one shared keymap:

- `totem_left`
- `totem_right`
- `totem_dongle_central`
- `totem_dongle_left`
- `totem_dongle_right`

The main editable keymap lives in `config/totem.keymap`.
Keyboard metadata for graphical editors lives in `config/totem.json`.

Upstream references and base commits are documented in `UPSTREAM.md`.

## Dongle Notes

- `CONFIG_ZMK_DONGLE_DISPLAY_DONGLE_BATTERY=y` enables the dongle OLED to show the
  dongle battery alongside the two split peripheral batteries.
- `CONFIG_BT_CTLR_TX_PWR_PLUS_8=y` raises BLE transmit power to `+8 dBm`. This can
  help range or link stability, but it also increases power draw, so it is best
  treated as an optional tuning knob.
