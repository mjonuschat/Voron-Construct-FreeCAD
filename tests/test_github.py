import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter
from voron_construct.github import GitHubClient, GitHubError

DATA = json.loads((Path(__file__).parent / "data" / "tree_truncated.json").read_text())


def reply(status, json_body=None, content=b"", headers=None):
    response = requests.Response()
    response.status_code = status
    response._content = (
        json.dumps(json_body).encode() if json_body is not None else content
    )
    response.headers.update(headers or {})
    return response


class HandlerAdapter(BaseAdapter):
    """Answers every request with whatever the handler function returns."""

    def __init__(self, handler):
        super().__init__()
        self.handler = handler

    def send(self, request, **kwargs):
        response = self.handler(request)
        response.request = request
        response.url = request.url
        return response

    def close(self):
        pass


def make(handler, token=""):
    session = requests.Session()
    session.mount("https://", HandlerAdapter(handler))
    return GitHubClient(token=token, session=session)


def path_of(req):
    return urlsplit(req.url).path


def test_resolve_default_branch():
    def handler(req):
        if path_of(req) == "/repos/o/r":
            return reply(200, {"default_branch": "main"})
        assert path_of(req) == "/repos/o/r/commits/main"
        return reply(200, {"sha": "abc"})

    assert make(handler).resolve("o/r") == ("main", "abc")


def test_resolve_explicit_branch_skips_repo_call():
    paths = []

    def handler(req):
        paths.append(path_of(req))
        return reply(200, {"sha": "abc"})

    assert make(handler).resolve("o/r", "dev") == ("dev", "abc")
    assert paths == ["/repos/o/r/commits/dev"]


def test_fetch_tree_single_call():
    calls = []

    def handler(req):
        calls.append(req.url)
        return reply(200, DATA["full"])

    assert make(handler).fetch_tree("o/r", "root") == DATA["full"]["tree"]
    assert len(calls) == 1 and calls[0].endswith("/git/trees/root?recursive=1")


def test_fetch_tree_truncated_walks_subtrees():
    def handler(req):
        sha = path_of(req).rsplit("/", 1)[1]
        if sha == "root":
            return reply(200, DATA["root"])
        return reply(200, DATA["subtrees"][sha])

    got = make(handler).fetch_tree("o/r", "root")
    assert sorted(e["path"] for e in got) == sorted(
        e["path"] for e in DATA["full"]["tree"]
    )


def test_download_quotes_spaces_and_writes_atomically(tmp_path):
    urls = []

    def handler(req):
        urls.append(req.url)
        return reply(200, content=b"data")

    dest = tmp_path / "sub" / "Misumi 3030 Cube.step"
    make(handler).download("o/r", "sha1", "CAD/Misumi 3030 Cube.step", dest)
    assert "Misumi%203030%20Cube.step" in urls[0]
    assert urls[0].startswith("https://raw.githubusercontent.com/o/r/sha1/")
    assert dest.read_bytes() == b"data"
    assert [p.name for p in dest.parent.iterdir()] == [dest.name]


def test_404_not_found():
    with pytest.raises(GitHubError) as e:
        make(lambda req: reply(404)).resolve("o/r", "x")
    assert e.value.kind == "not_found"


def test_rate_limit_message():
    def handler(req):
        return reply(403, headers={"X-RateLimit-Remaining": "0"})

    with pytest.raises(GitHubError) as e:
        make(handler).resolve("o/r", "x")
    assert e.value.kind == "rate_limit"
    assert "token" in str(e.value)


def test_token_header_only_when_set():
    seen = []

    def handler(req):
        seen.append(req.headers.get("Authorization"))
        return reply(200, {"sha": "a"})

    make(handler).resolve("o/r", "b")
    make(handler, token="t0k").resolve("o/r", "b")
    assert seen == [None, "Bearer t0k"]


def test_failed_download_leaves_no_dest(tmp_path):
    dest = tmp_path / "f.step"
    with pytest.raises(GitHubError):
        make(lambda req: reply(404)).download("o/r", "s", "f.step", dest)
    assert list(tmp_path.iterdir()) == []

    def boom(req):
        raise requests.ConnectionError("down")

    with pytest.raises(GitHubError) as e:
        make(boom).download("o/r", "s", "f.step", dest)
    assert e.value.kind == "network"
    assert list(tmp_path.iterdir()) == []


def test_missing_branch_422_is_not_found_branch():
    def handler(req):
        return reply(422, {"message": "No commit found"})

    with pytest.raises(GitHubError) as err:
        make(handler).resolve("o/r", "nope")
    assert err.value.kind == "not_found"
    assert "nope" in str(err.value)


def test_missing_repo_404_is_not_found_repo():
    def handler(req):
        return reply(404, {"message": "Not Found"})

    with pytest.raises(GitHubError) as err:
        make(handler).resolve("o/r")
    assert err.value.kind == "not_found"
    assert "o/r" in str(err.value)
