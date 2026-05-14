#!/usr/bin/env python3
"""Harness CLI convergence point."""

from __future__ import annotations

import sys

from harness_core.cli import main as cli_main


def main() -> int:
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
