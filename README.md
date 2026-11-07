# MX Options

A settings app for Logitech MX Master mice on Linux, in the spirit of Logi Options+: buttons,
gestures, the Actions Ring, the wheels, haptics and Easy-Switch, with a tray icon, a background
service and a D-Bus API for other programs.

> **Written by an AI.** Every part of this project (the code, the interface, the sounds, the tests
> and this documentation) was written by [Claude](https://claude.com/claude-code), Anthropic's AI
> model, working in Claude Code. A human, [nictonus](https://github.com/nictonus), directed the work
> and tried each build on a real MX Master 4. Read the code with that in mind, and see
> [Known limits](#known-limits) for what has and has not been checked on hardware.

> **Unofficial.** Not affiliated with or endorsed by Logitech. "Logitech", "MX Master", "Logi
> Options+", "Easy-Switch" and "SmartShift" are trademarks of Logitech.

![Actions Ring](docs/screenshots/ring.png)

| | |
|---|---|
| ![Gestures](docs/screenshots/gestures.png) | ![Buttons](docs/screenshots/buttons.png) |
| ![Wheel](docs/screenshots/wheel-click.png) | ![Haptics for gestures](docs/screenshots/gestures-haptics.png) |

## What it does

- **Buttons.** Middle, back, forward, gesture, wheel-mode button and the haptic panel each take
  any of about 70 ready actions (each done the way your desktop does it), a keyboard shortcut, a
  command, a script, a macro, or a signal to another program. The mouse is drawn with the button you are pressing lit
  up.
- **Gestures.** Hold a button and swipe in four directions, or tap. A live compass shows how your
  movement is read. You choose when a swipe fires (on release, at once, or repeating as you keep
  moving), the distances in millimetres, a dead zone for diagonals, and a vibration pattern for each
  moment of a gesture. The same button also reads sixteen shapes drawn with it held (corners,
  there and back, circles, shakes), each with an action of its own.
- **Actions Ring.** A menu around the cursor, as bubbles, a pie or tiles. Bubbles run actions, open
  their own ring of bubbles (three levels deep), or are *dials* that you turn with the wheel or the
  thumb wheel without closing the menu: volume, tabs, zoom, undo, tracks and more. The cursor stays
  free while the ring is open. Presets are included and your own can be saved.
- **Wheels.** Pointer speed (two speeds and a precision speed), SmartShift and its threshold,
  ratchet force, natural direction, high-resolution scrolling, and what the thumb wheel does. An
  optional click, felt or heard, marks SmartShift letting the wheel go and catching it again.
- **Haptics.** Strength, the built-in patterns, and how hard the thumb panel has to be pressed.
  Rumble from games can be played on the mouse: see [Rumble from games](#rumble-from-games).
- **Also:** Easy-Switch between computers, a tray icon in five styles (plain ones in the colour of
  your panel that show a missing mouse and a low battery, one that fills with the charge), firmware
  versions with an update check through fwupd, four themes with any accent colour.
- **For other programs:** a [D-Bus API](docs/API.md) to play vibrations, run actions, show a ring of
  their own, change settings, and follow buttons, gestures and the wheel.

## Requirements

Developed and tested on **KDE Plasma 6 (Wayland)**, on an Arch-based distribution, with an **MX
Master 4**, on a Bolt receiver and over Bluetooth.

Other Logitech mice that speak HID++ 2.0 are taken as they are: the app offers what the mouse
reports it has (its buttons, SmartShift old or new, thumb wheel, battery) and hides the rest. The
MX Masters before the 4 (3S, 3, 2S and the first) are drawn with the 3D model, any other mouse
with a plain drawing of its own buttons. None of these was tried by the author; a user reported
gestures working on a Signature M650 L.

- Python 3.12 or newer
- PySide6 (Qt 6.6 or newer), with Qt Declarative and Qt Multimedia
- python-evdev
- layer-shell-qt (its QML module draws the ring over other windows on Wayland; a small library, not a
  desktop: it is wanted on sway and Hyprland as much as on KDE Plasma)
- numpy, optional: the glossy 3D model and soft shadows
- for the *Text* action, optional: xclip or xsel on X11, wl-clipboard on Wayland (Plasma needs neither).
  Without one, text is typed key by key with a US layout.

Use your distribution's PySide6. One installed with pip brings its own Qt, which cannot see the
system's layer-shell module, so the Actions Ring would not appear.

On Arch-based systems: `pyside6 python-evdev qt6-declarative qt6-multimedia layer-shell-qt python-numpy`.

### Desktops

What talks to the mouse (buttons, gestures, the wheels, pointer speed, haptics, Easy-Switch, game
rumble) does not depend on the desktop. What talks to the desktop does, and is done in the way
each desktop allows:

| | KDE Plasma | sway, Hyprland and other compositors with layer-shell | GNOME on Wayland | X11 desktops (Xfce, Cinnamon, MATE, i3, …) |
|---|---|---|---|---|
| Ready actions for windows and the desktop | KDE's own shortcuts: all of them | `swaymsg`, `hyprctl`; a launcher, screenshots and a terminal from what is installed (fuzzel, wofi, rofi; grim and slurp) | GNOME's key combinations as it ships them | the usual key combinations (Alt+F4, Ctrl+Alt+arrows, Print, …) |
| Actions Ring | on a layer above the windows | the same | in a window on the session's X server (XWayland), which takes no focus; a little soft where the display is scaled by a fraction | in a window the window manager leaves alone; as a panel of the ring's size where nothing composites |

An action a desktop has no way of doing is not offered there, and settings made on KDE keep working:
*Overview* stays *Overview*, done as the desktop at hand does it. The key combinations are the
ones a desktop comes with; one you have rebound will not do its job, and then a keyboard shortcut of
your own in its place will.

**What was actually run.** Only KDE Plasma 6 on Wayland is used day to day. The X11 ring window was
run in a virtual X server with no window manager. The ring through XWayland was run on KWin, where it
comes up over everything, is picked from and leaves the focus where it was. Nothing at all was run on GNOME,
sway, Hyprland or any X11 desktop itself: their commands and key combinations come from their
documentation. Reports are welcome.

On GNOME the ring is drawn by a small second program (it has to talk to the X server, which the
main one, a Wayland program, cannot). Where the session keeps no X server the ring falls back to an
ordinary window, which takes the focus while it is open.

`MXOPTIONS_DESKTOP` (`kde`, `gnome`, `sway`, `hyprland`, `other`) and `MXOPTIONS_RING` (`layer`, `x11`,
`xwayland`, `window`) override what the program works out for itself, should it get one of them wrong.

## Installing

### Any distribution, for your user only (no root)

Install the requirements above, then:

```sh
git clone https://github.com/nictonus/mxoptions.git && cd mxoptions
make install-user     # into ~/.local
make enable           # start now and at every login
```

If the app then reports that it cannot find or reach the mouse, see [Permissions](#permissions).

### Any distribution, for all users

```sh
sudo make install     # into /usr/local, device access rules included
sudo make udev        # apply those rules now, without replugging the receiver
systemctl --user enable --now mxoptions.service
```

### Without installing

```sh
python3 main.py
```

## Running as a service

An installation brings a systemd *user* service, `mxoptions.service`, tied to your graphical
session. It keeps the mouse configured in the background; the window is opened from the
application menu or the tray icon.

```sh
systemctl --user status mxoptions      # is it running, has it found the mouse
journalctl --user -u mxoptions -f      # its log
systemctl --user restart mxoptions
systemctl --user disable --now mxoptions
```

"Start at login" in the app's settings switches the same service on and off. Quitting from the tray
stops the service until the next login; while it is stopped the mouse behaves as it does without
any software.

The service starts with systemd's `graphical-session.target`. KDE Plasma and GNOME reach it by
themselves. A compositor started on its own (sway, Hyprland, a window manager from `.xinitrc`)
does not, unless you have set that up; there, start the program from the compositor's own
configuration instead:

```
exec mxoptions --background          # sway, i3
exec-once = mxoptions --background   # Hyprland
```

Without a system tray the program has nowhere to sit behind its window: started in the background
it still runs, and starting it again from the menu opens the window.

## Permissions

The app talks to the mouse through its `hidraw` device and sends key presses, clicks and scrolling
through `/dev/uinput`. Neither is open to ordinary users by default. `data/70-mxoptions.rules`
grants both to whoever is logged in at the computer:

```sh
sudo make udev
```

The Arch package and `sudo make install` already include the rules. Many systems have equivalent
rules from Solaar, Steam or KDE Connect, in which case nothing more is needed.

## Other mouse software

Stop **logid** (logiops) and **Solaar** before using MX Options. Two programs redirecting the same
buttons undo each other's settings.

```sh
sudo systemctl disable --now logid
```

## Rumble from games

Games vibrate game controllers, not mice. With *Haptics → Game rumble* switched on, the app adds a
virtual gamepad to the system (it shows up as an Xbox 360 controller named "MX Options rumble
pad"). The rumble a game sends to it, through SDL, Steam Input or Proton, is played on the mouse's
haptic motor.

- The motor plays short patterns, not a continuous hum, so a rumble becomes a row of pulses: one
  pattern each for weak, medium and strong rumble, a chosen time apart.
- A game then sees a controller. Some show gamepad prompts because of it, and some only vibrate a
  controller that is actually being played with, in which case nothing reaches the mouse. Switch
  the option off if a game misbehaves; the virtual gamepad is gone at once.
- `journalctl --user -u mxoptions -f` shows "a game started vibrating" whenever rumble arrives,
  which tells whether a game sends any.

It needs a mouse with a haptic motor (the MX Master 4).

## The picture of the mouse

The Buttons page can show Logitech's own render of the MX Master 4, in three body colours. Those
pictures belong to Logitech and are not part of this repository: the app downloads them from
logitech.com when you press *Download* and keeps them in `~/.local/share/mxoptions/mouse`. Until
then, and for other mice, it draws its own 3D model.

## Files

| | |
|---|---|
| Settings | `~/.config/mxoptions/config.json` |
| Mouse pictures | `~/.local/share/mxoptions/mouse/` |
| Generated click sounds | `~/.cache/mxoptions/sounds/` |
| Tray icon drawings | `~/.local/share/icons/hicolor/scalable/status/mxoptions-tray-*.svg` |

## Known limits

- **Left and right buttons cannot be reassigned.** The mouse does not let software take them over.
- **SmartShift's own switching is inferred.** The mouse announces a mode change made with the
  button, not the one SmartShift makes at speed, so the app works that out from how fast the wheel
  turns. The click can be a notch or two away from the real moment.
- **Text in macros is pasted.** It goes through the clipboard and Ctrl+V, so it does not work in
  terminals.
- **Smooth scrolling passes through the app.** With it on, the wheel only scrolls while the app
  runs.
- **There is no firmware to update to.** The app shows the firmware versions and asks fwupd, the
  system's firmware updater, for updates. fwupd can flash both the mouse and the Bolt receiver, but
  Logitech has published no firmware for either of them for Linux, so the check finds nothing. The
  app does not flash anything itself.
- **Game rumble was not tried in a game.** A test program playing rumble on the virtual gamepad
  makes the mouse vibrate on time; which games send rumble to it has not been explored.
- **Run on one desktop.** KDE Plasma on Wayland is where the program is used. What it does on other
  desktops is set out under [Desktops](#desktops), with what was and was not run there.
- **Checked on one mouse.** Everything was tried on a single MX Master 4. Synthetic tests cover the
  logic; the feel of gestures, vibrations and sounds was judged by one person.
- **The haptic panel does not answer while a main button is held.** With the left button down the
  mouse reports nothing for the panel, however hard it is pressed; the gesture button is reported
  all the same. So gestures made while a window is being dragged want the gesture button, not the
  panel. This was read off what the mouse sends, with nothing of this program in between.

## Development

```sh
make test                                  # unit tests for the logic (no mouse needed)
python3 tools/screenshots.py /tmp/shots    # render every page without a mouse or a screen
```

| | |
|---|---|
| `mxoptions/hidpp.py`, `device.py` | HID++ 2.0 transport and the features of the mouse |
| `mxoptions/engine.py` | the worker thread: applies settings, turns buttons, wheels and gestures into actions |
| `mxoptions/actions.py`, `vinput.py` | the action catalogue, its executor, the virtual keyboard and mouse |
| `mxoptions/config.py` | the settings file: defaults, validation, migration, ring presets |
| `mxoptions/api.py` | the D-Bus interface |
| `mxoptions/rumble.py` | the virtual gamepad that games vibrate |
| `mxoptions/clipboard.py` | text on the clipboard, for the *Text* action |
| `mxoptions/ui/` | the settings window, the ring overlay, sounds |
| `data/` | desktop entry, systemd unit, udev rules |

## Uninstalling

```sh
make uninstall-user          # or: sudo make uninstall, or: sudo pacman -R mxoptions
rm -r ~/.config/mxoptions ~/.local/share/mxoptions ~/.cache/mxoptions    # settings and downloads
rm ~/.local/share/icons/hicolor/scalable/status/mxoptions-tray-*.svg     # the tray icon (after a system-wide install)
```

## Licence

[MIT](LICENSE).
