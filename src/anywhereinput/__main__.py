"""Entry point for `python -m anywhereinput`."""

import argparse
import sys
from pathlib import Path

# Ensure src is on the path so relative imports work
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main():
    # Check for --help first to delegate to launcher's full help
    if "--help" in sys.argv or "-h" in sys.argv:
        from .launcher import main as launcher_main

        # Let launcher handle --help completely
        sys.argv[1:] = [a for a in sys.argv[1:] if a != "--app"]
        launcher_main()
        return

    parser = argparse.ArgumentParser(prog="anywhereinput", add_help=False)
    parser.add_argument(
        "--app",
        action="store_true",
        help="Open the desktop admin app (PyQt6 GUI) instead of the terminal launcher.",
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit."
    )
    args, rest = parser.parse_known_args()

    if args.app:
        from .admin import run_admin_app

        run_admin_app()
    else:
        from .launcher import main as launcher_main

        sys.argv[1:] = rest  # remove --app flag before passing to launcher
        launcher_main()


if __name__ == "__main__":
    main()
