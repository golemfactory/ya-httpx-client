
from yapapi.services import Service
from yapapi.payload import vm


PROVIDER_SERVER_URL = 'unix:///tmp/golem.sock'


class ServiceBase(Service):
    @classmethod
    async def get_payload(cls):
        print("SERVICE DEF", cls._service_def)
        return await vm.repo(image_hash=cls._service_def['image_hash'])

    async def start(self):
        start_steps = self._service_def['start_steps']
        start_steps(self._ctx, PROVIDER_SERVER_URL)
        self._ctx.run('/bin/ls', '-l')
        yield self._ctx.commit()
        print("STARTED")

    async def run(self):
        print("RUN")
        self._ctx.send_file('sample_request.json', '/golem/work/req.json')
        self._ctx.run('/bin/sh', '-c', f'python -m yagna_requests --url {PROVIDER_SERVER_URL} req.json res.json')
        self._ctx.download_file('/golem/work/res.json', 'res.json')
        res = yield self._ctx.commit()
        from pprint import pprint
        pprint(res)
