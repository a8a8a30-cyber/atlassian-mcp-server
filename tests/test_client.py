"""Unit tests for Atlassian API client wrapper."""

import json
import unittest

import httpx

from atlassian_mcp_server.client import AtlassianAPIError, AtlassianClient


class AtlassianClientTests(unittest.TestCase):
    def test_search_jira_issues_builds_expected_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.method, "GET")
            self.assertEqual(str(request.url.path), "/rest/api/3/search")
            self.assertEqual(request.url.params["jql"], "project = DEMO")
            self.assertEqual(request.url.params["maxResults"], "5")
            return httpx.Response(
                status_code=200,
                content=json.dumps({"issues": [{"key": "DEMO-1"}]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        with httpx.Client(base_url="https://example.atlassian.net", transport=transport) as http:
            client = AtlassianClient(
                base_url="https://example.atlassian.net",
                email="user@example.com",
                api_token="token",
                http_client=http,
            )
            data = client.search_jira_issues(jql="project = DEMO", max_results=5)

        self.assertIn("issues", data)
        self.assertEqual(data["issues"][0]["key"], "DEMO-1")

    def test_raises_api_error_on_http_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=401,
                content=b'{"error":"Unauthorized"}',
                headers={"Content-Type": "application/json"},
                request=request,
            )

        transport = httpx.MockTransport(handler)
        with httpx.Client(base_url="https://example.atlassian.net", transport=transport) as http:
            client = AtlassianClient(
                base_url="https://example.atlassian.net",
                email="user@example.com",
                api_token="invalid",
                http_client=http,
            )
            with self.assertRaises(AtlassianAPIError):
                client.get_jira_issue(issue_key="DEMO-1")


if __name__ == "__main__":
    unittest.main()
