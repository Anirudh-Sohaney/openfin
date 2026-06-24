#!/usr/bin/env python3
"""CLI entry point for the OpenFin webapp server."""

import sys
import os
import threading
import time

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from OpenFin.main.webapp.server import main as _server_main


def main():
    server_thread = threading.Thread(target=_server_main, daemon=True)
    server_thread.start()

    # Brief pause to let the server bind and print its own startup messages
    time.sleep(1)

    print()
    print("  OpenFin server started at http://127.0.0.1:6161")
    print("  Press Ctrl+C to stop")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == '__main__':
    main()
