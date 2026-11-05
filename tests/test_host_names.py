"""Native tests for firmware logic, also run by the existing CI unittest step."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HostNameTests(unittest.TestCase):
    def test_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            headers = ["zephyr/bluetooth/conn.h", "zephyr/bluetooth/gatt.h",
                       "zephyr/bluetooth/uuid.h", "zephyr/kernel.h", "zephyr/settings/settings.h",
                       "zmk/ble.h", "zmk/events/position_state_changed.h", "zmk/event_manager.h"]
            for header in headers:
                path = work / header
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("/* Deterministic adapter in test_host_names_backend.c */\n")
            executable = work / "backend"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-Wno-unused-parameter", "-fsanitize=undefined",
                            "-I", str(work), "-I", str(ROOT / "firmware/host-names/include"),
                            str(ROOT / "tests/test_host_names_backend.c"),
                            str(ROOT / "firmware/host-names/src/core.c"), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    def test_modal_input(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "host-names"
            subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-fsanitize=undefined", "-I", str(ROOT / "firmware/host-names/include"),
                            str(ROOT / "tests/test_host_names.c"),
                            str(ROOT / "firmware/host-names/src/core.c"), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
