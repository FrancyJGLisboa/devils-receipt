"""Minimal stdlib-only HTTP helper (no third-party deps).

Ported in spirit from last30days/http.py, trimmed to what the keyless source
modules need: a GET that returns parsed JSON or raw text, with a browser-ish
User-Agent and a couple of transient retries. Never used for keyed calls.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

DEFAULT_TIMEOUT = 30
USER_AGENT = "commodity-pulse/0.1 (Assistant Skill; keyless)"
MAX_RETRIES = 3
RETRY_DELAY = 1.5


class HTTPError(Exception):
    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    *,
    as_json: bool = True,
    retries: int = MAX_RETRIES,
) -> Any:
    """GET a URL. Returns parsed JSON (default) or raw text.

    Raises HTTPError on the final failed attempt; transient errors retry.
    """
    if params:
        url = f"{url}?{urlencode(params)}"
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)

    last_exc: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=hdrs, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            status = e.code
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            # 4xx (other than 429) won't fix on retry.
            if status != 429 and 400 <= status < 500:
                raise HTTPError(f"HTTP {status} for {url}", status, err_body) from e
            last_exc = HTTPError(f"HTTP {status} for {url}", status, err_body)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_exc = e
        if attempt < retries - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))

    if isinstance(last_exc, HTTPError):
        raise last_exc
    raise HTTPError(f"GET failed for {url}: {last_exc}") from last_exc
