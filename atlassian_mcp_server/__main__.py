"""CLI entrypoint for Atlassian MCP server."""

from __future__ import annotations

from .server import create_server


def main() -> None:
    """Run MCP server over stdio transport."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
