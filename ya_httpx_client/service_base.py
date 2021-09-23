from tempfile import NamedTemporaryFile

import aiohttp

from yapapi.services import Service
from yapapi.payload import vm
import shlex

from .serializable_request import Response

PROVIDER_URL = 'unix:///tmp/golem.sock'


class ServiceBase(Service):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.queue = self._yhc_cluster.request_queue  # pylint: disable=no-member

        self.current_req, self.current_fut = None, None

    @classmethod
    async def get_payload(cls):
        image_hash = cls._yhc_cluster.image_hash  # pylint: disable=no-member
        return await vm.repo(image_hash=image_hash, capabilities=[vm.VM_CAPS_VPN])

    async def start(self):
        async for script in super().start():
            yield script
        # start_steps = self._yhc_cluster.start_steps  # pylint: disable=no-member
        # start_steps(self._ctx, PROVIDER_URL)
        # yield self._ctx.commit()
        s = self._ctx.new_script()
        s.run("/docker-entrypoint.sh")
        s.run("/bin/chmod", "a+x", "/")
        msg = f"Hello from inside Golem!\n... running on {self.provider_name}"
        s.run(
            "/bin/sh",
            "-c",
            f"echo {shlex.quote(msg)} > /usr/share/nginx/html/index.html",
        )
        s.run("/usr/sbin/nginx"),
        yield s
        print(f"STARTED ON {self.provider_name}")

    async def run(self):
        print("MY NETWORK", self.network)
        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            res_str = await self.handle_request('/')
            res = Response(200, res_str.encode(), {})
            fut.set_result(res)
            # print(f"processing {req.url} on {self.provider_name}")
            # with NamedTemporaryFile() as in_file, NamedTemporaryFile() as out_file:
            #     req.to_file(in_file.name)
            #     self._ctx.send_file(in_file.name, '/golem/work/req.json')
            #     self._ctx.run('/bin/sh', '-c', f'python -m ya_httpx_client --url {PROVIDER_URL} req.json res.json')
            #     self._ctx.download_file('/golem/work/res.json', out_file.name)
            #     yield self._ctx.commit()

            #     res = Response.from_file(out_file.name)
            #     fut.set_result(res)

        #   We never get here, so nothing is yielded, but run is required to be a generator
        yield

    def restart_failed_request(self) -> None:
        if self.current_fut is not None and not self.current_fut.done():
            self.queue.put_nowait((self.current_req, self.current_fut))

    async def handle_request(self, query_string: str):
        """
        handle the request coming from the local HTTP server
        by passing it to the instance through the VPN
        """
        instance_ws = self.network_node.get_websocket_uri(80)
        app_key = self.cluster._engine._api_config.app_key

        ws_session = aiohttp.ClientSession()
        async with ws_session.ws_connect(
            instance_ws, headers={"Authorization": f"Bearer {app_key}"}
        ) as ws:
            await ws.send_str(f"GET {query_string} HTTP/1.0\n\n")
            headers = await ws.__anext__()
            content = await ws.__anext__()
            data: bytes = content.data

            response_text = data.decode("utf-8")

        await ws_session.close()
        return response_text
