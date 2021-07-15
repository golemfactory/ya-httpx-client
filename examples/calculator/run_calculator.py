import asyncio

from yagna_requests.session import Session

executor_cfg = {'budget': 10, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup(
    url='http://calc',
    image_hash='78be48312b494ac182ee3dd2d8ddb9bc2059000d42366528c51f3986',
    service_cnt=3,
)
def calculator_startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")


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
        await add_many_times(client, 50, 3)

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
