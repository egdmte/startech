"""WSGI entry point for the production CAM service."""

from startech_cam import create_app


app = create_app()
