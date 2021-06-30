import asyncio

from yagna_requests import Session

executor_cfg = {'budget': 1, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup('http://calculator', '040e5b765dcf008d037d5b840cf8a9678641b0ddd3b4fe3226591a11')
def calculator_startup(ctx, listen_on):
    ctx.run("/usr/local/bin/gunicorn", "--chdir", "/golem/run", "-b", listen_on, "calculator_server:app", "--daemon")


async def run_calculator():
    async with session.client() as client:
        res = await client.get('https://www.example.org/')
        print("EXAMPLE ORG", res)

        from yagna_requests.serializable_request import Request
        req = Request.from_file('sample_request.json')
        res = await session.send('http://calculator', req)
        print("SAMPLE REQUEST", res.status, res.data)

        req = Request.from_file('sample_request.json')
        res = await session.send('http://calculator', req)
        print("SAMPLE REQUEST 2", res.status, res.data)

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
