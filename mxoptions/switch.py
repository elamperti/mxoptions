"""Easy-Switch the mouse to another channel without the program running: python -m mxoptions.switch 2

Talks HID++ to the mouse directly, with nothing but the standard library. While MX Options runs, ask
it instead (its SwitchHost D-Bus method), so that two programs do not talk to the mouse at once;
mx-switch (data/mx-switch.in) does that and falls back to this."""

import sys

from . import device, hidpp


def switch(channel):
    """Send the first MX mouse found to Easy-Switch ``channel`` (counted from 1). Returns an error text, or None."""
    for path, is_receiver in hidpp.find_hidpp_nodes():
        try:
            transport = hidpp.Transport(path, is_receiver)
        except OSError:
            continue
        try:
            mouse = device.find_mouse(transport)
            if mouse is None:
                continue
            if not 1 <= channel <= mouse.host_count:
                return f"{mouse.name} has channels 1 to {mouse.host_count}"
            mouse.change_host(channel - 1)
            return None
        except hidpp.HidppError as e:
            return f"the mouse did not answer: {e}"
        finally:
            transport.close()
    return "no Logitech HID++ mouse found (see README, Permissions)"


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not args[0].isdigit():
        print("usage: python -m mxoptions.switch <channel, from 1>", file=sys.stderr)
        return 64
    problem = switch(int(args[0]))
    if problem:
        print(f"mx-switch: {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
