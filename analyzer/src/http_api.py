from .runtime import create_app

__all__ = ["app", "create_app"]

app = create_app()