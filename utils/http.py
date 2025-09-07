import requests
from requests.auth import HTTPBasicAuth


class APIClient:
    def __init__(self, base_url: str, timeout: int = 10, verify: bool = True):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.session = requests.Session()
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
        url = f"{self.base_url}/{path.lstrip('/')}"
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
