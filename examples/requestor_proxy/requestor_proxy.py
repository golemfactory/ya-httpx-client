#!/usr/bin/env python3
import sys

from quart import Quart

from ya_httpx_client.serializable_request import Request, Response
from ya_httpx_client.session import Session

SUBNET_TAG = sys.argv[1]

#   This is the only "host" we create here, so the name could be exactly anything
PROVIDER_URL = 'http://provider_http_server'

#   Image hash and the `startup` function define the HTTP server that will be running on the provider,
#   and thus the final behaviour of our requestor proxy.
#   Here we use the same image/startup as in the other example (calculator), but any server that would work
#   in a Dockerfile should be fine.
IMAGE_HASH = '1f43e06ecc4ef40084efcf57131aa6056c57b5732bef2bcb6a8cdad2'
def startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")

#   Number of providers that will be processing requests. NOTE: providers have no shared state, so
#   numbers >1 make sense only for stateless servers.
INIT_CLUSTER_SIZE = 1

#   Golem configuration - this will be passed directly to the Golem object
#   https://handbook.golem.network/yapapi/api-reference#golem-objects
EXECUTOR_CFG = {'budget': 10, 'subnet_tag': SUBNET_TAG}


async def init_session():
    '''
    Create a Session object.
    NOTE: it is important to initialize the session in the quart-managed async context,
          because we need everything to run in the same loop
    '''
    session = Session(EXECUTOR_CFG)
    session.add_startup(
        startup,
        url=PROVIDER_URL,
        image_hash=IMAGE_HASH,
        init_cluster_size=INIT_CLUSTER_SIZE,
    )
    return session


async def forward_request():
    '''
    Quart request -> provider-based HTTP server -> Quart response
    '''
    req = await Request.from_quart_request()
    req.replace_mount_url(PROVIDER_URL)
    res = await app.yhc_client.send(req.as_httpx_request())
    return Response.from_httpx_response(res).as_quart_response()


app = Quart(__name__)

@app.while_serving
async def with_yhc_session():
    session = await init_session()
    async with session.client() as client:
        app.yhc_client = client
        yield
    await session.close()

HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

@app.route('/', defaults={'_path': ''}, methods=HTTP_METHODS)
@app.route('/<path:_path>', methods=HTTP_METHODS)
async def catch_all(_path):
    res = await forward_request()
    return res

if __name__ == '__main__':
    app.run()
