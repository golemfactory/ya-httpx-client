'''
E2E tests for many different requests. Test goes like this:
1. Initialize a few services with echo-like server
2. For each predefined httpx.Request:
    *   send it to the provider
    *   ensure response contains the original request

This tests various serialization-related methods of seriablizable_request.Request/Response
classes, in this order:
    Called when request is being sent to the provider:
        Request.from_httpx_handle_request_args
        Request.to_file
    Called on provider when request is sent to the echo server
        Request.from_file
        Request.as_requests_request
    Called on provider by the echo server
        Request.from_flask_request
        Request.as_dict
    Called on provider when echo server response is processed
        Response.from_requests_response
        Response.to_file
    Called when response from the provider is processed:
        Response.from_file
    Called directly here, to compare with the original request
        Request.from_dict
        Request.from_httpx_request

NOTE: there are some other methods defined on those objects and they are *not* tested here.
'''
import asyncio

import pytest

from .sample_requests import sample_requests, BASE_URL
from yagna_requests.session import Session
from yagna_requests import serializable_request

EXECUTOR_CFG = {
    'budget': 1,
    'subnet_tag': 'devnet-beta.2',
}

STARTUP_CFG = {
    'url': BASE_URL,
    #   Image created from `docker build tests/echo_server/`
    'image_hash': 'cadb48ec91b7f162666afcca98e6ebfb8215649411373861a26d7f07',
    'service_cnt': 1,
}


@pytest.fixture(scope="module")
def event_loop():
    '''
    We want to have a single event loop for all tests in this file https://stackoverflow.com/a/49940520/15851655
    '''
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


def echo_server_startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "echo_server:app", "--daemon")


@pytest.fixture(scope='module')
async def client():
    #   TODO command arg for subnet_tag
    session = Session(EXECUTOR_CFG)
    session.startup(**STARTUP_CFG)(echo_server_startup)
    async with session.client() as client:
        yield client
    await session.close()


def assert_request_equals(req_1, req_2):
    assert req_1.method == req_2.method
    assert req_1.data == req_2.data

    url_1 = req_1.url.rstrip('/')
    url_2 = req_2.url.rstrip('/')
    assert url_1 == url_2

    headers_1 = {key.lower(): val.lower() for key, val in req_1.headers.items()}
    headers_2 = {key.lower(): val.lower() for key, val in req_2.headers.items()}
    assert headers_1 == headers_2


@pytest.mark.asyncio
@pytest.mark.parametrize('method, url, kwargs', sample_requests)
async def test_on_provider(client, method, url, kwargs):
    httpx_req = client.build_request(method, url, **kwargs)
    response = await client.send(httpx_req)
    assert response.status_code == 200
    req_data = response.json()['req']

    returned_req = serializable_request.Request.from_dict(req_data)
    expected_req = serializable_request.Request.from_httpx_request(httpx_req)

    assert_request_equals(returned_req, expected_req)
