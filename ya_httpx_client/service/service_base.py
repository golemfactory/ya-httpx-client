from abc import ABC

from yapapi.services import Service


class AbstractServiceBase(ABC, Service):
    '''Base class for all services. Contains common things, inheriting classes
    are expected to implement the `run` method.'''
    PROVIDER_URL = ''  # TODO this will be removed with https://github.com/golemfactory/ya-httpx-client/issues/14

    def __init__(self, *args, start_steps, request_queue, **kwargs):
        super().__init__(*args, **kwargs)

        self.start_steps = start_steps
        self.queue = request_queue

        self.current_req, self.current_fut = None, None

    async def start(self):
        async for script in super().start():
            yield script
        self.start_steps(self._ctx, self.PROVIDER_URL)
        yield self._ctx.commit()
        print(f"STARTED ON {self.provider_name}")

    async def run(self):
        raise NotImplementedError

        # method run must be a generator
        yield  # pylint: disable=unreachable

    def restart_failed_request(self) -> None:
        '''Put failed request back into request queue'''
        if self.current_fut is not None and not self.current_fut.done():
            self.queue.put_nowait((self.current_req, self.current_fut))
