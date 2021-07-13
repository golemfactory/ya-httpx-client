'''
E2E test for "all" possible requests. Test goes like this:
1. Initialize a few services with echo-like server
2. For each predefined request
    *   send it to the provider
    *   ensure response contains the original request

This tests various serialization-related methods of seriablizable_request.Request/Response
classes, in this order:
    Called when request is being sent to the provider:
        Request.from_httpx_handle_request_args
        Request.to_file
    Called on provider
        Request.from_file
        Request.as_requests_request
        Response.from_requests_response
        Response.to_file
    Called when response from the provider is processed:
        Response.from_file
    Called directly here, to compare with the original request
        Request.from_json
        Request.as_httpx_request

NOTE: there are some other methods defined on those objects and they are *not* tested here.
'''
import asyncio

import pytest

from .sample_requests import sample_requests, SAMPLE_URL
from yagna_requests import Session


EXECUTOR_CFG = {
    'budget': 1,
    'subnet_tag': 'devnet-beta.2',
}

STARTUP_CFG = {
    'url': SAMPLE_URL,
    'image_hash': '040e5b765dcf008d037d5b840cf8a9678641b0ddd3b4fe3226591a11',
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
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")


@pytest.fixture(scope='session')
async def client():
    #   TODO command arg for subnet_tag
    session = Session(EXECUTOR_CFG)
    session.startup(**STARTUP_CFG)(echo_server_startup)
    async with session.client() as client:
        yield client
    await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('src_req', sample_requests)
async def test_on_provider(client, src_req):
    response = await client.send(src_req)
    print(response)
    print(response.content.decode())
    assert True
