from quart import Quart

from ya_httpx_client.serializable_request import Request, Response
from ya_httpx_client.session import Session


HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']
PROVIDER_URL = 'http://calc'
IMAGE_HASH = '1f43e06ecc4ef40084efcf57131aa6056c57b5732bef2bcb6a8cdad2'
INIT_CLUSTER_SIZE = 1

executor_cfg = {'budget': 10, 'subnet_tag': 'devnet-beta.2'}

app = Quart(__name__)


def startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")


async def init_session():
    #   NOTE: it is important to initialize the session in the quart-managed async context,
    #         so we have everything running in the same loop
    session = Session(executor_cfg)
    session.startup(
        url=PROVIDER_URL,
        image_hash=IMAGE_HASH,
        init_cluster_size=INIT_CLUSTER_SIZE,
    )(startup)
    return session


@app.while_serving
async def start_provider():
    session = await init_session()
    async with session.client() as client:
        app.yhc_client = client
        yield
    await session.close()


async def forward_request():
    req = await Request.from_quart_request()
    req.replace_mount_url(PROVIDER_URL)
    res = await app.yhc_client.send(req.as_httpx_request())
    return Response.from_httpx_response(res).as_quart_response()


@app.route('/', defaults={'path': ''}, methods=HTTP_METHODS)
@app.route('/<path:_path>', methods=HTTP_METHODS)
async def catch_all(_path):
    res = await forward_request()
    return res

if __name__ == '__main__':
    app.run()
