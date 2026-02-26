"""MCP tool definitions for Atlassian APIs."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .client import AtlassianClient
from .config import AtlassianConfig, load_config

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - only triggered when runtime dependency is absent
    FastMCP = None  # type: ignore[assignment]


def _validate_limit(value: int, *, minimum: int = 1, maximum: int = 100) -> int:
    if value < minimum or value > maximum:
        raise ValueError(f"Value must be between {minimum} and {maximum}")
    return value


@lru_cache(maxsize=1)
def get_config() -> AtlassianConfig:
    """Load and cache environment configuration."""
    return load_config()


@lru_cache(maxsize=1)
def get_client() -> AtlassianClient:
    """Build and cache the Atlassian API client."""
    config = get_config()
    return AtlassianClient(
        base_url=config.normalized_base_url,
        email=config.email,
        api_token=config.api_token,
        timeout_seconds=config.timeout_seconds,
    )


def create_server() -> Any:
    """Create and configure the MCP server instance."""
    if FastMCP is None:
        raise RuntimeError(
            "Missing optional dependency 'mcp'. Install project dependencies first."
        )

    mcp = FastMCP("atlassian-mcp-server")

    @mcp.tool(name="jira_search_issues")
    def jira_search_issues(jql: str, max_results: int = 10) -> dict[str, Any]:
        """Search Jira issues with JQL."""
        return get_client().search_jira_issues(
            jql=jql, max_results=_validate_limit(max_results)
        )

    @mcp.tool(name="jira_get_issue")
    def jira_get_issue(issue_key: str) -> dict[str, Any]:
        """Fetch a Jira issue by key (e.g. PROJ-123)."""
        return get_client().get_jira_issue(issue_key=issue_key)

    @mcp.tool(name="confluence_search")
    def confluence_search(query: str, limit: int = 10) -> dict[str, Any]:
        """Search Confluence content by text query."""
        return get_client().search_confluence(
            query=query,
            limit=_validate_limit(limit),
        )

    @mcp.tool(name="confluence_get_page")
    def confluence_get_page(page_id: str) -> dict[str, Any]:
        """Fetch Confluence page details by page id."""
        return get_client().get_confluence_page(page_id=page_id)

    return mcp
