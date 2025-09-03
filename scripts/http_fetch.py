#!/usr/bin/env python3
from __future__ import annotations
import os, time
from dataclasses import dataclass
from typing import Optional, Dict
from urllib.parse import urlparse, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib import robotparser

DEFAULT_UA = (
    "NewsBriefBot/0.2.2 (+https://github.com/bigthack/newsbrief-repo-v0.2.2/issues)"
)

# Global request budget per run (override with env NB_MAX_REQUESTS)
REQUEST_BUDGET = int(os.getenv("NB_MAX_REQUESTS", "40"))

@dataclass
class FetchConfig:
    timeout: float = float(os.getenv("NB_TIMEOUT", "8"))
    ua: str = os.getenv("NB_UA", DEFAULT_UA)
    max_retries: int = int(os.getenv("NB_MAX_RETRIES", "2"))
    backoff: float = float(os.getenv("NB_BACKOFF", "0.5"))

class Budget:
    def __init__(self, total: int) -> None:
        self.total = max(0, total)
        self.used = 0
    def take(self, n: int = 1) -> bool:
        if self.used + n > self.total:
            return False
        self.used += n
        return True

class RobotsCache:
    def __init__(self) -> None:
        self.cache: Dict[str, Optional[robotparser.RobotFileParser]] = {}

    def allowed(self, url: str, ua: str, allowlist_domains: set[str]) -> bool:
        pr = urlparse(url)
        host = pr.netloc.lower()
        if host in allowlist_domains:
            # Still check robots if available, but default allow on failure
            pass
        robots_url = urljoin(f"{pr.scheme}://{host}", "/robots.txt")
        rp = self.cache.get(host)
        if rp is None:
            rp = robotparser.RobotFileParser()
            try:
                # Fetch robots with a tiny client so we respect site limits
                r = requests.get(robots_url, timeout=4, headers={"User-Agent": ua})
                if r.status_code >= 200 and r.status_code < 400 and r.text:
                    rp.parse(r.text.splitlines())
                else:
                    rp = None
            except Exception:
                rp = None
            self.cache[host] = rp
        if rp is None:
            # If we cannot get robots, be conservative unless host in allowlist
            return host in allowlist_domains
        try:
            return rp.can_fetch(ua, url)
        except Exception:
            return host in allowlist_domains

def build_session(cfg: FetchConfig) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=cfg.max_retries,
        backoff_factor=cfg.backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": cfg.ua, "Accept-Language": "en, *;q=0.1"})
    return s

def fetch_html(
    session: requests.Session,
    url: str,
    cfg: FetchConfig,
    robots: RobotsCache,
    allowlist_domains: set[str],
    budget: Budget,
) -> str:
    if not budget.take():
        return ""
    if not robots.allowed(url, cfg.ua, allowlist_domains):
        return ""
    try:
        r = session.get(url, timeout=cfg.timeout)
        if r.status_code >= 200 and r.status_code < 400:
            # Crude politeness: tiny sleep after HTML fetches
            time.sleep(0.05)
            return r.text or ""
    except Exception:
        return ""
    return ""
