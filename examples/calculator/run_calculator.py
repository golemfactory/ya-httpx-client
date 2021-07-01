import asyncio

from yagna_requests import Session

executor_cfg = {'budget': 1, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup('http://calc', '040e5b765dcf008d037d5b840cf8a9678641b0ddd3b4fe3226591a11', 3)
def calculator_startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")


async def add(client, x, y):
    req_url = f'http://calc/add/{x}/{y}'
    res = await client.get(req_url)
    print(f"CALCULATED: {x} + {y} =", res.content.decode())


async def run_calculator():
    async with session.client() as client:
        requests = []
        for x in range(0, 5):
            for y in range(0, 5):
                requests.append(add(client, x, y))
        await asyncio.gather(*requests)

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
