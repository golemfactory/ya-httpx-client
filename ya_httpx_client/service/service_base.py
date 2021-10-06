from abc import ABC
from typing import TYPE_CHECKING

from yapapi.services import Service
from yapapi.script.command import Run

if TYPE_CHECKING:
    import asyncio
    from typing import Tuple, Optional
    from ya_httpx_client.serializable_request import Request


class AbstractServiceBase(ABC, Service):
    '''Base class for all services. Contains common things, inheriting classes
    are expected to implement the `run` method.'''

    def __init__(self, *args, entrypoint: 'Tuple[str, ...]', request_queue: 'asyncio.Queue', **kwargs):
        super().__init__(*args, **kwargs)

        self.entrypoint: 'Tuple[str, ...]' = entrypoint
        self.queue: 'asyncio.Queue' = request_queue

        self.current_req: 'Optional[Request]' = None
        self.current_fut: 'Optional[asyncio.Future]' = None

    async def start(self):
        async for script in super().start():
            yield script

        if self.entrypoint:
            script = self._ctx.new_script()
            script.add(Run(*self.entrypoint))
            yield script

        print(f"STARTED ON {self.provider_name}")

    async def run(self):
        raise NotImplementedError

        # method run must be a generator
        yield  # pylint: disable=unreachable

    def restart_failed_request(self) -> None:
        '''Put failed request back into request queue'''
        if self.current_fut is not None and not self.current_fut.done():
            self.queue.put_nowait((self.current_req, self.current_fut))
