"""Run ŞUBİRU locally with ``python -m subiru``."""

from .app import app


def main() -> None:
    app.run(debug=True, port=5057)


if __name__ == "__main__":
    main()
