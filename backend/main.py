"""Vercel FastAPI entrypoint; the service root is the backend directory."""
from app.main import app

__all__ = ["app"]
