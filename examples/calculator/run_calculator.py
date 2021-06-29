from yagna_requests import Session
from os import path
import asyncio

executor_cfg = {'budget': 1, 'subnet_tag': 'devnet-beta.2'}
session = Session(executor_cfg)


@session.startup('http://calculator', 'd44c88b6c3d4a5f6e645a9e7f9ebab2cc171f402ef11da088c2d62e8')
def calculator_startup(ctx, listen_on):
    ctx.send_file('examples/calculator/calculator_server.py', path.join('/golem/work/calculator_server.py'))
    # ctx.send_file('process_request.py', path.join('/golem/work/process_request.py'))
    # ctx.send_file('serializable_request.py', path.join('/golem/work/serializable_request.py'))
    ctx.run("/usr/local/bin/gunicorn", "-b", listen_on, "calculator_server:app", "--daemon")


async def run_calculator():
    async with session.client() as client:
        res = await client.get('https://www.example.org/')
        print(res)
    
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
