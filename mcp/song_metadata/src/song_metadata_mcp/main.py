from __future__ import annotations

from .config import load_settings
from .server import create_server


def main() -> None:
    settings = load_settings()
    mcp = create_server(settings)
    mcp.run(transport=settings.transport, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
