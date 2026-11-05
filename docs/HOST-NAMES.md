# Bluetooth host names

The dongle OLED shows **saved alias → automatic host name → BT 1 … BT 5**,
in that order. The name belongs to the selected Bluetooth profile, even when
USB is the active output.

Names support up to **24 ASCII characters**; longer names scroll. Unsupported
characters, including Korean, appear as `?`. Entirely unsupported names fall
back to the profile number.

## Automatic names

The dongle requests the host's Bluetooth device name once per encrypted
connection. No extra app or pairing is needed, but some hosts provide no name
or a generic name. Reconnecting retries the request; a failure keeps the cached name.

Names and aliases survive power cycles and remain visible offline.
Clearing or replacing the pairing removes both.

## Edit an alias

Requires the OLED dongle and a paired Bluetooth profile; the host may be offline.

1. Select the intended profile on the device layer and release the keys.
2. Hold both layer thumbs, then hold **Q (`BT name`) for at least 0.8 seconds**.
3. Release all keys to open `BT n NAME`.
4. Type an alias and save with the rightmost thumb.

The editor uses physical QWERTY positions regardless of the normal keymap or
host language. Thumb controls, left to right:

| Base key | Editor function | OLED hint |
| --- | --- | --- |
| Left GUI | Cancel | `ESC` |
| Symbol layer | Backspace | `<` |
| Navigation layer | Hold for top-row digits `1 2 3 4 5 6 7 8 9 0` | `#` |
| Space | Space | `_` |
| Right Shift | Hold for uppercase | `^` |
| Right Alt | Save | `OK` |

Comma, period, slash, apostrophe and semicolon keep their base positions.
The outer left Ctrl position types `-`, or `_` with Shift. There is no key repeat.
Only an existing alias is prefilled; automatic names are not copied into the draft.
Save an empty alias to restore automatic naming. Trailing spaces are removed.

Editing does not send keystrokes to the host. Inactivity for 60 seconds or a
profile change cancels editing. `Save failed` keeps the draft open for retry
or cancellation. Release all keys to resume normal typing.

If a saved ZMK Studio keymap overrides the entry key, assign
`Edit BT host name (hold)` or restore the default keymap. Moving the entry key
does not change the editor's physical layout.

## Update

After [setup](../README.md#build), build the dongle application:

```sh
./scripts/container.sh python3 scripts/build.py totem_dongle_central_oled
```

Install `build/artifacts/totem_dongle_central_oled-ota.zip` using the
[OTA guide](OTA.md#android-ota). This feature requires only a dongle application
update. See [UPSTREAM.md](../UPSTREAM.md) for the implementation sources.

English automatic names have been confirmed on hardware. Alias save/persistence,
cancel and empty-alias behavior still need hardware verification.
