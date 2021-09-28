from requests import Request
from urllib.parse import urljoin

BASE_URL = 'http://localhost:5000/echo/'

sample_requests = [
    Request('get', BASE_URL),
    Request('post', urljoin(BASE_URL, 'aaa/zz')),
    Request('get', BASE_URL, params={'aa': 'bbb'}),
    Request('get', BASE_URL, params={'key1': 'value1', 'key2': ['value2', 'value3']}),

    Request('patch', BASE_URL, headers={'user-agent': 'my-app/0.0.1'}),

    Request('post', BASE_URL, files={'file': open('.gitignore', 'rb')}),
    Request('post', BASE_URL, files={'file': open('.gitignore', 'r')}),
    Request('post', BASE_URL, files={'file': ('a.txt', 'bbb\nddd', 'application/vnd.ms-excel', {'Expires': '0'})}),

    Request('post', urljoin(BASE_URL, 'aaa/zz'), data={'foo': 'bar'}),
    Request('post', BASE_URL, data=[('foo', 'bar'), ('baz', 'foo')]),
    Request('post', BASE_URL, data="kgkjhti7fg"),

    Request('post', BASE_URL, json={'x': ['y', 'z', {'a': 7}]}),

    Request('post', BASE_URL, cookies={'aa': 'bb'}),

    Request('post', BASE_URL, auth=('aa', 'zz')),

    #   requests do something with accept-encoding (--> compare tests.helpers.clean_headers)
    Request('get', BASE_URL, headers={'accept-encoding': 'gzip'}),
    Request('get', BASE_URL, headers={'Accept-Encoding': 'gzip', 'Something-Else': 'nope'}),
]
