import json
from urllib.parse import urlsplit, urlunsplit


class Response:
    def __init__(self, status, data, headers):
        self.status = status
        self.data = data
        self.headers = headers

    @classmethod
    def from_file(cls, fname):
        with open(fname, 'r') as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        return cls(
            int(data['status']),
            data['data'].encode('utf-8'),
            data['headers'],
        )

    @classmethod
    def from_requests_response(cls, res):
        return cls(res.status_code, res.content, dict(res.headers))

    def to_file(self, fname):
        with open(fname, 'w') as f:
            f.write(self.as_json())

    def as_json(self):
        return json.dumps(self.as_dict())

    def as_dict(self):
        return {
            'status': self.status,
            'data': self.data.decode('utf-8'),
            'headers': self.headers,
        }

    def as_flask_response(self):
        return self.data.decode('utf-8'), self.status, self.headers


class Request:
    def __init__(self, method, url, data, headers):
        self.method = method
        self.url = url
        self.data = data
        self.headers = headers

    def replace_mount_url(self, new_base_url):
        if '://' not in new_base_url:
            raise ValueError(f"Missing schema in url {new_base_url}")

        new_base_url = new_base_url.rstrip('/')

        self.url = self.url.replace(self.base_url, new_base_url, 1)

    @property
    def base_url(self):
        url_parts = list(urlsplit(self.url))
        base_url_parts = url_parts[:2] + ['', '', '']
        return urlunsplit(base_url_parts)

    @classmethod
    def from_flask_request(cls):
        from flask import request
        return cls(request.method, request.url, request.get_data(), dict(request.headers))

    @classmethod
    async def from_quart_request(cls):
        from quart import request
        data = await request.get_data()
        return cls(request.method, request.url, data, dict(request.headers))

    @classmethod
    def from_file(cls, fname):
        with open(fname, 'r') as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['method'],
            data['url'],
            data['data'].encode('utf-8'),
            data['headers'],
        )

    @classmethod
    def from_httpx_handle_request_args(cls, method, url, headers, stream):
        method = method.decode()

        scheme, host, port, path = url
        scheme, host, path = scheme.decode(), host.decode(), path.decode()

        if port is None:
            url = f'{scheme}://{host}{path}'
        else:
            url = f'{scheme}://{host}:{port}{path}'

        headers = {key.decode(): val.decode() for key, val in headers}
        data = stream.read()

        return cls(method, url, data, headers)

    @classmethod
    def from_httpx_request(cls, req):
        return cls(
            req.method,
            str(req.url),
            req.read(),
            dict(req.headers),
        )

    def to_file(self, fname):
        with open(fname, 'w') as f:
            f.write(self.as_json())

    def as_json(self):
        return json.dumps(self.as_dict())

    def as_dict(self):
        return {
            'method': self.method,
            'url': self.url,
            'data': self.data.decode('utf-8'),
            'headers': self.headers,
        }

    def as_requests_request(self):
        #   Imported here, because we use this only on the provider side
        import requests
        req = requests.Request(
            method=self.method,
            url=self.url,
            data=self.data,
            headers=self.headers,
        )
        return req
