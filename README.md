# Atlassian MCP Server

MCP server for Atlassian Cloud that exposes Jira and Confluence tools for MCP clients.

## Features

- Jira issue search by JQL
- Jira issue details by key
- Confluence content search
- Confluence page details by page ID

## Requirements

- Python 3.10+
- Atlassian Cloud account
- Atlassian API token

## Environment Variables

Copy `.env.example` and set values:

```bash
ATLASSIAN_BASE_URL=https://your-domain.atlassian.net
ATLASSIAN_EMAIL=you@example.com
ATLASSIAN_API_TOKEN=your_atlassian_api_token
ATLASSIAN_TIMEOUT_SECONDS=30
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
atlassian-mcp-server
```

The server runs over stdio transport, which is the default expected by MCP clients.

## Exposed MCP Tools

- `jira_search_issues(jql: str, max_results: int = 10)`
- `jira_get_issue(issue_key: str)`
- `confluence_search(query: str, limit: int = 10)`
- `confluence_get_page(page_id: str)`