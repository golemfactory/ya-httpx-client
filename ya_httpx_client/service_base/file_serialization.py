from tempfile import NamedTemporaryFile

from .service_base import AbstractServiceBase
from ..serializable_request import Response


class FileSerializationServiceBase(AbstractServiceBase):
    REQUIRED_CAPABILITIES = []
    PROVIDER_URL = 'unix:///tmp/golem.sock'

    async def run(self):
        while True:
            req, fut = self.current_req, self.current_fut = await self.queue.get()
            print(f"processing {req.url} on {self.provider_name}")
            with NamedTemporaryFile() as in_file, NamedTemporaryFile() as out_file:
                req.to_file(in_file.name)
                script = self._ctx.new_script()
                script.upload_file(in_file.name, '/golem/work/req.json')
                script.run('/bin/sh', '-c', f'python -m ya_httpx_client --url {self.PROVIDER_URL} req.json res.json')
                script.download_file('/golem/work/res.json', out_file.name)
                yield script

                res = Response.from_file(out_file.name)
                fut.set_result(res)
