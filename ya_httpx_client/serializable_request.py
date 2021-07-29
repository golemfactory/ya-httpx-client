import json
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    from typing import Dict, TypedDict, Tuple, Optional, List  # pylint: disable=ungrouped-imports
    import requests
    import httpx

    class DictResponse(TypedDict):
        status: int
        data: str
        headers: 'Dict[str, str]'

    class DictRequest(TypedDict):
        method: str
        url: str
        data: str
        headers: 'Dict[str, str]'


class Response:
    def __init__(self, status: int, data: bytes, headers: 'Dict[str, str]'):
        self.status = status
        self.data = data
        self.headers = headers

    @classmethod
    def from_file(cls, fname: str) -> 'Response':
        with open(fname, 'r') as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, json_data: str) -> 'Response':
        data = json.loads(json_data)
        return cls(
            int(data['status']),
            data['data'].encode('utf-8'),
            data['headers'],
        )

    @classmethod
    def from_requests_response(cls, res: 'requests.Response') -> 'Response':
        return cls(res.status_code, res.content, dict(res.headers))

    @classmethod
    def from_httpx_response(cls, res: 'httpx.Response') -> 'Response':
        return cls(res.status_code, res.content, dict(res.headers))

    def to_file(self, fname: str) -> None:
        with open(fname, 'w') as f:
            f.write(self.as_json())

    def as_json(self) -> str:
        return json.dumps(self.as_dict())

    def as_dict(self) -> 'DictResponse':
        return {
            'status': self.status,
            'data': self.data.decode('utf-8'),
            'headers': self.headers,
        }

    def as_flask_response(self) -> 'Tuple[str, int, Dict[str, str]]':
        return self.data.decode('utf-8'), self.status, self.headers

    def as_quart_response(self) -> 'Tuple[str, int, Dict[str, str]]':
        return self.as_flask_response()


class Request:
    def __init__(self, method: str, url: str, data: bytes, headers: 'Dict[str, str]'):
        self.method = method
        self.url = url
        self.data = data
        self.headers = headers

    def replace_mount_url(self, new_base_url: str) -> None:
        if '://' not in new_base_url:
            raise ValueError(f"Missing schema in url {new_base_url}")

        new_base_url = new_base_url.rstrip('/')

        self.url = self.url.replace(self.base_url, new_base_url, 1)

    @property
    def base_url(self) -> str:
        url_parts = list(urlsplit(self.url))
        base_url_parts = url_parts[:2] + ['', '', '']
        return urlunsplit(base_url_parts)

    @classmethod
    def from_flask_request(cls) -> 'Request':
        from flask import request  # pylint: disable=import-outside-toplevel
        return cls(request.method, request.url, request.get_data(), dict(request.headers))

    @classmethod
    async def from_quart_request(cls) -> 'Request':
        from quart import request  # pylint: disable=import-outside-toplevel

        data = await request.get_data()
        return cls(request.method, request.url, data, dict(request.headers))

    @classmethod
    def from_file(cls, fname: str) -> 'Request':
        with open(fname, 'r') as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, json_data: str) -> 'Request':
        data = json.loads(json_data)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: 'DictRequest') -> 'Request':
        return cls(
            data['method'],
            data['url'],
            data['data'].encode('utf-8'),
            data['headers'],
        )

    @classmethod
    def from_httpx_handle_request_args(
        cls,
        _method: bytes,
        _url: 'Tuple[bytes, bytes, Optional[int], bytes]',
        _headers: 'List[Tuple[bytes, bytes]]',
        stream: 'httpx.ByteStream',
    ) -> 'Request':
        method = _method.decode()
        scheme, host, port, path = cls._decode_httpx_url(_url)
        headers = {key.decode(): val.decode() for key, val in _headers}

        if port is None:
            url = f'{scheme}://{host}{path}'
        else:
            url = f'{scheme}://{host}:{port}{path}'

        data = stream.read()

        return cls(method, url, data, headers)

    @staticmethod
    def _decode_httpx_url(url: 'Tuple[bytes, bytes, Optional[int], bytes]') -> 'Tuple[str, str, Optional[int], str]':
        scheme, host, port, path = url
        return scheme.decode(), host.decode(), port, path.decode()

    @classmethod
    def from_httpx_request(cls, req: 'httpx.Request') -> 'Request':
        return cls(
            req.method,
            str(req.url),
            req.read(),
            dict(req.headers),
        )

    def to_file(self, fname: str) -> None:
        with open(fname, 'w') as f:
            f.write(self.as_json())

    def as_json(self) -> str:
        return json.dumps(self.as_dict())

    def as_dict(self) -> 'DictRequest':
        return {
            'method': self.method,
            'url': self.url,
            'data': self.data.decode('utf-8'),
            'headers': self.headers,
        }

    def as_requests_request(self) -> 'requests.Request':
        #   Imported here, because we use this only on the provider side
        import requests  # pylint: disable=import-outside-toplevel

        req = requests.Request(
            method=self.method,
            url=self.url,
            data=self.data,
            headers=self.headers,
        )
        return req

    def as_httpx_request(self) -> 'httpx.Request':
        import httpx
        req = httpx.Request(
            method=self.method,
            url=self.url,
            content=self.data,
            headers=self.headers,
        )
        return req
