"""HTTP client for Atlassian Cloud REST APIs."""

from __future__ import annotations

from typing import Any

import httpx


class AtlassianAPIError(RuntimeError):
    """Raised when an Atlassian API call fails."""


class AtlassianClient:
    """A thin, testable wrapper around Jira and Confluence APIs."""

    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        api_token: str,
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = http_client is None
        self._base_url = base_url.rstrip("/")

        if http_client is not None:
            self._http = http_client
            return

        self._http = httpx.Client(
            base_url=self._base_url,
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=timeout_seconds,
        )

    def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._owns_client:
            self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._http.request(method, path, params=params, json=json_body)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise AtlassianAPIError(
                f"Atlassian API error {exc.response.status_code}: {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AtlassianAPIError(f"Atlassian request failed: {exc}") from exc

        if not response.content:
            return {}

        data = response.json()
        if not isinstance(data, dict):
            return {"data": data}
        return data

    def search_jira_issues(
        self,
        *,
        jql: str,
        max_results: int = 10,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)
        return self._request("GET", "/rest/api/3/search", params=params)

    def get_jira_issue(
        self,
        *,
        issue_key: str,
        expand: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] | None = None
        if expand:
            params = {"expand": ",".join(expand)}
        return self._request("GET", f"/rest/api/3/issue/{issue_key}", params=params)

    def search_confluence(
        self,
        *,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        params = {"cql": f'text~"{query}"', "limit": limit}
        return self._request("GET", "/wiki/rest/api/search", params=params)

    def get_confluence_page(
        self,
        *,
        page_id: str,
        expand: list[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] | None = None
        if expand:
            params = {"expand": ",".join(expand)}
        return self._request("GET", f"/wiki/rest/api/content/{page_id}", params=params)
