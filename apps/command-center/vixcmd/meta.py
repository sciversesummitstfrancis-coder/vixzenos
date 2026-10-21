"""Vixzen version + help text."""
import os

VERSION = "0.3 (Preview)"


def version():
    for p in ("/etc/vixzen-release",):
        if os.path.isfile(p):
            try:
                for line in open(p):
                    if line.startswith("VERSION="):
                        print("vix " + line.split("=", 1)[1].strip()
                              .strip('"'))
                        return 0
            except OSError:
                pass
    print(f"vix {VERSION}")
    return 0
