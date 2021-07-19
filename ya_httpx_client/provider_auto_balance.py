from typing import TYPE_CHECKING
from datetime import datetime
if TYPE_CHECKING:
    from ya_httpx_client.cluster import Cluster


class SimpleLoadBalancer:  # pylint: disable=too-few-public-methods
    '''
    NOTE: this implementation is only an example how such things should be done.

    Implemented logic doesn't make much sense, but I don't think it's possible to
    create a very good load balancer without any knowledge of a particular task
    it will be used for.
    '''

    MAX_PROVIDER_CNT = 5

    def __init__(self, cluster: 'Cluster'):
        self.cluster = cluster

        self.cnt, self.prev_queue_size, self.prev_queue_check_at = None, None, None

    def __int__(self):
        '''
        Returns the desirde number of providers.
        To avoid too frequent changes we recalculate the number at most once in every 10 seconds.
        '''
        now = datetime.now()
        if self.cnt is None or (now - self.prev_queue_check_at).seconds > 10:
            self.cnt = self._calculate_new_cnt()
            self.prev_queue_size = self.cluster.request_queue.qsize()
            self.prev_queue_check_at = now
        return self.cnt

    def _calculate_new_cnt(self) -> int:
        current_cnt = self.cnt
        current_queue_size = self.cluster.request_queue.qsize()

        if current_cnt is None:  # pylint: disable=no-else-return
            #   Initial value
            return 3
        elif not current_queue_size and not self.prev_queue_size:
            #   Queue is empty now and was empty before -> seems like there's not much work
            return 1
        elif self.prev_queue_size < current_queue_size:
            #   Queue grown in size -> let's add a provider (unless we already reached the limit)
            return min(self.cnt + 1, self.MAX_PROVIDER_CNT)
        else:
            return self.cnt
