import asyncio

from yagna_requests import Session

executor_cfg = {'budget': 1, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup('http://calc', '040e5b765dcf008d037d5b840cf8a9678641b0ddd3b4fe3226591a11')
def calculator_startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")


async def run_calculator():
    async with session.client() as client:
        for x, y in ((1, 2), (7, 8)):
            res = await client.get(f'http://calc/add/{x}/{y}')
            print(f"CALCULATED: {x} + {y} =", res.content.decode())

        #   NOTE: requests sent somewhere else work exactly as in httpx.AsyncClient()
        res = await client.get('https://www.example.org/')
        print("EXAMPLE ORG", res)

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
