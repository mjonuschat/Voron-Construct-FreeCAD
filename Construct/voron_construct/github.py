"""Minimal GitHub client for resolving refs, listing trees and downloading files."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import quote

import requests

API_BASE = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"
TIMEOUT = 30.0

ErrorKind = Literal["not_found", "rate_limit", "network", "other"]


class GitHubError(Exception):
    """Raised for any GitHub failure; ``kind`` classifies it."""

    def __init__(self, kind: ErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class GitHubClient:
    def __init__(
        self, token: str = "", session: requests.Session | None = None
    ) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "voron-construct-browser",
                "Accept": "application/vnd.github+json",
            }
        )
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, url: str) -> requests.Response:
        try:
            response = self._session.get(url, timeout=TIMEOUT)
        except requests.RequestException as err:
            raise GitHubError("network", f"Network error: {err}") from err
        status = response.status_code
        if status == 200:
            return response
        if (
            status in (403, 429)
            and response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            raise GitHubError(
                "rate_limit",
                "GitHub rate limit reached. "
                "Add a GitHub token in the settings to continue.",
            )
        if status == 404:
            raise GitHubError("not_found", f"Not found: {url}")
        raise GitHubError("other", f"Unexpected response {status} from {url}")

    def resolve(self, repo: str, branch: str = "") -> tuple[str, str]:
        if not branch:
            try:
                branch = self._get(f"{API_BASE}/repos/{repo}").json()["default_branch"]
            except GitHubError as err:
                if err.kind == "not_found":
                    raise GitHubError(
                        "not_found", f"Repository not found: {repo}"
                    ) from err
                raise
        try:
            sha = self._get(
                f"{API_BASE}/repos/{repo}/commits/{quote(branch, safe='/')}"
            ).json()["sha"]
        except GitHubError as err:
            if err.kind == "not_found" or "response 422" in str(err):
                raise GitHubError("not_found", f"Branch not found: {branch}") from err
            raise
        return branch, sha

    def fetch_tree(self, repo: str, sha: str) -> list[dict]:
        data = self._get(f"{API_BASE}/repos/{repo}/git/trees/{sha}?recursive=1").json()
        if not data.get("truncated"):
            return data["tree"]
        return self._walk(repo, sha, "")

    def _walk(self, repo: str, sha: str, prefix: str) -> list[dict]:
        data = self._get(f"{API_BASE}/repos/{repo}/git/trees/{sha}").json()
        entries: list[dict] = []
        for entry in data["tree"]:
            full = {**entry, "path": prefix + entry["path"]}
            entries.append(full)
            if entry["type"] == "tree":
                entries.extend(self._walk(repo, entry["sha"], full["path"] + "/"))
        return entries

    def download(self, repo: str, ref: str, rel_path: str, dest: Path) -> None:
        url = f"{RAW_BASE}/{repo}/{ref}/{quote(rel_path)}"
        part = dest.with_name(dest.name + ".part")
        try:
            response = self._get(url)
            dest.parent.mkdir(parents=True, exist_ok=True)
            part.write_bytes(response.content)
            part.replace(dest)
        finally:
            part.unlink(missing_ok=True)
