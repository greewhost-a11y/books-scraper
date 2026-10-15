"""HTTP layer: one shared session with retries, timeouts and a polite delay."""

from __future__ import annotations

import logging
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

USER_AGENT = "books-scraper/1.0 (portfolio demo)"


class Fetcher:
    def __init__(self, delay: float = 0.2, timeout: float = 20.0, retries: int = 3):
        self.delay = delay
        self.timeout = timeout
        self._lock = threading.Lock()
        self._last = 0.0

        retry = Retry(
            total=retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _throttle(self) -> None:
        # Spread requests out across all worker threads, not per thread.
        with self._lock:
            wait = self._last + self.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def get(self, url: str) -> str:
        self._throttle()
        log.debug("GET %s", url)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
