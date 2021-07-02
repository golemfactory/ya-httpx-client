from tempfile import NamedTemporaryFile

from yapapi.services import Service
from yapapi.payload import vm

from .serializable_request import Response

PROVIDER_URL = 'unix:///tmp/golem.sock'


class ServiceBase(Service):
    @classmethod
    async def get_payload(cls):
        image_hash = cls._yhc_cluster.image_hash
        return await vm.repo(image_hash=image_hash)

    async def start(self):
        start_steps = self._yhc_cluster.start_steps
        start_steps(self._ctx, PROVIDER_URL)
        yield self._ctx.commit()
        print("STARTED")

    async def run(self):
        queue = self._yhc_cluster.request_queue
        while True:
            req, fut = await queue.get()
            print(f"processing {req.url} on {self.provider_name}")
            with NamedTemporaryFile() as in_file, NamedTemporaryFile() as out_file:
                req.to_file(in_file.name)
                self._ctx.send_file(in_file.name, '/golem/work/req.json')
                self._ctx.run('/bin/sh', '-c', f'python -m yagna_requests --url {PROVIDER_URL} req.json res.json')
                self._ctx.download_file('/golem/work/res.json', out_file.name)

                yield self._ctx.commit()

                res = Response.from_file(out_file.name)
                fut.set_result(res)
