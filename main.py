"""Entry point: launches the GUI by default, or the CLI if arguments are given."""
import sys


def main():
    if len(sys.argv) > 1:
        from tunetidy_app.cli import main as cli_main
        cli_main()
    else:
        from tunetidy_app.gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
