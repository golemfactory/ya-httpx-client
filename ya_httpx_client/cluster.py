import asyncio
from typing import TYPE_CHECKING

from yapapi.payload import vm

from . import service

if TYPE_CHECKING:
    from typing import Callable, Union, SupportsInt, List, Optional
    from yapapi_service_manager import ServiceManager
    from yapapi import WorkContext
    from .network_wrapper import NetworkWrapper


class Cluster:
    '''
    Q: Here is a Cluster class, and we have a `yapapi.Cluster`. Both seem to wrap a bunch of services.
       Do we need two separate clusters for this?
    A: In the future, this Cluster and `yapapi.Cluster` and also `yapapi_service_manager.ServiceWrapper`
       should be merged into the same cluster-wrapper-thingy, but we can't do this without yapapi-side modifications.
       Currently I don't think an instance of `yapapi.Cluster` class could be used instead of this one.
    '''

    #   If True, requests will be forwarded via VPN
    #   If False, requests will be serialized
    USE_VPN = True

    def __init__(
            self,
            manager: 'ServiceManager',
            image_hash: str,
            start_steps: 'Callable[[WorkContext, str], None]',
            network_wrapper: 'NetworkWrapper'
    ):
        self.manager = manager
        self.image_hash = image_hash
        self.start_steps = start_steps
        self.network_wrapper = network_wrapper

        #   This queue is filled by YagnaTransport and emptied by Service instances
        self.request_queue: asyncio.Queue = asyncio.Queue()

        #   This is how many services we want to have running. It is set here to 0, but curretly
        #   every Cluster initialization is followed by a call to set_size, so this doesn't really matter.
        self.expected_cnt: 'Union[int, SupportsInt]' = 0

        #   Task that starts new services will be stored here (created later, because now we might not
        #   have a loop running yet)
        self._new_services_starter_task: 'Optional[asyncio.Task]' = None

        #   Each task in this lists corresponds to a single instance of yapapi_service_manager.ServiceWrapper
        #   (and thus to a single instance of a running service, assuming it already started and didn't stop)
        self._manager_tasks: 'List[asyncio.Task]' = []

    @property
    def cnt(self) -> int:
        current_manager_tasks = [task for task in self._manager_tasks if not task.done()]
        return len(current_manager_tasks)

    def start(self) -> None:
        if self._new_services_starter_task is None:
            self._new_services_starter_task = asyncio.create_task(self._start_new_services())

    def stop(self) -> None:
        for task in self._manager_tasks:
            task.cancel()
        if self._new_services_starter_task is not None:
            self._new_services_starter_task.cancel()

    def set_size(self, size: 'Union[int, Callable[[Cluster], SupportsInt]]') -> None:
        if isinstance(size, int):
            self.expected_cnt = size
        else:
            self.expected_cnt = size(self)

    async def _start_new_services(self) -> None:
        while True:
            expected_cnt = int(self.expected_cnt)
            new_tasks = [asyncio.create_task(self._manage_single_service()) for _ in range(self.cnt, expected_cnt)]
            self._manager_tasks += new_tasks
            await asyncio.sleep(1)

    async def _manage_single_service(self) -> None:
        service_wrapper = None

        while True:
            if service_wrapper is None:
                service_wrapper = await self._create_service_wrapper()

            if int(self.expected_cnt) < self.cnt:
                #   There are too many services running, (at least) one has to stop
                service_wrapper.stop()
                break

            await asyncio.sleep(1)

            if service_wrapper.status in ('pending', 'starting'):
                print(f"waiting for the service, current status: {service_wrapper.status}")
            elif service_wrapper.status == 'running':
                pass
            else:
                print(f"Replacing service on {service_wrapper.service.provider_name} - it is {service_wrapper.status}")
                service_wrapper.service.restart_failed_request()

                #   TODO: We don't stop the old service_wrapper, because it is dead either way.
                #         We can distinguish "stopped" wrappers from  "failed"  (although we don't
                #         use this distinction). Think again if this is harmless.
                service_wrapper = None

    async def _create_service_wrapper(self):
        service_cls = self._service_cls()
        capabilities = service_cls.REQUIRED_CAPABILITIES
        payload = await vm.repo(image_hash=self.image_hash, capabilities=capabilities)
        network = await self.network_wrapper.network()

        return self.manager.create_service(
            service_cls,
            run_service_params={
                'payload': payload,
                'network': network,
                'instance_params': [{
                    'start_steps': self.start_steps,
                    'request_queue': self.request_queue,
                }],
            },
        )

    def _service_cls(self):
        cls = service.VPNService if self.USE_VPN else service.FileSerializationService
        return cls
