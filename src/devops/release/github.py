"""Minimal GitHub REST client for the release tooling."""

from __future__ import annotations

import json
import os
import typing
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import ReleaseError

if typing.TYPE_CHECKING:
    from typing import Any

HTTP_NOT_FOUND = 404


class GitHubClient:
    """Send JSON requests to the GitHub REST API.

    The API URL comes from ``GITHUB_API_URL`` and the token from ``GH_TOKEN``
    or ``GITHUB_TOKEN``, as set by GitHub Actions.
    """

    def __init__(
        self, api_url: str | None = None, token: str | None = None, timeout: float = 30
    ) -> None:
        """Initialize the client.

        Parameters
        ----------
        api_url: str | None
            The API base URL. Defaults to ``GITHUB_API_URL`` or the public API.
        token: str | None
            The access token. Defaults to ``GH_TOKEN`` or ``GITHUB_TOKEN``.
        timeout: float
            The timeout of one request in seconds.

        """
        api_url = api_url or os.getenv("GITHUB_API_URL", "https://api.github.com")
        self.api_url = api_url.rstrip("/")
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        self.timeout = timeout

    def request(
        self,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        allow_missing: bool = False,
    ) -> Any:
        """Send a GET request, or a POST request if ``data`` is given.

        Parameters
        ----------
        path: str
            The API path, for example ``/repos/owner/name/releases``.
        query: dict[str, Any] | None
            Query parameters.
        data: dict[str, Any] | None
            The JSON body of a POST request.
        allow_missing: bool
            Return None instead of raising when GitHub answers 404.

        Returns
        -------
        Any
            The decoded JSON response, or None for an allowed 404.

        Raises
        ------
        ReleaseError
            If the request fails or the response is not valid JSON.

        """
        url = self.api_url + path
        if query:
            url += "?" + urlencode(query)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()

        if not url.startswith(("https://", "http://")):
            msg = f"GitHub API URL must use http(s): {self.api_url}"
            raise ReleaseError(msg)
        request = Request(url, headers=headers, data=body)  # noqa: S310
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                return json.load(response)
        except HTTPError as error:
            if allow_missing and error.code == HTTP_NOT_FOUND:
                return None
            msg = f"GitHub returned HTTP {error.code} for {path}"
            raise ReleaseError(msg) from error
        except (URLError, OSError, ValueError) as error:
            msg = f"GitHub request for {path} failed: {error}"
            raise ReleaseError(msg) from error
