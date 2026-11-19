"""Tests for devops.release.github against a local HTTP server."""

from __future__ import annotations

import json
import typing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from devops.release import GitHubClient, ReleaseError

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

TOKEN = "test-token"  # noqa: S105 - fake token for a local test server


class Server:
    """Serve fixed answers and record requests."""

    def __init__(self) -> None:
        """Start the server on a free local port."""
        self.status = 200
        self.body: bytes = b"{}"
        self.requests: list[dict[str, Any]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def answer(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                owner.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": self.headers,
                        "body": self.rfile.read(length) if length else None,
                    }
                )
                self.send_response(owner.status)
                self.end_headers()
                self.wfile.write(owner.body)

            do_GET = answer  # noqa: N815
            do_POST = answer  # noqa: N815

            def log_message(self, *_: object) -> None:
                pass

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"

    def stop(self) -> None:
        """Stop the server."""
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()


@pytest.fixture
def server() -> Iterator[Server]:
    """Run a local server for one test."""
    running = Server()
    yield running
    running.stop()


def test_get_sends_query_and_token(server: Server) -> None:
    """GET requests carry the query, API headers and the bearer token."""
    server.body = b'{"ok": true}'
    client = GitHubClient(api_url=server.url + "/", token=TOKEN)
    assert client.request("/repos/o/r/runs", query={"a": 1, "b": "x"}) == {"ok": True}
    request = server.requests[0]
    assert request["method"] == "GET"
    assert request["path"] == "/repos/o/r/runs?a=1&b=x"
    assert request["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert request["headers"]["X-GitHub-Api-Version"] == "2022-11-28"


def test_post_sends_json(server: Server) -> None:
    """POST requests send a JSON body."""
    client = GitHubClient(api_url=server.url, token=TOKEN)
    client.request("/repos/o/r/releases", data={"tag_name": "v1.0.0"})
    request = server.requests[0]
    assert request["method"] == "POST"
    assert request["headers"]["Content-Type"] == "application/json"
    assert json.loads(request["body"]) == {"tag_name": "v1.0.0"}


def test_environment_sets_url_and_token(
    server: Server, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GITHUB_API_URL and GH_TOKEN are used by default; no token sends none."""
    monkeypatch.setenv("GITHUB_API_URL", server.url)
    monkeypatch.setenv("GH_TOKEN", "from-env")
    GitHubClient().request("/x")
    assert server.requests[-1]["headers"]["Authorization"] == "Bearer from-env"
    monkeypatch.delenv("GH_TOKEN")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    GitHubClient().request("/x")
    assert "Authorization" not in server.requests[-1]["headers"]


def test_missing_resource_can_be_allowed(server: Server) -> None:
    """404 returns None only when allowed."""
    server.status = 404
    client = GitHubClient(api_url=server.url)
    assert client.request("/x", allow_missing=True) is None
    with pytest.raises(ReleaseError, match="HTTP 404"):
        client.request("/x")


@pytest.mark.parametrize("status", [403, 422, 500])
def test_http_errors_are_release_errors(server: Server, status: int) -> None:
    """Other HTTP errors always fail."""
    server.status = status
    with pytest.raises(ReleaseError, match=f"HTTP {status}"):
        GitHubClient(api_url=server.url).request("/x", allow_missing=True)


def test_invalid_json_is_an_error(server: Server) -> None:
    """A broken body fails instead of being read as empty."""
    server.body = b"{broken"
    with pytest.raises(ReleaseError, match="failed"):
        GitHubClient(api_url=server.url).request("/x")


def test_unreachable_api_is_an_error() -> None:
    """A closed port fails with a release error."""
    with pytest.raises(ReleaseError, match="failed"):
        GitHubClient(api_url="http://127.0.0.1:9", timeout=2).request("/x")


def test_non_http_urls_are_rejected() -> None:
    """file:// and other schemes are never opened."""
    with pytest.raises(ReleaseError, match="http"):
        GitHubClient(api_url="file:///etc").request("/passwd")
