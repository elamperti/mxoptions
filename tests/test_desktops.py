"""What depends on the desktop besides the actions: the way to the clipboard for typed text and the
kind of window the ring is drawn in. The desktops themselves are stand-ins here."""

import os
import stat
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication  # noqa: E402

import tests.support  # noqa: E402,F401
from mxoptions import clipboard, environment  # noqa: E402
from mxoptions.ui import ring  # noqa: E402

APP = QGuiApplication.instance() or QGuiApplication([])


class Desktop(unittest.TestCase):
    """Pretends to be on some desktop for the length of a test."""

    def pretend(self, desktop, session, offers=()):
        for module, name, value in ((environment, "current", lambda: desktop), (environment, "session", lambda: session),
                                    (environment, "wayland_globals", lambda timeout=1.0: frozenset(offers))):
            self.addCleanup(setattr, module, name, getattr(module, name))
            setattr(module, name, value)

    def without(self, *names):
        for name in names:
            if name in os.environ:
                self.addCleanup(os.environ.__setitem__, name, os.environ[name])
                del os.environ[name]


XCLIP = """#!/bin/sh
if [ "$3" = "-o" ]; then cat "$STORE/clip" 2>/dev/null || exit 1; else cat > "$STORE/clip"; fi
"""


@unittest.skipIf(sys.platform == "win32", "xclip is an X11 thing")
class TextThroughXclip(Desktop):
    """The text action's way to the clipboard on X11 without Plasma: a stand-in for xclip."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="mxoptions-test-")
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)
        path = os.path.join(self.folder, "xclip")
        with open(path, "w") as f:
            f.write(XCLIP)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        for name, value in (("PATH", self.folder + os.pathsep + "/usr/bin:/bin"), ("STORE", self.folder)):
            self.addCleanup(os.environ.__setitem__, name, os.environ[name]) if name in os.environ else self.addCleanup(os.environ.pop, name, None)
            os.environ[name] = value
        self.addCleanup(setattr, clipboard, "klipper", clipboard.klipper)
        clipboard.klipper = lambda method, *args: None  # no Plasma here
        self.pretend(environment.OTHER, "x11")

    def test_text_goes_there_and_back(self):
        self.assertEqual(clipboard.get_text(), "")  # nothing copied yet
        self.assertTrue(clipboard.set_text("hello, xclip"))
        self.assertEqual(clipboard.get_text(), "hello, xclip")

    def test_no_tool_at_all(self):
        os.environ["PATH"] = os.path.join(self.folder, "nowhere")
        self.assertIsNone(clipboard.get_text())
        self.assertFalse(clipboard.set_text("x"))


class WhichWindowForTheRing(Desktop):
    def setUp(self):
        self.without("MXOPTIONS_RING")
        self.addCleanup(os.environ.__setitem__, "DISPLAY", os.environ["DISPLAY"]) if "DISPLAY" in os.environ else \
            self.addCleanup(os.environ.pop, "DISPLAY", None)

    def test_kde(self):
        self.pretend(environment.KDE, "wayland", ("zwlr_layer_shell_v1",))
        self.assertEqual(ring.overlay_kind(), ring.LAYER)
        self.pretend(environment.KDE, "x11")
        self.assertEqual(ring.overlay_kind(), ring.X11)

    def test_x11(self):
        self.pretend(environment.OTHER, "x11")
        self.assertEqual(ring.overlay_kind(), ring.X11)

    def test_wayland_with_layers(self):
        self.pretend(environment.SWAY, "wayland", ("zwlr_layer_shell_v1",))
        self.assertEqual(ring.overlay_kind(), ring.LAYER)

    def test_wayland_without(self):
        self.pretend(environment.GNOME, "wayland", ("xdg_wm_base",))
        os.environ["DISPLAY"] = ":7"  # such a session keeps an X server for X11 programs: the ring goes there
        self.assertEqual(ring.overlay_kind(), ring.XWAYLAND)
        del os.environ["DISPLAY"]     # ... unless it was told not to keep one
        self.assertEqual(ring.overlay_kind(), ring.WINDOW)

    def test_it_can_be_named(self):
        self.pretend(environment.GNOME, "wayland")
        os.environ["MXOPTIONS_RING"] = "x11"
        self.addCleanup(os.environ.pop, "MXOPTIONS_RING", None)
        self.assertEqual(ring.overlay_kind(), ring.X11)


@unittest.skipIf(sys.platform == "win32", "only GNOME needs the ring in a program of its own")
class RingInAProgramOfItsOwn(unittest.TestCase):
    """The overlay's own program and what stands for it here, talking as they do on GNOME; only the X server
    is left out (the other program draws to nowhere)."""

    def setUp(self):
        self.addCleanup(setattr, ring, "HELPER_PLATFORM", ring.HELPER_PLATFORM)
        ring.HELPER_PLATFORM = "offscreen"
        self.proxy = ring.RingProxy()
        self.addCleanup(self.proxy.shutdown)
        self.heard = []
        self.proxy.opened.connect(lambda on: self.heard.append(("opened", on)))
        self.proxy.cue.connect(lambda wave: self.heard.append(("cue", wave)))

    def wait(self, condition, seconds=15.0):
        deadline = time.monotonic() + seconds
        while not condition() and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        return condition()

    def test_it_opens_and_closes_when_told_and_says_so(self):
        self.assertFalse(self.proxy.open())  # not there yet, and nothing to show
        self.proxy.set_look("graphite", "#2fd6a7", "en")
        self.proxy.configure({"size": 1.0, "style": "bubbles", "bubbles": [
            {"label": "", "icon": "", "color": "", "action": {"type": "keys", "keys": ["KEY_A"]}}]})
        self.assertTrue(self.wait(lambda: self.proxy.available), "the other program never said it was ready")
        self.assertTrue(self.proxy.open())
        self.assertTrue(self.wait(lambda: ("opened", True) in self.heard))
        self.assertFalse(self.proxy.open())  # open already
        self.proxy.handle("down")            # the button that opens the ring, pressed again, closes it
        self.assertTrue(self.wait(lambda: ("opened", False) in self.heard))
        self.assertTrue(any(kind == "cue" for kind, _value in self.heard))

    def test_a_ring_of_the_callers_own(self):
        self.assertTrue(self.wait(lambda: self.proxy.available))
        self.assertFalse(self.proxy.open())  # no ring of the user's has been told
        self.assertTrue(self.proxy.open([{"label": "x", "icon": "", "color": "", "action": {"type": "hook", "name": "x"}}]))
        self.assertTrue(self.wait(lambda: ("opened", True) in self.heard))

    def test_it_is_started_again_when_it_dies(self):
        self.assertTrue(self.wait(lambda: self.proxy.available))
        self.proxy.configure({"size": 1.0, "style": "pie", "bubbles": [
            {"label": "", "icon": "", "color": "", "action": {"type": "keys", "keys": ["KEY_A"]}}]})
        self.proxy._process.kill()
        self.assertTrue(self.wait(lambda: not self.proxy.available))
        self.assertTrue(self.wait(lambda: self.proxy.available), "it did not come back")
        self.assertTrue(self.proxy.open())   # and it was told the ring again
        self.assertTrue(self.wait(lambda: ("opened", True) in self.heard))


@unittest.skipIf(sys.platform == "win32", "there is one desktop on Windows")
class FindingTheCompositor(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="mxoptions-test-")
        self.addCleanup(__import__("shutil").rmtree, self.folder, True)
        kept = {name: os.environ.get(name) for name in ("XDG_RUNTIME_DIR", "XDG_CURRENT_DESKTOP", "MXOPTIONS_DESKTOP", "SWAYSOCK",
                                                        "HYPRLAND_INSTANCE_SIGNATURE")}
        self.addCleanup(lambda: [os.environ.pop(name, None) if value is None else os.environ.__setitem__(name, value)
                                 for name, value in kept.items()])
        self.addCleanup(setattr, environment, "_current", environment._current)
        for name in kept:
            os.environ.pop(name, None)
        os.environ["XDG_RUNTIME_DIR"] = self.folder
        environment._current = None

    def test_by_what_the_session_says(self):
        for said, desktop in (("KDE", environment.KDE), ("ubuntu:GNOME", environment.GNOME), ("sway", environment.SWAY),
                              ("Hyprland", environment.HYPRLAND), ("XFCE", environment.OTHER), ("", environment.OTHER)):
            os.environ["XDG_CURRENT_DESKTOP"] = said
            environment._current = None
            self.assertEqual(environment.current(), desktop, said)

    def test_by_the_socket_where_a_service_was_told_nothing(self):
        socket = os.path.join(self.folder, f"sway-ipc.{os.getuid()}.4242.sock")
        open(socket, "w").close()
        self.assertEqual(environment.current(), environment.SWAY)
        self.assertEqual(os.environ["SWAYSOCK"], socket)  # for the swaymsg run from here

    def test_hyprland_by_its_socket(self):
        os.makedirs(os.path.join(self.folder, "hypr", "abc_1700000000"))
        open(os.path.join(self.folder, "hypr", "abc_1700000000", ".socket.sock"), "w").close()
        self.assertEqual(environment.current(), environment.HYPRLAND)
        self.assertEqual(os.environ["HYPRLAND_INSTANCE_SIGNATURE"], "abc_1700000000")

    def test_it_can_be_named(self):
        os.environ.update(MXOPTIONS_DESKTOP="gnome", XDG_CURRENT_DESKTOP="KDE")
        self.assertEqual(environment.current(), environment.GNOME)

    def test_no_compositor_to_ask(self):
        self.addCleanup(setattr, environment, "_globals", environment._globals)
        self.addCleanup(os.environ.__setitem__, "WAYLAND_DISPLAY", os.environ["WAYLAND_DISPLAY"]) if "WAYLAND_DISPLAY" in os.environ else None
        os.environ["WAYLAND_DISPLAY"] = "wayland-none"
        environment._globals = None
        self.assertEqual(environment.wayland_globals(), frozenset())


if __name__ == "__main__":
    unittest.main()


class RawInputOfWindows(unittest.TestCase):
    """The records Windows hands out about a mouse, read as bytes (rawmouse_windows.py)."""

    def setUp(self):
        import struct

        from mxoptions import rawmouse_windows
        self.raw = rawmouse_windows
        self.record = lambda device=7, flags=0, buttons=0, data=0, dx=0, dy=0, kind=0: (
            struct.pack("<IIQQ", kind, 48, device, 0) + struct.pack("<HxxHhIiiI", flags, buttons, data, 0, dx, dy, 0))

    def test_a_movement(self):
        self.assertEqual(self.raw.parse(self.record(dx=5, dy=-3)), (7, 5, -3, 0, 0))

    def test_a_position_is_no_movement(self):
        self.assertEqual(self.raw.parse(self.record(flags=1, dx=30000, dy=20000))[1:3], (0, 0))

    def test_the_wheel_and_a_button(self):
        self.assertEqual(self.raw.parse(self.record(buttons=0x0400, data=-120))[3:], (0x0400, -120))
        self.assertEqual(self.raw.parse(self.record(buttons=0x0001))[3], 0x0001)

    def test_what_is_no_mouse_or_too_short_is_nothing(self):
        self.assertIsNone(self.raw.parse(self.record(kind=1)))
        self.assertIsNone(self.raw.parse(b"\0" * 20))

    def test_the_collections_of_one_mouse_go_by_one_name(self):
        hidpp_side = r"\\?\hid#{00001812-0000-1000-8000-00805f9b34fb}_dev_vid&02046d_pid&b042_rev&0017_0123456789ab&col02#a&1b2c3d4&0&0001#{4d1e55b2}"
        mouse_side = r"\\?\HID#{00001812-0000-1000-8000-00805f9b34fb}_Dev_VID&02046d_PID&b042_REV&0017_0123456789ab&Col01#a&1b2c3d4&0&0000#{378de44c}"
        other = r"\\?\HID#VID_06CB&PID_CE7E&Col01#5&2a3b&0&0000#{378de44c}"
        self.assertEqual(self.raw.device_key(hidpp_side), self.raw.device_key(mouse_side))
        self.assertNotEqual(self.raw.device_key(hidpp_side), self.raw.device_key(other))
        self.assertEqual(self.raw.device_key(r"\\?\hid#vid_046d&pid_c548&mi_02&col02#8&1&0&1#{4d1e}"),
                         self.raw.device_key(r"\\?\HID#VID_046D&PID_C548&MI_00#8&2&0&0#{378d}"))

    def test_what_a_hand_does_is_told_and_what_a_program_sends_is_not(self):
        told = []
        mouse = self.raw.RawMouse.__new__(self.raw.RawMouse)  # the part that makes sense of records, without the window
        mouse._key, mouse._any, mouse._buttons, mouse._wheel, mouse._devices = "k", False, 0, 0, {7: True, 9: False}
        mouse._on_change = lambda _m, bits: told.append(("buttons", bits))
        mouse._on_wheel = lambda _m, notches, _when: told.append(("wheel", notches))
        mouse.on_motion, mouse.last_input = (lambda _m, dx, dy, _when: told.append(("moved", dx, dy))), None
        mouse._record(self.record(dx=4, dy=1))
        mouse._record(self.record(buttons=0x0001))          # left down
        mouse._record(self.record(buttons=0x0002 | 0x0100)) # left up, forward down
        mouse._record(self.record(buttons=0x0400, data=-60))  # half a notch
        mouse._record(self.record(buttons=0x0400, data=-60))  # the other half
        mouse._record(self.record(device=0, dx=50))         # sent by a program
        mouse._record(self.record(device=9, dx=50))         # another mouse
        self.assertEqual(told, [("moved", 4, 1), ("buttons", 1), ("buttons", 16), ("wheel", -1)])


class RumbleOnWindows(unittest.TestCase):
    def test_what_two_motors_come_to(self):
        from mxoptions import rumble_windows

        self.assertEqual(rumble_windows.strength_of(0, 0), 0.0)
        self.assertEqual(rumble_windows.strength_of(255, 0), 1.0)
        self.assertAlmostEqual(rumble_windows.strength_of(0, 255), 0.6)   # the small motor counts for less
        self.assertAlmostEqual(rumble_windows.strength_of(128, 255), 0.6)
        self.assertIsNone(rumble_windows.create(lambda level: None) if sys.platform != "win32" else None)
