"""统一 HTTP 请求封装"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import USER_AGENT, REQUEST_TIMEOUT, GEQUBAO_BASE

_session = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.4,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        _session = s
    return _session


def get(url, referer: str = None, **kwargs):
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    if referer:
        kwargs.setdefault("headers", {})["Referer"] = referer
    return get_session().get(url, **kwargs)


def post(url, referer: str = None, **kwargs):
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    if referer:
        kwargs.setdefault("headers", {})["Referer"] = referer
    return get_session().post(url, **kwargs)


def gequbao_headers(referer_path: str = "/") -> dict:
    """gequbao 所需的请求头（防盗链）"""
    return {
        "Referer": GEQUBAO_BASE + referer_path,
        "User-Agent": USER_AGENT,
    }
