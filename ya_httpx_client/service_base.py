from tempfile import NamedTemporaryFile

from yapapi.services import Service
from yapapi.payload import vm

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
        return await vm.repo(image_hash=image_hash)

    async def start(self):
        async for script in super().start():
            yield script
        start_steps = self._yhc_cluster.start_steps  # pylint: disable=no-member
        start_steps(self._ctx, PROVIDER_URL)
        yield self._ctx.commit()
        print(f"STARTED ON {self.provider_name}")

    async def run(self):
        print("MY NETWORK", self.network)
        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            print(f"processing {req.url} on {self.provider_name}")
            with NamedTemporaryFile() as in_file, NamedTemporaryFile() as out_file:
                req.to_file(in_file.name)
                self._ctx.send_file(in_file.name, '/golem/work/req.json')
                self._ctx.run('/bin/sh', '-c', f'python -m ya_httpx_client --url {PROVIDER_URL} req.json res.json')
                self._ctx.download_file('/golem/work/res.json', out_file.name)
                yield self._ctx.commit()

                res = Response.from_file(out_file.name)
                fut.set_result(res)

    def restart_failed_request(self) -> None:
        if self.current_fut is not None and not self.current_fut.done():
            self.queue.put_nowait((self.current_req, self.current_fut))
