"""Text on the clipboard, for the action that types text by pasting it.

Plasma's clipboard service (klipper, over D-Bus) is asked first; otherwise the clipboard programs
installed here: wl-copy/wl-paste on Wayland, xclip or xsel on X11. Without any of them the caller
falls back to typing."""

import logging
import shutil
import subprocess

from . import environment

log = logging.getLogger(__name__)

TOOL_TIMEOUT = 3  # s a clipboard program gets to answer


def klipper(method, *args):
    """Call Plasma's clipboard service; returns the reply value, or None when it is unavailable."""
    try:
        from PySide6.QtDBus import QDBus, QDBusConnection, QDBusMessage

        message = QDBusMessage.createMethodCall("org.kde.klipper", "/klipper", "org.kde.klipper.klipper", method)
        message.setArguments(list(args))
        reply = QDBusConnection.sessionBus().call(message, QDBus.CallMode.Block, 700)
        if reply.type() != QDBusMessage.MessageType.ReplyMessage:
            return None
        values = reply.arguments()
        return values[0] if values else True
    except Exception:
        log.exception("clipboard call failed")
        return None


def _tool(argv, data=None):
    """Run a clipboard program: its output as bytes, or None if it failed. One that stays behind to hand
    out what it was given (wl-copy, xclip) must not keep a pipe of ours open, so its output is not read."""
    try:
        if data is None:
            done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  timeout=TOOL_TIMEOUT)
        else:
            done = subprocess.run(argv, input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TOOL_TIMEOUT)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return (done.stdout or b"") if done.returncode == 0 else None


def _text_tools():
    """(read, write) command lines of the clipboard programs installed here, for text, best first."""
    wayland = environment.session() == "wayland"
    if wayland and shutil.which("wl-copy") and shutil.which("wl-paste"):
        yield ["wl-paste", "--no-newline", "--type", "text/plain"], ["wl-copy"]
    if shutil.which("xclip"):
        yield ["xclip", "-selection", "clipboard", "-o"], ["xclip", "-selection", "clipboard", "-i"]
    if shutil.which("xsel"):
        yield ["xsel", "--clipboard", "--output"], ["xsel", "--clipboard", "--input"]


def get_text():
    """The text on the clipboard, from any thread: "" if there is none, None if it cannot be reached that way."""
    text = klipper("getClipboardContents")
    if isinstance(text, str):
        return text
    for paste, _copy in _text_tools():
        found = _tool(paste)
        return "" if found is None else found.decode("utf-8", "replace")  # failing is how they say "nothing is copied"
    return None


def set_text(text):
    """Put text on the clipboard, from any thread. True if that was possible."""
    if klipper("setClipboardContents", text) is not None:
        return True
    return any(_tool(copy, text.encode("utf-8")) is not None for _paste, copy in _text_tools())
