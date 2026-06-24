#!/usr/bin/env python3
"""CLI entry point for the OpenFin webapp server."""

import sys
import os
import subprocess


def main():
    _src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    from OpenFin.main.webapp import server as server_module
    server_path = os.path.abspath(server_module.__file__)

    # Launch server as a detached background process with all output suppressed
    proc = subprocess.Popen(
        [sys.executable, server_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    print(f"OpenFin server started as background process (PID {proc.pid})")
    print(f"Open http://127.0.0.1:6161 in your browser")


if __name__ == '__main__':
    main()
