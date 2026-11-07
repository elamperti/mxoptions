# MX Options: a per-user installation in its own Python virtual environment.
#
#   make venv             create the virtual environment and install the dependencies into it
#   make test             run the unit tests
#   make run              start the program from this source tree
#   make install          install for the current user under ~/.local (no root needed)
#   mx-switch 2           (once installed) send the mouse to Easy-Switch channel 2
#   make enable           start the service now and with every graphical session
#   make i3               let the service start with an i3 session (see README, "i3")
#   sudo make udev        install the device access rules (once; see README, "Permissions")
#   make uninstall        remove the installation (the virtual environment included)
#
# Nothing is installed into the system's Python: PySide6 (with its own Qt), evdev and numpy live
# in $(VENV). After the system's Python moves to a new minor version, run "make venv-reset".

# The interpreter the virtual environment is made from. Named by its full path so that a pyenv
# shim earlier on PATH does not pick an older Python.
SYSTEM_PYTHON ?= /usr/bin/python3

PREFIX ?= $(HOME)/.local
bindir = $(PREFIX)/bin
libdir = $(PREFIX)/lib/mxoptions
datadir = $(or $(XDG_DATA_HOME),$(PREFIX)/share)
unitdir = $(or $(XDG_CONFIG_HOME),$(HOME)/.config)/systemd/user
udevdir = /etc/udev/rules.d

VENV ?= $(libdir)/venv
PYTHON = $(VENV)/bin/python
DEPENDENCIES = "PySide6>=6.6" "evdev>=1.6" numpy

substitute = sed -e 's|@BINDIR@|$(bindir)|g' -e 's|@LIBDIR@|$(libdir)|g' -e 's|@PYTHON@|$(PYTHON)|g'

.PHONY: all venv venv-reset build test check run screenshots install uninstall enable disable i3 udev clean

all: build

$(PYTHON):
	$(SYSTEM_PYTHON) -m venv "$(VENV)"
	$(PYTHON) -m pip install --quiet --upgrade pip
	$(PYTHON) -m pip install --quiet $(DEPENDENCIES)

venv: $(PYTHON)

venv-reset:
	rm -rf "$(VENV)"
	$(MAKE) venv

build: $(PYTHON)
	$(PYTHON) -m compileall -q mxoptions

test: $(PYTHON)
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m unittest discover -s tests

check: build test

run: $(PYTHON)
	$(PYTHON) main.py

screenshots: $(PYTHON)
	$(PYTHON) tools/screenshots.py docs/screenshots

install: build
	install -d "$(libdir)" "$(bindir)" "$(unitdir)" "$(datadir)/applications"
	rm -rf "$(libdir)/mxoptions"
	cp -r mxoptions "$(libdir)/mxoptions"
	find "$(libdir)/mxoptions" -name __pycache__ -prune -exec rm -rf {} +
	$(PYTHON) -m compileall -q "$(libdir)/mxoptions"
	$(substitute) data/mxoptions.in > "$(bindir)/mxoptions"
	chmod 755 "$(bindir)/mxoptions"
	$(substitute) data/mx-switch.in > "$(bindir)/mx-switch"
	chmod 755 "$(bindir)/mx-switch"
	$(substitute) data/mxoptions.service.in > "$(unitdir)/mxoptions.service"
	sed -e 's|^Exec=mxoptions|Exec=$(bindir)/mxoptions|' data/mxoptions.desktop > "$(datadir)/applications/mxoptions.desktop"
	install -Dm644 mxoptions/assets/icon.svg "$(datadir)/icons/hicolor/scalable/apps/mxoptions.svg"
	-systemctl --user daemon-reload
	@echo
	@echo "Installed under $(PREFIX). Next:"
	@echo "  make enable       start it now and with every graphical session"
	@echo "  make i3           on i3, which does not start graphical-session.target by itself"
	@echo "  sudo make udev    only if the program cannot reach the mouse (see README, Permissions)"

uninstall: disable
	rm -rf "$(libdir)"
	rm -f "$(bindir)/mxoptions" "$(bindir)/mx-switch" "$(unitdir)/mxoptions.service" "$(unitdir)/i3-session.target" \
		"$(datadir)/applications/mxoptions.desktop" "$(datadir)/icons/hicolor/scalable/apps/mxoptions.svg" \
		"$(datadir)"/icons/hicolor/scalable/status/mxoptions-tray-*.svg  # the last ones are drawn by the program for its tray icon
	-systemctl --user daemon-reload

enable:
	systemctl --user daemon-reload
	systemctl --user enable --now mxoptions.service

disable:
	-systemctl --user disable --now mxoptions.service

i3:
	install -Dm644 data/i3-session.target "$(unitdir)/i3-session.target"
	systemctl --user daemon-reload
	@echo
	@echo "Add this line to your i3 config, then reload i3 (or log in again):"
	@echo "  exec --no-startup-id systemctl --user start i3-session.target"

udev:
	install -Dm644 data/70-mxoptions.rules "$(udevdir)/70-mxoptions.rules"
	-udevadm control --reload-rules
	-udevadm trigger --subsystem-match=hidraw
	-udevadm trigger --sysname-match=uinput

clean:
	rm -rf build dist *.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +
