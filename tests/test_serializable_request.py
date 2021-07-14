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

NOTE: there are some other methods defined on those objects and they are *not* tested here.
'''
import asyncio

import pytest

from .sample_requests import sample_requests, SAMPLE_URL
from yagna_requests import Session, serializable_request

EXECUTOR_CFG = {
    'budget': 1,
    'subnet_tag': 'devnet-beta.2',
}

STARTUP_CFG = {
    'url': SAMPLE_URL,
    #   Image created from `docker build tests/echo_server/`
    'image_hash': '39fc9be3ffef142ae02c57a398d87e4a0ffc32c22c2497516e955466',
    'service_cnt': 1,
}


@pytest.fixture(scope="session")
def event_loop():
    '''
    We want to have a single event loop for a whole testing session https://stackoverflow.com/a/49940520/15851655
    '''
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


def echo_server_startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "echo_server:app", "--daemon")


@pytest.fixture(scope='session')
async def client():
    #   TODO command arg for subnet_tag
    session = Session(EXECUTOR_CFG)
    session.startup(**STARTUP_CFG)(echo_server_startup)
    async with session.client() as client:
        yield client
    await session.close()


def assert_request_equals(req_1, req_2):
    assert req_1.method == req_2.method
    assert req_1.url == req_2.url
    assert req_1.data == req_2.data

    headers_1 = {key.lower(): val.lower() for key, val in req_1.headers.items()}
    headers_2 = {key.lower(): val.lower() for key, val in req_2.headers.items()}
    headers_1.pop('accept-encoding', None)
    headers_2.pop('accept-encoding', None)
    assert headers_1 == headers_2


@pytest.mark.asyncio
@pytest.mark.parametrize('httpx_req', sample_requests)
async def test_on_provider(client, httpx_req):
    response = await client.send(httpx_req)
    assert response.status_code == 200
    req_data = response.json()['req']

    returned_req = serializable_request.Request.from_dict(req_data)
    expected_req = serializable_request.Request.from_httpx_request(httpx_req)

    assert_request_equals(returned_req, expected_req)
