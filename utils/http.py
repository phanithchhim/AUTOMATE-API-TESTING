import requests
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


def get_session_with_retries(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist=(500, 502, 504),
    allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]),
) -> requests.Session:
    """
    Return a requests.Session configured with retry/backoff semantics.
    Use this session for more resilient HTTP calls from tests.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class APIClient:
    def __init__(self, base_url: str, timeout: int = 10, verify: bool = True, retries: int = 3):
        self.base_url = base_url.rstrip("/") if base_url else ""
        # session with retry/backoff
        self.session = get_session_with_retries(retries=retries)
        self.timeout = timeout
        # controls TLS cert verification (useful for local self-signed certs)
        self.session.verify = verify

    def set_basic_auth(self, username: str, password: str):
        self.session.auth = HTTPBasicAuth(username, password)

    def set_bearer_token(self, token: str):
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def set_cookie(self, name: str, value: str, path: str = "/"):
        if name and value is not None:
            self.session.cookies.set(name, value, path=path)

    def set_cookies_from_response(self, resp: requests.Response):
        if resp is None:
            return
        for cookie in resp.cookies:
            self.session.cookies.set(cookie.name, cookie.value, path=cookie.path or "/")

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/') }"
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return self.session.request(method, url, **kwargs)

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)
