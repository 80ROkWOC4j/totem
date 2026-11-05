"""Strict UF2 validation before offering a bootloader self-update artifact."""
import struct


def read_uf2(path, family):
    raw = path.read_bytes()
    if not raw or len(raw) % 512:
        raise ValueError("Invalid UF2 length")
    memory, seen = {}, set()
    count = len(raw) // 512
    for offset in range(0, len(raw), 512):
        block = raw[offset:offset + 512]
        m0, m1, flags, addr, size, number, total, fid = struct.unpack_from("<8I", block)
        if ((m0, m1, flags, size, total, fid) !=
                (0x0A324655, 0x9E5D5157, 0x2000, 256, count, family) or
                struct.unpack_from("<I", block, 508)[0] != 0x0AB16F30 or
                number >= count or number in seen or addr % 256):
            raise ValueError("Invalid or conflicting UF2 block")
        seen.add(number)
        for i, byte in enumerate(block[32:32 + size]):
            if addr + i in memory:
                raise ValueError("Overlapping UF2 blocks")
            memory[addr + i] = byte
    return memory


def validate_bootloader(path, vid_pid):
    memory = read_uf2(path, 0xD663823C)
    if any(not (0 <= a < 0x1000 or 0xF4000 <= a < 0xFE000 or
                0x10001000 <= a < 0x10001100) for a in memory):
        raise ValueError("Self-update touches SoftDevice/application/settings")

    def word(addr):
        return struct.unpack("<I", bytes(memory[addr + i] for i in range(4)))[0]

    if (word(0x10001014), word(0x10001018)) != (0xF4000, 0xFE000):
        raise ValueError("Bootloader/MBR parameter addresses changed")
    if (word(0xFD800), word(0xFD804)) != (0x1E9E10F1, 0x20227A79):
        raise ValueError("Missing CF2 self-update identity")
    count = word(0xFD808)
    if not 1 <= count <= 100:
        raise ValueError("Invalid CF2 table length")
    config = {word(0xFD810 + 8 * i): word(0xFD814 + 8 * i) for i in range(count)}
    if config.get(208) != vid_pid or config.get(209) != 0xADA52840:
        raise ValueError("Bootloader targets a different USB board identity")
    if not 0x20000000 < word(0xF4000) <= 0x20040000:
        raise ValueError("Invalid bootloader stack")
    reset = word(0xF4004)
    if not reset & 1 or not 0xF4000 <= (reset & ~1) < 0xFD800:
        raise ValueError("Invalid bootloader reset vector")
