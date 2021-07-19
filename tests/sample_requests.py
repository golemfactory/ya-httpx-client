
BASE_URL = 'http://hi.my.name.is.golem'

sample_requests = [
    ('GET', BASE_URL, {}),
    ('GET', BASE_URL + '/some/path', {}),
    ('GET', BASE_URL + '/some/path/7', {'params': (('x', 7), ('y', 8))}),
    ('GET', BASE_URL + '/some/path/7', {'params': (('x', 7), ('y', 8))}),

    ('patch', BASE_URL, {'headers': {'user-agent': 'my-app/0.0.1'}}),
    ('patch', BASE_URL, {'headers': {'accept-encoding': 'gzip', 'user-agent': 'aaa'}}),
    ('GET', BASE_URL, {'cookies': {'peanut': 'butter'}}),

    ('PUT', BASE_URL + '/file', {
        'files': {'some-file': open('.gitignore', 'rb'),  # pylint: disable=consider-using-with
                  'other-file': open('tests/echo_server/echo_server.py', 'r')}}),  # pylint: disable=consider-using-with
    ('post', BASE_URL, {'data': {'x': 'y'}}),
    ('post', BASE_URL, {'json': {'x': ['y', 'z', {'a': 7}]}}),
    ('POST', BASE_URL + '/some/path/?a=11', {'data': {'x': 77, 'y': 88}}),
    ('POST', BASE_URL, {'content': b'gAUygauygaihua\x32'}),
]
