# Upstream References

This repository started from a minimal merge of Totem-specific files from:

- `Keycoon/zmk-config-totem`
  - store: https://aliexpress.com/item/1005009718551409.html
  - doc: https://suns-shave-80u.craft.me/NDKH6lhuW8BzBi
  - repo: https://github.com/Keycoon/zmk-config-totem
  - base commit: `b66b405ff4aef822955360d705966ebfa996ea2c`
- `a741725193/zmk-sofle-dongle`
  - store: https://aliexpress.com/item/1005011640674919.html
  - doc: https://ae-pic-a1.aliexpress-media.com/kf/Se2ead0612b7448f2b4678e32ee36c0ecD.pdf
  - repo: https://github.com/a741725193/zmk-sofle-dongle
  - base commit: `d3f2f764d5324af0dbac1a680fabf33d930e6026`

The intent here is to maintain a standalone Totem-focused config repo with:

- a single shared keymap
- non-dongle firmware targets
- dongle firmware targets

## Custom ZMK Source

This repo now pins `zmk` through [config/west.yml](/home/td/keyboard/totem/config/west.yml:1) to:

- `80ROkWOC4j/zmk`
  - tracking branch: `totem-battery-curve`

That fork carries local battery-reporting changes only. The Totem shield/base config in this repo still
originates from `Keycoon/zmk-config-totem` commit `b66b405ff4aef822955360d705966ebfa996ea2c`.

This file is documentation only. It does not imply any licensing grant from the upstream repositories.
