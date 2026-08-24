"""Development entry point. Production uses Gunicorn and wsgi.py."""

from . import create_app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8765, debug=False)
