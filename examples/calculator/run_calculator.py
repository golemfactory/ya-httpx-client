import asyncio

from ya_httpx_client.session import Session


executor_cfg = {'budget': 10, 'subnet_tag': 'devnet-beta'}
session = Session(executor_cfg)

CLUSTER_SIZE = 3
session.add_url(
    url='http://calc',
    image_hash='3bf3667fd14ed87881e7e868f551fac0e4c15fe202e68203b384af98',
    entrypoint=(
        "/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", "0.0.0.0:80", "calculator_server:app", "--daemon",
    ),
    init_cluster_size=CLUSTER_SIZE,
)


async def add(client, x, y):
    req_url = f'http://calc/add/{x}/{y}'
    res = await client.get(req_url)
    print(f"CALCULATED: {x} + {y} =", res.content.decode())


async def add_many_times(client, total_request_cnt, max_concurrent_requests):
    '''
    total_request_cnt
        Number of requests (additions) to be performed.
    max_concurrent_requests
        How many requests could be performed at the same time.
        Lower than the number of providers working -> we'll have some idle provider(s) all the time
        Much higher than the number of providers working -> requests that failed & caused provider recycling
        will be performed much later than they could/should be (they go to the end of the queue)
    '''
    add_args_queue = asyncio.Queue()
    for x in range(total_request_cnt):
        add_args_queue.put_nowait((x, 1))

    async def add_from_queue():
        while not add_args_queue.empty():
            x, y = add_args_queue.get_nowait()
            await add(client, x, y)

    tasks = [asyncio.create_task(add_from_queue()) for _ in range(max_concurrent_requests)]
    await asyncio.gather(*tasks)


async def run_calculator():
    async with session.client() as client:
        await add_many_times(client, 50, CLUSTER_SIZE + 3)

    await session.close()


def main():
    try:
        loop = asyncio.get_event_loop()
        run_calculator_task = loop.create_task(run_calculator())
        loop.run_until_complete(run_calculator_task)
    except KeyboardInterrupt:
        shutdown = loop.create_task(session.close())
        loop.run_until_complete(shutdown)
        run_calculator_task.cancel()


if __name__ == '__main__':
    main()
