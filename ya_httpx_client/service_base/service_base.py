from abc import ABC

from yapapi.services import Service
from yapapi.payload import vm


class AbstractServiceBase(ABC, Service):
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
        start_steps = self._yhc_cluster.start_steps  # pylint: disable=no-member
        start_steps(self._ctx, self.PROVIDER_URL)
        yield self._ctx.commit()
        print(f"STARTED ON {self.provider_name}")

    async def run(self):
        raise NotImplementedError
        yield

    def restart_failed_request(self) -> None:
        if self.current_fut is not None and not self.current_fut.done():
            self.queue.put_nowait((self.current_req, self.current_fut))
