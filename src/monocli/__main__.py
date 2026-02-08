"""Entry point for Mono CLI.

Run the dashboard with: python -m monocli
"""

from monocli.ui.app import MonoApp


def main() -> None:
    """Run the Mono CLI dashboard application."""
    app = MonoApp()
    app.run()


if __name__ == "__main__":
    main()
