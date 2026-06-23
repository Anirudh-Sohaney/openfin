#!/usr/bin/env python3
"""CLI entry point for the OpenFin webapp server."""

import sys
import os

_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from OpenFin.main.webapp.server import main as _server_main


def main():
    _server_main()


if __name__ == '__main__':
    main()
