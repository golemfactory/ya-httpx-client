import asyncio

from yagna_requests import Session

executor_cfg = {'budget': 10, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup('http://calc', '040e5b765dcf008d037d5b840cf8a9678641b0ddd3b4fe3226591a11', 3)
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
    pairs = [(x, 1) for x in range(0, total_request_cnt)]

    current_requests_cnt = 0
    all_requests = []

    async def run_single_request(x, y):
        await add(client, x, y)

        nonlocal current_requests_cnt
        current_requests_cnt -= 1

    while len(all_requests) < len(pairs):
        if current_requests_cnt == max_concurrent_requests:
            await asyncio.sleep(0.1)
            continue

        x, y = pairs[len(all_requests)]
        all_requests.append(asyncio.create_task(run_single_request(x, y)))
        current_requests_cnt += 1

    await asyncio.gather(*all_requests)


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
