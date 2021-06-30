import asyncio
from os import path

from yagna_requests import Session

executor_cfg = {'budget': 1, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup('http://calculator', '855c7b4bba2ff00005a52bf29048130e8648955b020e1735b6da7fe4')
def calculator_startup(ctx, listen_on):
    ctx.send_file('examples/calculator/calculator_server.py', path.join('/golem/work/calculator_server.py'))
    ctx.run("/usr/local/bin/gunicorn", "-b", listen_on, "calculator_server:app", "--daemon")


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
